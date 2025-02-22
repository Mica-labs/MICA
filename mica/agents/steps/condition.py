import operator
import re
from typing import Optional, Text, List, Any, Dict

from mica.agents.steps.base import Base

from mica.constants import MAIN_FLOW
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker, FlowInfo
from mica.utils import extract_expression_parts, arg_format, parse_and_evaluate_expression


class If(Base):
    def __init__(self,
                 statement: Optional[Text] = None,
                 then: Optional[List[Any]] = None,
                 tries: Optional[Any] = None,
                 config: Optional[Any] = None,
                 flow_name: Optional[Any] = None,
                 llm_model: Optional[Any] = None,
                 ):
        self.statement = statement
        self.then = then
        self.tries = tries or float('inf')
        self.llm_model = llm_model or OpenAIModel.create(config)
        self._flow_name = flow_name
        super(If, self).__init__()

    @classmethod
    def from_dict(cls, data: Dict, **kwargs):
        config = kwargs.get("config")
        flow_name = kwargs.get("root_agent_name")
        llm_model = kwargs.get("llm_model")

        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")

        from mica.agents.steps.step_loader import StepLoader

        statement = data.get("if")
        tries = data.get("tries")
        then = []
        if isinstance(data.get("then"), Text):
            data["then"] = [data["then"]]
        for next_step in data["then"]:
            then.append(StepLoader.create(next_step, **kwargs))
        return cls(statement, then, tries, config, flow_name, llm_model)

    def __repr__(self):
        details = "\n".join([repr(step) for step in self.then])
        return f"If(statement={self.statement}, then={len(self.then)})\ndetails={details}\n"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        info.is_listen = False
        if info.get_counter(id(self)) >= self.tries:
            return "Skip", []
        info.count(id(self))
        if "the user claims" in self.statement:
            all_examples = self._extract_input_examples()
            user_input = tracker.latest_message.text
            prompt = self._generate_prompt(all_examples, user_input)
            print("if prompt", prompt)
            llm_result = await self.llm_model.generate_message(prompt)
            response = llm_result[0].text
            response_flag = "True" in response
            if response_flag:
                return "Do", []
            return "Skip", []
        else:
            flag = parse_and_evaluate_expression(self.statement, tracker, self._flow_name)
            if flag:
                return "Do", []
            return "Skip", []
            # arg_name_str, comparator, value = extract_expression_parts(self.statement)
            # if arg_name_str is not None:
            #     arg_info = arg_format(arg_name_str, self._flow_name)
            #     arg_value = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
            #     response_flag = self.compare(arg_value, comparator, value)
            #     if response_flag:
            #         return "Do", []
            #     return "Skip", []

    def compare(self, arg_value, comparator, target_value):
        operations = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge
        }

        if comparator in operations:
            return operations[comparator](arg_value, target_value)
        else:
            raise ValueError(f"Unknown operator: {comparator}")

    def _generate_prompt(self, examples, user_input):
        user_content = "- Examples:\n" + "\n".join(examples) + f"\n-User: {user_input} \n" \

        user_content += f"Does sentence \"{user_input}\" have the same meaning as the sentences in the examples?"
        prompt = [
            {"role": "system",
             "content": "You are an intelligent conversational bot. "
                        "Your task is to determine the user’s intent. "
                        "I will give you some examples. If the user’s message has the same meaning as the examples "
                        "I give you, please respond with ‘True’; otherwise, respond with ‘False.’ DO NOT EXPLAIN."},
            {"role": "user",
             "content": user_content}
        ]
        return prompt

    def _extract_input_examples(self):
        # 正则表达式匹配双引号中的内容
        pattern = r'"(.*?)"'
        # 使用 findall 查找所有匹配的字符串
        return re.findall(pattern, self.statement)


class ElseIf(Base):
    def __init__(self,
                 statement: Optional[Text] = None,
                 then: Optional[List[Any]] = None,
                 tries: Optional[Any] = None,
                 config: Optional[Any] = None,
                 flow_name: Optional[Any] = None,
                 llm_model: Optional[Any] = None,
                 ):
        self.statement = statement
        self.then = then
        self.tries = tries or float('inf')
        self.llm_model = llm_model or OpenAIModel.create(config)
        self._flow_name = flow_name
        super(ElseIf, self).__init__()

    @classmethod
    def from_dict(cls, data: Dict, **kwargs):
        config = kwargs.get("config")
        flow_name = kwargs.get("root_agent_name")
        llm_model = kwargs.get("llm_model")
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server") + "/rpc/rasa/message"
            config["headers"] = kwargs.get("headers")

        from mica.agents.steps.step_loader import StepLoader

        statement = data.get("else if")
        tries = data.get("tries")
        then = []
        if isinstance(data.get("then"), str):
            data["then"] = [data["then"]]
        for next_step in data["then"]:
            then.append(StepLoader.create(next_step, **kwargs))
        return cls(statement, then, tries, config, flow_name, llm_model)

    def __repr__(self):
        details = "\n".join([repr(step) for step in self.then])
        return f"ElseIf(statement={self.statement}, then={len(self.then)})\ndetails={details}\n"

    async def run(self,
            tracker: Optional[Tracker] = None,
            info: Optional[FlowInfo] = None,
            **kwargs):
        info.is_listen = False
        if info.get_counter(id(self)) >= self.tries:
            return "Skip", []
        info.count(id(self))
        if "the user claims" in self.statement:
            all_examples = self._extract_input_examples()
            user_input = tracker.latest_message.text
            prompt = self._generate_prompt(all_examples, user_input)
            print("else if prompt", prompt)
            llm_result = await self.llm_model.generate_message(prompt)
            response = llm_result[0].text
            response_flag = "True" in response
            if response_flag:
                return "Do", []
            else:
                return "Skip", []
        else:
            flag = parse_and_evaluate_expression(self.statement, tracker, self._flow_name)
            if flag:
                return "Do", []
            return "Skip", []
            # arg_name_str, comparator, value = extract_expression_parts(self.statement)
            # if arg_name_str is not None:
            #     arg_info = arg_format(arg_name_str, self._flow_name)
            #     arg_value = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
            #     response_flag = self.compare(arg_value, comparator, value)
            #     if response_flag:
            #         return "Do", []
            #     return "Skip", []

    def compare(self, arg_value, comparator, target_value):
        operations = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge
        }

        if comparator in operations:
            return operations[comparator](arg_value, target_value)
        else:
            raise ValueError(f"Unknown operator: {comparator}")

    def _generate_prompt(self, examples, user_input):
        user_content = "- Examples:\n" + "\n".join(examples) + f"\n-User: {user_input}"
        prompt = [{"role": "system", "content": "You are an intelligent conversational bot. Your task is to determine the user’s intent. I will give you some examples. If the user’s message has the same meaning as the examples I give you, please respond with ‘True’; otherwise, respond with ‘False.’ DO NOT EXPLAIN."},
        {
            "role": "user", "content": user_content
        }]
        return prompt

    def _extract_input_examples(self):
        # 正则表达式匹配双引号中的内容
        pattern = r'"(.*?)"'
        # 使用 findall 查找所有匹配的字符串
        return re.findall(pattern, self.statement)


class Else(Base):
    def __init__(self,
                 then: Optional[List[Any]] = None,
                 tries: Optional[Any] = None
                 ):
        self.then = then
        self.tries = tries or float('inf')
        super(Else, self).__init__()

    @classmethod
    def from_dict(cls, data: Dict, **kwargs):
        from mica.agents.steps.step_loader import StepLoader
        then = []
        tries = data.get("tries")
        if isinstance(data.get("else"), str):
            data["else"] = [data["else"]]
        for next_step in data["else"]:
            then.append(StepLoader.create(next_step, **kwargs))
        return cls(then, tries)

    def __repr__(self):
        details = "\n".join([repr(step) for step in self.then])
        return f"Else(then={len(self.then)})\ndetails={details}\n"

    async def run(self,
                  tracker: Optional[Tracker] = None,
                  info: Optional[FlowInfo] = None,
                  **kwargs):
        info.is_listen = False
        if info.get_counter(id(self)) >= self.tries:
            return "Skip", []
        info.count(id(self))
        return "Do", []
