# Function Calling 完全指南

> **核心认知**：Function Calling 是 LLM 从"聊天机器人"进化为"AI Agent"的关键技术。它让模型不再只是"说话"，而是能"干活"--调用你的代码、查询数据库、操作外部系统。

---

## 目录

1. [什么是 Function Calling](#1-什么是-function-calling)
2. [为什么需要 Function Calling](#2-为什么需要-function-calling)
3. [核心概念](#3-核心概念)
4. [工作原理与流程](#4-工作原理与流程)
5. [如何定义一个 Function](#5-如何定义一个-function)
6. [完整代码实战](#6-完整代码实战)
7. [关键设计要点](#7-关键设计要点)
8. [进阶用法](#8-进阶用法)
9. [常见陷阱与避坑](#9-常见陷阱与避坑)
10. [与其他技术的关系](#10-与其他技术的关系)
11. [学习路径建议](#11-学习路径建议)

---

## 1. 什么是 Function Calling

### 1.1 定义

**Function Calling（函数调用）** 是 LLM API 提供的一种能力：**模型可以根据用户意图，自主决定调用你预先定义的函数，并生成符合函数参数 schema 的 JSON，由你的代码执行后把结果返回给模型，最终生成自然语言回复。**

通俗地说：**你给 LLM 一份"工具清单 + 使用说明"，LLM 在对话中判断该用哪个工具、填什么参数，然后"喊"你的代码去执行，拿到结果后再组织语言回答用户。**

### 1.2 一个直观例子

用户问："北京今天天气怎么样？"

```text
没有 Function Calling 时:
用户: 北京今天天气怎么样？
LLM:  我猜北京今天可能...（开始编造，因为它不知道实时数据）

有 Function Calling 时:
用户: 北京今天天气怎么样？
LLM:  [判断] 需要调用 get_weather 工具
      [返回] {"name": "get_weather", "arguments": {"city": "北京"}}
你的代码: 执行 get_weather(city="北京") -> {"temp": 25, "desc": "晴"}
LLM:  [基于结果] 北京今天 25°C，晴天，适合出行。
```

### 1.3 前端类比

> 前端同学可以这样理解：LLM 就像一个子组件，Function Calling 就是它 `emit` 出来的事件。子组件不知道怎么查天气，但它能告诉你"我需要查北京天气"，你（父组件）去执行查询，把结果通过 `props` 传回去。

---

## 2. 为什么需要 Function Calling

### 2.1 LLM 的天然局限

| 局限 | 表现 | Function Calling 如何解决 |
|------|------|--------------------------|
| **知识截止** | 训练数据有截止日期，不知道最新信息 | 调用 `search_web` 获取实时数据 |
| **不会算数** | 复杂计算经常出错 | 调用 `calculator` 精确计算 |
| **无法访问外部系统** | 不能查数据库、调 API | 调用 `query_database`、`send_email` |
| **无法感知时间** | 不知道"现在"是几点 | 调用 `get_current_time` |
| **容易幻觉** | 编造看似合理的信息 | 调用 `search_docs` 基于 RAG 回答 |

### 2.2 它带来的能力跃迁

```text
普通 LLM:     输入文本  -> 输出文本
Function Calling: 输入文本  -> 输出"动作指令" -> 执行 -> 输出文本
                  ↑ 这是从"聊天机器人"到"AI Agent"的分水岭
```

### 2.3 应用场景

- **智能客服**：查询订单、物流、退款
- **AI 助手**：日程管理、邮件发送、文件操作
- **数据分析**：查询数据库、生成图表、跑 SQL
- **工具集成**：调用 GitHub、Slack、Notion 等 API
- **RAG 系统**：检索知识库
- **Agent 系统**：多步推理 + 工具调用（ReAct、LangGraph）

---

## 3. 核心概念

### 3.1 Tool（工具）/ Function（函数）

你预先定义好、可被 LLM 调用的函数。每个工具有三个核心要素：
- **name**：函数名（LLM 用它来调用）
- **description**：功能描述（**决定 LLM 会不会选用这个工具**）
- **parameters**：参数的 JSON Schema

### 3.2 Tool Call（工具调用）

LLM 返回的调用请求，包含：
- `id`：本次调用的唯一标识（用于把结果回传）
- `name`：要调用的函数名
- `arguments`：参数（JSON 字符串）

### 3.3 Tool Result（工具结果）

你的代码执行函数后返回的结果，会以 `role: "tool"` 的消息形式追加到对话历史中。

### 3.4 三种消息角色（Function Calling 场景）

| 角色 | 作用 | 类比 |
|------|------|------|
| `system` | 告诉 LLM 它是谁、有哪些工具 | "岗位说明书" |
| `user` | 用户的输入 | "客户提问" |
| `assistant` | LLM 的回复（含 tool_calls） | "客服回应" |
| `tool` | 工具执行结果 | "后台查询结果" |

### 3.5 tool_choice 参数

控制 LLM 是否调用工具：

| 值 | 含义 |
|----|------|
| `"auto"` | 模型自主决定（默认，最常用） |
| `"none"` | 禁止调用工具 |
| `"required"` | 必须调用工具 |
| `{"type": "function", "function": {"name": "xxx"}}` | 强制调用指定工具 |

---

## 4. 工作原理与流程

### 4.1 完整流程图

```text
┌─────────────────────────────────────────────────────────┐
│  用户输入: "北京今天天气怎么样？"                          │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: 构建 messages + tools，调用 LLM                │
│  messages = [system, user]                              │
│  tools = [get_weather, calculator, ...]                 │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: LLM 返回 tool_calls                            │
│  tool_calls = [{                                        │
│    "id": "call_001",                                    │
│    "name": "get_weather",                               │
│    "arguments": '{"city": "北京"}'                      │
│  }]                                                     │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 你的代码执行函数                                │
│  result = get_weather(city="北京")                      │
│  result = {"temp": 25, "desc": "晴"}                    │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: 把结果以 role=tool 追加到 messages              │
│  messages.append({"role": "tool",                       │
│                    "tool_call_id": "call_001",           │
│                    "content": '{"temp":25,"desc":"晴"}'})│
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: 再次调用 LLM（带工具结果）                      │
│  LLM 基于结果生成自然语言                                │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  最终回复: "北京今天 25°C，晴天，适合出行。"              │
└─────────────────────────────────────────────────────────┘
```

### 4.2 核心循环（ReAct 模式）

Function Calling 的多轮循环本质就是 **ReAct** 模式：

```text
Thought（思考） -> Act（调用工具） -> Observe（观察结果）
     ↑                                          │
     └──────────── 循环直到能回答 ─────────────┘
                          │
                          ▼
                       Answer
```

### 4.3 伪代码

```python
def run_agent(user_input):
    messages = [
        {"role": "system", "content": "你是助手，可以调用工具"},
        {"role": "user", "content": user_input},
    ]
    
    for turn in range(max_turns):
        # 1. 调用 LLM
        response = llm.chat(messages=messages, tools=TOOLS)
        msg = response.choices[0].message
        
        # 2. 没有 tool_calls -> 直接回答，结束
        if not msg.tool_calls:
            return msg.content
        
        # 3. 有 tool_calls -> 执行每个工具
        messages.append(msg)  # 把 assistant 的 tool_calls 加入历史
        for tc in msg.tool_calls:
            result = TOOL_FUNCTIONS[tc.function.name](
                **json.loads(tc.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
        # 4. 循环继续，让 LLM 基于工具结果再判断
    
    return "达到最大轮数"
```

---

## 5. 如何定义一个 Function

### 5.1 OpenAI 标准 Schema

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息。当用户询问天气、气温、是否下雨等问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'、'上海'",
                    },
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。默认为今天。",
                    },
                },
                "required": ["city"],
            },
        },
    },
]
```

### 5.2 JSON Schema 字段速查

| 字段 | 作用 | 示例 |
|------|------|------|
| `type` | 数据类型 | `"string"` / `"number"` / `"boolean"` / `"array"` / `"object"` |
| `description` | 字段说明（**最重要**） | `"城市名称"` |
| `enum` | 枚举可选值 | `["celsius", "fahrenheit"]` |
| `required` | 必填字段列表 | `["city"]` |
| `default` | 默认值 | `"celsius"` |
| `items` | 数组元素 schema | `{"type": "string"}` |

### 5.3 三要素写作要点

#### ① name：函数名
- 用 `snake_case`
- 动词开头：`get_`、`search_`、`create_`、`send_`、`calculate_`
- 语义清晰：`get_weather` > `weather` > `w`

#### ② description：功能描述（最关键）
> **description 写得好不好，直接决定 LLM 会不会调用这个工具！**

```text
✗ "获取天气"
✓ "获取指定城市的天气信息。当用户询问天气、气温、是否下雨等问题时使用。"
```

要点：
- 说清"做什么"
- 说清"什么时候用"（触发场景）
- 必要时说清"不适用什么场景"

#### ③ parameters：参数 schema
- 每个参数都要有 `description`
- 用 `enum` 限定取值范围
- 用 `required` 明确必填项
- 用 `default` 给出默认值

---

## 6. 完整代码实战

### 6.1 最小可运行示例（OpenAI SDK）

```python
import json
from openai import OpenAI

client = OpenAI()

# 1. 定义工具函数
def get_weather(city: str) -> dict:
    weather_data = {
        "北京": {"temp": 25, "desc": "晴"},
        "上海": {"temp": 28, "desc": "多云"},
    }
    return weather_data.get(city, {"temp": 20, "desc": "未知"})

# 2. 定义 Tool Schema
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"},
            },
            "required": ["city"],
        },
    },
}]

# 3. 第一次调用 LLM
messages = [
    {"role": "user", "content": "北京天气怎么样？"},
]
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)
msg = response.choices[0].message

# 4. 处理 tool_calls
if msg.tool_calls:
    # 把 assistant 消息加入历史
    messages.append(msg)
    
    for tc in msg.tool_calls:
        # 解析参数
        args = json.loads(tc.function.arguments)
        # 执行函数
        result = get_weather(**args)
        # 把结果以 tool 消息回传
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False),
        })
    
    # 5. 第二次调用 LLM，让它基于结果生成回复
    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
# 没有 tool_calls -> 直接输出
else:
    print(msg.content)
```

### 6.2 封装成 Agent 类（推荐工程实践）

```python
import json
from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable
    
    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Agent:
    def __init__(self, tools: list[Tool], model: str = "gpt-4o-mini"):
        self.tools = {t.name: t for t in tools}
        self.schemas = [t.to_schema() for t in tools]
        self.model = model
    
    def execute(self, name: str, args: dict) -> str:
        tool = self.tools.get(name)
        if not tool:
            return json.dumps({"error": f"未知工具 {name}"})
        try:
            return str(tool.handler(**args))
        except Exception as e:
            return f"工具执行错误: {e}"
    
    def run(self, user_input: str, max_turns: int = 5) -> str:
        messages = [
            {"role": "system", "content": "你是助手，可以调用工具完成任务。"},
            {"role": "user", "content": user_input},
        ]
        for _ in range(max_turns):
            resp = self._call_llm(messages)
            msg = resp.choices[0].message
            
            if not msg.tool_calls:
                return msg.content
            
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = self.execute(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        return "达到最大轮数"
    
    def _call_llm(self, messages):
        from openai import OpenAI
        return OpenAI().chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.schemas,
            tool_choice="auto",
        )
```

> 完整实战代码见项目：[01_FunctionCalling与Agent.py](file:///Users/kevinzzzzzz/Documents/code/AIAPP_learning/python/07_Agent/01_FunctionCalling与Agent.py) 和 [02_function_calling实战.py](file:///Users/kevinzzzzzz/Documents/code/AIAPP_learning/week3-llm/code/02_function_calling实战.py)

---

## 7. 关键设计要点

### 7.1 工具粒度设计

```text
✗ 太细: create_user, update_user, delete_user, get_user (4个)
✓ 合适: manage_user(action: "create"|"update"|"delete"|"get", ...) (1个)

✗ 太粗: do_anything(task: string)
✓ 合适: get_weather, calculate, search_docs (各自职责清晰)
```

原则：**一个工具做一件事，但相关的操作可以合并**。

### 7.2 description 的写法进阶

```python
# 基础写法
"description": "搜索文档"

# 推荐写法（含触发场景）
"description": "搜索知识库文档。当用户询问技术概念、定义、原理等问题时使用，而不是直接用 LLM 自己的知识。"

# 高级写法（含边界与不适用场景）
"description": "搜索公司内部文档库。适用于查询产品文档、API 文档、设计规范。不适用于：实时新闻（用 search_web）、个人数据（用 query_database）。"
```

### 7.3 参数设计

```python
# ✗ 不好：让 LLM 拼日期字符串
"date": {"type": "string", "description": "日期"}

# ✓ 好：明确格式
"date": {"type": "string", "description": "日期，格式 YYYY-MM-DD", "example": "2024-12-25"}

# ✓ 好：用 enum 限定取值
"unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
```

### 7.4 错误处理

工具函数要返回**结构化的错误信息**，而不是抛异常：

```python
def get_weather(city: str) -> dict:
    if not city:
        return {"error": "城市名不能为空"}  # ✓ 返回错误信息
    # 不要: raise ValueError("城市名不能为空")  # ✗ 抛异常会让 LLM 困惑
```

---

## 8. 进阶用法

### 8.1 并行工具调用

OpenAI 的新模型支持一次返回多个 `tool_calls`，可以并行执行：

```python
# 用户问: "北京和上海的天气怎么样？"
# LLM 可能返回:
# tool_calls = [
#   {name: "get_weather", args: {city: "北京"}},
#   {name: "get_weather", args: {city: "上海"}},
# ]

# 处理：循环执行每个 tool_call，结果都 append 到 messages
for tc in msg.tool_calls:
    args = json.loads(tc.function.arguments)
    result = execute(tc.function.name, args)
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "content": json.dumps(result),
    })
```

### 8.2 多轮工具调用

LLM 可能需要**连续调用多个工具**才能完成任务：

```text
用户: "北京今天的天气适合户外运动吗？"
Turn 1: LLM 调用 get_weather(北京) -> 25°C 晴
Turn 2: LLM 调用 search_outdoor_activities(天气=晴, 温度=25) -> [跑步, 骑行]
Turn 3: LLM 综合结果回答用户
```

### 8.3 工具调用的流式输出

```python
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    stream=True,
)
# 流式时 tool_calls 是分片返回的，需要累积拼接
```

### 8.4 Structured Outputs（结构化输出）

OpenAI 的新功能，比 Function Calling 更严格地保证输出符合 schema：

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "weather_response",
            "schema": {...},
            "strict": True,  # 严格模式
        },
    },
)
```

---

## 9. 常见陷阱与避坑

### 9.1 ❌ 忘记把 assistant 消息加入历史

```python
# ✗ 错误：直接执行工具，没把 tool_calls 消息加入 messages
for tc in msg.tool_calls:
    result = execute(tc.function.name, args)
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
# 会报错：tool message 必须跟在对应的 assistant tool_calls 后面

# ✓ 正确：先把 assistant 消息加入，再添加 tool 结果
messages.append(msg)
for tc in msg.tool_calls:
    result = execute(tc.function.name, args)
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
```

### 9.2 ❌ description 写得太简略

```python
# ✗ LLM 不知道何时该用
"description": "查询"

# ✓ 说清触发场景
"description": "查询订单物流状态。当用户询问'我的快递到哪了''物流进度'时使用。需要订单号。"
```

### 9.3 ❌ 参数 schema 不完整

```python
# ✗ 没有 description，LLM 猜不出该填什么
"parameters": {"type": "object", "properties": {"q": {"type": "string"}}}

# ✓ 每个字段都有清晰说明
"parameters": {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "搜索关键词，如 'Python 异步编程'"},
    },
    "required": ["query"],
}
```

### 9.4 ❌ 死循环

LLM 可能反复调用工具而不给最终答案。**必须设置 `max_turns` 兜底**。

### 9.5 ❌ 安全风险：直接 eval 用户输入

```python
# ✗ 危险！LLM 生成的表达式可能包含恶意代码
result = eval(expression)

# ✓ 白名单校验
allowed = set("0123456789+-*/.() ")
if not all(c in allowed for c in expression):
    return {"error": "表达式包含不允许的字符"}
result = eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt})
```

### 9.6 ❌ 工具结果太大

```python
# ✗ 把整个数据库返回给 LLM，会撑爆 context
result = db.query("SELECT * FROM orders")  # 10万条记录
messages.append({"role": "tool", "content": json.dumps(result)})

# ✓ 分页 + 摘要
result = db.query("SELECT * FROM orders LIMIT 10")
summary = f"共 {total} 条，前10条: {result}"
```

---

## 10. 与其他技术的关系

### 10.1 Function Calling vs RAG

| 维度 | Function Calling | RAG |
|------|------------------|-----|
| **本质** | 让 LLM 调用外部函数 | 让 LLM 基于检索到的知识回答 |
| **解决什么** | "不会做"（计算、查实时数据、操作系统） | "不知道"（私有知识、最新信息） |
| **谁触发** | LLM 自主决定调用 | 开发者在调用前检索，把结果塞入 prompt |
| **典型场景** | 查天气、算数、发邮件 | 企业知识库问答、文档问答 |
| **关系** | RAG 本身可以封装成一个 `search_docs` 工具 | - |

> **常见组合**：把 RAG 检索封装成 `search_docs` 工具，让 LLM 决定何时检索。

### 10.2 Function Calling vs Agent

- **Function Calling** 是底层机制（一次工具调用）
- **Agent** 是上层架构（多轮工具调用 + 推理 + 决策）
- **ReAct** 是 Agent 的经典模式：Thought -> Action -> Observation 循环

```text
Function Calling ⊂ Agent
一次工具调用   多轮推理+调用+观察的循环
```

### 10.3 Function Calling vs ChatGPT Plugins / GPTs

- ChatGPT Plugins / GPTs 是 OpenAI 面向 C 端的产品形态
- 底层都是 Function Calling
- 你自己开发的应用用 Function Calling API 即可，不需要走 Plugins

### 10.4 与 LangChain / LangGraph 的关系

- LangChain 把 Function Calling 封装成 `Tool`、`Agent`、`AgentExecutor`
- LangGraph 用图（Graph）来编排多步工具调用，适合复杂 Agent 工作流
- 底层调用的还是 LLM 的 Function Calling 能力

---

## 11. 学习路径建议

### 阶段一：理解机制（1~2 天）
- 通读本文档，理解 5 步流程
- 跑通一个最小示例（get_weather）
- 理解 messages 流转过程

### 阶段二：动手实战（3~5 天）
- 定义 3~5 个实用工具（天气、计算、搜索、时间、发邮件）
- 封装成 Agent 类，支持多轮调用
- 实践并行工具调用、错误处理

### 阶段三：工程化（1~2 周）
- 工具注册表设计（参考项目中的 `Tool` dataclass）
- 工具结果序列化与截断
- 与 FastAPI 结合，做成 API 服务
- 日志、监控、重试机制

### 阶段四：Agent 进阶（持续）
- 学习 ReAct 模式（见 [02_ReAct模式.py](file:///Users/kevinzzzzzz/Documents/code/AIAPP_learning/python/07_Agent/02_ReAct模式.py)）
- 学习 LangGraph 多 Agent 编排
- 结合 RAG 构建知识库 Agent
- 探索 Multi-Agent 协作

### 推荐资源
- OpenAI 官方文档：Function Calling Guide
- Anthropic Claude Tool Use 文档
- LangChain Tools & Agents 文档
- 论文：*ReAct: Synergizing Reasoning and Acting in Language Models*

---

## 附录：核心概念速查表

| 概念 | 一句话理解 |
|------|-----------|
| **Tool / Function** | 你定义的、可被 LLM 调用的函数 |
| **Tool Call** | LLM 返回的"我要调用这个函数 + 参数" |
| **Tool Result** | 你执行函数后返回给 LLM 的结果 |
| **tool_choice** | 控制 LLM 是否/如何调用工具 |
| **JSON Schema** | 描述函数参数结构的规范 |
| **ReAct** | Reasoning + Acting，Agent 的经典模式 |
| **Parallel Tool Calls** | 一次返回多个工具调用，可并行执行 |
| **Structured Outputs** | 更严格的 JSON 输出模式 |

---

## 附录：典型场景的 Tool 设计参考

| 场景 | 工具名 | 关键参数 |
|------|--------|---------|
| 天气查询 | `get_weather` | `city`, `date?`, `unit?` |
| 数学计算 | `calculate` | `expression` |
| 网页搜索 | `search_web` | `query`, `num_results?` |
| 知识库检索 | `search_docs` | `query`, `top_k?` |
| 数据库查询 | `query_database` | `sql`, `database` |
| 发送邮件 | `send_email` | `to`, `subject`, `body` |
| 创建日程 | `create_event` | `title`, `start_time`, `end_time` |
| 获取时间 | `get_current_time` | (无参数) |
| 文件操作 | `read_file` / `write_file` | `path`, `content?` |
| API 调用 | `call_api` | `url`, `method`, `params?`, `body?` |

---

> **结语**：Function Calling 是 AI 应用开发的"分水岭"。掌握它，你就从"调 API 聊天"进入了"构建能干活的 AI Agent"的世界。下一步，把它和 RAG、LangGraph 结合，你就能构建出真正强大的 AI 应用。
