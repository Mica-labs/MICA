from typing import List, Optional, Text, Any, Dict

from mica.agents.steps.base import Base
from mica.event import SetSlot
from mica.tracker import Tracker, FlowInfo
from mica.utils import arg_format, logger


class Set(Base):
    def __init__(self,
                 data: Optional[Dict[Text, Any]] = None,
                 flow_name: Optional[Text] = None):
        self.data = data
        self.flow_name = flow_name
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        data = data.get("set")
        flow_name = kwargs.get("root_agent_name")
        return cls(data, flow_name)

    def __repr__(self):
        return f"Set(data={self.data})"

    async def run(self,
                  tracker: Optional[Tracker] = None,
                  info: Optional[FlowInfo] = None,
                  **kwargs):
        if info is not None:
            info.is_listen = False
        result = []
        for target, source in self.data.items():
            target_arg_info = arg_format(target, self.flow_name)
            if not isinstance(source, str):
                tracker.set_arg(target_arg_info["flow_name"],
                                target_arg_info["arg_name"], source)
            if not isinstance(source, Text):
                source_value = source
            else:
                source_arg_info = arg_format(source, self.flow_name)

                source_value, source_exist = tracker.get_arg(source_arg_info["flow_name"], source_arg_info["arg_name"])
                if not source_exist:
                    source_value = source

            tracker.set_arg(target_arg_info["flow_name"],
                            target_arg_info["arg_name"], source_value)
        logger.info(f"Agent: [{self.flow_name}] execute set step: {self.data}")
        return "Finished", result


