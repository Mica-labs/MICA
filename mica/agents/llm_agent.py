import json
import re
from typing import Optional, Dict, Text, Any, List, Union

import requests

from mica.agents.agent import Agent
from mica.event import BotUtter, SetSlot, AgentFail, AgentComplete, FunctionCall
from mica.exec_tool import SafePythonExecutor
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker
from mica.utils import arg_format, logger, safe_json_loads


class LLMAgent(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 prompt: Optional[Text] = None,
                 args: Optional[List[Any]] = None,
                 uses: Optional[List[Any]] = None,
                 llm_model: Optional[Any] = None,
                 **kwargs
                 ):
        self.llm_model = llm_model or OpenAIModel.create(config)
        self.prompt = prompt
        self.args = args
        self.uses = uses
        super().__init__(name, description)

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               description: Optional[Text] = None,
               config: Optional[Dict[Text, Any]] = None,
               prompt: Optional[Text] = None,
               args: Optional[List[Any]] = None,
               uses: Optional[List[Text]] = None,
               llm_model: Optional[Any] = None,
               **kwargs
               ):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")
        return cls(name, description, config, prompt, args, uses, llm_model)

    def __repr__(self):
        description = self.description.replace('\n', ' ')
        return f"LLM_agent(name={self.name}, description={description})"

    async def run(self, tracker: Tracker, is_tool=False, **kwargs):
        prompt = self._generate_agent_prompt(tracker, is_tool=is_tool)
        logger.debug("LLM agent prompt: \n%s", json.dumps(prompt, indent=2, ensure_ascii=False))
        functions = self._generate_function_prompt(**kwargs)
        logger.debug("LLM agent functions prompt: \n%s", json.dumps(functions, indent=2, ensure_ascii=False))
        llm_result = await self.llm_model.generate_message(prompt,
                                                           functions=functions,
                                                           tracker=tracker,
                                                           provider=self.name)
        is_end = True
        final_result = []

        for event in llm_result:
            if isinstance(event, FunctionCall):
                tracker.set_conv_history(self.name, event.metadata)
                tools: SafePythonExecutor = kwargs.get("tools")
                if tools is None:
                    msg = f"Cannot find any functions."
                    logger.error(msg)
                    raise ValueError(msg)

                tool_rst = tools.execute_function(event.function_name, **event.args)
                logger.debug(f"Execute function: {event.function_name}, get result: {tool_rst}")
                if tool_rst['status'] == 'error':
                    is_end = True
                    return is_end, []

                if tool_rst['result'] is not None:
                    tool_rst_states = tool_rst['result']
                    if isinstance(tool_rst_states, Text):
                        final_result.append(BotUtter(tool_rst_states, provider=self.name))
                    elif isinstance(tool_rst_states, List):
                        for evt in tool_rst_states:
                            if isinstance(evt, str):
                                final_result.append(BotUtter(evt, provider=self.name))
                                continue
                            if evt.get('slot_name') is not None:
                                setslot = SetSlot.from_dict(evt)
                                slot_info = arg_format(setslot.slot_name, self.name)
                                tracker.set_arg(slot_info.get("flow_name"), slot_info.get("arg_name"), setslot.value)
                            if evt.get('text') is not None:
                                final_result.append(BotUtter.from_dict(evt))
                if tool_rst['stdout'] is not None and len(tool_rst['stdout']) > 0:
                    tracker.set_conv_history(self.name, {"role": "tool",
                                                         "tool_call_id": event.call_id,
                                                         "name": event.function_name,
                                                         "content": tool_rst['stdout']
                                                         })
                    is_end, sec_call_result = await self.run(tracker, is_tool=True, **kwargs)
                    final_result.extend(sec_call_result)

            if isinstance(event, SetSlot):
                tracker.set_arg(self.name, event.slot_name, event.value)
            if isinstance(event, AgentFail):
                is_end = False
            if isinstance(event, BotUtter):
                try:
                    try:
                        response = json.loads(event.text)
                    except json.JSONDecodeError:
                        # Only look for JSON objects starting with '{'
                        json_starts = [m.start() for m in re.finditer(r'\{', event.text)]
                        
                        for start in json_starts:
                            stack = []
                            found_end = False
                            
                            for i, char in enumerate(event.text[start:], start):
                                if char == '{':
                                    stack.append(char)
                                elif char == '}':
                                    stack.pop()
                                    if not stack:  # Found matching closing bracket
                                        json_candidate = event.text[start:i+1]
                                        try:
                                            response = json.loads(json_candidate)
                                            found_end = True
                                            break
                                        except json.JSONDecodeError:
                                            continue  # Try next possible ending position
                            
                            if found_end:
                                break
                        else:  # No valid JSON found
                            raise json.JSONDecodeError("No valid JSON object found", event.text, 0)
                            
                except json.JSONDecodeError as e:
                    logger.error(f"JSON extraction failed: {e}. Text: {event.text}")
                    response = {
                        "bot": event.text
                    }
                if len(llm_result) == 1:
                    tracker.set_conv_history(self.name, {"role": "assistant", "content": event.text})
                data = response.get("data")
                bot_reply = response.get("bot")
                status = response.get("status")

                if data is not None:
                    for name, value in data.items():
                        tracker.set_arg(self.name, name, value)
                        final_result.append(SetSlot(name, value, self.name))
                if status is not None and status == "quit":
                    is_end = False
                    event = AgentFail(provider=self.name)
                    if bot_reply is not None:
                        final_result.append(BotUtter(bot_reply, metadata=self.name))
                elif status == "complete":
                    is_end = False
                    event = AgentComplete(provider=self.name)
                    tracker.clear_conv_history(self.name)

                    if bot_reply is not None:
                        final_result.append(BotUtter(bot_reply, metadata=self.name))
                else:
                    event = BotUtter(bot_reply, metadata=self.name)

            final_result.append(event)

        return is_end, final_result

    def contains_args(self):
        return self.args

    def _generate_agent_prompt(self, tracker: Tracker, is_tool=False):
        all_agents = list(tracker.args.keys())
        all_agents.remove(self.name)
        current_event = tracker.peek_agent()
        if current_event.metadata is not None:
            flow_name = current_event.metadata["flow"]
            if flow_name in all_agents:
                all_agents.remove(flow_name)
        agent_names = ", ".join(all_agents)

        valid_states_info = ""
        for agent_name, args in tracker.args.items():
            if agent_name in ["sender", "bot_name"]:
                continue
            if args is not None and len(args) > 0:
                valid_states_info += f"{agent_name}: ("
                for arg_name, arg_value in args.items():
                    valid_states_info += f"{arg_name}: {arg_value}, "
                valid_states_info += ")\n"

        system = f"You can talk to the user and act according to the instruction below: \n{self.prompt}\n" \
                 f"## RULES\n1. Respond STRICTLY according to the instruction above.\n" \
                 f"2. Try to clarify user's intent instead of quit directly.\n" \
                 f"3. Unless specified in the task, do not make assumptions about any information the user has not provided.\n" \
                 f"## INFORMATION\n{valid_states_info}.\n" \
                 f"## OUTPUT\n" \
                 f"1. If a user's intent is unrelated to the current conversation and instruction, for example: " \
                 f"{agent_names} or user want to quit, output: " \
                 f"{{\"bot\": \"\", \"status\": \"quit\"}}\n" \
                 "2. Based on the conversation history, once the instruction ends, directly output: " \
                 "{\"status\": \"complete\"}\n"

        if self.args is not None and len(self.args) > 0:
            args = ", ".join(self.args)
            system += f"3. If the user mentions: {args}, " \
                 f"extract them in the output. Example: {{\"data\": {{\"{self.args[0]}\": xxx if exists, ...}}, " \
                 f"\"bot\": \"your reply\", \"status\": \"running\"}}\n"
        else:
            system += f"3. Generally output: {{\"bot\": \"Your reply\", \"status\": \"running\"}}\n"
        system += "Only output JSON structure. Do not output any other content. Do not use Markdown format."

        system += f"## CONVERSATION HISTORY\n {tracker.get_history_str()}"

        prompt = [{"role": "system", "content": system}]
        history = tracker.get_or_create_agent_conv_history(self.name)
        prompt.extend(history)
        # this turn
        if not is_tool:
            latest_user = {"role": "user", "content": "(Asked something else before and have now returned here) " +
                                                      tracker.latest_message.text if self._is_interrupted(tracker) else
                                                      tracker.latest_message.text}
            prompt.append(latest_user)
            tracker.set_conv_history(self.name, latest_user)
        return prompt

    def _is_interrupted(self, tracker: Tracker) -> bool:
        if len(tracker.get_or_create_agent_conv_history(self.name)) == 0:
            return False
        last_agent_response = safe_json_loads(tracker.get_or_create_agent_conv_history(self.name)[-1].get("content")).get("bot")
        last_bot_response = ""
        for i in range(len(tracker.events)-1, -1, -1):
            if isinstance(tracker.events[i], BotUtter):
                last_bot_response = tracker.events[i].text
                break
        return last_agent_response != last_bot_response

    def _generate_function_prompt(self,
                                  tools: Optional[Any] = None,
                                  **kwargs) -> Union[List, None]:
        if self.uses is None:
            return []
        functions = []
        for function_name in self.uses:
            func = tools.get(function_name)
            if func is None:
                logger.error(
                    f"No corresponding function: {function_name} was found. "
                    f"Please check your Python code snippet.")
                return functions
            functions.append(func.function_prompt())
        return functions
