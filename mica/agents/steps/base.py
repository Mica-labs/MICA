from abc import ABC, abstractmethod
from typing import Optional

from mica.tracker import Tracker, FlowInfo


class Base(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def run(self,
                  tracker: Optional[Tracker] = None,
                  info: Optional[FlowInfo] = None,
                  **kwargs):
        pass
