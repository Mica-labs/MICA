import copy
import json
import os.path
import subprocess
import time
from itertools import chain
from pathlib import Path
from typing import Optional, Text, List, Union, Dict, Any, Tuple

from mica import utils
from mica.agents.agent import Agent, Main
from mica.agents.default import DefaultExitAgent, DefaultFallbackAgent
from mica.agents.ensemble_agent import EnsembleAgent
from mica.agents.exception_agent import ExceptionAgent
from mica.agents.flow_agent import FlowAgent
from mica.agents.functions import Function
from mica.agents.llm_agent import LLMAgent
from mica.agents.kb_agent import KBAgent
from mica.channel import ChatChannel
from mica.event import UserInput, BotUtter, FollowUpAgent, AgentComplete, AgentFail, CurrentAgent
from mica.exec_tool import SafePythonExecutor
from mica.llm.openai_model import OpenAIModel
from mica.model_config import ModelConfig
from mica.tracker_store import TrackerStore, InMemoryTrackerStore
from mica.utils import find_config_files, save_file, replace_args_in_string, logger, short_uuid


class InvalidBot(Exception):
    """Exception that can be raised when bot file is not valid."""


class Bot(object):
    """
    The Bot class is a single bot. It can handle a conversation based on the flow information.
    """
    def __init__(self,
                 name: Optional[Text] = None,
                 config: Optional[Dict] = None,
                 tracker_store: Optional[TrackerStore] = None,
                 agents: Optional[Dict[Text, Agent]] = None,
                 scheduler: Optional[Any] = None,
                 entrypoint: Optional[Agent] = None,
                 tools: Optional[Any] = None,
                 connector: Optional[Any] = None
                 ):
        self.name = name
        self.config = config
        self.tracker_store = tracker_store
        self.agents = agents
        self.scheduler = scheduler
        self.entrypoint = entrypoint
        self._args_config = self._find_all_args(agents)
        self.count = 0
        self.sum_rsp_time = 0
        self.tools = tools
        self.connector = connector or {}
        self._func_args_config = {name: {} for name in self.tools.functions.keys()} or {}

    @classmethod
    def from_json(cls,
                  name: Optional[Text] = None,
                  data: Optional[Any] = None,
                  llm_config: Optional[Any] = None,
                  tool_code: Optional[Text] = None,
                  connector: Optional[Any] = None):
        name = name or short_uuid(10)
        config = llm_config or {}

        # # get schedule method
        # from mica.processor import DispatcherProcessor, PriorityProcessor
        # scheduler_create = {
        #     "priority": PriorityProcessor.create,
        #     "dispatcher": DispatcherProcessor.create
        # }
        # scheduler = scheduler_create.get(data.get("main").get("steps")[0].get("schedule") or "priority")()
        # entrypoint = Main.create("main", **data["main"])
        # data.pop("main")
        from mica.processor import DispatcherProcessor, PriorityProcessor
        scheduler = PriorityProcessor.create()

        llm_model = OpenAIModel.create(config)

        # create agent objs
        create_agents = {
            "llm agent": LLMAgent.create,
            "ensemble agent": EnsembleAgent.create,
            "flow agent": FlowAgent.create,
            "kb agent": KBAgent.create
        }
        agents = {n: create_agents[value.get('type')](name=n, **value, **config, llm_model=llm_model)
                  for n, value in data.items()
                  if value.get('type') is not None}

        for _, agent in list(agents.items()):
            if isinstance(agent, EnsembleAgent):
                if agent.exit_agent is not None:
                    if agent.exit_agent == "default":
                        exit_agent = DefaultExitAgent.create(name=f"DefaultExitAgent_{agent.name}")
                        agents[exit_agent.name] = exit_agent
                    else:
                        exit_agent = agents.get(agent.exit_agent) or \
                                     DefaultExitAgent.create(name= f"ExitAgent_{agent.name}",
                                                             prompt=agent.exit_agent,
                                                             llm_model=llm_model)

                    agent.exit_agent = exit_agent

            if isinstance(agent, (FlowAgent, EnsembleAgent)):
                if agent.fallback is not None:
                    if agent.fallback == 'default':
                        fallback_agent = DefaultFallbackAgent.create(name=f"DefaultFallbackAgent_{agent.name}")
                        agents[fallback_agent.name] = fallback_agent
                    else:
                        fallback_agent = agents.get(agent.fallback) or \
                                         DefaultFallbackAgent.create(
                                             name=f"FallbackAgent_{agent.name}",
                                             prompt=agent.fallback,
                                             llm_model=llm_model)
                    agent.fallback = fallback_agent

        # load function tools code into memory
        tools = None
        if tool_code is not None:
            tools = SafePythonExecutor()
            load_rst = tools.load_script(tool_code)
            if load_rst['status'] == 'success':
                logger.info('Succeed in loading python script.')
            else:
                logger.error(f"Failed in loading python script. Error: {load_rst['error']}")
                logger.error(f"Traceback: {load_rst['traceback']}")
                raise InvalidBot('Not a valid chatbot')

        tracker_store = InMemoryTrackerStore.create()
        logger.debug(f"here are all the registered agents: {agents}")

        if 'main' not in agents:
            logger.error("The 'main' agent is missing")
            raise InvalidBot("A 'main' agent is required.")

        entrypoint = agents['main']

        return cls(name,
                   tracker_store=tracker_store,
                   agents=agents,
                   config=config,
                   scheduler=scheduler,
                   entrypoint=entrypoint,
                   tools=tools,
                   connector=connector)

    # TODO: logic about the stop sign of this turn
    async def handle_message(self,
                             user_id: Text,
                             message: Any,
                             channel: ChatChannel = None):
        tracker = self.tracker_store.get_or_create_tracker(user_id,
                                                           args=copy.deepcopy(self._args_config),
                                                           functions=copy.deepcopy(self._func_args_config))
        user_event = UserInput(text=message, metadata=channel)
        tracker.update(user_event)
        tracker.latest_message = user_event
        start = time.time()
        response = await self.scheduler.predict_next_action(user_id, tracker, self)
        end = time.time()
        print("####response time:", end-start)
        self.count += 1
        self.sum_rsp_time += end-start
        print("####avg time:", self.sum_rsp_time / self.count)
        return response

    def _find_all_args(self, agents: Dict[Text, Agent]):
        all_args = {
            "sender": "",
            "bot_name": self.name,
            "__mapping__": {}
        }
        if agents is None:
            return all_args
        for name, agent in agents.items():
            all_args[name] = {}
            args = agent.contains_args()
            if args is None:
                continue
            for arg in args:
                if isinstance(arg, Dict):
                    arg_name = list(arg.keys())[0]
                    all_args[name][arg_name] = None
                else:
                    all_args[name][arg] = None
            if isinstance(agent, EnsembleAgent):
                mapping = agent.mapping
                for revoke_agent_name, arg_info in mapping.items():
                    all_args['__mapping__'].setdefault(revoke_agent_name, {})
                    for arg_name, ensemble_arg_name in arg_info.items():
                        tmp = {
                            'type': "ref" if ensemble_arg_name.startswith("ref ") else "value",
                            'agent': name,
                            'arg': ensemble_arg_name[4:] if ensemble_arg_name.startswith("ref ") else ensemble_arg_name
                        }
                        all_args['__mapping__'][revoke_agent_name][arg_name] = tmp

        return all_args

    # TODO: instead of returning the first one, find the parent.
    def _find_meta_agent(self):
        if self.agents is None:
            return None
        ensembles = []
        for name, agent in self.agents.items():
            if isinstance(agent, EnsembleAgent):
                ensembles.append(agent)

        # if no ensemble agent, use the first agent
        if len(ensembles) == 0:
            return list(self.agents.values())[0]

        return ensembles[0]

