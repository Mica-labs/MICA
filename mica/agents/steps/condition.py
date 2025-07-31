import json
import operator
import re
from typing import Optional, Text, List, Any, Dict

from mica.agents.steps.base import Base

from mica.constants import MAIN_FLOW
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker, FlowInfo
from mica.utils import parse_and_evaluate, logger


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
        self.flow_name = flow_name
        super(If, self).__init__()

    @classmethod
    def from_dict(cls, data: Dict, **kwargs):
        config = kwargs.get("config")
        flow_name = kwargs.get("root_agent_name")
        llm_model = kwargs.get("llm_model")

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
            prompt = self._generate_prompt(all_examples, user_input, tracker)
            logger.debug("If prompt: \n%s", json.dumps(prompt, indent=2, ensure_ascii=False))
            llm_result = await self.llm_model.generate_message(prompt, provider=self.flow_name)
            response = llm_result[0].text
            response_flag = "True" in response
            if response_flag:
                logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is True.")
                return "Do", []
            logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is False.")
            return "Skip", []
        elif "the user clicks" in self.statement:
            target_button_name = self._extract_button_name(self.statement)
            if not target_button_name:
                logger.error("No button name found in the statement: %s", self.statement)
                return "Skip", []
            user_input = tracker.latest_message.text
            extracted_button_name = self._extract_button_name(user_input)
            if extracted_button_name and extracted_button_name == target_button_name:
                logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is True.")
                return "Do", []
            logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is False.")
            return "Skip", []
        else:
            flag = parse_and_evaluate(self.statement, tracker, self.flow_name)
            if flag:
                logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is True.")
                return "Do", []
            logger.info(f"Agent: [{self.flow_name}] execute if step: {self.statement} is False.")
            return "Skip", []
            # arg_name_str, comparator, value = extract_expression_parts(self.statement)
            # if arg_name_str is not None:
            #     arg_info = arg_format(arg_name_str, self.flow_name)
            #     arg_value = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
            #     response_flag = self.compare(arg_value, comparator, value)
            #     if response_flag:
            #         return "Do", []
            #     return "Skip", []

    @staticmethod
    def _generate_prompt(examples, user_input, tracker: Tracker):
        user_content = "- Targets:\n" + "\n".join(examples) + \
                       f"\n- Previous Conversation: \n {tracker.get_history_str()}\n"

        user_content += f"Does sentence \"{user_input}\" have the same meaning as any sentences in the targets?"
        prompt = [{"role": "system",
                   "content": "Your task is to identify the user’s intent. "
                              "I will give you some targets. "
                              "If the user’s message has the same meaning as any one sentence in targets, "
                        "please respond with ‘True’; otherwise, respond with ‘False.’ DO NOT EXPLAIN."},
            {"role": "user",
             "content": user_content}
        ]
        return prompt

    def _extract_input_examples(self):
        pattern = r'"(.*?)"'
        return re.findall(pattern, self.statement)

    def _extract_button_name(self, user_input: Text):
        # Extract button name from either 'the user clicks "Button 1"' or '/click: Button 1'
        # Pattern 1: the user clicks "Button 1"
        pattern1 = r'the user clicks\s+"([^"]+)"'
        match1 = re.search(pattern1, user_input)
        if match1:
            return match1.group(1).strip()
        # Pattern 2: /click: Button 1
        pattern2 = r'^/click:\s*(.+)$'
        match2 = re.match(pattern2, user_input)
        if match2:
            return match2.group(1).strip()
        return None

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
        self.flow_name = flow_name
        super(ElseIf, self).__init__()

    @classmethod
    def from_dict(cls, data: Dict, **kwargs):
        config = kwargs.get("config")
        flow_name = kwargs.get("root_agent_name")
        llm_model = kwargs.get("llm_model")

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
            prompt = self._generate_prompt(all_examples, user_input, tracker)
            logger.debug("Else If prompt: \n%s", json.dumps(prompt, indent=2, ensure_ascii=False))
            llm_result = await self.llm_model.generate_message(prompt, provider=self.flow_name)
            response = llm_result[0].text
            response_flag = "True" in response
            if response_flag:
                logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is True.")
                return "Do", []
            else:
                logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is False.")
                return "Skip", []
        elif "the user clicks" in self.statement:
            target_button_name = self._extract_button_name(self.statement)
            if not target_button_name:
                logger.error("No button name found in the statement: %s", self.statement)
                return "Skip", []
            user_input = tracker.latest_message.text
            extracted_button_name = self._extract_button_name(user_input)
            if extracted_button_name and extracted_button_name == target_button_name:
                logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is True.")
                return "Do", []
            logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is False.")
            return "Skip", []
        else:
            flag = parse_and_evaluate(self.statement, tracker, self.flow_name)
            if flag:
                logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is True.")
                return "Do", []
            logger.info(f"Agent: [{self.flow_name}] execute else if step: {self.statement} is False.")
            return "Skip", []
            # arg_name_str, comparator, value = extract_expression_parts(self.statement)
            # if arg_name_str is not None:
            #     arg_info = arg_format(arg_name_str, self._flow_name)
            #     arg_value = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
            #     response_flag = self.compare(arg_value, comparator, value)
            #     if response_flag:
            #         return "Do", []
            #     return "Skip", []

    @staticmethod
    def _generate_prompt(examples, user_input, tracker: Tracker):
        user_content = "- Targets:\n" + "\n".join(examples) + \
                       f"\n- Previous Conversation: \n {tracker.get_history_str()}\n"
        user_content += f"Does sentence \"{user_input}\" have the same meaning as any sentences in the targets?"
        prompt = [{"role": "system",
                   "content": "Your task is to identify the user’s intent. "
                              "I will give you some targets. "
                              "If the user’s message has the same meaning as any one sentence in targets, "
                              "please respond with ‘True’; otherwise, respond with ‘False.’ DO NOT EXPLAIN."},
                  {"role": "user", "content": user_content}]
        return prompt

    def _extract_input_examples(self):
        pattern = r'"(.*?)"'
        return re.findall(pattern, self.statement)

    def _extract_button_name(self, user_input: Text):
        # Extract button name from either 'the user clicks "Button 1"' or '/click: Button 1'
        # Pattern 1: the user clicks "Button 1"
        pattern1 = r'the user clicks\s+"([^"]+)"'
        match1 = re.search(pattern1, user_input)
        if match1:
            return match1.group(1).strip()
        # Pattern 2: /click: Button 1
        pattern2 = r'^/click:\s*(.+)$'
        match2 = re.match(pattern2, user_input)
        if match2:
            return match2.group(1).strip()
        return None

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
            logger.info(f"Agent: [{self.flow_name}] skip else step: {self.name} because of tries limit ({self.tries}).")
            return "Skip", []
        info.count(id(self))
        logger.info(f"Agent: [{self.flow_name}] execute else step: {self.name}.")
        return "Do", []
