from typing import Optional, Text

from mica.agents.steps.base import Base
from mica.event import BotUtter, AgentComplete, AgentFail
from mica.tracker import Tracker, FlowInfo
from mica.utils import replace_args_in_string


class Return(Base):
    def __init__(self,
                 status: Optional[Text] = None,
                 msg: Optional[Text] = None,
                 flow_name: Optional[Text] = None):
        self.status = status
        self.msg = msg
        self.flow_name = flow_name
        super(Return, self).__init__()

    @classmethod
    def from_dict(cls, data, **kwargs):
        text_list = data.get("return").split(',')
        status = "success"
        msg = ""
        if len(text_list) == 1:
            status = text_list[0]
        elif len(text_list) == 2:
            status = text_list[0]
            msg = text_list[1].strip()
        flow_name = kwargs.get("root_agent_name")
        return cls(status, msg, flow_name)

    def __repr__(self):
        return f"Return(status={self.status}, msg={self.msg})"

    async def run(self,
                  tracker: Optional[Tracker] = None,
                  info: Optional[FlowInfo] = None,
                  **kwargs):
        rst = []
        if self.status == "success":
            rst.append(AgentComplete(provider=self.flow_name, metadata=self.msg))
        else:
            rst.append(AgentFail(provider=self.flow_name, metadata=self.msg))
        return "Finished", rst
