from typing import Optional, Text, List

from mica.agents.steps.base import Base

from mica.tracker import Tracker, FlowInfo
from mica.utils import short_uuid


class Subflow(Base):
    def __init__(self,
                 label: Optional[Text] = None,
                 steps: Optional[List] = None):
        self.label = label or short_uuid()
        self.steps = steps
        super(Subflow, self).__init__()

    @classmethod
    def from_dict(cls, data: List, label: Text, **kwargs):
        from mica.agents.steps.step_loader import StepLoader
        # when there's no "begin" placeholder, add one
        # if (type(data[0]) == str and data[0] != 'begin') or (type(data[0]) == dict and data[0].get('begin') is None):
        #     data = ['begin'] + data
        # if type(data[0]) == str:
        #     label = short_uuid()
        # else:
        #     label = data[0].get("begin")
        steps = []
        for step in data:
            steps.append(StepLoader.create(step, **kwargs))
        return cls(label, steps)

    def __repr__(self):
        details = "\n".join([repr(step) for step in self.steps])
        return f"Subflow(label={self.label}, steps={len(self.steps)})\ndetails={details}\n"

    def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        # start with the first node
        if info.is_stack_empty():
            next_step = self.steps[0]
        else:
            _, step_id = info.pop()
            next_step = self.find_next_step(step_id)

        if next_step is None:
            info.is_listen = True
            result = []
        else:
            result = next_step.run(tracker, info)
            info.push(self.label, id(next_step))
        return result

    def find_next_step(self, step_id):
        for index, step in enumerate(self.steps):
            if id(step) == step_id:
                if index + 1 < len(self.steps):
                    return self.steps[index + 1]
                else:
                    return None  # if there is no next step, return None
        return None  # if the target step is not found, return None
