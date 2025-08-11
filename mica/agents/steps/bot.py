from typing import Optional, Text

from mica.agents.steps.base import Base
from mica.event import BotUtter
from mica.tracker import Tracker, FlowInfo
from mica.utils import replace_args_in_string, logger


class Bot(Base):
    def __init__(self,
                 text: Optional[Text] = None,
                 flow_name: Optional[Text] = None):
        self.text = text
        self.flow_name = flow_name
        super(Bot, self).__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        text = data.get("bot")
        flow_name = kwargs.get("root_agent_name")
        return cls(text, flow_name)

    def __repr__(self):
        return f"Bot(text={self.text})"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        if info is not None:
            info.is_listen = False
        text = self.text
        if self.flow_name is not None:
            text = replace_args_in_string(text, self.flow_name, tracker)
        logger.info(f"Agent: [{self.flow_name}] > step > Bot: {text}")
        return "Finished", [BotUtter(text=text)]
