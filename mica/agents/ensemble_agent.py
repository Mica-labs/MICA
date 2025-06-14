import json
from typing import Optional, Dict, Text, Any, List, Set, Tuple, Union

from mica.agents.agent import Agent
from mica.agents.default import DefaultFallbackAgent, DefaultExitAgent
from mica.agents.flow_agent import FlowAgent
from mica.agents.kb_agent import KBAgent
from mica.agents.llm_agent import LLMAgent
from mica.agents.steps.bot import Bot
from mica.agents.steps.step_loader import StepLoader
from mica.agents.steps.user import User
from mica.event import FollowUpAgent, BotUtter, AgentFail, AgentComplete
from mica.llm.openai_model import OpenAIModel
from mica.model_config import ModelConfig
from mica.tracker import Tracker
from mica.utils import number_to_uppercase_letter, logger


class EnsembleAgent(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 contains: Optional[List[Any]] = None,
                 steps: Optional[Any] = None,
                 args: Optional[Any] = None,
                 llm_model: Optional[Any] = None,
                 fallback: Optional[Any] = None,
                 exit_agent: Optional[Any] = None,
                 mapping: Optional[Dict] = None,
                 ):
        self.llm_model = llm_model or OpenAIModel.create(config)
        self.contains = contains
        self.steps = steps
        self.args = args
        self.fallback = fallback
        self.exit_agent = exit_agent
        self.mapping = mapping
        super().__init__(name, description)

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               description: Optional[Text] = None,
               config: Optional[Dict[Text, Any]] = None,
               contains: Optional[List[Any]] = None,
               steps: Optional[Any] = None,
               args: Optional[Any] = None,
               llm_model: Optional[Any] = None,
               fallback: Optional[Any] = None,
               exit: Optional[Any] = None,
               **kwargs):

        if steps is not None:
            steps = [StepLoader.create(step, root_agent_name=name) for step in steps]
        exit_agent = exit
        mapping_relationship, processed_contains = cls.unwrap_contains_args(contains)
        return cls(name,
                   description,
                   config,
                   processed_contains,
                   steps,
                   args,
                   llm_model,
                   fallback,
                   exit_agent,
                   mapping_relationship)

    def __repr__(self):
        return f"Ensemble_agent(name={self.name}, description={self.description}, fallback={self.fallback}," \
               f" exit={self.exit_agent})"

    def contains_args(self):
        return self.args

    # TODO: fallback and exit execute logic need improve later. change the event storage in tracker later
    async def run(self,
                  model_config: Optional[ModelConfig] = None,
                  tracker: Optional[Tracker] = None,
                  agents: Optional[Dict[Text, Agent]] = None,
                  **kwargs
                  ):
        result = []
        # when the conversation start, first execute self.step
        if len(tracker.events) == 1 and self.steps is not None and not isinstance(self.steps[0], User):
            is_end = True
            for step in self.steps:
                step_flag, step_result = await step.run(tracker, agents=agents, **kwargs)
                result.extend(step_result)
                if step_flag in ["Await"]:
                    is_end = False
            if tracker.latest_message.text == '/init':
                return is_end, result + [tracker.peek_agent()]

        if tracker.latest_message.text == '/init':
            return True, result + [tracker.peek_agent()]

        # call rag_agent first
        rag_result = None
        if tracker.events[-1] == tracker.latest_message:
            for agent in agents.values():
                if isinstance(agent, KBAgent):
                    _, [rag_result] = await agent.run(tracker)
                    logger.debug(f"This is the result of Rag agent: {rag_result}")
                    rag_result = rag_result.metadata
                    break

        is_end = False
        agent_result = result
        next_agent = await self._select_followup_agent(tracker, agents, rag_result)
        if next_agent is not None:
            if next_agent in self.contains:
                agent_result.append(FollowUpAgent(provider=self.name, next_agent=next_agent))
                return is_end, agent_result
            elif isinstance(next_agent, str):
                agent_result.append(BotUtter(text=next_agent, provider=self.name))
                return True, agent_result

        # if agent fail to answer and there are no response from the user input
        if tracker.events[-1] == tracker.latest_message:
            if self.fallback is not None:
                _, fallback_response = await self.fallback.run(tracker)
                agent_result.extend(fallback_response)
            is_end = True
            return is_end, agent_result

        if self.exit_agent is not None and len(agent_result) == 0:
            _, exit_response = await self.exit_agent.run(tracker)
            agent_result.extend(exit_response)
        return True, agent_result

    def _is_agent_found(self, event):
        llm_result_name = event.text.strip()
        if "None" in llm_result_name:
            return None
        # llm result match the agent name, directly return llm result
        if llm_result_name in self.contains:
            return llm_result_name
        for agent in self.contains:
            if agent in llm_result_name:
                return agent
        return None

    def _generate_agent_prompt(self,
                               tracker: Tracker,
                               agents: Dict[Text, Any],
                               candidates: Set[Text],
                               rag_result: Optional[Any] = None):
        valid_states_info = ""
        for agent_name, args in tracker.args.items():
            if agent_name not in candidates \
                    or agent_name in ["sender", "bot_name", "__mapping__", "main"]:
                continue
            if args is not None and len(args) > 0:
                valid_states_info += f"{agent_name}: ("
                for arg_name, arg_value in args.items():
                    valid_states_info += f"{arg_name}: {arg_value}, "
                valid_states_info += ")\n"

        agent_info = ""
        for idx, name in enumerate(candidates):
            if isinstance(agents[name], KBAgent):
                continue
            agent = agents.get(name)
            if agent is None:
                logger.error(f"There exists an agent {name} claimed in ensemble agent,"
                             f" but not included in other places.")
                continue
            agent_info += f"- {name}: {agent.description}\n"

        system = "Your task is to select an agent to handle user requests. " \
                 "You will be provided agent information and a conversation. " \
                 "Choose an agent from the provided agents list and output its name. \n"

        if self.fallback is not None:
            fallback_info = "- If the user’s input exceeds the scope that all agents can respond to, " \
                            "output: [Fallback].\n"
            system += fallback_info

        if self.exit_agent is not None:
            exit_info = "- If the current conversation does not require the chatbot to continue responding, " \
                        "output: [Exit].\n"
            system += exit_info

        system += "- If no more response is needed, output: None.\n" \
                  "### INFORMATION:\n" \
                  f"{valid_states_info}\n" \
                  f"### AGENTS:\n" \
                  f"{agent_info}"

        rag_info = "\nHere is some potentially relevant knowledge base content. " \
                   "If you think the user’s input is related to these items, " \
                   "output: \"[FAQ].\"\n" \
                   "## KNOWLEDGE BASE:\n"

        if rag_result is not None:
            for idx, item in enumerate(rag_result.get('matches')):
                rag_info += f"{idx+1}. {item.get('content')}\n"
            rag_info += f"### SUGGEST ANSWER: {rag_result.get('answer')}\n"
            system += rag_info

        # conversation history
        history = tracker.get_history_str()
        user_content = f"### CONVERSATION:\n{history}\n"

        prompt = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
        return prompt

    def _generate_function_prompt(self):
        functions = [
            {
                "name": "generate_response",
                "description": "When the agent fail to answer user, generate an apologize response.",
                "parameters": {
                    "type": "object",
                    "properties": {"next_response": {
                        "description": "The next response of bot based on the conversation and the rule."
                    }},
                    "required": ["next_response"]
                },
            }
        ]
        return functions

    async def _select_followup_agent(self,
                                     tracker: Optional[Tracker] = None,
                                     agents: Optional[Dict[Text, Agent]] = None,
                                     rag_result: Optional[Any] = None
                                     ):
        """
        select an agent from candidates(self.contain), if there's no agent available, return None
        :param tracker:
        :param agents:
        :return:
        """
        # get available candidates from events
        agents_up_to_now = []
        for evt in reversed(tracker.events):
            if evt == tracker.latest_message:
                break
            if isinstance(evt, AgentFail) or isinstance(evt, AgentComplete):
                agents_up_to_now.append(evt.provider)
        agents_remain = set(self.contains) - set(agents_up_to_now)
        # if there is no candidate, don't need to ask llm. quit.
        if len(agents_remain) == 0 and rag_result is None:
            return None

        prompt = self._generate_agent_prompt(tracker, agents, agents_remain, rag_result)
        logger.debug("Ensemble agent prompt: \n%s", json.dumps(prompt, indent=2, ensure_ascii=False))
        llm_result = await self.llm_model.generate_message(prompt, tracker)
        # analyze llm result, generate agent result
        agent_result = []
        for event in llm_result:
            if isinstance(event, BotUtter):
                if "[FAQ]" in event.text:
                    return rag_result.get('answer')
                if "[Fallback]" in event.text:
                    return self.fallback
                if "[Exit]" in event.text:
                    return self.exit_agent
                next_agent = self._is_agent_found(event)
                return next_agent
        return None

    @staticmethod
    def unwrap_contains_args(contains: List[Any]) -> Union[Any, List[Text]]:
        contains_agents = []
        mapping = {}
        for c in contains:
            if isinstance(c, Text):
                contains_agents.append(c)
            else:
                agent_name = list(c.keys())[0]
                mapping[agent_name] = c[agent_name].get("args")
                contains_agents.append(agent_name)
        return mapping, contains_agents
