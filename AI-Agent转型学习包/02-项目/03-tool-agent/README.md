# 项目 03：工具调用 Agent（手写 ReAct）

> 对应模块：**模块 04（Tool Calling）+ 模块 05（Agent 架构）**｜建议在第 8 周完成后动手
> 难度：★★★★☆｜代码量：约 1100 行 Python

**不依赖 LangChain / LangGraph**，从零手写 ReAct 循环、工具注册表、安全护栏、上下文管理。附 LangGraph 对照版本。

---

## 一句话理解这个项目

**项目 02 是"每次都检索"，项目 03 是"模型自己决定要不要检索、检索几次、用什么词"。**

这就是 RAG 应用 → Agent 应用的关键跃迁。

---

## 项目结构

```
03-tool-agent/
├── main.py                      # CLI 入口
├── pyproject.toml
├── .env.example
├── sandbox/                     # 文件工具的沙箱目录（自动创建）
└── src/
    ├── config.py                # 模型配置
    ├── tools.py                 # ⭐ 工具定义 + 注册表（校验/超时/错误兜底）
    ├── toolkit.py               # 具体工具实现（计算/时间/天气/文件/检索）
    ├── safety.py                # ⭐ 安全护栏（危险拦截 + 人工确认）
    ├── agent.py                 # ⭐⭐ 手写 ReAct 循环（项目心脏）
    ├── context_management.py    # 上下文裁剪与摘要压缩
    └── langgraph_version.py     # LangGraph 对照实现
```

---

## 快速开始

```bash
cd 02-项目/03-tool-agent

cp .env.example .env      # 填入 DEEPSEEK_API_KEY
uv sync

# 看有哪些工具
uv run main.py --tools

# 单工具任务
uv run main.py "北京今天天气怎么样？"

# 多步任务（需要串联两个工具）
uv run main.py "现在几点？帮我算一下从今天到 2027 年元旦还有多少天"

# 需要内部知识（触发检索工具）
uv run main.py "公司的退款政策是什么？"

# 会触发【敏感操作确认】的任务
uv run main.py "帮我写个文件 note.md，内容是：明天下午三点开会"

# 交互式多轮对话
uv run main.py --chat
```

---

## 30 行看懂 ReAct

`src/agent.py` 的核心就这些：

```python
messages = [system, user]              # 1. 准备消息历史

for step in range(max_steps):          # 2. 最多循环 N 次（防死循环）
    resp = model(messages, tools)      # 3. 请求模型

    if not resp.tool_calls:            # 4a. 没有工具调用 → 结束
        return resp.content

    messages.append(assistant_msg_with_tool_calls)   # 4b. 记下调用意图

    for tc in resp.tool_calls:         # 5. 执行工具（我的代码执行！）
        result = registry.execute(tc.name, tc.args)
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    # 回到 3，带着工具结果再问一次
```

**所有 Agent 框架（LangGraph、AutoGPT、CrewAI）都是这个骨架加东西。** 记住这点，你就不会被框架绕晕。

---

## 五个必须理解的设计点（面试高频）

### 1. 模型不执行任何代码 —— 安全边界在你的代码里

看起来很神奇，实际上模型只能输出一段 JSON：

```json
{"name": "write_file", "arguments": {"filename": "note.md", "content": "..."}}
```

**真正执行的是 `registry.execute()`。** 这意味着：

- 想禁止某个操作，在 `execute` 里拦，不要指望改 prompt 让模型"自觉"
- 提示注入能骗模型输出恶意调用，但骗不过你的代码校验

### 2. 参数校验——模型会给错参数

模型会：漏必填参数、把数字传成字符串、幻觉出不存在的字段、返回非法 JSON。

`_validate_params()` 逐个检查，`agent.py` 里对 JSON 解析失败做了专门处理（不崩溃，把错误告诉模型让它自己修）。

**实测**：故意传 `calculator` 一个字符串表达式类型错误，模型收到错误信息后 90% 的情况能自己换对参数重试。

### 3. 报错处理——错误要变成"可读的观察结果"

错误不抛出，而是变成文本返回给模型：

```python
# ❌ 差的错误信息
return "FileNotFoundError"

# ✅ 好的错误信息（指导下一步）
return "文件不存在：notes.txt。请先调用 list_files 查看工作目录下有哪些文件。"
```

差的错误让模型傻乎乎重试同样的错误，好的错误让它自我修复。**这是 Agent 可靠性的关键细节。**

### 4. 死循环防御——必须有，一定会遇到

模型有时会反复调同一个工具。`max_steps` 是硬刹车。

本项目默认 8 步。达到上限后**明确告知任务未完成**，而不是假装成功：

```python
result.answer = f"已尝试 {max_steps} 步仍未完成任务，已停止以避免继续消耗。..."
```

### 5. 上下文成本——平方级增长

每轮都把全部历史发给模型（模型无状态）：

```
第 1 轮发 1 份，第 2 轮发 2 份… 累计 = n(n+1)/2
10 轮对话，累计发送 55 倍单轮量
```

`context_management.py` 给了四种策略对比，生产用「滑动窗口 + 摘要压缩」。

---

## 安全演示：亲手试一次

```bash
uv run main.py "帮我写个文件 notes.md，内容是：测试"
```

你会看到：

```
🔒 敏感操作确认
⚠️  工具 [write_file] 请求执行敏感操作：
      filename = notes.md
      content = 测试
是否允许执行？ (y/N):
```

**注意两个设计细节**：

1. **展示完整参数，不只是工具名**。模型说"写个临时文件"，实际参数可能是 `filename="../../.ssh/authorized_keys"`。必须看见真相。
2. **默认值是 N（拒绝）**。直接回车 = 取消。安全的默认值必须站在拒绝这一侧。

再试一下沙箱越界：

```bash
uv run main.py "读一下 /etc/passwd 这个文件"
```

会被 `_safe_path()` 拦下（拒绝绝对路径 + 解析后校验是否越界）。**这就是"安全边界在代码里"的具体含义。**

---

## 进阶练习

1. **加一个 shell 工具（⭐️⭐️）**：允许执行命令但必须过滤 `BLOCKED_PATTERNS`。体会"给模型执行权有多危险"。
2. **并行工具调用（⭐️⭐️）**：模型一次可能返回多个 tool_calls，现在是串行执行。改成 `ThreadPoolExecutor` 并行，对比耗时。
3. **接入项目 02 的真实 RAG（⭐️⭐️⭐️）**：把 `search_knowledge_base` 换成调用项目 02 的 `RAGAssistant`。观察 Agent 如何自主决定何时检索、检索几次。
4. **加持久化（⭐️⭐️⭐️）**：把每一步写入 sqlite，进程崩溃后能从断点续跑。这是 LangGraph Checkpointer 做的事——自己实现一遍就知道它值多少钱。
5. **写一个"失败案例集"（⭐️⭐️⭐️）**：收集 20 个 Agent 失败的例子（调错工具、参数错误、死循环），每修一个就记一条。**这是提升 Agent 质量唯一靠谱的方法。**

---

## 常见坑

| 现象 | 原因 | 解决 |
|---|---|---|
| `400 tool_call_id not found` | 忘了把带 tool_calls 的 assistant 消息加进历史 | `agent.py` 里有注释标出这个位置，检查那一段 |
| 模型不调工具，直接瞎编 | 工具 description 写得太差 | 改成"什么时候用"的写法，参考 `toolkit.py` 的注释 |
| 模型反复调同一个工具 | 工具返回的信息让它觉得"没得到答案" | 优化工具的错误信息，或在 system prompt 加"不要重复调用同一工具" |
| 任务做到一半停了 | 撞到 `max_steps` | 调大上限，或把任务拆小 |
| 成本比预期高很多 | 工具返回结果太长，每轮重发 | 用 `truncate_tool_result()` 裁剪 |
| 中文参数名导致调用失败 | 模型对中文参数名支持不稳定 | 参数名一律用英文小写下划线 |

---

## 与 LangGraph 的取舍

| 场景 | 建议 |
|---|---|
| 学习/理解原理 | **手写**（本项目） |
| 单人小项目、流程简单 | 手写够了，依赖少更可控 |
| 需要持久化、断点续跑 | LangGraph（Checkpointer 太省事） |
| 需要复杂分支/多 Agent | LangGraph（声明式条件边更清晰） |
| 需要人在环审批（Web 场景） | LangGraph（`interrupt()` 原生支持异步） |

**但无论用哪个，你都得懂下面这个 while 循环。** 不懂的话，框架出诡异行为时你无从下手。

> ⚠️ **版本坑**：LangGraph 1.0 已废弃 `langgraph.prebuilt.create_react_agent`，改用 `langchain.agents.create_agent`。网上大量教程还是旧写法。
