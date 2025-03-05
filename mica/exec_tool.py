import builtins
import importlib
import traceback
import contextlib
import io
import re
import ast
from typing import List, Dict, Any, Optional, Text

from mica.agents.functions import Function


class ImportTransformer(ast.NodeTransformer):
    """AST转换器，用于处理import语句"""

    def __init__(self, allowed_modules):
        self.allowed_modules = allowed_modules
        self.required_imports = set()

    def visit_Import(self, node):
        """处理 import xxx 语句"""
        for alias in node.names:
            if alias.name in self.allowed_modules:
                self.required_imports.add(alias.name)
            else:
                raise ValueError(f"Module {alias.name} is not in the whitelist")
        return node

    def visit_ImportFrom(self, node):
        """处理 from xxx import yyy 语句"""
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
        安全代码执行器

        Args:
            allowed_modules: 允许导入的模块白名单
            max_execution_time: 最大执行时间(秒)
            max_memory_mb: 最大内存限制(MB)
        """
        self.allowed_modules = allowed_modules or [
            'math', 'random', 'statistics',
            'datetime', 'time', 're', 'json',
            'itertools', 'functools', 'collections',
            'requests', 'urllib', 'subprocess', 'sqlite3',
            'mysql.connector', 'logging', 'pathlib', 'typing'
        ]
        self.script_namespace: Dict[Text, Any] = {}
        self.imported_modules: Dict[Text, Any] = {}
        self.functions: Dict[Text, Function] = {}

    def _safe_import(self, name, *args, **kwargs):
        """安全导入函数"""
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
        """准备安全的执行环境"""

        # 创建一个受限的 __import__ 函数
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            return self._safe_import(name)

        # 创建基础内置函数的副本
        safe_builtins = dict(builtins.__dict__)

        # 移除危险的内置函数
        for name in [
            'exec', 'eval', 'compile', 'open', 'input',
            '__import__', 'globals', 'locals', 'vars'
        ]:
            safe_builtins.pop(name, None)

        # 添加安全的import函数
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
        加载脚本到内存

        Args:
            script_str: 脚本字符串

        Returns:
            Dict 包含执行状态和结果
        """
        # 安全性检查模式
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
            # 解析AST
            tree = ast.parse(script_str)

            # 分析和转换导入语句
            transformer = ImportTransformer(self.allowed_modules)
            transformed_tree = transformer.visit(tree)

            # function definition
            formatted_functions = self._extract_functions_from_script(tree)
            self.functions = {func["name"]: Function.create(**func) for func in formatted_functions}

            # 编译转换后的代码
            compiled_code = compile(transformed_tree, '<string>', 'exec')

            # 准备命名空间
            safe_namespace = self._prepare_safe_namespace()

            # 执行代码
            exec(compiled_code, safe_namespace)

            # 存储命名空间
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
        执行已加载脚本中的指定函数

        Args:
            func_name: 函数名
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Dict 包含执行结果或错误信息
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
                return {
                    'status': 'success',
                    'stdout': output.getvalue(),
                    'result': result
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
