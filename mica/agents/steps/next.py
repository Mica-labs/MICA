from typing import Optional

from mica.agents.steps.base import Base
from mica.tracker import Tracker, FlowInfo
from mica.utils import logger

class Next(Base):
    def __init__(self, name, flow_name, tries=None):
        self.name = name
        self.flow_name = flow_name
        self.tries = tries or float('inf')
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        name = data.get("next")
        tries = data.get("tries")
        flow_name = kwargs.get("root_agent_name")
        return cls(name, flow_name, tries)

    def __repr__(self):
        return f"Next(name={self.name})"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        if info is not None:
            info.is_listen = False
            if info.get_counter(id(self)) < self.tries:
                info.count(id(self))
                logger.info(f"Agent: [{self.flow_name}] > step > next: {self.name}")
                return "Do", []
        return "Skip", []