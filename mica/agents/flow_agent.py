import copy
import json
import traceback
from typing import Optional, Dict, Text, Any, List, Union, Tuple

from mica import event
from mica.agents.agent import Agent
from mica.agents.default import DefaultFallbackAgent
from mica.agents.steps.call import Call
from mica.agents.steps.condition import If, ElseIf, Else
from mica.agents.steps.label import Label
from mica.agents.steps.next import Next
from mica.agents.steps.step_loader import StepLoader
from mica.agents.steps.subflow import Subflow
from mica.agents.steps.termination import Return
from mica.agents.steps.user import User
from mica.agents.llm_agent import LLMAgent
from mica.constants import MAIN_FLOW
from mica.event import CurrentAgent, BotUtter, AgentFail, AgentComplete, SetSlot, UserInput, Event
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker, FlowInfo
from mica.utils import logger, safe_json_loads


class NameRepeatError(Exception):
    pass


class FlowAgent(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 subflows: Optional[Dict[Text, Subflow]] = None,
                 main_flow_name: Optional[Text] = None,
                 args: Optional[List[Any]] = None,
                 llm_model: Optional[Any] = None,
                 fallback: Optional[Any] = None
                 ):
        self.llm_model = llm_model or OpenAIModel.create(config)
        self.subflows = subflows
        self.args = args
        self.labels = self._find_all_labels(subflows)
        self.main_flow_name = main_flow_name
        self.fallback = fallback or DefaultFallbackAgent.create(config=config, llm_model=llm_model)
        super().__init__(name, description)

    @classmethod
    def from_dict(cls, data, **kwargs):
        subflows = {}
        subflow_steps = []

        main_flow_name = None
        for step in data:
            if isinstance(step, str) and step == "end":
                subflow_obj = StepLoader.create(subflow_steps, **kwargs)
                subflow_label = subflow_obj.label
                if subflows.get(subflow_label) is not None:
                    raise NameRepeatError()

                if main_flow_name is None:
                    main_flow_name = subflow_label
                subflows[subflow_label] = subflow_obj
                subflow_steps = []
                continue
            # if isinstance(step, dict) and step.get("begin") is not None:
            #     subflow_label = step["begin"]
            subflow_steps.append(step)

        # when there's only one flow, no need to write begin/end
        if len(subflow_steps) > 0 and len(subflows) == 0:
            subflow_obj = StepLoader.create(subflow_steps, **kwargs)
            main_flow_name = subflow_obj.label
            subflows[main_flow_name] = subflow_obj

        return subflows, main_flow_name

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               description: Optional[Text] = None,
               steps: Optional[List] = None,
               args: Optional[List[Any]] = None,
               config: Optional[Any] = None,
               llm_model: Optional[Any] = None,
               **kwargs):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")
        steps, main_flow_name = cls.from_dict(steps, config=config, root_agent_name=name, llm_model=llm_model)
        return cls(name=name,
                   config=config,
                   description=description,
                   subflows=steps,
                   main_flow_name=main_flow_name,
                   args=args,
                   llm_model=llm_model)

    @staticmethod
    def _find_all_labels(subflows: Dict) -> Dict:
        """
        get a mapping from label's name to the path
        """

        def recur_search(steps, label_path=None, result=None) -> Dict:
            if label_path is None:
                label_path = []
            if result is None:
                result = {}

            for s in steps:
                curr_path = label_path + [id(s)]
                if isinstance(s, Label):
                    result[s.name] = curr_path
                if isinstance(s, (If, ElseIf, Else)):
                    recur_search(s.then, curr_path, result)

            return result

        labels = {}
        for subflow_name, subflow in subflows.items():
            labels[subflow_name] = [subflow_name, id(subflow.steps[0])]
            labels_in_subflow = recur_search(subflow.steps)
            for label_name, path in labels_in_subflow.items():
                labels[label_name] = [subflow_name] + path

        return labels

    def __repr__(self):
        description = self.description.replace('\n', ' ')
        return f"Flow_agent(name={self.name}, description={description}, fallback={self.fallback})"

    def contains_args(self):
        return self.args

    async def run(self, tracker: Tracker,
                  agents: Optional[Dict[Text, Agent]] = None,
                  current_nodes=None,
                  **kwargs):
        info = tracker.get_or_create_flow_agent(self.name)

        # extract any args from the latest message
        if not info.has_extract_args_after_latest_user_message(tracker.latest_message):
            agent_exception = await self.get_message_args(tracker, agents)
            if agent_exception is not None:
                if self.fallback is None:
                    return False, agent_exception
                _, fallback_response = await self.fallback.run(tracker)
                for evt in fallback_response:
                    evt.provider = self.name
                return False, agent_exception + fallback_response

        if info.is_stack_empty():
            subflow = self.subflows[self.main_flow_name]
            exec_path = [self.main_flow_name,
                         id(subflow.steps[0]) if not isinstance(subflow.steps[0], User)
                         else id(subflow.steps[1])]
            info.push(exec_path)
        else:
            exec_path = info.peek()

        # find the step that this time will execute by path and then run()
        curr_subflow = exec_path[0]
        curr_step = self.get_step_from_path(self.subflows[curr_subflow].steps, exec_path[1:])
        logger.debug("Current step in flow agent %s: %s", self.name, curr_step)
        state, result = await curr_step.run(tracker, info, agents=agents, **kwargs)

        # find next step by the result
        complete = self.find_next_step(info, previous_step_state=state)

        is_end = info.is_listen

        if complete is not None:
            if isinstance(complete, Event):
                result.append(complete)
            tracker.remove_flow_agent(self.name)
        return is_end, result

    def get_step_from_path(self, steps, previous_path, depth=0):
        all_steps = copy.copy(steps)
        while depth < len(previous_path):
            for step in all_steps:
                if id(step) == previous_path[depth]:
                    depth += 1
                    # the last time
                    if depth == len(previous_path):
                        return step
                    else:
                        all_steps = step.then
                    break
            else:
                logger.error("Didn't find this step in given path")
                return None
        return None

    def find_next_step(self,
                       flow_info: FlowInfo,
                       previous_step_state=None) -> Union[None, Event, bool]:
        if flow_info.is_stack_empty():
            return
        logger.debug("Current stack info in flow agent %s: %s", self.name, flow_info.runtime_stack)
        next_step = None
        next_step_path = None
        while next_step is None and not flow_info.is_stack_empty():
            previous_path = flow_info.pop()
            depth = 1
            all_steps = self.subflows[previous_path[0]].steps
            while depth < len(previous_path):
                for idx, step in enumerate(all_steps):
                    if id(step) == previous_path[depth]:
                        depth += 1
                        # the last time
                        if depth == len(previous_path):
                            # decide by previous type
                            if isinstance(step, (If, ElseIf, Else)):
                                if previous_step_state == "Do":
                                    next_step = step.then[0]
                                    next_step_path = previous_path + [id(next_step)]
                                    flow_info.push(previous_path)
                                    break
                            if isinstance(step, Next) and previous_step_state == "Do":
                                next_step = step.name
                                next_step_path = self.labels[step.name]
                                flow_info.clear()
                                break
                            if isinstance(step, Call) and previous_step_state == "Await":
                                next_step = step
                                next_step_path = previous_path
                                break
                            if isinstance(step, Call) and previous_step_state == "Failed":
                                break
                            if isinstance(step, Return):
                                return True

                            for next_id in range(idx + 1, len(all_steps)):
                                if isinstance(step, (If, ElseIf)) and previous_step_state == "Finished":
                                    if isinstance(all_steps[next_id], (ElseIf, Else)):
                                        continue
                                next_step = all_steps[next_id]
                                next_step_path = previous_path[:-1] + [id(next_step)]
                                break
                            if idx == len(all_steps) - 1:
                                previous_step_state = "Finished"
                        else:
                            all_steps = step.then
                        break

        if next_step is not None:
            flow_info.push(next_step_path)
            return
        flow_info.is_listen = False
        return AgentComplete(provider=self.name)

    # TODO: use LLM to get the intent of latest message
    async def get_message_args(self,
                               tracker: Tracker,
                               agents: Optional[Dict[Text, Agent]] = None
                               ) -> Union[None, List[Event]]:
        prompt = self._generate_prompt(tracker, agents)
        logger.debug("Flow agent prompt: %s", json.dumps(prompt, indent=2, ensure_ascii=False))

        llm_result = await self.llm_model.generate_message(prompts=prompt,
                                                           tracker=tracker)
        for event in llm_result:
            if isinstance(event, AgentFail):
                return llm_result
            if isinstance(event, BotUtter):
                response = safe_json_loads(event.text)
                data = response.get("data")
                status = response.get("status")

                if data is not None:
                    for name, value in data.items():
                        tracker.set_arg(self.name, name, value)
                if status is not None and status == "quit":
                    return [AgentFail(provider=self.name)]
        return

    def _generate_prompt(self,
                         tracker: Tracker,
                         agents: Optional[Dict[Text, Agent]] = None
                         ) -> List[Dict[Any, Any]]:
        all_agents = list(tracker.args.keys())
        all_agents.remove(self.name)
        for agent_name in self._all_related_agent(agents):
            if agent_name in all_agents:
                all_agents.remove(agent_name)
        # all_agents.remove("meta")
        agent_names = ", ".join(all_agents)

        sys_content = f"You are a intelligent chatbot. Your name is: {self.name}. " \
                      f"Here's your task: {self.description}. "
        if self._contains_user_node():
            sys_content += f"Your task is to collect user's information " \
                           f"according to the conversation I provided."
        sys_content += f"Please reply in JSON format. There are several response scenarios: \n" \
                       f"- ONLY when the user’s intent is related to one of the following: " \
                       f"{agent_names}, or when the user clearly indicates they want to exit or not continue, " \
                       f"output: {{\"status\": \"quit\"}}\n" \
                       f"Example:\n" \
                       f"User: \"{self.name}\"\n" \
                       f"Output: {{}}"
        if self._contains_user_node() and self.args is not None and len(self.args) > 0:
            args = ", ".join(self.args)
            sys_content += f"- If the user mentions the following data in the conversation: {args}, " \
                           f"extract them. Example: {{\"data\": {{\"{self.args[0]}\": xxx, ...}}}}\n"
        sys_content += "- Otherwise, output: {}"

        user_content = f"User: {tracker.latest_message.text}\n"
        prompt = [{
            "role": "system",
            "content": sys_content}, {
            "role": "user",
            "content": user_content
        }]
        return prompt

    def _all_related_agent(self, bot_agents: Optional[Dict[Text, Agent]] = None) -> List[Text]:
        agents = []

        def traverse(steps):
            for step in steps:
                if isinstance(step, (If, ElseIf, Else)):
                    traverse(step.then)
                if isinstance(step, Call):
                    agents.append(step.name)

        for subflow_name, subflow in self.subflows.items():
            traverse(subflow.steps)
        return agents

    def _contains_user_node(self) -> bool:
        def traverse(steps):
            for step in steps:
                if isinstance(step, User):
                    return True
                if isinstance(step, (If, ElseIf, Else)) and traverse(step.then):
                    return True
            return False

        for subflow_name, subflow in self.subflows.items():
            if traverse(subflow.steps):
                return True
        return False
