"""
Agent 主循环在这里。

顺序是输入 -> 工具调用（读文件 + 静态检查）-> 推理（LLM）-> 输出，
跟 PPT 上写的"输入->推理->工具调用->输出"反了一下工具调用和推理的顺序，
原因见 DESIGN.md。
"""

from .llm_client import LLMClient
from .prompts import build_review_messages
from .tools import ToolError, read_file, static_check


class ReviewResult:
    """一次审查的结果，方便在 CLI 层和记忆模块里统一处理。"""

    def __init__(self, file_path: str, static_findings: str, review_text: str):
        self.file_path = file_path
        self.static_findings = static_findings
        self.review_text = review_text


class CodeReviewAgent:
    """
    代码审查 Agent。

    职责划分很明确：
        - self.memory      存上下文记忆（本次会话审查过哪些文件、结论是什么）
        - self.llm         负责"推理"这一步
        - tools 模块里的函数  负责"工具调用"这一步
        - review_file()    把上面几步串成一条完整的 Agent 循环
    """

    def __init__(self, llm_client: LLMClient = None, memory_limit: int = 5):
        self.llm = llm_client or LLMClient()
        self.memory: list[ReviewResult] = []
        self.memory_limit = memory_limit  # 只保留最近 N 次，避免 prompt 无限增长

    def review_file(self, file_path: str) -> ReviewResult:
        """
        对外暴露的主入口：完整走一遍 Agent 循环。

        流程：
            1. 工具调用 —— read_file 读取源码
            2. 工具调用 —— static_check 做 AST 静态检查
            3. 推理     —— 把代码 + 静态检查结果 + 历史记忆丢给 LLM
            4. 输出     —— 整理成 ReviewResult，同时写入记忆

        异常处理：
            - 工具调用失败（文件不存在、编码错误等）会直接抛出 ToolError，
              交给调用方（CLI 层）捕获并给用户友好提示，不会让程序崩溃退出。
            - LLM 调用失败的重试/降级逻辑在 LLMClient 内部已经处理掉了，
              这里拿到的 review_text 一定是可用的字符串。
        """
        # ---- 1. 工具调用：读文件 ----
        code = read_file(file_path)  # 可能抛 ToolError，交给上层处理

        # ---- 2. 工具调用：静态检查 ----
        findings = static_check(code)

        # ---- 3. 推理：构造 prompt 并调用 LLM ----
        memory_context = self._build_memory_context()
        messages = build_review_messages(
            file_path=file_path,
            code=code,
            static_findings=findings,
            memory_context=memory_context,
        )
        review_text = self.llm.chat(messages)

        # ---- 4. 输出 + 写入记忆 ----
        result = ReviewResult(file_path=file_path, static_findings=findings, review_text=review_text)
        self._remember(result)
        return result

    def _build_memory_context(self) -> str:
        """把最近几次审查结果压缩成一小段文本，作为上下文记忆喂给 LLM。"""
        if not self.memory:
            return ""
        lines = []
        for item in self.memory[-self.memory_limit:]:
            lines.append(f"- 曾审查过 `{item.file_path}`，发现问题数（静态检查行数估计）：{len(item.static_findings.splitlines())}")
        return "\n".join(lines)

    def _remember(self, result: ReviewResult) -> None:
        self.memory.append(result)
        if len(self.memory) > self.memory_limit:
            self.memory.pop(0)

    def history_summary(self) -> str:
        """给 CLI 的 `history` 命令用，列出本次会话审查过的文件。"""
        if not self.memory:
            return "（本次会话还没有审查过任何文件）"
        return "\n".join(f"{i+1}. {r.file_path}" for i, r in enumerate(self.memory))
