from typing import Optional, Text

from mica.agents.steps.base import Base
from mica.tracker import Tracker, FlowInfo
from mica.utils import logger


class User(Base):
    def __init__(self, flow_name: Optional[Text] = None):
        self.flow_name = flow_name
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        flow_name = kwargs.get("root_agent_name")
        return cls(flow_name)

    def __repr__(self):
        return "User()"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        if tracker.has_bot_response_after_user_input():
            info.is_listen = True
        logger.info(f"[{self.flow_name}]: wait for user input")
        return "Finished", []
