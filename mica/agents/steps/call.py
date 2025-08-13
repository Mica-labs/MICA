import json
import re
from typing import Optional, Dict, Text, List, Tuple, Any

import requests

from mica.agents.agent import Agent
from mica.agents.steps.base import Base
from mica.agents.functions import Function
from mica.event import BotUtter, CurrentAgent, SetSlot, AgentFail
from mica.exec_tool import SafePythonExecutor
from mica.tracker import Tracker, FlowInfo
from mica.utils import arg_format, replace_args_in_string, logger


class Call(Base):
    def __init__(self,
                 name: Text,
                 args: Optional[Dict] = None,
                 flow_name: Optional[Text] = None):
        self.name = name
        self.args = args
        self.flow_name = flow_name
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        name = data.get("call")
        args = {}
        flow_name = kwargs.get("root_agent_name")
        if data.get("args") is not None:
            for target, source in data.get("args").items():
                args[target] = arg_format(source, flow_name)

        return cls(name, args, flow_name)

    def __repr__(self):
        return f"Call(name={self.name}, args={self.args}, flow_name={self.flow_name})"

    # TODO: 1. call llm_agent; 2. what if the function return other event types?
    async def run(self,
                  tracker: Optional[Tracker] = None,
                  info: Optional[FlowInfo] = None,
                  **kwargs
                  ):
        from mica.agents.flow_agent import FlowAgent
        from mica.agents.llm_agent import LLMAgent
        from mica.agents.ensemble_agent import EnsembleAgent

        if info is not None:
            info.is_listen = False
        agents: Dict[Text, Agent] = kwargs.get("agents")
        if agents.get(self.name) is None:
            result = []
            tools: SafePythonExecutor = kwargs.get("tools")
            if tools is None:
                msg = f"Cannot find any functions."
                logger.error(msg)
                raise ValueError(msg)
            tool_rst = tools.execute_function(self.name, **self._get_args_value(tracker))
            logger.info(f"Agent: [{self.flow_name}] execute function: {self.name}, get result: {tool_rst}")
            if tool_rst['status'] == 'error':
                return "Finished", []
            if tool_rst['result'] is not None:
                tool_evts = tool_rst['result']
                for evt in tool_evts:
                    if isinstance(evt, SetSlot):
                        slot_info = arg_format(evt.slot_name, self.name)
                        tracker.set_arg(slot_info.get("flow_name"), slot_info.get("arg_name"), evt.value)
                    elif isinstance(evt, BotUtter):
                        text = evt.text
                        text = replace_args_in_string(text, self.name, tracker)
                        evt.text = text
                        evt.provider = self.name
                        result.append(evt)
                    else:
                        evt.provider = self.name
                        result.append(evt)

        else:
            call_result = info.get_call_result(call_agent_name=id(self)) if info is not None else None
            if call_result is not None:
                if isinstance(call_result, AgentFail):
                    return "Failed", []
                return "Finished", []
            logger.info(f"Agent: [{self.flow_name}] call other agent: {self.name} with args: {self.args}")
            tracker.push_agent(CurrentAgent(
                agent=agents.get(self.name),
                metadata={"flow": self.flow_name,
                          "step": id(self)}))
            # set args to target agent
            if self.args is not None:
                for target, source in self.args.items():
                    value, _ = tracker.get_arg(source["flow_name"], source["arg_name"])
                    tracker.set_arg(self.name, target, value)
            return "Await", []

        return "Finished", result

    def _get_args_value(self, tracker: Tracker):
        parts = tracker.args.get("bot_name").split("_")
        # kwargs = {
        #     "sender": tracker.args.get("sender"),
        #     "accountName": parts[0],
        #     "projectId": "_".join(parts[1:])
        # }
        kwargs = {}
        if self.args is not None:
            for target, source in self.args.items():
                value, _ = tracker.get_arg(source["flow_name"], source["arg_name"])
                kwargs[target] = value
        return kwargs
