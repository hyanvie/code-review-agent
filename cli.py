"""
命令行交互入口。

用法：
    python cli.py

进入交互模式后：
    - 输入一个 .py 文件路径 -> 对该文件跑一次完整的 Agent 审查循环
    - 输入 history          -> 查看本次会话审查过哪些文件（体现上下文记忆）
    - 输入 exit / quit      -> 退出
"""

import sys

from agent import CodeReviewAgent
from agent.tools import ToolError


def print_banner(agent: CodeReviewAgent):
    mode = "mock 模式（未检测到 LLM_API_KEY，先用规则输出演示流程）" if agent.llm.mock_mode else f"真实模型模式（{agent.llm.model}）"
    print("=" * 60)
    print("Code Review Agent - 命令行版")
    print(f"当前运行模式：{mode}")
    print("输入代码文件路径开始审查；输入 history 查看历史；输入 exit 退出")
    print("=" * 60)


def main():
    agent = CodeReviewAgent()
    print_banner(agent)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("再见！")
            break

        if user_input.lower() == "history":
            print(agent.history_summary())
            continue

        try:
            result = agent.review_file(user_input)
        except ToolError as e:
            # 工具调用失败（比如文件不存在），给用户友好提示，不让程序崩溃
            print(f"[错误] {e}")
            continue

        print("\n" + "-" * 60)
        print(f"审查结果：{result.file_path}")
        print("-" * 60)
        print(result.review_text)
        print("-" * 60)


if __name__ == "__main__":
    sys.exit(main())
