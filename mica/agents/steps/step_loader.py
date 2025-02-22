from typing import List, Dict, Text

from mica.agents.steps.bot import Bot
from mica.agents.steps.call import Call
from mica.agents.steps.label import Label
from mica.agents.steps.next import Next
from mica.agents.steps.set import Set
from mica.agents.steps.subflow import Subflow
from mica.agents.steps.termination import Return
from mica.agents.steps.user import User
from mica.agents.steps.condition import If, ElseIf, Else


class StepLoader:
    @staticmethod
    def create(data, **kwargs):
        if isinstance(data, List):
            return Subflow.from_dict(data, **kwargs)
        if isinstance(data, Dict):
            if data.get("bot") is not None:
                return Bot.from_dict(data, **kwargs)
            if data.get("set") is not None:
                return Set.from_dict(data, **kwargs)
            if data.get("if") is not None:
                return If.from_dict(data, **kwargs)
            if data.get("else if") is not None:
                return ElseIf.from_dict(data, **kwargs)
            if data.get("else") is not None:
                return Else.from_dict(data, **kwargs)
            if data.get("label") is not None:
                return Label.from_dict(data, **kwargs)
            if data.get("next") is not None:
                return Next.from_dict(data, **kwargs)
            if data.get("call") is not None:
                return Call.from_dict(data, **kwargs)
            if data.get("return") is not None:
                return Return.from_dict(data, **kwargs)
        if isinstance(data, Text):
            if data == "user":
                return User.from_dict(data, **kwargs)
            else:
                return Next.from_dict({"next": data}, **kwargs)
