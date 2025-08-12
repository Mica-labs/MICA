import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Text, Any, Union, Tuple

from mica.event import Event, UserInput, BotUtter, AgentFail
from mica.utils import logger


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
                 args: Optional[Dict[Text, Any]] = None,
                 functions: Optional[Dict[Text, Any]] = None,
                 ):
        self.user_id = user_id
        self.events = events or []
        self.args = args or {}
        self.func_args = functions or {}
        self.agent_stack = OrderedDict()
        self.latest_message = None
        self.flow_info = {}
        self.agent_conv_history = {}
        self.predicted_responses = []

    @classmethod
    def create(cls,
               user_id: Text,
               events: Optional[List[Event]] = None,
               args: Optional[Dict[Text, Any]] = None,
               functions: Optional[Dict[Text, Any]] = None
               ):
        return cls(user_id, events, args, functions)

    def update(self, event: Event):
        self.events.append(event)
        if isinstance(event, UserInput):
            self.update_latest_message(event)

    def get_history_str(self):
        conversation_history = ""
        for event in self.events:
            if isinstance(event, UserInput):
                if event.text == "/init":
                    continue
                conversation_history += f"User: {event.text}\n"
            if isinstance(event, BotUtter):
                conversation_history += f"{event.metadata or 'Bot'}: {event.text}\n"
            if isinstance(event, AgentFail):
                conversation_history += f"<agent \'{event.provider}\' failed to respond.>\n"

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
        if arg_name[0] != '_' and (agent_name not in self.args and agent_name not in self.func_args):
            logger.error(f"Cannot find agent: {agent_name} when setting argument value.")
            return False
        if agent_name in self.args and (arg_name[0] != '_' and arg_name not in self.args[agent_name]):
            logger.error(f"Didn't find argument: {arg_name} in agent: {agent_name}")
            return False

        if agent_name in self.func_args:
            self.func_args[agent_name][arg_name] = arg_value
            logger.info(f"system: set {agent_name}.{arg_name} = {arg_value}")
            logger.debug(f"Set argument Success. This is an argument in Functions: {self.func_args}")
            return True

        self.args[agent_name][arg_name] = arg_value
        logger.info(f"system: set {agent_name}.{arg_name} = {arg_value}")
        if self.args['__mapping__'].get(agent_name) \
                and self.args['__mapping__'][agent_name].get(arg_name) \
                and self.args['__mapping__'][agent_name][arg_name]['type'] == "ref":
            ensemble_agent = self.args['__mapping__'][agent_name][arg_name]['agent']
            ensemble_arg = self.args['__mapping__'][agent_name][arg_name]['arg']
            self.args[ensemble_agent][ensemble_arg] = arg_value
            logger.debug("Successfully synchronized '%s' in '%s'", ensemble_arg, ensemble_agent)
        else:
            filtered = {k: v for k, v in self.args.items() if k != "__mapping__"}
            logger.debug(f"Set argument Success. Current agents' arguments: {filtered}")
        return True

    def get_args(self, agent_name):
        all_args = self.args.get(agent_name)
        replaced_args = {}
        for arg_name, arg_value in all_args.items():
            if self.args['__mapping__'].get(agent_name) \
                    and self.args['__mapping__'][agent_name].get(arg_name) \
                    and self.args['__mapping__'][agent_name][arg_name].get('type') == 'ref':
                ensemble_agent = self.args['__mapping__'][agent_name][arg_name]['agent']
                ensemble_arg = self.args['__mapping__'][agent_name][arg_name]['arg']
                replaced_args[arg_name] = self.args[ensemble_agent][ensemble_arg]
            else:
                replaced_args[arg_name] = arg_value
        return replaced_args

    def get_arg(self, agent_name, arg_name) -> Tuple[Any, bool]:
        if arg_name == "_user_input":
            return self.latest_message.text, True
        if agent_name not in self.args and agent_name not in self.func_args:
            logger.error(f"Cannot find agent: {agent_name}.")
            return None, False
        if agent_name in self.args and arg_name not in self.args[agent_name]:
            logger.error(f"Cannot find argument: {arg_name}.")
            return None, False

        if agent_name in self.func_args:
            return self.func_args[agent_name].get(arg_name), True

        if self.args['__mapping__'].get(agent_name) and self.args['__mapping__'][agent_name].get(arg_name):
            if self.args['__mapping__'][agent_name][arg_name].get('type') == 'ref':
                ensemble_agent = self.args['__mapping__'][agent_name][arg_name]['agent']
                ensemble_arg = self.args['__mapping__'][agent_name][arg_name]['arg']
                return self.args[ensemble_agent][ensemble_arg], True

        if self.args[agent_name][arg_name] is None:
            if self.args['__mapping__'].get(agent_name) and self.args['__mapping__'][agent_name].get(arg_name):
                ensemble_agent = self.args['__mapping__'][agent_name][arg_name]['agent']
                ensemble_arg = self.args['__mapping__'][agent_name][arg_name]['arg']
                return self.args[ensemble_agent][ensemble_arg], True

        return self.args[agent_name][arg_name], True

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
