"""
LLM 调用这块单独拎出来一个文件。

走的是 OpenAI 兼容接口，不是因为非要用 OpenAI，是因为国内大部分模型服务
（通义千问、DeepSeek、智谱等）现在基本都兼容这个格式，改个 base_url 就能换，
不用每家都单独写一套调用逻辑。

没有 key 的时候会自动切 mock 模式，不然本地没 key 根本没法跑起来调试。
调用失败也加了重试，别网络抖一下整个程序就挂了。
"""

import os
import time


class LLMError(Exception):
    """多次重试后仍然失败时抛出。"""
    pass


class LLMClient:
    def __init__(self, model: str = None, max_retries: int = 3, base_delay: float = 1.0):
        """
        Args:
            model: 模型名，不传就从环境变量 LLM_MODEL 读，再不行用默认值
            max_retries: 最大重试次数
            base_delay: 重试的基础等待时间（秒），每次重试翻倍（指数退避）
        """
        self.api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.mock_mode = not bool(self.api_key)

        self._client = None
        if not self.mock_mode:
            try:
                from openai import OpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                # 没装 openai 包也不至于直接崩，退化成 mock 模式
                self.mock_mode = True

    def chat(self, messages: list) -> str:
        """
        调用 LLM，带指数退避重试。

        Args:
            messages: OpenAI 格式的消息列表 [{"role": ..., "content": ...}, ...]

        Returns:
            模型回复的文本内容

        Raises:
            LLMError: 重试用完依然失败
        """
        if self.mock_mode:
            return self._mock_reply(messages)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                )
                return response.choices[0].message.content
            except Exception as e:  # noqa: BLE001 - 这里故意兜底所有异常，统一走重试逻辑
                last_error = e
                if attempt < self.max_retries:
                    wait = self.base_delay * (2 ** (attempt - 1))
                    print(f"[llm_client] 第 {attempt} 次调用失败（{e}），{wait:.1f}s 后重试...")
                    time.sleep(wait)
                else:
                    print(f"[llm_client] 已重试 {self.max_retries} 次仍失败，改用本地静态检查结果作为兜底输出")

        # 重试全部失败后不直接崩掉整个程序，而是退化成基于静态检查结果的简单报告，
        # 保证用户至少能拿到一份"降级版"的审查结果
        return self._mock_reply(messages, failure_note=str(last_error))

    def _mock_reply(self, messages: list, failure_note: str = None) -> str:
        """
        没有 key（或者调用彻底失败）时的兜底回复。

        直接把 static_check 的结果整理成一份简化版报告返回，
        这样整条 Agent 流程（输入 -> 推理 -> 工具调用 -> 输出）依然能跑通，
        只是"推理"这步退化成了规则匹配而不是真正的 LLM 推理。
        """
        user_content = messages[-1]["content"] if messages else ""
        header = "【Mock 模式输出】当前没有配置可用的 LLM API Key"
        if failure_note:
            header = f"【降级输出】LLM 调用多次失败（{failure_note}），以下是基于静态检查的简化报告"

        return (
            f"{header}\n\n"
            "## 1. 总体评价\n"
            "未接入真实模型，以下内容仅基于静态检查规则生成，仅供流程演示参考。\n\n"
            "## 2. 发现的问题\n"
            f"{self._extract_findings(user_content)}\n\n"
            "## 3. 改进建议\n"
            "- 配置 LLM_API_KEY 环境变量后即可获得真实模型给出的详细审查意见\n\n"
            "## 4. 代码亮点\n"
            "- （mock 模式下无法评估代码亮点，需要真实模型调用）\n"
        )

    @staticmethod
    def _extract_findings(user_content: str) -> str:
        """从 prompt 文本里把"静态检查工具的初步发现"那一段抠出来复用。"""
        marker = "## 静态检查工具的初步发现"
        if marker not in user_content:
            return "（无静态检查结果）"
        after = user_content.split(marker, 1)[1]
        # 截取到下一个 "## " 标题之前
        if "\n## " in after:
            after = after.split("\n## ", 1)[0]
        return after.strip()
