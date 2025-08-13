from abc import ABC, abstractmethod
from difflib import get_close_matches
from typing import List, Dict, Any, Set, Text, Type, Optional, Union
import yaml
from dataclasses import dataclass


# TODO: if there's any subflow, do the same operation
def parse_agents(raw_agents: Dict):
    processed_agents = {}
    for agent_name, agent_content in raw_agents.items():
        processed_agent_content = agent_content
        if agent_content.get("type") and agent_content["type"] == "flow agent":
            for key, value in agent_content.items():
                if key in ['type', 'description', 'fallback', 'exit', 'args']:
                    continue
                temp_steps = []
                for step in value:
                    if isinstance(step, dict) and "if" in step:
                        if_dict = {
                            'if': step['if'],
                            'then': step.get('then', []),
                            'tries': step.get('tries')
                        }
                        temp_steps.append(if_dict)

                        if 'else' in step:
                            else_dict = {
                                'else': step['else']
                            }
                            temp_steps.append(else_dict)
                    elif isinstance(step, dict) and "else if" in step:
                        elif_dict = {
                            'else if': step['else if'],
                            'then': step.get('then', []),
                            'tries': step.get('tries')
                        }
                        temp_steps.append(elif_dict)

                        if 'else' in step:
                            else_dict = {
                                'else': step['else']
                            }
                            temp_steps.append(else_dict)
                    else:
                        temp_steps.append(step)
                processed_agent_content[key] = temp_steps
        processed_agents[agent_name] = processed_agent_content
    return processed_agents


@dataclass
class ValidationError:
    rule_name: Text
    message: Text
    path: Text = ""


class TypeSpec:
    """Type specification class, used to define type requirements for values."""
    def __init__(
        self,
        expected_type: Union[Type, tuple[Type, ...]],
        nullable: bool = False,
        nested_schema: Optional[Dict[str, 'TypeSpec']] = None
    ):
        self.expected_type = expected_type
        self.nullable = nullable
        self.nested_schema = nested_schema or {}


class AgentValidator(ABC):
    """Base class of validator"""

    def __init__(self):
        self.valid_keys: Set[Text] = set()
        self.type_specs: Dict[Text, TypeSpec] = {}
        self.step_schema: Dict[Text, Any] = {
            'keywords': {'bot', 'user', 'if', 'else if', 'else', 'then', 'tries',
                         'begin', 'end', 'call', 'next', 'label', 'return', 'args',
                         'set'},
            'string_literals': {'begin', 'end', 'user'},
            'compound_keys': {'bot', 'if', 'begin'}
        }

    @abstractmethod
    def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
        """
        validate agent configuration
        content: current agent configuration
        path: current path
        context: contain all the context of YAML
        """
        pass

    def validate_required_keys(self, content: Dict[Text, Any], required_keys: Set[Text], path: Text) -> List[
        ValidationError]:
        """verify all the required keys"""
        errors = []
        for key in required_keys:
            if key not in content:
                errors.append(ValidationError(
                    self.__class__.__name__,
                    f"Missing required key '{key}'",
                    path
                ))
        return errors

    def validate_spelling(self, content: Dict[Text, Any], path: Text) -> List[ValidationError]:
        """verify the spelling of the keys"""
        errors = []
        if "*" in self.valid_keys:
            return errors

        for key in content:
            if key not in self.valid_keys:
                # find the most similar valid key by get_close_matches
                close_matches = get_close_matches(key, self.valid_keys, n=3, cutoff=0.6)
                suggestion = f"Did you mean: {', '.join(close_matches)}" if close_matches else "No similar keys found"

                errors.append(ValidationError(
                    self.__class__.__name__,
                    f"Possible spelling error in key '{key}'. {suggestion}",
                    path
                ))
        return errors

    def validate_type(self, content: Dict[str, Any], path: str) -> List[ValidationError]:
        """validate the type of the key"""
        errors = []

        def _validate_value(value: Any, type_spec: TypeSpec, current_path: str) -> List[ValidationError]:
            local_errors = []

            # null
            if value is None:
                if not type_spec.nullable:
                    local_errors.append(ValidationError(
                        self.__class__.__name__,
                        f"Value at '{current_path}' cannot be null",
                        path
                    ))
                return local_errors

            # type validation
            if not isinstance(value, type_spec.expected_type):
                local_errors.append(ValidationError(
                    self.__class__.__name__,
                    f"Type mismatch at '{current_path}': expected {type_spec.expected_type}, got {type(value).__name__}",
                    path
                ))
                return local_errors

            # If dict type with nested schema, validate recursively
            if isinstance(value, Dict) and type_spec.nested_schema:
                for key, nested_value in value.items():
                    if key in type_spec.nested_schema:
                        nested_spec = type_spec.nested_schema[key]
                        local_errors.extend(_validate_value(
                            nested_value,
                            nested_spec,
                            f"{current_path}.{key}"
                        ))

            return local_errors

        # validate all the value
        for key, value in content.items():
            if key in self.type_specs:
                errors.extend(_validate_value(
                    value,
                    self.type_specs[key],
                    f"{path}.{key}"
                ))

        return errors

    def validate_ref(self, agent_name: Text, path: Text, context: Dict[Text, Any], code_str=None) -> List[ValidationError]:
        errors = []
        all_agents = context.get('all_agents', set())  # get the names of all the agents
        if agent_name not in all_agents and (code_str is not None and agent_name not in code_str):
            errors.append(ValidationError(
                self.__class__.__name__,
                f"Referenced agent '{agent_name}' is not defined in this file",
                f"{path}/agent[{agent_name}]"
            ))
        elif agent_name == path.split('[')[1].split(']')[0]:  # self reference
            errors.append(ValidationError(
                self.__class__.__name__,
                f"Agent cannot reference itself",
                f"{path}/agent[{agent_name}]"
            ))
        return errors

    def validate_steps(self, steps: List[Any],
                       path: str,
                       context: Dict[Text, Any],
                       in_condition: bool = False,
                       code_str = None) -> List[ValidationError]:
        """validate steps list"""
        errors = []

        for i, step in enumerate(steps):
            step_path = f"{path}[{i}]"

            if isinstance(step, Text):
                # string type step
                if step not in self.step_schema['string_literals']:
                    errors.append(ValidationError(
                        "StepValidation",
                        f"Invalid step string '{step}'. Valid values are: {', '.join(self.step_schema['string_literals'])}",
                        step_path
                    ))

            elif isinstance(step, Dict):
                for key in step:
                    if key not in self.step_schema['keywords']:
                        errors.append(ValidationError(
                            "StepValidation",
                            f"Invalid step key '{key}'. Valid keys are: {', '.join(self.step_schema['keywords'])}",
                            step_path
                        ))

                    # 验证条件结构
                    if key in ['if', 'else if', 'else']:
                        if 'then' not in step:
                            errors.append(ValidationError(
                                "StepValidation",
                                "'if' / 'else if' must have a 'then' block",
                                step_path
                            ))
                        else:
                            # 递归验证then块
                            if isinstance(step['then'], List):
                                errors.extend(self.validate_steps(step['then'], f"{step_path}/then", context, True))
                            else:
                                errors.append(ValidationError(
                                    "StepValidation",
                                    "'then' block must be a list",
                                    f"{step_path}/then"
                                ))

                    if key == 'call':
                        errors.extend(self.validate_ref(step['call'], f"{step_path}", context=context, code_str=code_str))
        return errors


class EnsembleAgentValidator(AgentValidator):
    """Validator for Ensemble Agent"""

    def __init__(self):
        super().__init__()
        self.required_keys = {'type'}
        self.valid_keys = {'description', 'args', 'steps', 'type', 'contains', 'fallback', 'exit'}
        self.type_specs = {
            "type": TypeSpec(Text),
            "contains": TypeSpec(List),
            "description": TypeSpec(Text),
            "args": TypeSpec(List),
            "steps": TypeSpec(List)
        }

    def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
        errors = []

        # 验证必需的键
        errors.extend(self.validate_required_keys(content, self.required_keys, path))
        errors.extend(self.validate_spelling(content, path))
        errors.extend(self.validate_type(content, path))

        if len(errors) > 0:
            return errors

        # 验证agents列表
        if 'contains' in content:
            for i, agent_name in enumerate(content['contains']):
                if isinstance(agent_name, Dict):
                    agent_name = list(agent_name.keys())[0]
                if not isinstance(agent_name, Text):
                    errors.append(ValidationError(
                        self.__class__.__name__,
                        f"Agent reference must be a string",
                        f"{path}/contains[{i}]"
                    ))
                errors.extend(self.validate_ref(agent_name, path, context))

        if 'steps' in content:
            if not isinstance(content['steps'], List):
                errors.append(ValidationError(
                    self.__class__.__name__,
                    f"'steps' block must be a list",
                    f"{path}/steps"
                ))
            else:
                errors.extend(self.validate_steps(content['steps'], path, context))

        return errors


class KBAgentValidator(AgentValidator):
    """Knowledge Base Agent 的验证器"""

    def __init__(self):
        super().__init__()
        self.required_keys = {'type'}
        self.valid_keys = {'faq', 'web', 'file', 'sources', 'type', 'description'}
        self.type_specs = {
            "type": TypeSpec(Text),
            "web": TypeSpec(List),
            "file": TypeSpec(Text),
            "faq": TypeSpec(List),
            "sources": TypeSpec(List)
        }

    def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
        errors = []

        errors.extend(self.validate_required_keys(content, self.required_keys, path))
        errors.extend(self.validate_spelling(content, path))
        errors.extend(self.validate_type(content, path))

        return errors


class FlowAgentValidator(AgentValidator):
    """Validator for Flow Agent"""

    def __init__(self):
        super().__init__()
        self.required_keys = {'type', 'steps'}
        self.valid_keys = {'description', 'args', 'type', 'steps', 'fallback', '*'}
        self.step_schema = {
            'keywords': {'bot', 'user', 'if', 'else if', 'else', 'then', 'tries',
                         'call', 'next', 'label', 'return', 'set', 'args'},
            'string_literals': {'begin', 'end', 'user'},
            'compound_keys': {'bot', 'if', 'begin'}
        }

    def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
        errors = []

        # 验证必需的键
        errors.extend(self.validate_required_keys(content, self.required_keys, path))
        errors.extend(self.validate_spelling(content, path))

        # 验证步骤
        if 'steps' in content:
            errors.extend(self.validate_steps(content['steps'], f"{path}/steps", context))

        return errors


class LLMAgentValidator(AgentValidator):
    """Validator for LLM Agent"""
    def __init__(self):
        super().__init__()
        self.required_keys = {'type', 'prompt'}
        self.valid_keys = {'description', 'prompt', 'args', 'uses', 'type', 'steps'}
        self.type_specs = {
            "type": TypeSpec(Text),
            "description": TypeSpec(Text),
            "prompt": TypeSpec(Text),
            "args": TypeSpec(List),
            "uses": TypeSpec(List)
        }

    def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
        errors = []

        errors.extend(self.validate_required_keys(content, self.required_keys, path))
        errors.extend(self.validate_spelling(content, path))
        errors.extend(self.validate_type(content, path))

        return errors


# class MainAgentValidator(AgentValidator):
#     def __init__(self):
#         super().__init__()
#         self.valid_keys = {'call', 'schedule'}
#         self.required_keys = {'steps'}
#         self.type_specs = {
#             "steps": TypeSpec(List)
#         }
#
#     def validate(self, content: Dict[Text, Any], path: Text, context: Dict[Text, Any], code_str: Text = None) -> List[ValidationError]:
#         errors = []
#
#         # validate format problem: required_key/type
#         errors.extend(self.validate_required_keys(content, self.required_keys, path))
#         errors.extend(self.validate_type(content, path))
#         if len(errors) > 0:
#             return errors
#         # validate steps
#         errors.extend(self._validate_steps(content.get('steps'), path))
#
#         return errors
#
#     def _validate_steps(self, content: List[Any], path: Text) -> List[ValidationError]:
#         errors = []
#
#         for i, step in enumerate(content):
#             step_path = f"{path}[{i}]"
#             if 'call' not in step:
#                 errors.append(ValidationError(
#                     "StepValidation",
#                     "Keyword 'call' not found; Step must invoke an agent.",
#                     step_path
#                 ))
#             else:
#                 errors.extend(self.validate_spelling(step, step_path))
#                 if 'schedule' in step and step['schedule'] not in ['priority', 'mediator']:
#                     errors.append(ValidationError(
#                         "StepValidation",
#                         "Only two schedule methods are supported now: 'mediator' and 'priority'.",
#                         step_path
#                     ))
#
#         return errors


class Validator:
    def __init__(self):
        # 注册不同类型的验证器
        self.validators = {
            'flow agent': FlowAgentValidator,
            'llm agent': LLMAgentValidator,
            'ensemble agent': EnsembleAgentValidator,
            'kb agent': KBAgentValidator
        }

    def validate(self, agents_dict: Dict, code_str: Text = None) -> List[ValidationError]:
        """验证YAML内容"""
        if not isinstance(agents_dict, Dict):
            return [ValidationError("BasicValidation", f"Invalid agents.yml structure.")]

        errors = []

        # 创建验证上下文，包含所有agent名称
        context = {
            'all_agents': set(agents_dict.keys()) - {'main', 'tools'},  # 所有定义的agent名称
            'full_config': agents_dict  # 完整的配置内容
        }

        # 验证每个代理
        for agent_name, agent_content in agents_dict.items():
            if agent_name == 'tools':
                continue
            # if agent_name == 'main':
            #     validator = self.validators[agent_name]()
            #     errors.extend(validator.validate(
            #         agent_content,
            #         f"agent[{agent_name}]",
            #         context,
            #         code_str
            #     ))
            #     continue
            if not isinstance(agent_content, Dict):
                errors.append(ValidationError(
                    "BasicValidation",
                    f"Agent '{agent_name}' content must be a dictionary",
                    f"agent[{agent_name}]"
                ))
                continue

            # 验证type字段
            if 'type' not in agent_content:
                errors.append(ValidationError(
                    "BasicValidation",
                    "Missing 'type' field",
                    f"agent[{agent_name}]"
                ))
                continue

            agent_type = agent_content['type']
            if agent_type not in self.validators:
                errors.append(ValidationError(
                    "BasicValidation",
                    f"Invalid agent type '{agent_type}'. Valid types are: {', '.join(self.validators.keys())}",
                    f"agent[{agent_name}]/type"
                ))
                continue

            # 使用对应的验证器进行验证，传入上下文
            validator = self.validators[agent_type]()
            errors.extend(validator.validate(
                agent_content,
                f"agent[{agent_name}]",
                context,
                code_str
            ))

        return errors
