from typing import Optional, Text

from mica.agents.steps.base import Base
from mica.event import BotUtter
from mica.tracker import Tracker, FlowInfo


class User(Base):
    @classmethod
    def from_dict(cls, data, **kwargs):
        return cls()

    def __repr__(self):
        return "User()"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        if tracker.has_bot_response_after_user_input():
            info.is_listen = True
        return "Finished", []
