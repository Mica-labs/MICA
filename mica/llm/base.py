from abc import ABC, abstractmethod
from typing import Optional, Any

from mica.tracker import Tracker


class BaseModel(ABC):

    @abstractmethod
    def generate_message(self,
                         prompts: Any,
                         tracker: Optional[Tracker] = None,
                         **kwargs: Any):
        """
        :param prompts:
        :param tracker:
        :param kwargs:
        :return:
        """

