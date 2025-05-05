import io
import json
import os
import re
from typing import Text
import logging
import uuid

from logging.config import dictConfig

# 定义日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s.%(filename)-25s - %(levelname)-8s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default",
            "level": "DEBUG",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "LLMChatbot": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("LLMChatbot")

def read_file(filename, encoding="utf-8"):
    """Read text from a file."""
    with io.open(filename, encoding=encoding) as f:
        return f.read()


def read_yaml_file(filename):
    """Read contents of `filename` interpreting them as yaml."""
    return read_yaml_string(read_file(filename))


def read_yaml_string(string):
    import ruamel.yaml

    yaml_parser = ruamel.yaml.YAML(typ="safe")
    yaml_parser.version = "1.1"
    yaml_parser.unicode_supplementary = True

    return yaml_parser.load(string)


def interpolator_text(text, slot_dict):
    try:
        text = re.sub(r"{([^\n{}]+?)}", r"{0[\1]}", text)
        text = text.format(slot_dict)
        if "0[" in text:
            # regex replaced tag but format did not replace
            # likely cause would be that tag name was enclosed
            # in double curly and format func simply escaped it.
            # we don't want to return {0[SLOTNAME]} thus
            # restoring original value with { being escaped.
            return text.format({})
        return text
    except Exception as e:
        print("cannot find slot ", e)
        return text


def number_to_uppercase_letter(number):
    if 0 <= number <= 25:
        return chr(ord('A') + number)
    else:
        raise ValueError("Number must be between 0 and 25")


def find_config_files(directory):
    yml_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.yml'):
                yml_files.append(os.path.join(root, file))
    return yml_files


def save_file(file_name, content):
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(content)


def extract_expression_parts(expression: Text):
    # 正则表达式，匹配操作数和操作符（==, !=, <, >, <=, >=）
    pattern = r'(\S+)\s*(==|!=|<=|>=|<|>)\s*(\S+)'

    match = re.match(pattern, expression)
    if match:
        operand1 = match.group(1)
        operator = match.group(2)
        operand2 = match.group(3)

        if operand2 == "None":
            operand2 = None
        else:
            try:
                operand2 = int(operand2)
            except ValueError:
                try:
                    operand2 = float(operand2)
                except ValueError:
                    pass
        return operand1, operator, operand2
    else:
        return None, None, None


def parse_and_evaluate_expression(expression, tracker=None, flow_name=None):
    if tracker is None:
        tracker = {}

    parsed_expression = []
    i = 0
    regex_delimiters = ["re.match", "re.search", "re.fullmatch"]

    while i < len(expression):
        # 检查是否进入正则表达式
        if any(expression[i:].startswith(delim) for delim in regex_delimiters):
            start = i
            # 查找正则表达式函数的起始和结束括号
            regex_start = expression.find("(", start)
            regex_end = find_matching_paren(expression, regex_start)
            regex_expr = expression[start:regex_end + 1]

            # 替换正则表达式中的变量
            regex_expr = replace_context_values(regex_expr, tracker, flow_name)
            parsed_expression.append(regex_expr)
            i = regex_end + 1
        elif expression[i:i+3] == "and" or expression[i:i+2] == "or" or expression[i] in "()":
            # 直接添加逻辑运算符和括号
            if expression[i:i+3] == "and":
                parsed_expression.append("and")
                i += 3
            elif expression[i:i+2] == "or":
                parsed_expression.append("or")
                i += 2
            else:
                parsed_expression.append(expression[i])
                i += 1
        else:
            # 匹配单个条件表达式
            condition_match = re.match(r'(\w+\s*[!=<>]=?\s*\w+)', expression[i:])
            if condition_match:
                token = condition_match.group()
                parts = re.split(r'([!=<>]=?)', token)
                if len(parts) == 3:
                    left, operator, right = parts[0].strip(), parts[1], parts[2].strip()
                    arg_info = arg_format(left, flow_name)
                    left_val, _ = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
                    arg_info = arg_format(right, flow_name)
                    right_val, _ = tracker.get_arg(agent_name=arg_info["flow_name"], arg_name=arg_info["arg_name"])
                    parsed_expression.append(f"{left_val} {operator} {right_val}")
                i += len(token)
            else:
                i += 1

    # 生成完整的表达式字符串
    final_expression = " ".join(parsed_expression)
    print("this is the final expression", final_expression)
    # 计算表达式结果
    try:
        result = eval(final_expression)
    except Exception as e:
        result = f"Error evaluating expression: {e}"

    return result

def replace_context_values(regex_expr, tracker, flow_name):
    """替换正则表达式中的变量为context中的值"""
    for key, value in tracker.get_args(flow_name).items():
        regex_expr = regex_expr.replace(key, repr(value))
    return regex_expr

def find_matching_paren(text, start_index):
    """在字符串中查找与给定索引处的开括号匹配的闭括号位置"""
    stack = 1
    for i in range(start_index + 1, len(text)):
        if text[i] == "(":
            stack += 1
        elif text[i] == ")":
            stack -= 1
            if stack == 0:
                return i
    raise ValueError("No matching closing parenthesis found")

def arg_format(statement, flow_name):
    pattern = r"^(.+)\.(.+)$"
    match = re.match(pattern, statement)
    if match:
        flow_name = match.group(1)
        statement = match.group(2)
    return {"flow_name": flow_name,
            "arg_name": statement}


def replace_args_in_string(input_str, flow_name, tracker):
    """
    Replaces variables enclosed in {} with corresponding values from vars_dict.

    Parameters:
    s (str): The input string containing variables in {}.
    vars_dict (dict): A dictionary mapping variable names to their values.

    Returns:
    str: The string with variables replaced by their corresponding values.
    """
    # Pattern to match {variable_name}
    pattern = re.compile(r'\$\{([^}]+)\}')

    # Function to replace each match with the corresponding value
    def replace_match(match):
        arg = match.group(1)
        arg_info = arg_format(arg, flow_name)
        value, exist = tracker.get_arg(arg_info["flow_name"], arg_info["arg_name"])
        if not exist or value is None:
            return ""
        return str(value)

    # Replace all occurrences of the pattern
    result = pattern.sub(replace_match, input_str)

    return result


def safe_json_loads(json_str):
    """
    Safely parse a JSON string. Return an empty dictionary if parsing fails.

    Args:
        json_str (str): The JSON string to parse.

    Returns:
        dict: Parsed dictionary if valid JSON, otherwise an empty dictionary.
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def short_uuid(length=8):
    return str(uuid.uuid4()).replace("-", "")[:length]
