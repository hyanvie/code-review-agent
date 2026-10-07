"""
Prompt 模板放这一个文件里，单独改措辞不用动代码逻辑。
"""

SYSTEM_PROMPT = """你是一个资深的代码审查助手（Code Review Agent）。
你的任务是阅读用户提供的代码，结合静态检查工具给出的初步结果，
输出一份结构化的代码审查报告。

报告请按以下结构输出：
1. 总体评价（1-2 句话）
2. 发现的问题（按严重程度从高到低排列，每条说明：位置、问题描述、为什么是问题）
3. 改进建议（具体、可执行，最好带修改后的代码片段）
4. 代码亮点（如果有可取之处也指出来，不用全是挑刺）

请用中文回答，语气专业但不要太生硬，像学长/学姐给同学 code review 的感觉。
"""

REVIEW_USER_TEMPLATE = """## 待审查文件
文件路径：{file_path}

## 代码内容
```python
{code}
```

## 静态检查工具的初步发现
{static_findings}

## 历史审查上下文（同一会话里之前审查过的文件，供你参考风格是否一致，没有就是空）
{memory_context}

请基于以上信息给出审查报告。
"""


def build_review_messages(file_path: str, code: str, static_findings: str, memory_context: str):
    """组装一次完整对话需要的 messages 列表（Agent 推理这一步要用）。"""
    user_content = REVIEW_USER_TEMPLATE.format(
        file_path=file_path,
        code=code,
        static_findings=static_findings or "（静态检查未发现明显问题）",
        memory_context=memory_context or "（无历史记录）",
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
