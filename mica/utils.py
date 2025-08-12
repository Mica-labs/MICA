import io
import json
import os
import re
from typing import Text
import logging
import uuid

from logging.config import dictConfig

# log setting
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(filename)-18s - %(levelname)-6s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "console_file": {
            "format": "%(asctime)s - %(filename)-18s - %(levelname)-6s -     %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console-default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
        },
        "console-indent": {
            "class": "logging.StreamHandler",
            "formatter": "console_file",
            "level": "DEBUG",
        },
        "file-default": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default",
            "level": "DEBUG",
        },
        "file-indent": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "console_file",
            "level": "DEBUG",
        },
    },
    "root": {
        "handlers": ["console-default", "file-default"],
        "level": "INFO",
    },
    "loggers": {
        "user_info": {
            "handlers": ["console-default", "file-default"],
            "level": "DEBUG",
            "propagate": False,
        },
        "sys_info": {
            "handlers": ["console-indent", "file-indent"],
            "level": "DEBUG",
            "propagate": False,
        },
        "bot_info": {
            "handlers": ["console-default", "file-default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
dictConfig(LOGGING_CONFIG)

# Web log stream - for frontend display
import io

class WebLogFormatter(logging.Formatter):
    """Custom formatter for web logs with user_info (left) and bot_info (right) alignment"""
    
    def __init__(self, total_width=120):
        super().__init__()
        self.total_width = total_width
    
    def get_display_width(self, text):
        """Calculate the actual display width considering different character types"""
        width = 0
        for char in text:
            if ord(char) > 127:  # Non-ASCII characters (including Chinese)
                width += 2
            elif char in '[](){}/?\\|<>.,;:!@#$%^&*+`~"\'':  # Special symbols that might be narrower
                width += 0.9  # Slightly less than full width
            else:
                width += 1
        return width
    
    def calculate_precise_padding(self, content, target_width):
        """Calculate padding more precisely to account for font rendering differences"""
        display_width = self.get_display_width(content)
        padding_needed = target_width - display_width
        
        # # Add extra compensation for potential font rendering differences
        # # This is an empirical adjustment based on your observation
        # if padding_needed > 0:
        #     # For every special character, add a bit more padding
        #     special_chars = sum(1 for c in content if c in '[](){}/?\\|<>.,;:!@#$%^&*-=+`~"\'')
        #     compensation = special_chars * 0.2
        #     padding_needed += compensation
        
        return max(0, int(padding_needed))
    
    def truncate_to_width(self, text, max_width):
        """Truncate text to fit within max_width display characters"""
        if self.get_display_width(text) <= max_width:
            return text
        
        result = ""
        current_width = 0
        
        for char in text:
            char_width = 2 if ord(char) > 127 else 1
            if current_width + char_width > max_width - 3:  # Reserve 3 chars for "..."
                return result + "..."
            result += char
            current_width += char_width
        
        return result
    
    def format(self, record):
        level = record.levelname
        message = record.getMessage()
        
        if record.name == "user_info":
            # Left-aligned format: level | message
            base_message = f"{message}"
            # Truncate if too long to prevent line wrapping
            formatted_message = self.truncate_to_width(base_message, self.total_width)
            return formatted_message
        elif record.name == "sys_info":
            base_message = f"    {message}"
            formatted_message = self.truncate_to_width(base_message, self.total_width)
            return formatted_message
        elif record.name == "bot_info":
            # Right-aligned format: level | spaces + message (message ends at right edge)
            available_width = self.total_width
            
            if self.get_display_width(message) > available_width:
                message = self.truncate_to_width(message, available_width)
            
            # Use precise padding calculation
            complete_content = message
            padding_needed = self.calculate_precise_padding(complete_content, self.total_width)
            
            if padding_needed > 0:
                formatted_message = " " * padding_needed + message
            else:
                formatted_message = complete_content
            
            return formatted_message
        
        else:
            # Default format for any other loggers
            return f" {message}"

web_log_stream = io.StringIO()
web_handler = logging.StreamHandler(web_log_stream)

# Set total width for alignment (adjust based on your dialog box width)
TOTAL_WIDTH = 90  # You can adjust this value

web_handler.setFormatter(WebLogFormatter(total_width=TOTAL_WIDTH))
web_handler.setLevel(logging.INFO)  # Only record INFO and above

# Add web handler to the specific loggers
user_info_logger = logging.getLogger("user_info")
user_info_logger.addHandler(web_handler)
logger = logging.getLogger("sys_info")
logger.addHandler(web_handler)
bot_info_logger = logging.getLogger("bot_info")
bot_info_logger.addHandler(web_handler)

def get_web_log_contents():
    """Get the log contents for the frontend (only INFO level and above)"""
    return web_log_stream.getvalue()

def clear_web_log_contents():
    """Clear the web log buffer"""
    web_log_stream.seek(0)
    web_log_stream.truncate(0)

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
    # regex, match operator and operand (==, !=, <=, >=, <, >)
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
        # check if entering regex
        if any(expression[i:].startswith(delim) for delim in regex_delimiters):
            start = i
            # find the start and end of the regex function
            regex_start = expression.find("(", start)
            regex_end = find_matching_paren(expression, regex_start)
            regex_expr = expression[start:regex_end + 1]

            # replace variables in regex
            regex_expr = replace_context_values(regex_expr, tracker, flow_name)
            parsed_expression.append(regex_expr)
            i = regex_end + 1
        elif expression[i:i+3] == "and" or expression[i:i+2] == "or" or expression[i] in "()":
            # add logical operators and parentheses directly
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
            # match single condition expression
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

    # generate the final expression string
    final_expression = " ".join(parsed_expression)
    print("this is the final expression", final_expression)
    # calculate the expression result
    try:
        result = eval(final_expression)
    except Exception as e:
        result = f"Error evaluating expression: {e}"

    return result

def replace_context_values(regex_expr, tracker, flow_name):
    """replace variables in regex with context values"""
    for key, value in tracker.get_args(flow_name).items():
        regex_expr = regex_expr.replace(key, repr(value))
    return regex_expr

def find_matching_paren(text, start_index):
    """find the matching closing parenthesis in the string"""
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
    if not isinstance(input_str, Text):
        return ""
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


class ExpressionParser:
    def __init__(self, expr_str):
        self.expr_str = expr_str
        self.pos = 0
        self.tokens = self._tokenize(expr_str)
        self.current_token = 0

    def _tokenize(self, expr_str):
        # Split the expression into tokens
        # Handle parentheses, logical operators, and comparison expressions
        tokens = []
        i = 0
        while i < len(expr_str):
            if expr_str[i].isspace():
                i += 1
                continue
            elif expr_str[i] == '(':
                tokens.append('(')
                i += 1
            elif expr_str[i] == ')':
                tokens.append(')')
                i += 1
            elif self._is_logical_operator(expr_str, i, 'and'):
                tokens.append('and')
                i += 3
            elif self._is_logical_operator(expr_str, i, 'or'):
                tokens.append('or')
                i += 2
            elif expr_str[i:i + 8] == 're.match':
                # Handle regular expression
                j = i
                paren_count = 0
                while j < len(expr_str):
                    if expr_str[j] == '(':
                        paren_count += 1
                    elif expr_str[j] == ')':
                        paren_count -= 1
                        if paren_count == 0:
                            break
                    j += 1
                if j < len(expr_str):
                    tokens.append(expr_str[i:j + 1])
                    i = j + 1
                else:
                    raise ValueError("Unmatched parentheses in regex expression")
            else:
                # Handle general comparison expressions (a == b, a != b, a > b, etc.)
                j = i
                while j < len(expr_str) and expr_str[j] not in '()' and not self._is_logical_operator(expr_str, j, 'and') and not self._is_logical_operator(expr_str, j, 'or'):
                    j += 1
                if i != j:
                    expr = expr_str[i:j].strip()
                    if expr:
                        tokens.append(expr)
                i = j

        return tokens

    def _is_logical_operator(self, expr_str, pos, operator):
        """
        check if the specified position is a logical operator (not part of a variable name)
        
        Args:
            expr_str: expression string
            pos: current position
            operator: the operator to check ('and' or 'or')
        
        Returns:
            bool: if it is a standalone logical operator, return True, otherwise return False
        """
        op_len = len(operator)
        
        # check if the string length is enough
        if pos + op_len > len(expr_str):
            return False
        
        # check if the operator itself matches (ignore case)
        if expr_str[pos:pos + op_len].lower() != operator.lower():
            return False
        
        # check if the operator is preceded by a character
        if pos > 0:
            prev_char = expr_str[pos - 1]
            # if the character before is a letter, number, underscore, or dot, it is part of a variable name
            if prev_char.isalnum() or prev_char in '_.':
                return False
        
        # check if the operator is followed by a character
        if pos + op_len < len(expr_str):
            next_char = expr_str[pos + op_len]
            # if the character after is a letter, number, underscore, or dot, it is part of a variable name
            if next_char.isalnum() or next_char in '_.':
                return False
        
        return True

    def parse(self):
        return self._parse_expression()

    def _parse_expression(self):
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self.current_token < len(self.tokens) and self.tokens[self.current_token] == 'or':
            self.current_token += 1
            right = self._parse_and()
            left = {'type': 'or', 'left': left, 'right': right}
        return left

    def _parse_and(self):
        left = self._parse_primary()
        while self.current_token < len(self.tokens) and self.tokens[self.current_token] == 'and':
            self.current_token += 1
            right = self._parse_primary()
            left = {'type': 'and', 'left': left, 'right': right}
        return left

    def _parse_primary(self):
        if self.current_token >= len(self.tokens):
            raise ValueError("Incomplete expression")

        token = self.tokens[self.current_token]
        self.current_token += 1

        if token == '(':
            expr = self._parse_expression()
            if self.current_token >= len(self.tokens) or self.tokens[self.current_token] != ')':
                raise ValueError("Unmatched parentheses")
            self.current_token += 1
            return expr
        elif token.startswith('re.match'):
            # Handle regex expression
            match = re.match(r're\.match\((.*?), (.*?)\)', token)
            if match:
                pattern = match.group(1)
                arg_name = match.group(2)
                return {'type': 'regex', 'pattern': pattern, 'arg_name': arg_name}
            else:
                raise ValueError(f"Invalid regex expression: {token}")
        else:
            # Handle comparison expressions
            if "==" in token:
                parts = token.split("==")
                if len(parts) == 2:
                    return {'type': 'eq', 'left': parts[0].strip(), 'right': parts[1].strip()}
            elif "!=" in token:
                parts = token.split("!=")
                if len(parts) == 2:
                    return {'type': 'neq', 'left': parts[0].strip(), 'right': parts[1].strip()}
            elif ">=" in token:
                parts = token.split(">=")
                if len(parts) == 2:
                    return {'type': 'ge', 'left': parts[0].strip(), 'right': parts[1].strip()}
            elif "<=" in token:
                parts = token.split("<=")
                if len(parts) == 2:
                    return {'type': 'le', 'left': parts[0].strip(), 'right': parts[1].strip()}
            elif ">" in token:
                parts = token.split(">")
                if len(parts) == 2:
                    return {'type': 'gt', 'left': parts[0].strip(), 'right': parts[1].strip()}
            elif "<" in token:
                parts = token.split("<")
                if len(parts) == 2:
                    return {'type': 'lt', 'left': parts[0].strip(), 'right': parts[1].strip()}

            raise ValueError(f"Unable to parse expression: {token}")


def evaluate_expression(expr_tree, tracker, revoke_agent_name):
    """
    Evaluate the expression based on the parse tree and argument values

    Args:
        expr_tree: parsed expression tree
        tracker: Tracker, provide arg value
        revoke_agent_name: string, the default agent name in an arg_path

    Returns:
        Boolean result of the expression
    """
    if expr_tree['type'] == 'and':
        return evaluate_expression(expr_tree['left'], tracker, revoke_agent_name) \
               and evaluate_expression(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'or':
        return evaluate_expression(expr_tree['left'], tracker, revoke_agent_name) \
               or evaluate_expression(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'eq':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               == _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'neq':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               != _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'gt':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               > _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'lt':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               < _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'ge':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               >= _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'le':
        return _get_value(expr_tree['left'], tracker, revoke_agent_name) \
               <= _get_value(expr_tree['right'], tracker, revoke_agent_name)
    elif expr_tree['type'] == 'regex':
        pattern = expr_tree['pattern'].strip("'\"")
        arg_name = expr_tree['arg_name'].strip()
        arg_val = _get_value(arg_name, tracker, revoke_agent_name)
        if arg_val is None:
            return False
        return bool(re.match(pattern, str(arg_val)))
    else:
        raise ValueError(f"Unknown expression type: {expr_tree['type']}")


def _get_value(val_str, tracker, revoke_agent_name):
    """
    Retrieve the value from the string; if it's a parameter name, get it from the tracker,
    otherwise try converting to appropriate type.
    """
    val_str = val_str.strip()

    if val_str == "None":
        return None
    if val_str == "True":
        return True
    elif val_str == "False":
        return False

    if '.' in val_str and not (val_str.startswith('"') or val_str.startswith("'")):
        parts = val_str.split('.')
        if len(parts) == 2:
            agent_name, arg_name = parts
            value, is_exist = tracker.get_arg(agent_name, arg_name)
            if is_exist:
                return value

    value, is_exist = tracker.get_arg(revoke_agent_name, val_str)
    if is_exist:
        return value

    if not (val_str.startswith('"') or val_str.startswith("'")):
        if '.' in val_str:
            try:
                return float(val_str)
            except ValueError:
                pass
        else:
            try:
                return int(val_str)
            except ValueError:
                pass

    if (val_str.startswith('"') and val_str.endswith('"')) or \
       (val_str.startswith("'") and val_str.endswith("'")):
        return val_str[1:-1]

    return val_str


def parse_and_evaluate(expr_str, tracker, revoke_agent_name):
    """
    Parse and evaluate an expression

    Args:
        expr_str: expression string
        tracker: Tracker, provide arg value
        revoke_agent_name: string, the default agent name in an arg_path

    Returns:
        Boolean result
    """
    parser = ExpressionParser(expr_str)
    expr_tree = parser.parse()
    return evaluate_expression(expr_tree, tracker, revoke_agent_name)


def get_expression_from_condition(condition: Text, tracker, revoke_agent_name=None):
    expr_tree = parser.parse(condition)
    return evaluate_expression(expr_tree, tracker, revoke_agent_name)

