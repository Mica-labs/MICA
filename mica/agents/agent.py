from typing import Optional, Dict, Text, Any, List

from mica.tracker import Tracker


class Agent(object):
    """The Agent class is a kind of node in flow. It describes a GPT behaviour and build a rule on how to react.
    """

    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None):
        self.name = name
        self.description = description or ""

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               description: Optional[Text] = None):
        return cls(name, description)

    async def run(self, tracker: Tracker, **kwargs):
        pass

    def contains_args(self):
        return None


class Main(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 steps: Optional[Any] = None,
                 ):
        self.steps = steps
        super().__init__(name, description)

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               steps: Optional[Any] = None,
               **kwargs):
        from mica.agents.steps.step_loader import StepLoader
        if steps is not None:
            steps = [StepLoader.create(step, root_agent_name=name) for step in steps]
        description = ""

        return cls(name, description, steps)

    async def run(self, tracker: Tracker, agents: Optional[Any] = None, **kwargs):
        is_end = False
        result = []
        for step in self.steps:
            step_flag, step_result = await step.run(tracker, agents=agents, **kwargs)
            result.extend(step_result)
            if step_flag in ["Await"]:
                is_end = False
        return is_end, result
