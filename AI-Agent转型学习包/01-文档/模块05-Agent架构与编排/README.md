# 模块 05：Agent 架构与编排

> 对应周次：**W7–W8**｜预计耗时：**25–30 小时**
> 前置要求：完成模块 04（必须已经理解工具调用的机制）
>
> 本模块分两部分：
> - **Part A（W7）**：Agent 原理与 LangGraph 基础
> - **Part B（W8）**：记忆、中断、人在环

---

## 一、这个模块要解决什么问题

**一句话**：让模型**自己决定**要用几步、调哪些工具来完成任务——而不是你写死流程。

学完这一模块，你应该能回答：

- Agent 和"带工具的聊天机器人"到底差在哪？
- ReAct 是什么？为什么它有效？它会怎么失败？
- 什么时候该用 Agent（自主），什么时候该用工作流（写死）？
- 怎么让 Agent 记住之前的事？跨会话的记忆怎么做？
- Agent 跑到一半要人工审批，怎么暂停和恢复？
- 为什么我手写的 Agent 一到生产就各种诡异问题？

---

## 二、Agent 的本质：从"写死流程"到"自主决策"

### 2.1 三个层级的对比

| 层级 | 谁决定流程 | 例子 | 特点 |
|---|---|---|---|
| **固定工作流（Workflow）** | 开发者写死 | 先检索 → 再总结 → 再翻译 | 可控、可预测、便宜。**80% 的场景应该用这个** |
| **带工具聊天** | 模型的单次决策 | 一次问答决定要不要调工具 | 半自主 |
| **Agent** | 模型自主多步决策 | "帮我调研竞品并出报告" | 灵活、但不可预测、贵、难调试 |

**关键认知（面试高频）**：

> **能用工作流解决的，不要用 Agent。**
> Agent 的价值在于"你无法提前枚举所有步骤"的场景。如果流程是确定的（先 A 再 B 后 C），写死流程比让模型自由发挥**更可靠、更便宜、更快**。
>
> Anthropic 的工程文章把这个原则总结得很直接："找到最简单的方案，只在必要时增加复杂度。"很多团队一上来就做全自主 Agent，最后发现不稳定、烧钱，又退回工作流。

**决策表**：

| 场景特征 | 选择 |
|---|---|
| 步骤固定、顺序确定 | **工作流**（代码编排） |
| 步骤固定但每步需要模型判断 | **工作流 + 模型决策节点** |
| 步骤数量不定、依赖运行时信息 | **Agent**（ReAct） |
| 需要多个不同角色协作 | 多 Agent 或 Supervisor 模式（模块 06） |

### 2.2 ReAct：Agent 的经典模式

**ReAct = Reasoning + Acting**。核心思想：**让模型交替进行"推理"和"行动"**。

```
循环执行：
  Thought（思考）：我现在需要什么信息？下一步该做什么？
  Action（行动）：调用某个工具
  Observation（观察）：工具返回了什么？
  → 回到 Thought，直到得出最终答案
```

**具体例子**：

```
用户：帮我查一下北京今天适不适合户外跑步

第1轮
  Thought: 我需要知道北京今天的天气
  Action: get_weather(city="北京")
  Observation: {"condition": "阵雨", "temp": 18, "wind": "5级"}

第2轮
  Thought: 阵雨 + 5级风，不适合户外跑步。我已经有足够信息了
  Answer: 今天北京有阵雨，气温 18℃，风力 5 级。不建议户外跑步，
          建议改为室内运动。
```

**为什么这个模式有效**（回到模块 01 的机制）：

模型逐 token 生成，**写出来的 Thought 会成为后续生成的上下文**。这相当于给它一张草稿纸——它把"我要干什么"显式写出来，后续决策就基于这份推理，而不是凭直觉。这和 CoT（模块 02）是同一个原理。

**两种实现方式**：

| 方式 | 做法 | 现状 |
|---|---|---|
| **文本式 ReAct** | 提示词让模型输出 "Thought: ...\nAction: ..."，用正则解析 | 已过时，容易格式出错 |
| **原生 Function Calling** | 用工具调用机制，模型的推理放在 `content` 里 | **现代标准** ✅ |

> **重要**：现代框架（LangGraph 等）底层都用**原生 Function Calling**，不用文本解析。文本式 ReAct 只在教学里见到。**面试时如果你说"用正则解析 Thought/Action"，会显得知识过时。**

### 2.3 ReAct 的四种失败模式（必须记住）

**这是把"跑过 demo"和"做过生产"区分开的考点。**

| 失败模式 | 症状 | 根因 | 应对 |
|---|---|---|---|
| **无限循环** | 反复调用同一个工具，参数微调，永不收敛 | 工具返回模糊结果，模型试图靠重试解决 | ① 设 `max_iterations`；② 加循环检测（最近 3 步相同则中断）；③ 改进工具返回的明确性 |
| **上下文溢出** | 跑到第 10–15 步突然报错 | 每步都追加进上下文，累积超限 | ① 中间结果摘要压缩；② 只保留关键步骤；③ 用 `MessagesState` 加 trimmer |
| **思考幻觉** | 推理看着合理，但调错工具或误读结果 | 模型在模仿 ReAct 格式，而非真的基于观察推理 | ① 用原生 Function Calling（结构上无法产生格式错误的调用）；② 改进工具描述 |
| **注意力稀释** | 忘记早期关键信息，前后决策矛盾 | 长轨迹导致模型更关注近期上下文 | ① 每步重注入关键事实（"记住：用户预算 500 元"）；② 用专门的记忆/状态层 |

### 2.4 主流规划模式对比

除了 ReAct，还有几种规划模式。知道它们的取舍，能体现你的深度。

| 模式 | 机制 | 适合 | 不适合 |
|---|---|---|---|
| **ReAct** | 边做边想，每步根据观察调整 | 步骤无法预先枚举，需要探索 | 需要全局最优规划的任务 |
| **Plan-and-Execute** | 先出完整计划，再逐步执行 | 步骤可预知、需要审计（计划可先审阅） | 环境动态变化、计划容易失效 |
| **ReWOO** | 先规划所有步骤，再并行执行，减少 LLM 调用 | token 预算紧、步骤可预知 | 开放式探索（计划会不可恢复地错） |
| **Reflexion** | 执行后自我反思，把反思加进下一轮 | 有明确对错信号（如代码能否跑通） | 无客观反馈的开放任务 |

**选型要点**：
- 需要**审计**（计划要先给人看） → Plan-and-Execute
- 需要**省钱**（频繁调 LLM 太贵） → ReWOO
- 任务**有明确成功信号** → Reflexion
- **默认选择** → ReAct（最通用）

---

## 三、为什么需要 LangGraph（而不是手写 while 循环）

### 3.1 手写循环的四个局限

```python
# 手写 Agent 循环（模块 04 的写法）
while iteration < MAX:
    resp = call_model(messages)
    if no tool_calls: return answer
    execute_tools()
```

这个写法在 demo 里够用，但生产环境会遇到四个问题：

| 问题 | 说明 |
|---|---|
| **状态管理混乱** | 消息、中间结果、用户上下文全混在 `messages` 里，越跑越乱 |
| **无法持久化** | 进程重启，所有进度丢失。长任务跑到一半崩了要重头来 |
| **无法暂停恢复** | 需要人工审批时没法"暂停在这里，明天继续" |
| **无法可视化调试** | 出问题时不知道执行到了哪一步、走了哪条分支 |

### 3.2 LangGraph 的三个核心概念

**LangGraph 把 Agent 建模成"图"（Graph）**：节点是执行单元，边是流转关系。

| 概念 | 含义 | 前端类比 |
|---|---|---|
| **State（状态）** | 在节点间流转的共享数据（TypedDict 定义） | Redux store |
| **Node（节点）** | 一个执行单元（函数），接收 state，返回 state 更新 | reducer / 中间件 |
| **Edge（边）** | 节点之间的流转关系（普通边 / 条件边） | 路由 |
| **Checkpointer（检查点）** | 保存每一步的状态快照，支持恢复 | 持久化的 store |

**为什么用"图"而不是"链"**：因为 Agent 的流程有**分支和循环**（该调工具还是直接回答？工具调完回到思考？）。链式结构表达不了循环，图可以。

**LangGraph 的六个生产级能力**：

| 能力 | 价值 |
|---|---|
| 并行执行 | 多个节点同时跑 |
| 流式输出 | 实时看到中间进展（前端体验的关键） |
| **检查点持久化** | 崩溃可恢复、支持"时间旅行"调试 |
| **人在环** | 暂停等审批，恢复继续 |
| 追踪可观测 | 每步的输入输出可查 |
| 任务队列 | 异步处理长任务 |

### 3.3 ⚠️ 版本提醒（重要）

**LangGraph 1.0** 于 2025-10-20 发布，是当前 LTS 版本（0.4 维护至 2026-12-31）。**1.0 有一个关键 API 变更**：

```python
# ❌ 旧写法（langgraph.prebuilt）—— 已弃用，会弹警告
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(model, tools, prompt="...")

# ✅ 新写法（LangChain 1.x）—— 推荐
from langchain.agents import create_agent
agent = create_agent(model, tools, system_prompt="...")
```

**主要变化**：
- 函数从 `langgraph.prebuilt` 移到 `langchain.agents`
- `prompt` 参数改名为 `system_prompt`
- 新增**中间件系统**（middleware）：`before_model` / `after_model` / `modify_model_request` / `@wrap_tool_call`，内置人在环和摘要中间件
- 工具输入自动验证（不用手动加 ValidationNode）
- Node.js 18 支持已移除，要求 Node 20+

> **如果网上教程用 `create_react_agent`，那是旧版写法**（仍能跑但会警告）。以官方文档为准。
>
> **注意版本兼容坑**：有已知问题指 `langgraph-prebuilt==1.0.2` 会给 `ToolNode.afunc` 增加必需的运行参数，而 `langgraph==1.0.1` 未约束该依赖，导致全新安装可能拉入不兼容组合。**建议按官方文档锁定兼容版本对**。

---

## Part A（W7）：Agent 原理与 LangGraph 基础

## 四、代码示例：从零手写到框架

### 4.1 先手写 ReAct（理解原理，不要跳过）

```python
# src/react_from_scratch.py
"""完全手写的 ReAct Agent。
目的：让你彻底理解 Agent 循环，之后用框架才不会变成"调 API 的搬运工"。
"""
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# ---------- 工具定义 ----------
def search(query: str) -> dict:
    return {"query": query,
            "results": [f"关于 {query} 的资料A", f"关于 {query} 的资料B"]}

def calculate(expression: str) -> dict:
    try:
        # 生产环境要用安全的表达式求值（见模块 04）
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            return {"error": "表达式含非法字符"}
        return {"expression": expression, "result": eval(expression)}
    except Exception as e:
        return {"error": str(e)}

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "search", "description": "搜索信息。用于查找你不确定或需要最新数据的内容。",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                       "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "calculate", "description": "数学计算。任何计算都必须用它，不要心算。",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string", "description": "数学表达式"}},
                       "required": ["expression"], "additionalProperties": False}}},
]
TOOL_FNS = {"search": search, "calculate": calculate}

REACT_SYSTEM = """你是一个善于规划的助手。解决复杂问题时请遵循：

1. 先思考需要哪些信息（这部分放在你的回复文字里）
2. 调用工具获取信息，可以一次调用多个无依赖的工具
3. 拿到结果后判断是否还需要更多信息
4. 信息足够时给出最终答案，并说明你的推理依据

注意：计算必须使用 calculate 工具。最多 8 轮工具调用。"""


def run_react_agent(question: str, max_steps: int = 8, verbose: bool = True) -> dict:
    messages = [
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user", "content": question},
    ]
    trace = []          # 完整执行轨迹，用于调试和展示

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0,
        )
        msg = resp.choices[0].message

        # ===== Thought：模型的文字部分就是它的思考 =====
        if msg.content and verbose:
            print(f"\n[Thought {step+1}] {msg.content}")

        messages.append(msg)

        # ===== 终止条件：没有工具调用 =====
        if not msg.tool_calls:
            return {"answer": msg.content, "steps": step + 1, "trace": trace}

        # ===== Action + Observation =====
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            if verbose:
                print(f"[Action {step+1}] {name}({json.dumps(args, ensure_ascii=False)})")

            fn = TOOL_FNS.get(name)
            result = fn(**args) if fn else {"error": f"未知工具 {name}"}

            if verbose:
                print(f"[Observation] {json.dumps(result, ensure_ascii=False)[:150]}")

            trace.append({"step": step + 1, "tool": name, "args": args, "result": result})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return {"answer": "达到最大步数限制，未能完成。", "steps": max_steps, "trace": trace}


if __name__ == "__main__":
    r = run_react_agent("帮我查一下 RAG 的最佳实践，并计算 365 * 24 * 0.28 是多少")
    print(f"\n===== 最终答案 =====\n{r['answer']}")
    print(f"\n执行了 {r['steps']} 轮")
```

**为什么要手写这一遍**：手写之后你会真切感受到四个痛点——**状态管理乱、没法暂停、崩溃全丢、没法可视化**。这就是 LangGraph 存在的理由。**没有这个体感，用框架只是抄 API。**

### 4.2 用 LangGraph 重写（StateGraph 原生 API）

```python
# src/langgraph_agent.py
"""用 LangGraph 的 StateGraph 原生 API 构建 Agent。
依赖：
    uv add langgraph langchain-openai python-dotenv
"""
import os, json
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()

# ============ 1. 定义工具（LangChain 的 @tool 装饰器）============
# 关键：docstring 就是给模型看的描述，写法要求和模块 04 一致
@tool
def search(query: str) -> str:
    """搜索信息。

    何时使用：需要最新资讯、实时数据或你不确定的事实时。
    何时不要使用：常识问题、计算任务。
    """
    return f"关于「{query}」的搜索结果：资料A；资料B"

@tool
def calculate(expression: str) -> str:
    """执行数学计算，支持 + - * / ( )。

    何时使用：任何需要精确计算的场景。
    注意：你必须使用本工具计算，不要心算。
    """
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return json.dumps({"error": "表达式含非法字符"})
    try:
        return json.dumps({"result": eval(expression)})
    except Exception as e:
        return json.dumps({"error": str(e)})

TOOLS = [search, calculate]
TOOL_MAP = {t.name: t for t in TOOLS}

# ============ 2. 定义 State ============
class AgentState(TypedDict):
    # add_messages 是 reducer：新消息会追加而不是覆盖
    messages: Annotated[list, add_messages]
    iterations: int              # 记录循环次数，用于上限控制

# ============ 3. 初始化模型并绑定工具 ============
llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)
llm_with_tools = llm.bind_tools(TOOLS)

SYSTEM = SystemMessage(content="""你是一个善于规划的助手。

1. 需要外部信息时调用工具
2. 计算必须用 calculate 工具
3. 信息足够时给出最终答案""")

# ============ 4. 定义节点 ============
def agent_node(state: AgentState) -> dict:
    """模型节点：决定下一步行动"""
    msgs = [SYSTEM] + state["messages"]
    resp = llm_with_tools.invoke(msgs)
    return {
        "messages": [resp],
        "iterations": state.get("iterations", 0) + 1,
    }

def tool_node(state: AgentState) -> dict:
    """工具节点：执行模型请求的工具调用"""
    last = state["messages"][-1]
    results = []
    for tc in last.tool_calls:
        fn = TOOL_MAP.get(tc["name"])
        if fn is None:
            content = json.dumps({"error": f"未知工具 {tc['name']}"})
        else:
            try:
                content = fn.invoke(tc["args"])
            except Exception as e:
                # 错误返回给模型，让它自己修
                content = json.dumps({"error": str(e), "hint": "请检查参数格式"})
        results.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))
    return {"messages": results}

# ============ 5. 条件边：决定下一步走哪 ============
MAX_ITERATIONS = 8

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]

    # 超过迭代上限 → 强制结束（防止无限循环）
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return "end"

    # 有工具调用 → 执行工具
    if getattr(last, "tool_calls", None):
        return "tools"

    # 没有工具调用 → 结束
    return "end"

# ============ 6. 组装图 ============
builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)
builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "end": END},
)
builder.add_edge("tools", "agent")        # 工具执行完回到模型（形成循环）

memory = MemorySaver()                     # 检查点：保存每步状态
graph = builder.compile(checkpointer=memory)


# ============ 7. 运行 ============
def run(question: str, thread_id: str = "default") -> str:
    config = {"configurable": {"thread_id": thread_id}}     # thread_id 标识一个会话
    result = graph.invoke(
        {"messages": [{"role": "user", "content": question}], "iterations": 0},
        config=config,
    )
    return result["messages"][-1].content


def run_stream(question: str, thread_id: str = "default"):
    """流式执行：每个节点执行完就产出一次。前端体验的关键。"""
    config = {"configurable": {"thread_id": thread_id}}
    for event in graph.stream(
        {"messages": [{"role": "user", "content": question}], "iterations": 0},
        config=config,
        stream_mode="updates",       # 每次节点更新推送一次
    ):
        for node_name, update in event.items():
            print(f"[节点 {node_name} 完成]")
            yield node_name, update


if __name__ == "__main__":
    print(run("RAG 最新实践是什么？顺便算一下 365*24*0.28"))
    print("\n--- 流式执行 ---")
    for node, upd in run_stream("北京天气怎么样？", thread_id="t2"):
        pass
```

**这段代码的关键理解点**：

| 点 | 说明 |
|---|---|
| `Annotated[list, add_messages]` | 这是 **reducer**，告诉 LangGraph："messages 字段的新值要追加，不是覆盖" |
| 条件边 `should_continue` | 决定下一步走哪个节点。**这就是"图"比"链"强的地方** |
| `tools → agent` 的边 | 形成循环。**Agent 的本质就是这个循环** |
| `checkpointer` + `thread_id` | 状态持久化。同一个 thread_id 的多次调用共享历史 |
| `graph.stream()` | 流式输出，前端能看到"正在调工具"这个过程 |

### 4.3 用 `create_agent`（新 API，更简洁）

```python
# src/langchain_create_agent.py
"""LangGraph 1.0 推荐的新写法：langchain.agents.create_agent
注意：旧的 langgraph.prebuilt.create_react_agent 已弃用。
"""
import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

@tool
def search(query: str) -> str:
    """搜索信息。需要最新资讯或不确定的事实时使用。"""
    return f"搜索结果：关于「{query}」的资料A；资料B"

@tool
def calculate(expression: str) -> str:
    """执行数学计算。任何计算都必须用它，不要心算。"""
    return f"计算结果：{eval(expression)}"      # demo 用，生产要安全求值

model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

agent = create_agent(
    model,
    tools=[search, calculate],
    system_prompt="""你是善于规划的助手。
1. 需要外部信息时调用工具
2. 计算必须用 calculate
3. 信息足够时给出最终答案""",
    checkpointer=MemorySaver(),
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "session-1"}}

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "算一下 1234 * 5678"}]},
        config=config,
    )
    print(result["messages"][-1].content)

    # 同一个 thread_id → 模型记得上一轮
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "刚才的结果再乘以 2"}]},
        config=config,
    )
    print(result["messages"][-1].content)
```

### 4.4 中间件（LangGraph 1.0 的新能力）

`create_agent` 的新增价值在于**中间件系统**——不用改图结构就能插入通用逻辑。

```python
# src/middleware_demo.py
"""中间件：成本控制、输入脱敏、人在环。
LangChain 1.x 的内置中间件能力。
"""
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,       # 人在环
    SummarizationMiddleware,        # 自动摘要（防上下文溢出）
)

agent = create_agent(
    model,
    tools=[search],
    middleware=[
        # 高风险工具自动暂停等人工确认
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),

        # 上下文太长时自动摘要压缩（解决 ReAct 的"上下文溢出"失败模式）
        SummarizationMiddleware(
            model=model,
            max_tokens_before_summary=4000,
        ),
    ],
)
```

**中间件的四种钩子**（面试可能问）：

| 钩子 | 时机 | 典型用途 |
|---|---|---|
| `before_model` | 每次调模型前 | 注入上下文、裁剪历史、日志 |
| `after_model` | 每次模型返回后 | 输出校验、内容过滤 |
| `modify_model_request` | 修改请求内容 | 动态改系统提示词 |
| `@wrap_tool_call` | 包裹工具调用 | 权限校验、审计、重试 |

---

## Part B（W8）：记忆、中断与人在环

## 五、记忆系统

### 5.1 三种记忆类型

| 类型 | 作用 | 实现 | 生命周期 |
|---|---|---|---|
| **短期记忆** | 当前会话的对话历史 | Checkpointer（按 thread_id 存） | 会话期间 |
| **长期记忆** | 跨会话记住用户偏好、事实 | 持久化存储 + 检索 | 永久 |
| **工作记忆** | 当前任务中间结果 | Agent State | 任务期间 |

**为什么区分**：因为它们的生命周期和访问方式完全不同。

```
短期记忆："刚才我说了什么"     → 全量加载，按 thread_id
长期记忆："这个用户喜欢简洁回答" → 需要检索，跨会话
工作记忆："任务步骤 3 的中间结果" → 存在 State 里，任务结束就丢
```

### 5.2 短期记忆与上下文管理

**核心矛盾**：历史越全，模型越了解上下文，但 token 越多、越容易"中间遗忘"。

**五种管理策略**：

| 策略 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| 全量保留 | 所有历史都带上 | 信息最全 | token 线性增长，超限 |
| 滑动窗口 | 只保留最近 N 轮 | 简单 | 丢失早期信息 |
| 摘要压缩 | 把旧对话总结成一段 | 保留要点，省 token | 摘要会丢细节，多一次调用 |
| 语义检索 | 只把相关的历史检索出来 | 精准 | 实现复杂 |
| 分层 | 最近 N 轮全量 + 更早的摘要 | 平衡 | 实现较复杂 |

```python
# src/short_term_memory.py
"""短期记忆：基于 LangGraph Checkpointer 的会话内记忆。"""
from langgraph.checkpoint.sqlite import SqliteSaver      # 生产可用 SQLite
# from langgraph.checkpoint.postgres import PostgresSaver # 生产推荐 Postgres

# 方式一：内存版（开发用，进程重启就丢）
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

# 方式二：SQLite（持久化，进程重启不丢）
# with SqliteSaver.from_conn_string("checkpoints.db") as memory:
#     graph = builder.compile(checkpointer=memory)

graph = builder.compile(checkpointer=memory)

# 不同 thread_id 完全隔离 —— 相当于不同用户的会话
config_a = {"configurable": {"thread_id": "user-A-session-1"}}
config_b = {"configurable": {"thread_id": "user-B-session-1"}}

graph.invoke({"messages": [{"role": "user", "content": "我叫张三"}]}, config=config_a)
graph.invoke({"messages": [{"role": "user", "content": "我叫李四"}]}, config=config_b)

# A 问"我叫什么" → 张三；B 问 → 李四。互不干扰。
r = graph.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, config=config_a)
print(r["messages"][-1].content)      # 张三
```

**手动做上下文裁剪**（结合摘要）：

```python
# src/context_manager.py
from langchain_core.messages import SystemMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def trim_messages_node(state, max_turns: int = 10):
    """裁剪节点：超过上限时只保留最近 N 轮。
    在生产环境更推荐用 SummarizationMiddleware 自动摘要。
    """
    msgs = state["messages"]
    if len(msgs) <= max_turns * 2:
        return {}

    # 保留系统消息 + 最近 N 轮
    kept = msgs[-(max_turns * 2):]
    # 用 RemoveMessage 告诉 reducer 怎么改
    return {"messages": [RemoveMessage(id=m.id) for m in msgs[:-max_turns * 2]]}
```

### 5.3 长期记忆

**实现思路**：把"值得记住的事"存起来，下次对话时按需检索。

```python
# src/long_term_memory.py
"""长期记忆：跨会话记住用户偏好。
核心思路：从对话中抽取事实 → 存储 → 下次按需检索注入。
"""
import json, os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")


class LongTermMemory:
    """简化版长期记忆。生产可用向量库 + 数据库组合。"""

    def __init__(self, store_path: str = "memory.json"):
        self.store_path = store_path
        try:
            self.memories = json.load(open(store_path, encoding="utf-8"))
        except FileNotFoundError:
            self.memories = {}        # {user_id: [{"fact": str, "ts": str}]}

    def extract_and_save(self, user_id: str, conversation: str):
        """从对话中抽取值得记住的事实。"""
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": f"""从下面这段对话中提取值得长期记住的用户信息。

只提取稳定的偏好或事实（如职业、语言偏好、常用工具、习惯）。
不要提取临时信息（如"今天天气怎么样"）。
如果没有值得记住的，输出空数组。

对话：
{conversation}

输出 JSON 数组，如：["用户偏好简洁回答", "用户是前端工程师"]
只输出 JSON。"""}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        try:
            facts = json.loads(resp.choices[0].message.content)
            if isinstance(facts, dict):
                facts = facts.get("facts", [])
        except json.JSONDecodeError:
            return

        self.memories.setdefault(user_id, [])
        for f in facts:
            if isinstance(f, str) and f not in [m["fact"] for m in self.memories[user_id]]:
                import datetime
                self.memories[user_id].append(
                    {"fact": f, "ts": datetime.datetime.now().isoformat()})
        self._save()

    def get_context(self, user_id: str, limit: int = 10) -> str:
        """取出记忆，用于注入到 system prompt。

        生产环境这里应该用向量检索找与当前问题相关的记忆，
        而不是简单取最近 N 条。
        """
        items = self.memories.get(user_id, [])[-limit:]
        if not items:
            return ""
        facts = "\n".join(f"- {m['fact']}" for m in items)
        return f"\n\n【关于该用户的已知信息】\n{facts}"

    def _save(self):
        json.dump(self.memories, open(self.store_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)


# ============ 使用 ============
if __name__ == "__main__":
    mem = LongTermMemory("./user_memory.json")

    # 第一轮对话：抽取并保存
    mem.extract_and_save("user-001", "我是前端工程师，平时用 TypeScript，希望回答简短一点")
    print(mem.memories["user-001"])

    # 下次对话：注入记忆
    ctx = mem.get_context("user-001")
    messages = [
        {"role": "system", "content": "你是助手。" + ctx},
        {"role": "user", "content": "推荐一个学习路线"},
    ]
    # 模型现在知道用户是前端、喜欢简短回答
```

> ⚠️ **长期记忆的三个坑**：① **无差别存储**会导致记忆库污染（存了"用户问了天气"这种无用信息）；② **隐私合规**——用户数据要能删除，要符合法规；③ **记忆冲突**——用户说"我喜欢详细解释"后又改口，旧记忆要能更新。这是产品设计问题，不只是技术问题。

---

## 六、中断与人在环（Human-in-the-Loop）

### 6.1 为什么需要中断

**Agent 自主决策 = 它可能做出你不想要的决定。** 高风险操作必须有人把关。

**三种中断场景**：

| 场景 | 例子 | 需求 |
|---|---|---|
| **审批** | 执行退款前 | 暂停，等用户确认 |
| **补充信息** | 缺少用户 ID | 暂停，向用户提问 |
| **修正** | 用户发现 Agent 理解错了 | 中断当前执行，改方向 |

### 6.2 LangGraph 的 `interrupt` 机制

```python
# src/human_in_the_loop.py
"""完整的人在环实现：暂停 → 人工审批 → 恢复继续。
依赖：uv add langgraph langchain-openai
"""
import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]
    action: dict            # 待执行的操作
    approved: bool

llm = ChatOpenAI(model="deepseek-v4-flash",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 base_url="https://api.deepseek.com",
                 temperature=0)


# ---------- 节点 1：分析并提议操作 ----------
def propose_action(state: State) -> dict:
    user_msg = state["messages"][-1].content
    resp = llm.invoke([
        SystemMessage(content="""分析用户请求，决定要执行的操作。
输出格式（只输出这个 JSON）：
{"action": "refund", "order_id": "从用户消息提取", "amount": 数字, "reason": "原因"}"""),
        {"role": "user", "content": user_msg},
    ])

    import json
    try:
        action = json.loads(resp.content)
    except json.JSONDecodeError:
        action = {"action": "unknown", "raw": resp.content}

    return {"action": action, "messages": [resp]}


# ---------- 节点 2：人工审批（中断点）----------
def request_approval(state: State) -> dict:
    """这个节点会暂停图执行，等外部输入。

    interrupt() 会：
      1. 把当前状态保存到 checkpointer
      2. 抛出中断信号，图暂停
      3. 外部用 Command(resume=...) 恢复时，从这里继续
    """
    action = state["action"]

    # 把要审批的内容传给外部（前端会展示给用户）
    decision = interrupt({
        "type": "approval_request",
        "action": action,
        "message": f"即将执行：{action.get('action')} 订单 {action.get('order_id')} "
                   f"金额 {action.get('amount')}，是否批准？",
    })

    # decision 是恢复时传入的值
    return {"approved": decision.get("approved", False)}


# ---------- 节点 3：执行或取消 ----------
def execute_action(state: State) -> dict:
    if not state.get("approved"):
        return {"messages": [{"role": "assistant",
                              "content": "操作已被拒绝，未执行任何动作。"}]}

    action = state["action"]
    # 真实场景：这里调退款 API
    result = f"已成功执行 {action.get('action')}，订单 {action.get('order_id')}，" \
             f"金额 {action.get('amount')}"
    return {"messages": [{"role": "assistant", "content": result}]}


# ---------- 组装图 ----------
builder = StateGraph(State)
builder.add_node("propose", propose_action)
builder.add_node("approve", request_approval)
builder.add_node("execute", execute_action)

builder.add_edge(START, "propose")
builder.add_edge("propose", "approve")
builder.add_edge("approve", "execute")
builder.add_edge("execute", END)

# ⚠️ 人在环必须有 checkpointer，否则中断状态无法保存
memory = SqliteSaver.from_conn_string("hitl_checkpoints.db")
graph = builder.compile(checkpointer=memory)


# ---------- 使用流程 ----------
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "approval-001"}}

    # ===== 第 1 步：发起请求，图会停在 interrupt 处 =====
    print("【第 1 步】发起请求")
    result = graph.invoke(
        {"messages": [{"role": "user",
                       "content": "客户投诉了，帮我给订单 ORD-20260913 退款 500 元"}]},
        config=config,
    )
    # result 里会有 __interrupt__ 信息
    print("图已暂停，等待审批")
    print("中断信息：", result.get("__interrupt__"))

    # 实际应用中，这里把审批请求发给前端，用户点击后前端回调
    # ===== 第 2 步：模拟人工批准，恢复执行 =====
    print("\n【第 2 步】人工批准")
    resumed = graph.invoke(
        Command(resume={"approved": True}),       # 恢复并传入审批结果
        config=config,
    )
    print("执行结果：", resumed["messages"][-1].content)

    # ===== 场景二：拒绝 =====
    print("\n" + "=" * 50)
    config2 = {"configurable": {"thread_id": "approval-002"}}
    graph.invoke({"messages": [{"role": "user",
                                "content": "给订单 ORD-999 退款 50000 元"}]}, config=config2)
    print("【拒绝场景】")
    rejected = graph.invoke(Command(resume={"approved": False}), config=config2)
    print("执行结果：", rejected["messages"][-1].content)
```

**这段代码的三个关键点（面试常问）**：

1. **`interrupt()` 会保存状态并暂停**，不是"阻塞等待"。进程可以重启，恢复时从暂停点继续
2. **必须有 checkpointer**，否则中断状态无处保存，恢复时会从头开始
3. **`Command(resume=...)` 是恢复机制**，传入的值会成为 `interrupt()` 的返回值

**为什么这个能力对企业级落地至关重要**：

| 没有人在环 | 有 人在环 |
|---|---|
| 模型误判 → 直接执行 → 造成损失 | 模型提议 → 人确认 → 执行 |
| 无法通过合规审查 | 满足审计要求 |
| 用户不敢用（不信任 AI 决策） | 用户放心（关键决策在自己手里） |

### 6.3 人在环的交互设计（前端要展示什么）

这是你前端能力的发挥点。审批请求应该包含：

| 信息 | 为什么必要 |
|---|---|
| **要执行什么操作** | 用户知道在批什么 |
| **影响范围/金额** | 用户判断风险 |
| **AI 的判断依据** | 用户理解为什么 Agent 想这么做 |
| **可修改** | 不只批准/拒绝，还能"改成退款 300 元再批准" |
| **一键撤回** | 执行后能撤销（设计上要考虑） |

---

## 七、知识点清单

**Part A（Agent 原理）**
- [ ] Agent vs 工作流的区别，什么时候**不该**用 Agent
- [ ] ReAct 的 Thought-Action-Observation 循环，以及它为什么有效
- [ ] 文本式 ReAct 已过时，现代用原生 Function Calling
- [ ] ReAct 的四种失败模式及应对（无限循环/上下文溢出/思考幻觉/注意力稀释）
- [ ] 四种规划模式对比（ReAct / Plan-and-Execute / ReWOO / Reflexion）
- [ ] LangGraph 的核心概念：State / Node / Edge / Checkpointer
- [ ] 为什么用图而不是链（支持分支和循环）
- [ ] StateGraph 的关键 API：add_node / add_conditional_edges / compile
- [ ] `Annotated[list, add_messages]` 的 reducer 机制
- [ ] `create_agent` 新 API 与 `create_react_agent` 旧 API 的差异
- [ ] 中间件的四种钩子及其用途

**Part B（记忆与人在环）**
- [ ] 三种记忆类型（短期/长期/工作）的区别
- [ ] 上下文管理的五种策略及取舍
- [ ] Checkpointer 的作用，`thread_id` 的隔离机制
- [ ] 长期记忆的实现思路（抽取→存储→检索注入）及三个坑
- [ ] 人在环的三种场景（审批/补充信息/修正）
- [ ] `interrupt()` + `Command(resume=)` 的完整流程
- [ ] 为什么人在环必须有 checkpointer
- [ ] 审批交互应该展示哪些信息

---

## 八、常见坑

### 坑 1：一上来就做全自主 Agent
**后果**：不稳定、烧钱、难调试，最后退回工作流。
**正确做法**：先问"步骤能不能枚举"。能枚举就用工作流（代码编排），只在必要处用模型决策。**这是最常见的架构错误。**

### 坑 2：直接抄框架 API 不懂原理
**后果**：报错后完全无从下手，因为不知道框架在背后做了什么。
**正确做法**：先手写一遍 ReAct 循环（4.1 节），理解后再用 LangGraph。

### 坑 3：没有 max_iterations
**后果**：无限循环，token 账单失控。
**正确做法**：强制设置上限 + 循环检测（连续 3 步相同则中断）。

### 坑 4：忘记 reducer，导致 messages 被覆盖
**后果**：每轮只剩最后一条消息，Agent 完全没有历史。
**正确做法**：`Annotated[list, add_messages]`，理解 reducer 的作用。

### 坑 5：用内存版 checkpointer 上生产
**后果**：进程重启，所有会话状态丢失。
**正确做法**：生产用 `SqliteSaver` 或 `PostgresSaver`。注意 Postgres/Redis 后端需要先建表/migration。

### 坑 6：做了 interrupt 但忘了 checkpointer
**后果**：中断后无法恢复，或者恢复时从头执行（重复执行副作用）。
**正确做法**：人在环必须配持久化 checkpointer。

### 坑 7：长期记忆无差别存储
**后果**：记忆库塞满"用户问了天气"这类无用信息，注入后污染 Prompt。
**正确做法**：只存稳定偏好和事实，明确排除临时信息，并支持删除（合规要求）。

### 坑 8：上下文不做任何管理
**后果**：跑到第 15 步报错，或者成本飙升、回答质量下降。
**正确做法**：用摘要中间件或裁剪节点主动管理上下文。

### 坑 9：中断恢复后重复执行副作用
**后果**：退款执行了两次。
**正确做法**：副作用操作要做幂等设计（用唯一 ID 去重），或在执行前检查是否已执行。

### 坑 10：不区分 thread_id
**后果**：所有用户共享同一个会话，A 看到 B 的对话（严重的数据泄露）。
**正确做法**：`thread_id` 必须按"用户 + 会话"维度生成，且服务端要校验归属权限。

---

## 九、练习任务

### Part A（W7）

| # | 任务 | 难度 |
|---|---|---|
| 1 | 手写一个完整的 ReAct Agent（不用框架），能处理多步任务 | ⭐⭐⭐ |
| 2 | 故意构造一个无限循环场景（工具总是返回模糊结果），观察并加循环检测 | ⭐⭐⭐ |
| 3 | 用 LangGraph 的 StateGraph 重写上面的 Agent | ⭐⭐⭐⭐ |
| 4 | 用 `create_agent` 再写一遍，对比两种 API 的代码量差异 | ⭐⭐⭐ |
| 5 | 实现 `graph.stream()` 流式输出，把每个节点的执行实时打印出来 | ⭐⭐⭐ |
| 6 | **对比实验**：同一个"调研并出报告"任务，用工作流 vs ReAct 各实现一次，对比稳定性、延迟、成本，写结论 | ⭐⭐⭐⭐⭐ |

### Part B（W8）

| # | 任务 | 难度 |
|---|---|---|
| 7 | 实现短期记忆：两个 thread_id 的会话互不干扰 | ⭐⭐ |
| 8 | 把 MemorySaver 换成 SqliteSaver，验证进程重启后历史还在 | ⭐⭐⭐ |
| 9 | 实现长期记忆：从对话抽取偏好，下次对话自动注入 | ⭐⭐⭐⭐ |
| 10 | 实现完整的人在环：暂停 → 审批 → 恢复，含批准和拒绝两个路径 | ⭐⭐⭐⭐ |
| 11 | 给人在环加"修改后批准"能力（不只批/拒，还能改金额） | ⭐⭐⭐⭐ |
| 12 | **【项目任务】** 做一个"高风险操作需审批"的 Agent，并记录完整审计日志 | ⭐⭐⭐⭐⭐ |

**任务 6 是本模块最重要的练习。** 亲手验证"工作流比 Agent 更稳更便宜"，你才会有正确的架构判断力。这个体感在面试时能直接体现出来。

---

## 十、自测题

**Q1：Agent 和"带工具的聊天机器人"有什么区别？**
<details><summary>参考答案</summary>
核心区别在**决策轮数**。带工具的聊天机器人：一次问答中决定要不要调工具，调完就回答（单轮工具使用）。Agent：模型自主决定要调几轮、调哪些工具、按什么顺序、要不要换策略（多轮自主决策循环）。Agent 多了"规划"和"基于观察调整"的能力。但要注意：多轮不等于 Agent，如果轮数是写死的，那还是工作流。
</details>

**Q2：ReAct 为什么有效？**
<details><summary>参考答案</summary>
因为模型是逐 token 生成的，**写出来的推理过程会成为后续生成的上下文**。ReAct 让模型显式写出 Thought（我现在需要什么、下一步做什么），这份推理就作为"草稿纸"影响后续的 Action 决策。这和 CoT 是同一个原理。另外，"行动→观察→再思考"的循环让模型能基于真实结果调整，而不是一次性猜完所有步骤。
</details>

**Q3：什么时候不该用 Agent？**
<details><summary>参考答案</summary>
当流程可以预先枚举时。比如"先检索文档、再总结、再翻译"——步骤和顺序都确定，用代码编排（工作流）更可靠、更便宜、更快、更好调试。Agent 的价值在"你无法提前知道要几步、要走哪条路"的场景。业界经验：**大多数团队一上来就做全自主 Agent，最后都退回工作流**。正确的姿势是先用最简单的工作流，只在真正需要灵活性的地方引入模型决策。这是面试必考的判断力。
</details>

**Q4：ReAct 的四种失败模式是什么？**
<details><summary>参考答案</summary>
① **无限循环**——反复调同一工具（工具返回模糊结果），对策是 max_iterations + 循环检测 + 改进工具返回的明确性；② **上下文溢出**——每步追加导致超限，对策是摘要压缩 / 裁剪 / 状态管理；③ **思考幻觉**——推理看似合理但调错工具，对策是用原生 Function Calling（结构上无法产生格式错误调用）；④ **注意力稀释**——忘记早期关键信息，对策是每步重注入关键事实或用专门记忆层。能答出这四点说明你做过真实的 Agent 调试。
</details>

**Q5：为什么用图（Graph）而不是链（Chain）来表达 Agent？**
<details><summary>参考答案</summary>
因为 Agent 的流程有**分支和循环**——"该调工具还是直接回答"是分支，"工具执行完回到模型"是循环。链式结构是线性的，表达不了这两者。图结构天然支持条件路由（conditional edges）和环（cycle），正好匹配 Agent 的执行模式。另外图结构便于可视化调试和状态持久化。
</details>

**Q6：State 里的 `Annotated[list, add_messages]` 是什么意思？**
<details><summary>参考答案</summary>
这是 LangGraph 的 **reducer（归约器）** 声明。默认情况下，节点返回的 state 更新会**覆盖**原值。加上 `add_messages` 后，messages 字段的新值会**追加**到原列表而不是覆盖。Agent 需要累积对话历史，所以必须用它。如果忘了加，每轮 messages 只剩最后一条，Agent 完全没有上下文——这是非常常见的 bug。
</details>

**Q7：LangGraph 1.0 的 `create_react_agent` 有什么变化？**
<details><summary>参考答案</summary>
`langgraph.prebuilt.create_react_agent` 已被弃用（仍可用但会有警告），推荐改用 `langchain.agents.create_agent`。主要变化：① 函数位置从 `langgraph.prebuilt` 移到 `langchain.agents`；② `prompt` 参数改名为 `system_prompt`；③ 新增中间件系统（before_model / after_model / modify_model_request / @wrap_tool_call），内置人在环和摘要中间件；④ 工具输入自动验证，不用手动加 ValidationNode。迁移的价值在于中间件能力，不只是兼容性。
</details>

**Q8：短期记忆和长期记忆怎么实现？**
<details><summary>参考答案</summary>
短期记忆用 LangGraph 的 **Checkpointer**，按 `thread_id` 存会话状态（开发用 MemorySaver，生产用 SqliteSaver/PostgresSaver）。同一 thread_id 的多次调用共享历史，不同 thread_id 完全隔离。长期记忆需要自己实现：**从对话中抽取稳定事实（用户偏好、身份信息）→ 持久化存储 → 下次对话按需检索并注入 system prompt**。生产环境应该用向量检索找相关记忆，而不是简单取最近 N 条。关键难点不在技术而在策略：存什么、不存什么、冲突了怎么办、怎么删除（合规）。
</details>

**Q9：`interrupt()` 是怎么工作的？为什么人在环必须有 checkpointer？**
<details><summary>参考答案</summary>
`interrupt(value)` 执行时会做两件事：把当前完整状态保存到 checkpointer，然后抛出中断信号让图暂停执行。它**不是阻塞等待**——进程可以退出，状态已持久化。外部用 `Command(resume=some_value)` 恢复时，图从暂停的那个节点继续，`some_value` 成为 `interrupt()` 的返回值。必须有 checkpointer 是因为：中断状态（执行到哪、state 是什么）必须保存在某个地方，否则进程重启后无法恢复，或者会从头重跑（导致副作用重复执行）。
</details>

**Q10：长期记忆有哪些坑？**
<details><summary>参考答案</summary>
① **污染**——无差别存储会把"用户问了天气"这类临时信息也存进去，注入后干扰模型；必须只存稳定偏好和事实。② **隐私合规**——用户数据要支持删除，需符合数据保护法规（如个人信息保护法）。③ **冲突与更新**——用户先说"喜欢详细解释"后改口说"喜欢简短"，旧记忆必须能被打败或更新，否则模型行为矛盾。④ **注入时机**——不是所有记忆都该注入，应该按当前问题相关度检索注入，否则会污染上下文。这些是产品设计问题，不只是技术实现。
</details>

**Q11：你的 Agent 每隔一段时间就"忘记"早期的关键信息，怎么解决？**
<details><summary>参考答案</summary>
这是 ReAct 的"注意力稀释"失败模式——长轨迹下模型对早期上下文的注意力下降。解决方案：① **关键信息重注入**——每一步或每隔几步，把关键事实（如用户预算、约束条件）重新放进上下文；② **专门的记忆层**——把关键信息结构化存在 Agent State 里，每次请求时显式带上，而不是依赖模型从长历史里"回忆"；③ **摘要压缩**——把早期内容总结成要点，减少 token 并突出关键信息；④ **改进 prompt 结构**——把关键约束放在上下文靠后的位置（模型对末尾内容更敏感）。根本认知：**不要依赖模型自己记住，要靠工程手段确保它每次都看到。**
</details>

---

## 十一、延伸阅读

| 主题 | 资源 |
|---|---|
| **LangGraph 官方文档**（必读） | https://langchain-ai.github.io/langgraph/ |
| LangGraph v1 迁移指南 | https://docs.langchain.com/oss/python/migrate/langgraph-v1 |
| LangChain `create_agent` 文档 | https://docs.langchain.com/oss/python/langchain/agents |
| ReAct 原始论文 | 搜 "ReAct: Synergizing Reasoning and Acting in Language Models" |
| Reflexion 论文 | 搜 "Reflexion: Language Agents with Verbal Reinforcement Learning" |
| Anthropic 关于构建有效 Agent 的工程文章 | https://www.anthropic.com/engineering |
| 人在环设计指南 | https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/ |

---

## 十二、完成标志

- [ ] 手写过一个完整 ReAct Agent，并能说出它的痛点
- [ ] 用 LangGraph（StateGraph + create_agent 两种写法）各实现一遍
- [ ] 一份"工作流 vs Agent"的对比实验报告
- [ ] 短期记忆 + 长期记忆的实现
- [ ] 完整的人在环流程（含审批和拒绝两条路径）
- [ ] **项目 03 完成**（多工具 Agent + 权限 + 审计）
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 06，学习多 Agent 协作与工作流编排。
