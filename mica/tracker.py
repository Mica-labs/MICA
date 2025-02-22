from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Text, Any, Union

from mica.event import Event, UserInput, BotUtter, AgentFail


@dataclass
class FlowInfo:
    """
    Including all the runtime information of flow agent.
    """
    runtime_stack: list = field(default_factory=list)
    internal_states: dict = field(default_factory=dict)
    counter: dict = field(default_factory=dict)
    is_listen: bool = False

    def push(self, execute_path):
        self.runtime_stack.append(execute_path)

    def pop(self):
        if not self.is_stack_empty():
            return self.runtime_stack.pop()
        return None

    def is_stack_empty(self):
        return len(self.runtime_stack) == 0

    def get_state(self, key):
        return self.internal_states.get(key)

    def peek(self):
        if not self.is_stack_empty():
            return self.runtime_stack[-1]
        return None

    def count(self, step_id):
        if self.counter.get(step_id) is None:
            self.counter[step_id] = 1
        else:
            self.counter[step_id] += 1

    def get_counter(self, step_id):
        if self.counter.get(step_id) is None:
            return 0
        return self.counter[step_id]

    def clear(self):
        self.runtime_stack = []

    def has_extract_args_after_latest_user_message(self, latest_message: Event) -> bool:
        import time
        if "_last_time_extract" not in self.internal_states.keys():
            self.internal_states["_last_time_extract"] = time.time()
            return False

        result = self.internal_states["_last_time_extract"] >= latest_message.timestamp
        self.internal_states["_last_time_extract"] = time.time()
        return result

    def get_call_result(self, call_agent_name):
        return self.internal_states.get(call_agent_name)

    def set_call_result(self, call_agent_name, result):
        self.internal_states[call_agent_name] = result


class Tracker(object):
    def __init__(self,
                 user_id,
                 events: Optional[List[Event]] = None,
                 args: Optional[Dict[Text, Any]] = None
                 ):
        self.user_id = user_id
        self.events = events or []
        self.args = args or {}
        self.agent_stack = OrderedDict()
        self.latest_message = None
        self.flow_info = {}
        self.agent_conv_history = {}

    @classmethod
    def create(cls,
               user_id: Text,
               events: Optional[List[Event]] = None,
               args: Optional[Dict[Text, Any]] = None
               ):
        return cls(user_id, events, args)

    def update(self, event: Event):
        self.events.append(event)
        if isinstance(event, UserInput):
            self.update_latest_message(event)

    def get_history_str(self):
        conversation_history = ""
        for event in self.events:
            if isinstance(event, UserInput):
                conversation_history += f"User: {event.text}\n"
            if isinstance(event, BotUtter):
                conversation_history += f"{event.metadata or 'Bot'}: {event.text}\n"
            if isinstance(event, AgentFail):
                conversation_history += f"<agent \'{event.provider}\' failed to respond.>"

        return conversation_history

    def update_latest_message(self, event: UserInput):
        self.latest_message = event

    def is_agent_stack_empty(self):
        return not self.agent_stack

    def push_agent(self, agent):
        # if the agent already existed, then move it to the end
        if agent in self.agent_stack:
            self.agent_stack.move_to_end(agent)
        else:
            # if the agent doesn't exist, append to the end
            self.agent_stack[agent] = None

    def pop_agent(self):
        if self.is_agent_stack_empty():
            return None
        return self.agent_stack.popitem(last=True)

    def peek_agent(self):
        if self.is_agent_stack_empty():
            return None
        return next(reversed(self.agent_stack.keys()))

    def get_or_create_flow_agent(self, flow_name) -> FlowInfo:
        if self.flow_info.get(flow_name) is None:
            self.flow_info[flow_name] = FlowInfo()
        return self.flow_info[flow_name]

    def remove_flow_agent(self, flow_name):
        if self.flow_info.get(flow_name) is None:
            return
        self.flow_info.pop(flow_name)

    def set_arg(self, agent_name, arg_name, arg_value):
        if arg_name[0] != '_' and (
                agent_name not in self.args
                or arg_name not in self.args[agent_name]):
            return False
        self.args[agent_name][arg_name] = arg_value
        return True

    def get_args(self, agent_name):
        return self.args.get(agent_name)

    def get_arg(self, agent_name, arg_name):
        if (agent_name not in self.args) or (arg_name not in self.args[agent_name]):
            return None
        return self.args[agent_name][arg_name]

    def has_bot_response_after_user_input(self):
        for evt in reversed(self.events):
            if evt == self.latest_message:
                break
            if isinstance(evt, BotUtter):
                return True
        return False

    def get_or_create_agent_conv_history(self, agent_name) -> List:
        if self.agent_conv_history.get(agent_name) is None:
            self.agent_conv_history[agent_name] = []
        return self.agent_conv_history[agent_name]

    def set_conv_history(self, agent_name: Text, message: Dict) -> None:
        self.agent_conv_history[agent_name].append(message)

    def clear_conv_history(self, agent_name):
        self.agent_conv_history[agent_name] = []

