from typing import Optional

from mica.agents.steps.base import Base
from mica.tracker import Tracker, FlowInfo


class Label(Base):
    def __init__(self, name):
        self.name = name
        super().__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        name = data.get("label")
        return cls(name)

    def __repr__(self):
        return f"Label(name={self.name})"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        info.is_listen = False
        return "Finished", []