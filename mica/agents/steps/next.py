from typing import Optional

from mica.agents.steps.base import Base
from mica.tracker import Tracker, FlowInfo


class Next(Base):
    def __init__(self, name, tries=None):
        self.name = name
        self.tries = tries or float('inf')
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        name = data.get("next")
        tries = data.get("tries")
        return cls(name, tries)

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
                return "Do", []
        return "Skip", []