"""
Agent 能调用的工具，目前就两个：读文件、静态检查。

静态检查没用现成的 pylint/flake8，自己拿 ast 写了个简化版，
图的是不用额外装依赖，缺点是覆盖面肯定不如专业工具全。
"""

import ast
import os


class ToolError(Exception):
    """工具执行失败时抛出，方便上层统一捕获。"""
    pass


def read_file(file_path: str) -> str:
    """
    工具 1：读取源代码文件。

    Args:
        file_path: 文件路径

    Returns:
        文件内容字符串

    Raises:
        ToolError: 文件不存在 / 读取失败时
    """
    if not os.path.isfile(file_path):
        raise ToolError(f"文件不存在：{file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise ToolError(f"文件编码不是 UTF-8，读取失败：{e}")
    except OSError as e:
        raise ToolError(f"读取文件时发生系统错误：{e}")


def static_check(code: str) -> str:
    """
    工具 2：轻量静态检查，基于 Python 自带的 ast 模块。

    不追求覆盖 pylint/flake8 那么全，只检查几类最常见、最容易在
    代码审查里被提出来的问题，作为 LLM 推理前的"预处理结果"，
    让后面 LLM 的审查更有依据，而不是空对空地瞎猜。

    检查项：
        - bare except（裸 except，吞异常）
        - 函数可变默认参数（list/dict 作为默认值的经典坑）
        - 函数过长（超过 50 行，建议拆分）
        - 函数缺少 docstring
        - 未使用的 import（简单版本，只做名称匹配，不保证 100% 准确）

    Args:
        code: 源代码字符串

    Returns:
        以 markdown 列表形式组织的检查结果文本；如果代码无法解析（语法错误），
        会把语法错误本身作为一条发现返回，而不是抛异常中断整个流程——
        静态检查失败不应该让整个 Agent 跑不下去。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"- ⚠️ 语法错误，无法完成静态检查：第 {e.lineno} 行，{e.msg}"

    findings = []

    imported_names = set()
    used_names = set()

    for node in ast.walk(tree):
        # 裸 except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(f"- 第 {node.lineno} 行：使用了裸 `except:`，会吞掉所有异常（包括 KeyboardInterrupt），建议至少捕获具体异常类型")

        # 可变默认参数
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(f"- 第 {node.lineno} 行：函数 `{node.name}` 使用了可变对象（list/dict/set）作为默认参数，多次调用会共享同一个对象，是经典的坑")

            # 函数过长
            if hasattr(node, "end_lineno") and node.end_lineno and (node.end_lineno - node.lineno) > 50:
                findings.append(f"- 第 {node.lineno} 行：函数 `{node.name}` 长度约 {node.end_lineno - node.lineno} 行，超过 50 行，建议拆分职责")

            # 缺少 docstring
            if not ast.get_docstring(node):
                findings.append(f"- 第 {node.lineno} 行：函数 `{node.name}` 没有 docstring，建议补充说明用途、参数和返回值")

        # 收集 import 和使用情况（简单版，用于查未使用的 import）
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name.split(".")[0])
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        if isinstance(node, ast.Attribute):
            pass  # 属性访问这里不展开处理，避免误判

    unused = imported_names - used_names
    for name in sorted(unused):
        findings.append(f"- 疑似未使用的 import：`{name}`（简单名称匹配，如果是 `as` 重命名或者只在类型注解里用到，可能是误报，人工确认一下）")

    if not findings:
        return "（静态检查未发现明显问题）"

    return "\n".join(findings)
