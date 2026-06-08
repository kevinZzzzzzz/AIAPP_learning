# LangChain & LangGraph 详解（大白话版）

> 目标读者：前端转 AI 开发的工程师。既有专业概念，也有"人话"翻译。

---

## 一、先搞清楚一个根本问题：这两个东西是干嘛的？

| 框架 | 一句话总结 |
|------|-----------|
| **LangChain** | 帮你在代码里**拼装** LLM 应用的零件（Prompt、工具、记忆、链条） |
| **LangGraph** | 帮你在代码里**编排** LLM 应用的流程（状态机、多步骤、条件分支、循环） |

**大白话**：
- LangChain = 乐高积木盒子，里面有各种现成的零件（轮子）
- LangGraph = 说明书 + 流水线，决定这些零件怎么组装、按什么顺序走

你完全可以不用 LangChain 直接调 OpenAI API，但当你需要**链式调用、管理对话记忆、连接向量数据库、构建 Agent** 时，自己实现就太痛苦了——LangChain 把这些做成了标准零件。

---

## 二、LangChain 核心概念

### 2.1 Chain（链）—— 把多个步骤串起来

**专业解释**：Chain 是 LangChain 的基本执行单元，将一个或多个操作（LLM 调用、工具调用、数据处理）串联成流水线。可以是简单的单步链，也可以是复杂的多步并行链。

**大白话**：就像工厂流水线——A 工位加工完传给 B 工位，B 工位传给 C 工位。每个工位只做一件事，最终产出成品。

```
用户输入 → [翻译成英文] → [让 LLM 润色] → [转成 JSON] → 输出
```

**代码示例**：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 第 1 步：定义 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}，用{language}回答。"),
    ("user", "{question}"),
])

# 第 2 步：创建 LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 第 3 步：输出解析器（把 LLM 的输出转成纯字符串）
parser = StrOutputParser()

# 第 4 步：用 | 运算符串起来 —— 这就是 Chain！
chain = prompt | llm | parser

# 执行
result = chain.invoke({
    "role": "Python 专家",
    "language": "中文",
    "question": "什么是装饰器？",
})
print(result)
```

**大白话解释这段代码**：
`prompt | llm | parser` 的意思是："先把变量填进模板 → 然后把填好的 Prompt 发给 LLM → 再把 LLM 的回复洗成干净字符串"。`|` 就是管道，前端同学理解为 `pipe()` 函数。

---

### 2.2 LCEL（LangChain Expression Language）—— 管道的写法

**专业解释**：LCEL 是 LangChain 的核心语法，用 `|`（管道操作符）组合 Runnable 对象。它自动处理异步、流式、并行、重试等底层逻辑。

**大白话**：`A | B | C` 就是 `数据 → A → B → C → 结果`，从左到右，一目了然。比传统代码里 `B(A(x))` 这种嵌套清晰多了。

**三种等价写法**（你会爱上 LCEL）：

```python
# ❌ 传统嵌套写法（地狱回调既视感）
result = parser(llm(prompt.format(user_input)))

# ✅ LCEL 管道写法
chain = prompt | llm | parser
result = chain.invoke(user_input)

# ✅ 带中间处理的管道
chain = (
    prompt
    | llm
    | (lambda x: x.content.upper())  # 插入自定义处理
    | parser
)
```

**前端对照**：
```javascript
// JS 中的类似思路（函数式 pipe）
const pipe = (...fns) => (x) => fns.reduce((v, f) => f(v), x);
const chain = pipe(formatPrompt, callLLM, parseOutput);
```

---

### 2.3 Runnable 接口 —— 所有零件的统一协议

**专业解释**：LangChain 中所有组件都实现了 `Runnable` 接口，提供统一的方法：`invoke()`（单次调用）、`stream()`（流式）、`batch()`（批量）、`ainvoke()`（异步调用）。

**大白话**：就像 USB-C 接口——不管你插的是充电器、耳机还是显示器，接口都一样。`invoke()` 是"执行一次"，`stream()` 是"一边执行一边往外吐"。

```python
# 同一个 chain，三种调用方式
chain = prompt | llm | parser

# 方式 1：直接等结果
result = chain.invoke({"question": "你好"})

# 方式 2：流式（打字机效果）
for chunk in chain.stream({"question": "讲个笑话"}):
    print(chunk, end="")

# 方式 3：异步（FastAPI 里用）
result = await chain.ainvoke({"question": "你好"})

# 方式 4：批量
results = chain.batch([
    {"question": "问题1"},
    {"question": "问题2"},
])
```

---

### 2.4 Memory（记忆）—— 让 LLM 记住之前说了什么

**专业解释**：LLM 本身是无状态的，每次调用都是独立的。Memory 模块负责管理对话历史，自动将历史消息拼入新的请求中。常见策略：BufferMemory（全量）、SummaryMemory（摘要）、WindowMemory（滑动窗口）。

**大白话**：LLM 就是个金鱼脑——每次问你叫什么，它都"失忆"。Memory 就像给金鱼配了笔记本，每次对话前翻一翻之前记了什么。

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

llm = ChatOpenAI(model="gpt-4o-mini")
memory = ConversationBufferMemory(return_messages=True)

conversation = ConversationChain(llm=llm, memory=memory)

# 第一轮
conversation.predict(input="我叫小明")
# → "你好小明！"

# 第二轮 —— LLM 还记得！
conversation.predict(input="我叫什么名字？")
# → "你叫小明！"  ← Memory 起了作用
```

**三种常用记忆策略**：

| 策略 | 做法 | 什么时候用 |
|------|------|-----------|
| BufferMemory | 记住所有对话 | 短对话 |
| WindowMemory | 只记最近 K 轮 | 长对话（防止 token 爆炸） |
| SummaryMemory | 把旧对话总结成一段话再记住 | 超长对话 |

---

### 2.5 Tool & Agent —— 让 LLM 能"动手"

**专业解释**：Tool 是 LLM 可调用的外部函数（搜索、计算、查天气等）。Agent 是使用 Tool 的智能体，它决定什么时候调用哪个 Tool，如何处理 Tool 返回的结果。

**大白话**：LLM 只会"说"不会"做"。Tool 就是给 LLM 配了手脚——它能查天气（调 API）、算数学（调计算器）、搜信息（调搜索引擎）。Agent 就是它的"大脑"，决定什么时候该用哪只手。

```python
from langchain.agents import tool, AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI

# 定义工具（用 @tool 装饰器，秒变 Tool）
@tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city}今天 25°C，晴天"

@tool
def calculator(expression: str) -> str:
    """执行数学计算"""
    return str(eval(expression))  # 生产环境需安全处理

# 创建 Agent
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [get_weather, calculator]

agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

# Agent 自己决定要不要用工具、用哪个工具
executor.invoke({"input": "北京天气怎么样？"})  # → 调用 get_weather
executor.invoke({"input": "123 * 456 等于多少？"})  # → 调用 calculator
executor.invoke({"input": "你好"})  # → 不用工具，直接回答
```

---

## 三、LangGraph —— 给 Agent 装上一个"流程图大脑"

### 3.1 为什么需要 LangGraph？

**专业解释**：LangChain 的 Chain 是线性的（A → B → C），而真实世界的 Agent 往往需要**条件分支、循环、多路径并行、人工审批节点**。LangGraph 用有向图（Graph）来建模 Agent 的执行流程——每个节点是一个操作，边是流转条件。

**大白话**：LangChain 的 Chain 像一条单行道，只能一路往前开。LangGraph 像一个立交桥系统——你可以根据路况（条件）选择不同方向，甚至可以绕圈（循环），还能在某个路口等待人工确认。

### 3.2 核心概念对比

| 概念 | LangChain | LangGraph |
|------|-----------|-----------|
| 基本单元 | Chain（链条） | Graph（图 = 节点 + 边） |
| 流向 | 单向线性 | 任意方向（有向图） |
| 分支 | 有限支持（RouterChain） | 原生支持条件边 |
| 循环 | 不支持 | 原生支持（状态更新触发循环） |
| 人工介入 | 不支持 | 原生支持（interrupt） |
| 状态管理 | 链之间传递 | 全局 State，所有节点共享 |

### 3.3 LangGraph = State + Nodes + Edges

**专业解释**：LangGraph 基于状态机（State Machine）模型。State 是全局共享的数据结构，Node 是处理函数（读 State、写 State），Edge 决定下一步去哪（普通边/条件边）。

**大白话**：想象一个棋盘——State 是棋盘当前的样子，Node 是一步棋的规则，Edge 是"下完这步该谁走"。

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

# ===== 第 1 步：定义全局 State =====
class AgentState(TypedDict):
    messages: list[dict]      # 对话历史
    next_action: str          # 下一步做什么
    tool_results: list[str]   # 工具执行结果
    final_answer: str         # 最终答案

# ===== 第 2 步：定义 Node（节点） =====

def chat_node(state: AgentState) -> AgentState:
    """节点1：调用 LLM 决定下一步"""
    # 实际项目中这里调用 LLM
    user_msg = state["messages"][-1]["content"]
    
    if "天气" in user_msg:
        return {**state, "next_action": "call_tool"}
    else:
        return {**state, "next_action": "answer"}

def tool_node(state: AgentState) -> AgentState:
    """节点2：执行工具"""
    result = "北京今天 25°C，晴天"
    return {
        **state,
        "tool_results": [result],
        "next_action": "answer",
    }

def answer_node(state: AgentState) -> AgentState:
    """节点3：生成最终回复"""
    return {
        **state,
        "final_answer": "根据查询结果，这是回答...",
    }

# ===== 第 3 步：定义路由逻辑 =====
def router(state: AgentState) -> Literal["tool_node", "answer_node"]:
    """条件边：根据 next_action 决定走哪个节点"""
    if state["next_action"] == "call_tool":
        return "tool_node"
    return "answer_node"

# ===== 第 4 步：构建图 =====
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("chat_node", chat_node)
graph.add_node("tool_node", tool_node)
graph.add_node("answer_node", answer_node)

# 添加边
graph.set_entry_point("chat_node")                    # 从 chat_node 开始
graph.add_conditional_edges("chat_node", router)       # chat_node 之后分支
graph.add_edge("tool_node", "chat_node")               # 工具执行后回到 chat_node（循环！）
graph.add_edge("answer_node", END)                     # answer_node 后结束

# ===== 第 5 步：编译并运行 =====
app = graph.compile()
result = app.invoke({
    "messages": [{"role": "user", "content": "北京天气怎么样？"}],
    "next_action": "",
    "tool_results": [],
    "final_answer": "",
})
```

**大白话解释上图流程**：

```
用户提问
   ↓
[chat_node] → LLM 分析："用户想查天气，需要调工具"
   ↓
   ├─→ [tool_node] → 执行工具，拿到结果
   │        ↓
   │    (回到 chat_node) → LLM 看到工具结果："我现在可以回答了"
   │        ↓
   └─→ [answer_node] → 生成最终回复 → END
```

这就形成了一个 **循环**：`chat → tool → chat → answer`。这恰恰是 Agent 的 ReAct 模式——先思考、再行动、再思考、再回答。

---

### 3.4 LangGraph 的杀手功能：人工介入（Human-in-the-Loop）

**专业解释**：`interrupt()` 可以在任意节点暂停执行，等待外部审批后再继续。这在高风险场景（发送邮件、执行交易）中至关重要。

**大白话**：就像请假审批流程——员工提交后，系统暂停，等老板点了"同意"再继续。

```python
from langgraph.checkpoint import MemorySaver
from langgraph.graph import StateGraph, interrupt

def approval_node(state):
    """需要人工审批的节点"""
    # interrupt() 暂停执行，等人工审批
    approved = interrupt(f"请审批：{state['action']}")
    
    if approved:
        return {**state, "status": "已通过"}
    return {**state, "status": "已拒绝"}

# 运行时需要手动推进
app = graph.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "1"}}

# 第一次运行 —— 会在 interrupt() 处暂停
result = app.invoke(input_data, config)

# 人工审批通过后 —— 继续执行
app.invoke(None, config)  # 传入 None 继续
```

---

## 四、LangChain vs LangGraph：该用哪个？

| 场景 | 用什么 | 为什么 |
|------|--------|--------|
| 简单的 Prompt → LLM → 输出 | LangChain | LCEL 管道足够 |
| RAG 文档问答 | LangChain | 内置的 RetrievalQA 链开箱即用 |
| 简单的工具调用 | LangChain | create_openai_tools_agent 够用 |
| 多步骤复杂 Agent | **LangGraph** | 需要循环和分支 |
| 有人工审批的流程 | **LangGraph** | interrupt 原生支持 |
| 多 Agent 协作 | **LangGraph** | 子图 + 并行 + 通信 |
| 生产级 AI 应用 | **LangGraph** | 状态持久化、可恢复、可观测 |

**注意**：LangGraph 不是 LangChain 的替代品，而是补充。它们通常一起使用——LangChain 提供零件（Prompt、LLM、Tool），LangGraph 提供流程编排（图、状态、循环）。

---

## 五、一张图总结

```
┌─────────────────────────────────────────────┐
│                 LangGraph                    │
│  ┌───────────────────────────────────────┐  │
│  │         编排层（流程图大脑）             │  │
│  │   State → Nodes → Edges → Cycles      │  │
│  │   interrupt / checkpoint / stream     │  │
│  └───────────────────────────────────────┘  │
│                    ↓ 调用                    │
│  ┌───────────────────────────────────────┐  │
│  │         LangChain（零件库）              │  │
│  │  ┌─────────┐ ┌──────┐ ┌───────────┐  │  │
│  │  │ Prompt  │ │ LLM  │ │ Tools     │  │  │
│  │  │ Template│ │Client│ │ & Agent   │  │  │
│  │  └─────────┘ └──────┘ └───────────┘  │  │
│  │  ┌─────────┐ ┌──────┐ ┌───────────┐  │  │
│  │  │ Memory  │ │Vector│ │ Document  │  │  │
│  │  │         │ │Store │ │ Loaders   │  │  │
│  │  └─────────┘ └──────┘ └───────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 六、学习建议（给前端转 AI 的你）

1. **先不用 LangChain**：先用原生 OpenAI SDK 写一个小项目，感受一下"痛点"——管理 Prompt 字符串、手动处理对话历史、自己写重试逻辑。然后回头学 LangChain，你就能理解它解决了什么。

2. **LCEL 是核心**：花时间搞懂 `|` 管道操作符和 `Runnable` 接口。其他都是辅助。

3. **LangGraph 先理解再看代码**：它的核心是**状态机思维**（State → Node → Edge），和你前端里的 Redux/状态管理模式非常像。一旦你理解了"图"这个概念，代码水到渠成。

4. **不要追版本**：这两个库更新极快，不要追每个新特性。理解了"为什么要分 LangChain 和 LangGraph"比会 100 个 API 更重要。

---

> **一句话收尾**：LangChain 给你零件，LangGraph 给你流水线。零件要认全，流水线要画清，这就是 AI 应用开发的工程化基本功。
