import builtins
import importlib
import traceback
import contextlib
import io
import re
import ast
from typing import List, Dict, Any, Optional, Text

from mica.agents.functions import Function
from mica.event import BotUtter, SetSlot, AgentComplete, AgentFail
from mica.utils import logger


class ImportTransformer(ast.NodeTransformer):
    """AST transformer for handling import statements"""

    def __init__(self, allowed_modules):
        self.allowed_modules = allowed_modules
        self.required_imports = set()

    def visit_Import(self, node):
        """Handle 'import xxx' statements"""
        for alias in node.names:
            if alias.name in self.allowed_modules:
                self.required_imports.add(alias.name)
            else:
                raise ValueError(f"Module {alias.name} is not in the whitelist")
        return node

    def visit_ImportFrom(self, node):
        """Handle 'from xxx import yyy' statements"""
        if node.module in self.allowed_modules:
            self.required_imports.add(node.module)
            return node
        else:
            raise ValueError(f"Module {node.module} is not in the whitelist")


class SafePythonExecutor:
    def __init__(
            self,
            allowed_modules: Optional[List[str]] = None,
            max_execution_time: int = 30,
            max_memory_mb: int = 200
    ):
        """
        Safe code executor

        Args:
            allowed_modules: Whitelist of allowed modules to import
            max_execution_time: Maximum execution time (seconds)
            max_memory_mb: Maximum memory limit (MB)
        """
        self.allowed_modules = allowed_modules or [
            'math', 'random', 'statistics',
            'datetime', 'time', 're', 'json',
            'itertools', 'functools', 'collections',
            'requests', 'urllib', 'subprocess', 'sqlite3',
            'mysql.connector', 'logging', 'pathlib', 'typing',
            'jsonpath', 'inspect'
        ]
        self.script_namespace: Dict[Text, Any] = {}
        self.imported_modules: Dict[Text, Any] = {}
        self.functions: Dict[Text, Function] = {}

    def _safe_import(self, name, *args, **kwargs):
        """Safe import function"""
        if name in self.allowed_modules:
            if name not in self.imported_modules:
                try:
                    module = importlib.import_module(name)
                    self.imported_modules[name] = module
                except ImportError as e:
                    raise ImportError(f"Failed to import {name}: {str(e)}")
            return self.imported_modules[name]
        raise ImportError(f"Module {name} is not in the whitelist")

    def _prepare_safe_namespace(self) -> Dict[str, Any]:
        """Prepare a safe execution environment"""

        # Create a restricted __import__ function
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            return self._safe_import(name)

        # Create a copy of basic built-in functions
        safe_builtins = dict(builtins.__dict__)

        # Remove dangerous built-in functions
        for name in [
            'exec', 'eval', 'compile', 'open', 'input',
            '__import__', 'globals', 'locals', 'vars'
        ]:
            safe_builtins.pop(name, None)

        # Add safe import function
        safe_builtins['__import__'] = safe_import

        namespace = {
            '__builtins__': safe_builtins,
            '__name__': '__main__',
            '__doc__': None,
            '__package__': None,
            '__file__': '<string>',
        }

        return namespace

    def load_script(self, script_str: str) -> Dict[str, Any]:
        """
        Load a script into memory

        Args:
            script_str: Script as a string

        Returns:
            Dict containing execution status and result
        """
        # Security check patterns
        dangerous_patterns = [
            r'(exec|eval)\s*\(',
            r'__import__\s*\(',
            r'\bos\.',
            r'\bsys\.',
            r'(rmdir|unlink|chmod)',
            r'socket\.',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, script_str):
                raise ValueError(f"Dangerous code pattern detected: {pattern}")

        try:
            # Parse AST
            tree = ast.parse(script_str)

            # Analyze and transform import statements
            transformer = ImportTransformer(self.allowed_modules)
            transformed_tree = transformer.visit(tree)

            # function definition
            formatted_functions = self._extract_functions_from_script(tree)
            self.functions = {func["name"]: Function.create(**func) for func in formatted_functions}

            # Compile the transformed code
            compiled_code = compile(transformed_tree, '<string>', 'exec')

            # Prepare the namespace
            safe_namespace = self._prepare_safe_namespace()

            # Execute the code
            exec(compiled_code, safe_namespace)

            # Store the namespace
            self.script_namespace = safe_namespace

            return {
                'status': 'success',
                'message': 'Script loaded successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }

    def execute_function(self, func_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute a specified function from the loaded script

        Args:
            func_name: Function name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Dict containing execution result or error information
        """
        output = io.StringIO()
        error_output = io.StringIO()

        try:
            with contextlib.redirect_stdout(output), \
                    contextlib.redirect_stderr(error_output):

                target_func = self.script_namespace.get(func_name)
                if not target_func or not callable(target_func):
                    return {
                        'status': 'error',
                        'error': f'Function "{func_name}" not found or not callable'
                    }

                result = target_func(*args, **kwargs)
                structured_result = self._output_parser(func_name, result)
                return {
                    'status': 'success',
                    'stdout': output.getvalue(),
                    'result': structured_result
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'stderr': error_output.getvalue(),
                'traceback': traceback.format_exc()
            }

    def get(self, func_name):
        return self.functions.get(func_name)

    @staticmethod
    def _extract_functions_from_script(tree):
        functions = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                description = ""
                if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                ):

                    description = node.body[0].value.value
                    description = description.strip()

                func_name = node.name
                args = {}
                required = []
                defaults = node.args.defaults
                num_defaults = len(defaults)
                total_args = len(node.args.args)
                for i, arg in enumerate(node.args.args):
                    arg_name = arg.arg
                    arg_type = ast.unparse(arg.annotation) if arg.annotation else "string"
                    if arg_type in ["int", "float"]:
                        arg_type = "number"
                    elif arg_type == "bool":
                        arg_type = "boolean"

                    # if it is not a default parameter, then it will not in the required list
                    default_index = i - (total_args - num_defaults)

                    if default_index < 0:
                        required.append(arg_name)
                    args[arg_name] = {
                        "type": arg_type
                    }
                functions.append({
                        "name": func_name,
                        "description": description,
                        "args": args,
                        "required": required
                    }
                )

        return functions

    @staticmethod
    def _output_parser(func_name, stdout=None) -> List:
        if stdout is None:
            return []
        if not isinstance(stdout, List):
            logger.error("Parsing failed. Please format the standard output of the custom function "
                         "according to the specified requirements.")
            return []
        events = []
        for out in stdout:
            if out.get('bot'):
                events.append(BotUtter(text=out.get('bot')))
            if out.get('arg'):
                events.append(SetSlot(slot_name=out.get('arg'),
                                      value=out.get('value')))
            if out.get('status') is not None:
                if out.get('status') == 'success':
                    events.append(AgentComplete(provider=func_name, metadata=out.get('msg')))
                elif out.get('status') == 'error':
                    events.append(AgentFail(provider=func_name, metadata=out.get('msg')))
        return events
