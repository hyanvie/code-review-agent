# Code Review Agent

软件工程课 Homework 1。方向选的是代码审查 Agent：给一个 Python 文件，先用静态检查
扫一遍，再把代码和检查结果丢给 LLM，让它给一份 review 报告。

## 怎么跑

```bash
pip install -r requirements.txt
python cli.py
```

进去之后直接输文件路径就行，比如先拿项目自带的示例文件试一下：

```
> examples/sample_bad_code.py
```

其他命令：`history` 看这次会话审查过哪些文件，`exit` 退出。

不装 `openai` 包、或者没配 key 也能跑，会自动切到 mock 模式，用静态检查的结果拼一份
简化报告，先把流程跑通。想接真实模型就设几个环境变量（任意 OpenAI 兼容接口都行，所以
国内模型也能用）：

```bash
export LLM_API_KEY="你的key"
export LLM_BASE_URL="https://xxx/v1"   # 不设的话默认走 OpenAI 官方
export LLM_MODEL="gpt-4o-mini"
```

## 大概怎么搭的

流程是：读文件 → 静态检查（ast 写的，查裸 except、可变默认参数、超长函数、缺 docstring、
疑似没用的 import）→ 把代码和检查结果一起发给 LLM → 输出报告，同时存进本次会话的记忆里。

PPT 上要求的循环顺序是"输入→推理→工具调用→输出"，我这里是先调工具再推理——因为代码审查
这个任务得先把代码内容和静态检查结果准备好，LLM 才有东西可分析，不然第一轮推理根本没见过
代码，没法先推理。

LLM 那块单独封装了一层（`agent/llm_client.py`），失败了会重试几次（指数退避），重试完还是
不行就降级成只用静态检查结果拼的简化版报告，不会直接崩掉或者卡住。

## 目录结构

```
code-review-agent/
├── agent/
│   ├── agent_core.py   # 主循环 + 记忆
│   ├── llm_client.py   # LLM 调用，带重试和 mock 降级
│   ├── prompts.py      # prompt 模板
│   └── tools.py        # read_file / static_check
├── examples/sample_bad_code.py
├── cli.py
├── requirements.txt
├── DESIGN.md            # 更细的设计说明
└── README.md
```

## 有哪些没做完 / 能扩展的

- 静态检查是自己拿 ast 写的，没有 pylint 那么全，未用 import 检测只是简单名称匹配，有误报
  概率。
- 只能单文件审查，还没支持整个目录批量扫。
- 记忆只在这次运行有效，程序关了就没了，没做持久化。

有空的话可以把静态检查换成接真的 pylint，或者加个本地文件存历史记录。
