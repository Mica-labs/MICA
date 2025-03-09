import re
from typing import Optional, Text, List, Dict, Union, Any

from mica.agents.agent import Agent


class Function(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 body: Optional[Text] = None,
                 description: Optional[Text] = None,
                 args: Optional[Dict[Text, Any]] = None,
                 required: Optional[List] = None,
                 **kwargs):
        self.body = body
        self.args = args
        self.required = required or args
        super().__init__(name, description)

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               body: Optional[Text] = None,
               description: Optional[Text] = None,
               args: Optional[Union[List, Dict]] = None,
               required: Optional[List] = None,
               **kwargs
               ):
        return cls(name, body, description, args, required)

    def save(self):
        if self.body is not None:
            return self.name, self.body
        return None, None

    def is_python_code(self) -> bool:
        return self.body is not None

    def contains_args(self):
        return self.args

    def function_prompt(self) -> Dict:
        prompt = {
            "name": self.name
        }
        if self.description is not None and len(self.description) > 0:
            prompt["description"] = self.description
        args = {}
        # if self.args is not None:
        #     for arg in self.args:
        #         if type(arg) == str:
        #             attr = {"type": "string"}
        #             args[arg] = attr
        #         else:
        #             name = list(arg.keys())[0]
        #             attr = arg[name]
        #             attr["type"] = "string"
        #             args[name] = attr
        if self.args is not None and len(self.args) > 0:
            prompt["parameters"] = {
                "type": "object",
                "properties": self.args,
                "required": self.required
            }
        return prompt
