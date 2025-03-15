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
from mica.utils import find_config_files, save_file, replace_args_in_string, logger, load_func_info_from_str, \
    short_uuid


class InvalidBot(Exception):
    """Exception that can be raised when bot file is not valid."""


class Bot(object):
    """
    The Bot class is a single bot. It can handle a conversation based on the flow information.
    """
    def __init__(self,
                 name: Optional[Text] = None,
                 config: Optional[ModelConfig] = None,
                 tracker_store: Optional[TrackerStore] = None,
                 agents: Optional[Dict[Text, Agent]] = None,
                 scheduler: Optional[Any] = None,
                 entrypoint: Optional[Agent] = None,
                 tools: Optional[Any] = None
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
        self._func_args_config = {name: {} for name in self.tools.functions.keys()} or {}
        self._global_args = list(chain.from_iterable(
            a.contains_args() or [] for a in agents.values() if isinstance(a, EnsembleAgent)
        ))

    @classmethod
    def from_json(cls,
                  name: Optional[Text] = None,
                  data: Optional[Any] = None,
                  config: Optional[Any] = None,
                  tool_code: Optional[Text] = None):
        name = name or short_uuid(10)
        config = config or {}

        # get schedule method
        from mica.processor import DispatcherProcessor, PriorityProcessor
        scheduler_create = {
            "priority": PriorityProcessor.create,
            "dispatcher": DispatcherProcessor.create
        }
        scheduler = scheduler_create.get(data.get("main").get("steps")[0].get("schedule") or "priority")()
        entrypoint = Main.create("main", **data["main"])
        data.pop("main")

        if config.get('server') is not None:
            config['server'] = config['server'] + "/rpc/rasa/message" \
                if "openai" not in config["server"] else config["server"]
        llm_model = OpenAIModel.create(config)

        # create agent objs
        create_agents = {
            "llm agent": LLMAgent.create,
            "ensemble agent": EnsembleAgent.create,
            "flow agent": FlowAgent.create,
            "function": Function.create,
            "kb agent": KBAgent.create
        }
        agents = {name: create_agents[value.get('type')](name=name, **value, **config, llm_model=llm_model)
                  for name, value in data.items()
                  if value.get('type') is not None}

        for name, agent in list(agents.items()):
            if isinstance(agent, EnsembleAgent):
                if agent.exit_agent is not None:
                    if isinstance(agent.exit_agent, Text):
                        if agent.exit_agent == "default":
                            exit_agent = DefaultExitAgent.create(name=f"DefaultExitAgent_{agent.name}")
                            agents[exit_agent.name] = exit_agent
                        else:
                            exit_agent = agents.get(agent.exit_agent)
                        if exit_agent is None:
                            raise ValueError(f"{name} fail to initialize: Exit agent {agent.exit_agent} not found")
                        agent.exit_agent = exit_agent
                    elif isinstance(agent.exit_agent, Dict):
                        exit_agent = DefaultExitAgent.create(name= f"ExitAgent_{agent.name}",
                                                             prompt=agent.exit_agent.get('policy'),
                                                             llm_model=llm_model)
                        agents[exit_agent.name] = exit_agent

                        agent.exit_agent = exit_agent

            if isinstance(agent, (FlowAgent, EnsembleAgent)):
                if agent.fallback is not None:
                    if isinstance(agent.fallback, Text):
                        if agent.fallback == 'default':
                            fallback_agent = DefaultFallbackAgent.create(name=f"DefaultFallbackAgent_{agent.name}")
                            agents[fallback_agent.name] = fallback_agent
                        else:
                            fallback_agent = agents.get(agent.fallback)
                        if fallback_agent is None:
                            raise ValueError(f"{name} fail to initialize: Fallback {agent.fallback} not found")
                        agent.fallback = fallback_agent
                    elif isinstance(agent.fallback, Dict):
                        fallback_agent = DefaultFallbackAgent.create(
                            name=f"FallbackAgent_{agent.name}",
                            prompt=agent.fallback.get('policy'),
                            llm_model=llm_model)
                        agents[fallback_agent.name] = fallback_agent
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

            func_info = load_func_info_from_str(tool_code)
            # for func in func_info:
            #     func_obj = Function.create(**func)
            #     agents[(type(func_obj), func_obj.name)] = func_obj

        tracker_store = InMemoryTrackerStore.create()
        logger.debug(f"here are all the registered agents: {agents}")
        return cls(name,
                   tracker_store=tracker_store,
                   agents=agents,
                   config=config,
                   scheduler=scheduler,
                   entrypoint=entrypoint,
                   tools=tools)

    # TODO: logic about the stop sign of this turn
    async def handle_message(self,
                             user_id: Text,
                             message: Any,
                             channel: ChatChannel = None):
        tracker = self.tracker_store.get_or_create_tracker(user_id,
                                                           args=copy.deepcopy(self._args_config),
                                                           functions=copy.deepcopy(self._func_args_config),
                                                           global_args=self._global_args)
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
            "bot_name": self.name
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

