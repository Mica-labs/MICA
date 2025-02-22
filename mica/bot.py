import copy
import json
import os.path
import subprocess
import time
from pathlib import Path
from typing import Optional, Text, List, Union, Dict, Any

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

    @classmethod
    def from_path(cls, path: Union[Text, Path]):
        path = os.path.abspath(path)

        if not path or os.path.isfile(path) or not os.path.isdir(path):
            raise InvalidBot(
                "Please provide a valid path"
            )
        # bot name is the dir name
        bot_name = os.path.basename(path)

        # get all the configuration from multi files
        config_files = utils.find_config_files(path)
        flows_data = {}
        for file in config_files:
            config = utils.read_yaml_file(file)
            for item, value in config.items():
                if flows_data.get(item):
                    flows_data[item].update(value)
                else:
                    flows_data[item] = value

        # get schedule method
        from mica.processor import DispatcherProcessor, PriorityProcessor
        scheduler_create = {
            "priority": PriorityProcessor.create,
            "dispatcher": DispatcherProcessor.create
        }
        scheduler = scheduler_create.get(flows_data.get("main").get("schedule") or "priority")()
        entrypoint = flows_data.get("main").get("call")
        flows_data.pop("main")

        llm_model = OpenAIModel.create()
        agents = dict()
        if all(key not in flows_data for key in ["llm_agents", "ensemble_agents", "flow_agents"]):
            create_agents = {
                "llm_agent": LLMAgent.create,
                "ensemble_agent": EnsembleAgent.create,
                "flow_agent": FlowAgent.create,
                "function": Function.create
            }
            agents = {name: create_agents[value.get('type')](name=name, **value, llm_model=llm_model)
                      for name, value in agents.items()
                      if value.get('type') is not None}
        else:
            create_agents = {
                "llm_agents": LLMAgent.create,
                "ensemble_agents": EnsembleAgent.create,
                "flow_agents": FlowAgent.create,
                "pythons": Function.create,
                "functions": Function.create
            }
            agents = {
                name: create_agents[kind](name=name, **value, llm_model=llm_model)
                for kind, agents in flows_data.items()
                for name, value in agents.items()}

        # transfer main agent name to agent object
        entrypoint = agents.get(entrypoint)

        cls.save_custom_functions_to_local(agents)
        subprocess.call(["bash", "action/restart_server.sh"])

        tracker_store = InMemoryTrackerStore.create()

        return cls(bot_name, tracker_store=tracker_store, agents=agents, scheduler=scheduler, entrypoint=entrypoint)

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
        if all(key not in data for key in ["llm_agents", "ensemble_agents", "flow_agents"]):
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
        else:
            create_agents = {
                "llm agents": LLMAgent.create,
                "ensemble agents": EnsembleAgent.create,
                "flow agents": FlowAgent.create,
                "pythons": Function.create,
                "functions": Function.create,
                "kb agents": KBAgent.create
            }
            agents = {
                name: create_agents[kind](name=name, **value, **config, llm_model=llm_model)
                for kind, agents in data.items()
                for name, value in agents.items()}

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
                            raise ValueError(f"{name} fail to initialize: Exit agent {agent.fallback} not found")
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
            for func in func_info:
                agents[func['name']] = Function.create(**func)

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
        tracker = self.tracker_store.get_or_create_tracker(user_id, args=copy.deepcopy(self._args_config))
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

    def _find_all_args(self, agents: Dict):
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
                if isinstance(arg, dict):
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

    @classmethod
    def save_custom_functions_to_local(cls, agents):
        code_data = []
        for name, agent in agents.items():
            if isinstance(agent, Function):
                python_name, python_body = agent.save()
                if python_body is None:
                    continue
                code_data.append([python_name, python_body])
        mapping = ", ".join([f"\"{c[0]}\": {c[0]}" for c in code_data])
        append_content = "\n" \
                         "def point_to_func(func_name, **kwargs):\n" \
                         f"    func = {{{mapping}}}\n" \
                         f"    return func.get(func_name)(**kwargs)\n"
        code = "\n\n".join([c[1] for c in code_data])
        code += append_content
        save_file("action/custom_functions.py", code)

