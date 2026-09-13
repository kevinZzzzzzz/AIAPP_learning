# 模块 04：Tool Calling 工具调用

> 对应周次：**W6**｜预计耗时：**15–18 小时**
> 前置要求：完成模块 01–03
>
> **本模块是"聊天机器人"和"Agent"的分界线。** 学完这个模块，你的程序才真正开始"做事"。

---

## 一、这个模块要解决什么问题

**一句话**：让模型能调用你写的函数去获取信息、执行操作——从"只会说"变成"会做事"。

学完这一模块，你应该能回答：

- 模型是真的在执行我的代码吗？（不是）
- 它怎么知道该调哪个工具？为什么有时候不调或调错？
- 一次工具调用背后发生了几次 API 请求？
- 工具报错了怎么办？模型能自己修复吗？
- 模型能调用的工具越多越好吗？
- 危险操作（转账、删数据）怎么防止模型乱调？

---

## 二、核心概念

### 2.1 最重要的认知：模型不执行任何代码

**这是新手最大的误解，必须先纠正。**

看起来是"模型调用了一个工具"，实际发生的事情是：

```
第 1 次请求：你 → 模型
  你发送：问题 + 工具清单（名称、描述、参数 Schema）
  模型返回：不是文字答案，而是一个"工具调用意图"
           {"name": "get_weather", "arguments": {"city": "北京"}}

┌─────────────────────────────────────────────┐
│ 到这里为止，模型的工作结束了。                 │
│ 它没有执行任何代码，只是输出了一个结构化的 JSON。│
│ 真正执行 get_weather("北京") 的是【你的代码】。 │
└─────────────────────────────────────────────┘

你的代码：执行 get_weather("北京") → 得到 "晴，22℃"

第 2 次请求：你 → 模型
  你发送：原始问题 + 工具调用意图 + 工具执行结果
  模型返回：自然语言答案 "北京今天晴，气温 22℃"

你的代码：把答案给用户
```

**必须记住的三个推论**：

| 推论 | 含义 |
|---|---|
| 安全边界在你的代码里，不在模型里 | 模型可以"要求"调用任何工具，但**执不执行由你的代码决定**。这是权限控制的立足点 |
| 一次工具调用 = 至少 2 次 API 请求 | 所以多步 Agent 的 token 成本是叠加的 |
| 工具清单要每次都发 | 模型不记得上次的工具，每次请求都要带上 |

### 2.2 工具（Tool）的定义要素

一个工具定义包含四部分：

```python
{
    "type": "function",
    "function": {
        "name": "get_weather",                    # 1. 名称：模型靠它选择
        "description": "查询指定城市的实时天气",    # 2. 描述：最重要！模型靠它判断该不该调
        "parameters": {                            # 3. 参数 Schema
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如「北京」「上海」"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位，默认摄氏度"
                }
            },
            "required": ["city"],
            "additionalProperties": False
        }
    }
}
```

**四个要素里，`description` 和参数描述的质量决定了 80% 的成功率。** 这就是 Prompt 工程在工具场景的延续：你写的描述，就是给模型的使用说明书。

### 2.3 工具描述怎么写（最关键的一节）

**反面例子**：

```python
"description": "获取天气"          # ❌ 太模糊：什么天气？哪里？实时还是预报？
```

模型不知道什么时候该用它，也不知道不该用它。

**正面例子**：

```python
"description": """查询指定城市的当前实时天气状况，包括温度、天气现象、湿度、风力。

【何时使用】用户询问某个城市当前或今天的天气时使用。
【何时不要使用】查询历史天气、未来超过 3 天的天气预报时不要使用本工具。
【返回内容】温度（摄氏度）、天气现象（晴/多云/雨等）、湿度百分比、风力等级。"""
```

**工具描述的黄金四要素**：

| 要素 | 作用 | 例子 |
|---|---|---|
| **做什么** | 明确功能边界 | "查询指定城市的当前实时天气" |
| **何时用** | 正向触发条件 | "用户询问某城市当前天气时" |
| **何时不用** | 反向排除条件（**最容易被忽略但极其重要**） | "查历史天气、查预报时不要用" |
| **返回什么** | 让模型知道能拿到什么，决定后续步骤 | "返回温度、天气现象、湿度、风力" |

**参数描述同理**：

```python
# ❌ 差
"city": {"type": "string"}

# ✅ 好
"city": {
    "type": "string",
    "description": "城市名称，使用中文，如「北京」「上海」「深圳」。不要包含「市」以外的行政区划后缀。"
}
```

**枚举值是利器**：如果参数取值有限，**一定用 `enum` 约束**。

```python
"priority": {
    "type": "string",
    "enum": ["low", "medium", "high"],        # 模型不会输出 "urgent" 这种没定义的
    "description": "优先级。urgent 场景用 high"
}
```

### 2.4 工具选择的机制（为什么有时候不调）

模型决定是否调用工具，考虑：

1. **问题是否需要外部信息**（"你好"不需要调工具，"北京天气"需要）
2. **现有工具能否解决**（能解决才调）
3. **描述是否清晰**（描述模糊 → 模型不确定 → 倾向不调）
4. **`tool_choice` 参数**（你可以强制或禁止调用）

**`tool_choice` 的三种模式**：

| 值 | 行为 | 适用 |
|---|---|---|
| `"auto"` | 模型自己决定（默认） | 通用对话 |
| `"required"` | 必须调用某个工具 | 确保有工具调用（如强制检索）|
| `{"type":"function","function":{"name":"x"}}` | 强制调用指定工具 | 明确要调某个工具时 |
| `"none"` | 禁止调用工具 | 纯聊天模式 |

**为什么"不调工具"是常见的 bug**：

| 症状 | 原因 | 修法 |
|---|---|---|
| 该调时不调 | 描述太模糊，模型没意识到该用 | 补"何时使用" |
| 不该调时乱调 | 描述边界不清，或没有"何时不用" | 补"何时不要使用" |
| 调错工具 | 两个工具描述重叠 | 明确区分各自边界 |
| 参数填错 | 参数描述不清 or 没有 enum | 补参数说明、加 enum、加示例 |

### 2.5 并行工具调用

模型可以**一次返回多个工具调用请求**（如果它们互不依赖）。

```
用户：北京和上海今天天气怎么样？

模型返回两个 tool_calls：
  [{name: "get_weather", arguments: {city: "北京"}},
   {name: "get_weather", arguments: {city: "上海"}}]

你的代码：并发执行这两个调用（asyncio.gather），再一起返回
```

**收益**：延迟从"串行 2 次"变成"并发 1 次"，对 Agent 性能影响显著。

**判断依赖关系是你的责任**：模型有时会把有依赖关系的调用也并行发出（比如先查用户 ID 再查订单，它可能同时发两个）。**需要通过工具描述引导**（"调用本工具前必须先获得 user_id"）。

### 2.6 工具执行失败怎么处理

**这是工业级实现和新手实现的核心差异。**

```python
# ❌ 新手做法：异常直接抛出 → 整个 Agent 崩溃
result = tool_fn(**args)      # 工具报错，程序挂掉

# ❌ 次差做法：返回空字符串
except Exception:
    return ""                 # 模型收到空内容，开始编造

# ✅ 正确做法：把错误作为"观察结果"返回给模型
except Exception as e:
    return json.dumps({
        "success": False,
        "error": str(e),
        "hint": "参数格式错误，日期应为 YYYY-MM-DD 格式"
    }, ensure_ascii=False)
```

**为什么要把错误给模型**：模型看到错误信息后，往往能**自己修正参数重试**。这是 Agent 自愈能力的基础。

```
模型调用：get_orders(date="3月15日")
工具返回：{"success": false, "error": "日期格式错误", "hint": "请用 YYYY-MM-DD"}
模型反思 → 重新调用：get_orders(date="2026-03-15")   ✅ 成功
```

**错误处理的完整策略**：

| 错误类型 | 处理方式 |
|---|---|
| 参数格式错误 | 把错误+提示返回模型，让它自己修（通常 1 次就修好） |
| 权限不足 | 返回明确原因，不要重试（并记录审计日志） |
| 资源不存在 | 返回"未找到"，让模型决定下一步 |
| 临时故障（网络/超时） | 系统层面自动重试（指数退避），不暴露给模型 |
| 业务逻辑错误 | 返回业务含义的错误，让模型解释给用户 |

### 2.7 权限控制：安全的关键

**核心原则：模型可以"请求"任何能力，但你的代码决定给不给。**

**三层权限设计**：

| 层级 | 做法 | 适用 |
|---|---|---|
| **白名单** | 只把允许的工具传给模型（不给它危险工具） | 第一层，基础 |
| **参数校验** | 检查参数是否越界（如退款金额上限） | 第二层 |
| **人工确认** | 高风险操作暂停，等人点确认 | 第三层，终极手段 |

```python
# src/permissions.py
from enum import Enum
from dataclasses import dataclass

class RiskLevel(Enum):
    LOW = "low"           # 只读查询：直接执行
    MEDIUM = "medium"     # 写操作：记录日志，直接执行
    HIGH = "high"         # 危险操作：需人工确认

@dataclass
class ToolSpec:
    name: str
    fn: callable
    risk: RiskLevel
    requires_confirm: bool = False

# 注册表：明确每个工具的风险等级
TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tool(name: str, risk: RiskLevel = RiskLevel.LOW, requires_confirm: bool = False):
    def decorator(fn):
        TOOL_REGISTRY[name] = ToolSpec(name=name, fn=fn, risk=risk,
                                       requires_confirm=requires_confirm)
        return fn
    return decorator

# 危险工具标记
@register_tool("query_order", risk=RiskLevel.LOW)
def query_order(order_id: str):
    ...

@register_tool("refund_order", risk=RiskLevel.HIGH, requires_confirm=True)
def refund_order(order_id: str, amount: float):
    ...

# 执行前的守卫
def execute_tool(name: str, args: dict, user_confirmed: bool = False) -> dict:
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {"success": False, "error": f"未注册的工具：{name}"}   # 白名单拦截

    # 参数越界检查
    if name == "refund_order" and args.get("amount", 0) > 1000:
        return {"success": False, "error": "单笔退款不得超过 1000 元，需人工审批"}

    # 高风险操作需要确认
    if spec.requires_confirm and not user_confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "message": f"即将执行高风险操作：{name}，参数：{args}。请用户确认。",
        }

    try:
        result = spec.fn(**args)
        audit_log(name, args, result)            # 审计日志：谁、何时、调了什么、结果
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

> **这段设计在第 8 周学 LangGraph 的 `interrupt` 时会升级成完整的"人在环"流程。现在先建立这个意识。**

### 2.8 工具数量与上下文成本

**工具定义也占 token。** 每个工具的定义（名称+描述+Schema）大约 100–300 token。

| 工具数 | 每次都带的 token 成本 | 影响 |
|---|---|---|
| 3 个 | ~500 token | 可忽略 |
| 10 个 | ~2000 token | 开始有成本 |
| 50 个 | ~10000 token | 明显成本 + 模型选择困难（容易选错）|

**结论**：
1. **工具不要贪多**。5–10 个是舒适区。超过 15 个要考虑"工具分组/渐进式暴露"
2. **善用 prompt caching**：工具定义固定不变，放前面能命中缓存（DeepSeek 缓存命中价是 1/50）

**工具过多时的解法**：
- **分组加载**：根据用户意图先确定场景，只加载该场景的工具
- **工具检索**：用向量检索从工具库里找相关工具（工具本身也是文本）
- **层级化**：一个"总入口"工具，模型通过它逐步细化（类似 CLI 的子命令）

### 2.9 MCP：工具生态的标准化协议

**是什么**：Model Context Protocol，Anthropic 2024 年 11 月提出的开放协议，用来标准化"Agent 怎么发现和调用外部工具/数据源"。现在是跨厂商的标准，由 Linux 基金会下的 Agentic AI Foundation 治理。

**解决什么问题**：在 MCP 之前，每个 Agent 框架接入每个工具都要写一套适配代码。MCP 定义了统一的通信协议，**一次实现，到处可用**。

**核心概念**：

| 概念 | 说明 | 谁控制 |
|---|---|---|
| **Tools** | 模型可自主调用的函数 | 模型控制 |
| **Resources** | 可读取的数据（文档、数据） | 应用控制 |
| **Prompts** | 预设的提示词模板/工作流 | 用户控制 |

**传输方式**：本地进程用 `stdio`，远程服务用 `Streamable HTTP`。

> ⚠️ **版本提醒（重要）**：MCP 最新规范是 **2026-07-28**，相比 2025-11-25 版本有重大变化：
> - **无状态核心**：取消了 `initialize` 握手和 `Mcp-Session-Id`，每次请求自描述，普通轮询负载均衡即可水平扩展
> - **头部路由**：`Mcp-Method` 和 `Mcp-Name` HTTP 头用于网关路由和限流
> - **MRTR（多轮往返请求）**：替代原来需要长连接的 elicitation/sampling 机制
> - **Tasks 扩展**：支持长时间运行的异步工具调用
> - 旧的 Roots / Sampling 已废弃
>
> **如果你在网上看到需要 `initialize` 握手的 MCP 教程，那是 2025 年前的旧规范。**

**要不要现在学 MCP**：

| 你的情况 | 建议 |
|---|---|
| 学习阶段 | 知道它是什么、解决什么问题就够。**先把原生 Tool Calling 吃透** |
| 要用现成的 MCP 工具（如文件系统、数据库） | 直接用现成 MCP Server，不用自己实现 |
| 要把自己的服务暴露给其他 Agent | 读一下官方规范，用官方 SDK 实现 |
| 面试 | 大概率会问"MCP 是什么、和 Function Calling 什么关系"，要能答 |

**MCP 与 Function Calling 的关系**（面试高频）：

| 维度 | Function Calling | MCP |
|---|---|---|
| 层级 | 模型接口层能力 | 协议层标准 |
| 范围 | 单次请求内的工具调用 | 跨进程/跨服务的工具发现与调用 |
| 解决的问题 | 让模型能表达"我要调工具" | 让工具能被标准化地发现、描述、复用 |
| 关系 | MCP 底层仍然用 Function Calling 的机制 | MCP 是 Function Calling 的"标准化封装 + 生态" |

---

## 三、知识点清单

- [ ] 模型不执行代码，只输出工具调用意图（一次调用 = 2 次 API 请求）
- [ ] 工具定义的四个要素：name / description / parameters / required
- [ ] 工具描述的黄金四要素（做什么/何时用/何时不用/返回什么）
- [ ] 参数 Schema 设计：enum、description、required、additionalProperties
- [ ] `tool_choice` 的四种模式及适用场景
- [ ] 工具选择失败的四种症状与对应修法
- [ ] 并行工具调用的机制、收益与依赖关系处理
- [ ] 工具执行失败的分类处理策略（哪些给模型、哪些系统内重试）
- [ ] 三层权限设计（白名单 / 参数校验 / 人工确认）+ 审计日志
- [ ] 工具数量与 token 成本的关系，工具过多的三种解法
- [ ] MCP 的定位、三个核心概念、传输方式、与 Function Calling 的关系
- [ ] MCP 2026-07-28 规范的关键变化（无状态、MRTR、Tasks）

---

## 四、代码示例

### 4.1 最小工具调用（理解机制）

```python
# src/minimal_tool_call.py
"""最简工具调用 demo。理解这个循环，你就理解了 Function Calling 的全部本质。"""
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# ---------- 1. 定义真实函数 ----------
def get_weather(city: str, unit: str = "celsius") -> dict:
    """真实场景这里会调天气 API，demo 里返回模拟数据"""
    fake = {"北京": ("晴", 22), "上海": ("多云", 26), "深圳": ("阵雨", 29)}
    cond, temp = fake.get(city, ("未知", 20))
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32)
    return {"city": city, "condition": cond, "temperature": temp, "unit": unit}

# ---------- 2. 工具清单（发给模型的） ----------
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": """查询指定城市的当前实时天气。

【何时使用】用户询问某城市当前或今天的天气时使用。
【何时不要使用】查询历史天气或 3 天以上的预报时不要使用。
【返回内容】天气现象、温度、单位。""",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市中文名，如「北京」「上海」"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"],
                         "description": "温度单位，默认摄氏度"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}]

# 名称 → 函数的映射表（执行用）
TOOL_FUNCTIONS = {"get_weather": get_weather}


def ask_model(messages: list[dict]) -> object:
    return client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        tools=TOOLS,
        temperature=0,          # 工具调用必须低温
    )


def chat_with_tools(user_input: str):
    messages = [
        {"role": "system", "content": "你是助手。需要外部信息时调用提供的工具。"},
        {"role": "user", "content": user_input},
    ]

    # ===== 第 1 次请求：模型决定是否调工具 =====
    resp = ask_model(messages)
    msg = resp.choices[0].message

    # 没有工具调用 → 直接返回文字答案
    if not msg.tool_calls:
        return msg.content

    print(f"[模型决定调用 {len(msg.tool_calls)} 个工具]")

    # ===== 关键：把模型的"调用意图"加进消息历史 =====
    messages.append(msg)

    # ===== 执行工具（这才是你的代码真正干活的地方）=====
    for tc in msg.tool_calls:
        fn_name = tc.function.name
        args = json.loads(tc.function.arguments)
        print(f"  → 执行 {fn_name}({args})")

        if fn_name not in TOOL_FUNCTIONS:
            # 白名单校验：模型可以要求调用任何工具，但只有注册了的才执行
            result = {"success": False, "error": f"工具 {fn_name} 不存在"}
        else:
            try:
                result = {"success": True, "data": TOOL_FUNCTIONS[fn_name](**args)}
            except Exception as e:
                # 错误也返回给模型，让它自己修
                result = {"success": False, "error": str(e), "hint": "请检查参数格式"}

        print(f"  ← 结果 {result}")

        # ===== 把工具结果加进消息历史，关联 tool_call_id =====
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,                    # 必须对应，否则模型不知道这是哪个调用的结果
            "content": json.dumps(result, ensure_ascii=False),
        })

    # ===== 第 2 次请求：模型基于工具结果生成最终答案 =====
    final = ask_model(messages)
    return final.choices[0].message.content


if __name__ == "__main__":
    print(chat_with_tools("北京今天天气怎么样？"))
    print("\n" + "=" * 50 + "\n")
    print(chat_with_tools("你好，请介绍一下你自己"))     # 这个不会调工具
```

**这个 demo 你要能指认出三个关键点**：
1. `messages.append(msg)` —— 把模型的调用意图**也**加入历史，否则模型不知道自己刚才要求调什么
2. `tool_call_id` 的对应关系 —— 模型靠它把结果和请求关联起来，多个并行调用时尤其重要
3. 两次 API 请求的位置 —— 这就是"一次工具调用 = 2 次请求"的具体体现

### 4.2 并行工具调用 + 完整 Agent 循环

```python
# src/tool_agent.py
"""多工具 + 并行调用 + 循环上限 + 错误处理 的完整实现。
这个结构就是你后续所有 Agent 的骨架。
"""
import os, json, asyncio, logging
from typing import Callable
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

MAX_ITERATIONS = 10            # ⚠️ 必须有循环上限，否则可能无限调用烧钱


# ============ 工具定义与注册 ============
class Tool:
    def __init__(self, name: str, description: str, parameters: dict,
                 fn: Callable, requires_confirm: bool = False):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.fn = fn
        self.requires_confirm = requires_confirm

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册表：管理工具定义、执行、权限。"""
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        return self

    def schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def execute(self, name: str, args: dict, confirmed: bool = False) -> dict:
        """统一的工具执行入口，含白名单 + 权限 + 错误处理。"""
        tool = self._tools.get(name)
        if tool is None:
            return {"success": False, "error": f"未注册的工具：{name}"}

        if tool.requires_confirm and not confirmed:
            return {"success": False, "needs_confirmation": True,
                    "message": f"操作 {name} 需要用户确认，参数：{args}"}

        try:
            data = tool.fn(**args)
            logger.info(f"工具执行成功 {name}({args})")
            return {"success": True, "data": data}
        except TypeError as e:
            # 参数错误：把提示给模型，它通常能自己修
            return {"success": False, "error": f"参数错误：{e}",
                    "hint": f"请检查参数格式，期望：{tool.parameters}"}
        except Exception as e:
            logger.exception(f"工具执行失败 {name}")
            return {"success": False, "error": str(e)}


# ============ 具体工具 ============
registry = ToolRegistry()

def search_web(query: str, max_results: int = 3) -> list[dict]:
    """模拟联网搜索"""
    return [{"title": f"关于「{query}」的结果{i}", "url": f"https://example.com/{i}",
             "snippet": f"{query} 相关摘要内容 {i}"} for i in range(1, max_results + 1)]

def calculator(expression: str) -> dict:
    """安全计算器：只允许基础数学运算"""
    import ast, operator
    allowed = {ast.Add: operator.add, ast.Sub: operator.sub,
               ast.Mult: operator.mul, ast.Div: operator.truediv,
               ast.Pow: operator.pow, ast.USub: operator.neg}
    try:
        node = ast.parse(expression, mode="eval").body
        def ev(n):
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.BinOp) and type(n.op) in allowed:
                return allowed[type(n.op)](ev(n.left), ev(n.right))
            if isinstance(n, ast.UnaryOp) and type(n.op) in allowed:
                return allowed[type(n.op)](ev(n.operand))
            raise ValueError("不支持的表达式")
        return {"expression": expression, "result": ev(node)}
    except Exception as e:
        return {"error": f"计算失败：{e}", "hint": "只支持 + - * / ** 和数字"}

def get_weather(city: str, unit: str = "celsius") -> dict:
    fake = {"北京": ("晴", 22), "上海": ("多云", 26), "深圳": ("阵雨", 29)}
    cond, temp = fake.get(city, ("未知", 20))
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32)
    return {"city": city, "condition": cond, "temperature": temp, "unit": unit}

def send_email(to: str, subject: str, body: str) -> dict:
    """高风险操作：需要人工确认"""
    return {"sent": True, "to": to, "subject": subject}

registry.register(Tool(
    name="search_web",
    description="""联网搜索获取实时信息。

【何时使用】需要最新资讯、实时数据、或你不确定的事实时使用。
【何时不要使用】常识性问题、数学计算、查天气时不要使用。
【返回内容】搜索结果列表，含标题、链接、摘要。""",
    parameters={"type": "object", "properties": {
        "query": {"type": "string", "description": "搜索关键词，尽量具体"},
        "max_results": {"type": "integer", "description": "返回条数，1-10，默认 3",
                        "minimum": 1, "maximum": 10},
    }, "required": ["query"], "additionalProperties": False},
    fn=search_web,
))

registry.register(Tool(
    name="calculator",
    description="""执行数学计算，支持 + - * / ** 运算。

【何时使用】任何需要精确计算的场景，包括算术、百分比、幂运算。
【何时不要使用】不需要计算时不要调用。
【返回内容】计算结果数值。
注意：你必须使用本工具计算，不要自己心算。""",
    parameters={"type": "object", "properties": {
        "expression": {"type": "string",
                       "description": "数学表达式，如「12345 * 67890」或「(100-20)/4」"},
    }, "required": ["expression"], "additionalProperties": False},
    fn=calculator,
))

registry.register(Tool(
    name="get_weather",
    description="""查询指定城市的当前实时天气。

【何时使用】用户询问某城市当前或今天的天气。
【何时不要使用】查历史天气或多日预报时不要使用。
【返回内容】天气现象、温度、单位。""",
    parameters={"type": "object", "properties": {
        "city": {"type": "string", "description": "城市中文名，如「北京」"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"],
                 "description": "温度单位，默认摄氏度"},
    }, "required": ["city"], "additionalProperties": False},
    fn=get_weather,
))

registry.register(Tool(
    name="send_email",
    description="""发送邮件。

【何时使用】用户明确要求发送邮件时。
【何时不要使用】用户只是提到邮件内容但没要求发送时不要调用。
【注意】本操作会真实发送邮件，属于高风险操作，需要用户确认。""",
    parameters={"type": "object", "properties": {
        "to":      {"type": "string", "description": "收件人邮箱"},
        "subject": {"type": "string", "description": "邮件主题"},
        "body":    {"type": "string", "description": "邮件正文"},
    }, "required": ["to", "subject", "body"], "additionalProperties": False},
    fn=send_email,
    requires_confirm=True,          # 高风险标记
))


# ============ Agent 主循环 ============
SYSTEM_PROMPT = """你是一个能调用工具的助手。请遵守：

1. 需要工具能提供的信息时，主动调用工具，不要凭空回答
2. 涉及计算时**必须**使用 calculator，不要自己心算
3. 可以并行调用多个互不依赖的工具
4. 工具返回错误时，根据错误提示调整参数重试
5. 工具返回 needs_confirmation 时，告诉用户需要确认，不要重复调用
6. 最多进行 10 轮工具调用，如果无法完成就说明原因"""

def run_agent(user_input: str, max_iterations: int = MAX_ITERATIONS,
              auto_confirm: bool = False) -> dict:
    """Agent 主循环。返回 {answer, steps, tool_calls}"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    steps = []
    pending_confirmation = None

    for iteration in range(max_iterations):
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=registry.schemas(),
            temperature=0,
        )
        msg = resp.choices[0].message
        messages.append(msg)

        # 没有工具调用 → 得到最终答案
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "steps": steps,
                "pending_confirmation": pending_confirmation,
            }

        # 有工具调用 → 执行（并行）
        parallel = len(msg.tool_calls) > 1
        print(f"[第 {iteration+1} 轮] {'并行' if parallel else ''}调用 {len(msg.tool_calls)} 个工具")

        def exec_one(tc):
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                return tc, {"success": False, "error": "参数不是合法 JSON，请重新输出"}
            result = registry.execute(name, args, confirmed=auto_confirm)
            return tc, result

        # 并行执行（工具是 IO 密集型，用线程池能显著降低延迟）
        with ThreadPoolExecutor(max_workers=5) as pool:
            tool_results = list(pool.map(exec_one, msg.tool_calls))

        for tc, result in tool_results:
            name = tc.function.name
            print(f"  → {name}({tc.function.arguments[:60]}...)")
            print(f"  ← {json.dumps(result, ensure_ascii=False)[:100]}")

            steps.append({"tool": name,
                          "args": json.loads(tc.function.arguments or "{}"),
                          "result": result})

            if result.get("needs_confirmation"):
                pending_confirmation = {"tool": name, "args": json.loads(tc.function.arguments)}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return {"answer": "达到最大迭代次数，任务未完成。已完成步骤见 steps。",
            "steps": steps, "pending_confirmation": pending_confirmation}


if __name__ == "__main__":
    print("=" * 60)
    print(run_agent("北京和上海今天天气怎么样？")["answer"])         # 并行调用
    print("=" * 60)
    print(run_agent("12345 乘以 67890 等于多少？")["answer"])        # 工具计算
    print("=" * 60)
    r = run_agent("帮我把项目进度发给 boss@company.com")
    print(r["answer"])
    print("待确认：", r["pending_confirmation"])                     # 高风险拦截
```

### 4.3 异步版本（FastAPI 场景必备，W10 会用到）

```python
# src/async_agent.py
"""异步版本的 Agent。FastAPI 里必须用异步，否则阻塞事件循环。
注意：OpenAI SDK 有 AsyncOpenAI，工具也要用 async 函数。
"""
import asyncio, json, os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
aclient = AsyncOpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

async def search_web_async(query: str) -> dict:
    await asyncio.sleep(0.3)          # 模拟 IO 等待
    return {"query": query, "results": [f"结果1 for {query}", f"结果2 for {query}"]}

async def get_weather_async(city: str) -> dict:
    await asyncio.sleep(0.3)
    return {"city": city, "temperature": 22, "condition": "晴"}

ASYNC_TOOLS = {
    "search_web": search_web_async,
    "get_weather": get_weather_async,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_web",
        "description": "联网搜索实时信息",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                       "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "查询城市当前天气",
        "parameters": {"type": "object",
                       "properties": {"city": {"type": "string", "description": "城市名"}},
                       "required": ["city"], "additionalProperties": False}}},
]

async def run_agent_async(user_input: str, max_iter: int = 8) -> str:
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_iter):
        resp = await aclient.chat.completions.create(
            model="deepseek-v4-flash", messages=messages,
            tools=TOOL_SCHEMAS, temperature=0,
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        # 并发执行所有工具调用（关键性能优化）
        async def run_one(tc):
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            fn = ASYNC_TOOLS.get(name)
            if not fn:
                return tc.id, {"success": False, "error": f"未知工具 {name}"}
            try:
                return tc.id, {"success": True, "data": await fn(**args)}
            except Exception as e:
                return tc.id, {"success": False, "error": str(e)}

        results = await asyncio.gather(*[run_one(tc) for tc in msg.tool_calls])
        for call_id, result in results:
            messages.append({"role": "tool", "tool_call_id": call_id,
                             "content": json.dumps(result, ensure_ascii=False)})

    return "未能在限定轮次内完成"


if __name__ == "__main__":
    print(asyncio.run(run_agent_async("帮我查一下最新的 AI Agent 框架，并告诉我北京天气")))
```

---

## 五、常见坑

### 坑 1：以为模型在执行代码
**后果**：写出不安全的系统，以为"模型不会做危险的事"。
**正确做法**：记住模型只是输出 JSON 意图，**执行权完全在你的代码里**。所有权限校验放在你的执行层。

### 坑 2：工具描述太简短
**后果**：该调时不调、乱调、参数填错，整天在调 Prompt 却找不到根因。
**正确做法**：工具描述写"做什么/何时用/何时不用/返回什么"四要素。

### 坑 3：忘记把模型的消息（含 tool_calls）加进历史
**后果**：模型不知道自己在等什么结果，行为混乱。
**正确做法**：`messages.append(msg)`，且 `tool` 消息必须带正确的 `tool_call_id`。

### 坑 4：没有循环上限
**后果**：模型陷入循环（反复调同一个工具），token 疯狂消耗，账单失控。
**正确做法**：`MAX_ITERATIONS` 是**强制要求**，不是可选优化。

### 坑 5：工具报错就抛异常
**后果**：整个 Agent 崩溃，或者返回空导致模型开始编造。
**正确做法**：把错误结构化后返回给模型，让它自己修正（附 hint 效果更好）。

### 坑 6：并行执行有依赖关系的工具
**后果**：第二个工具需要第一个的结果（如 user_id），并发执行导致失败。
**正确做法**：在工具描述里写清依赖（"调用前必须先获得 user_id"）；必要时改成串行。

### 坑 7：不设 `temperature=0`
**后果**：输出的工具调用 JSON 格式不稳定，甚至参数值漂移。
**正确做法**：工具调用场景 `temperature ≤ 0.3`，最好 0。

### 坑 8：把所有工具都给模型
**后果**：token 成本高，模型选择困难，容易调错。
**正确做法**：控制在 5–10 个；超过 15 个用分组加载或工具检索。危险工具不给，或标记需确认。

### 坑 9：危险操作直接执行
**后果**：模型误判用户意图，真的删了数据/发了邮件/转了账。
**正确做法**：三层权限（白名单 + 参数校验 + 人工确认）+ 审计日志。**没有任何理由省略这一步。**

### 坑 10：工具结果不限制长度
**后果**：一个搜索返回 100KB 文本，直接把上下文撑爆。
**正确做法**：工具内部就做截断（如只返回 Top-3、单条限制 500 字），不要让原始数据直接进上下文。

---

## 六、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 跑通最小工具调用 demo，用日志确认"一次工具调用发生了 2 次 API 请求" | ⭐⭐ |
| 2 | 故意把工具描述写得很烂，观察模型的行为变化；再改成四要素写法对比 | ⭐⭐ |
| 3 | 实现 3 个工具（搜索/计算/天气），测试模型的工具选择准确性（20 条测试问题） | ⭐⭐⭐ |
| 4 | 实现并行工具调用，测量串行 vs 并行的延迟差异 | ⭐⭐⭐ |
| 5 | 实现错误自愈：让工具故意返回"日期格式错误"，观察模型能否自己修正重试 | ⭐⭐⭐ |
| 6 | 给工具加三层权限控制 + 审计日志，测试高风险工具被正确拦截 | ⭐⭐⭐⭐ |
| 7 | 实现"工具过多"的实验：注册 20 个工具，测试模型选择准确率是否下降 | ⭐⭐⭐⭐ |
| 8 | 接入一个现成的 MCP Server，理解 MCP 的调用流程 | ⭐⭐⭐⭐ |
| 9 | **【项目任务】** 做一个带工具执行轨迹可视化的 Agent（Web 界面） | ⭐⭐⭐⭐⭐ |

**任务 5、6 是重点。** 错误自愈和权限控制，是把"玩具 demo"和"能上线的系统"区分开的两件事。

---

## 七、自测题

**Q1：模型是怎么"调用"工具的？它真的执行了我的 Python 函数吗？**
<details><summary>参考答案</summary>
不是。模型只是在输出里生成了一个结构化的意图（工具名 + 参数 JSON）。真正执行函数的是你的代码。完整流程：① 你发请求（含工具清单）→ ② 模型返回工具调用意图 → ③ 你的代码校验权限、执行函数 → ④ 你把执行结果作为 tool 消息再发给模型 → ⑤ 模型基于结果生成自然语言答案。所以一次工具调用至少 2 次 API 请求。最重要的推论：**安全边界在你的代码里，不在模型里**。
</details>

**Q2：为什么工具描述要写"何时不要使用"？**
<details><summary>参考答案</summary>
因为模型判断"该不该调用"主要靠描述。只写"做什么"会让模型在边界情况上判断失误——比如"get_weather 查询天气"这个描述，模型可能在用户问"上周天气"或"明天天气"时也去调用。写明"查询历史天气或多日预报时不要使用"，能显著减少误调用。实践中，"何时不用"往往比"何时用"更能提升准确率，因为它排除了容易混淆的场景。
</details>

**Q3：一次"北京和上海天气"的提问，背后发生了几次 API 请求？**
<details><summary>参考答案</summary>
至少 2 次模型请求（第 1 次返回两个并行工具调用，第 2 次基于结果生成答案）。工具执行本身是本地/外部 API 调用，不算模型请求。如果模型在拿到结果后又决定调更多工具，请求数会继续增加。这就是 Agent 的成本模型：**请求数 = 轮数 + 1，成本随轮数线性增长**。
</details>

**Q4：工具执行的错误应该给模型还是自己处理？**
<details><summary>参考答案</summary>
分类型。① **参数格式错误**：给模型，并附上 hint（"日期格式应为 YYYY-MM-DD"），模型通常能自己修正重试——这是 Agent 自愈的基础；② **权限不足**：不给模型重试机会，直接拒绝并记录审计日志（重试也没用，且可能是攻击）；③ **临时故障**（网络/超时）：在系统层面自动重试（指数退避），不暴露给模型，避免模型被无意义的错误干扰；④ **业务错误**（如"余额不足"）：返回给模型，让它向用户解释。
</details>

**Q5：为什么工具调用必须设置 temperature=0？**
<details><summary>参考答案</summary>
因为工具调用要求输出严格的 JSON 结构（工具名 + 参数），任何随机性都可能导致格式错误或参数漂移。比如参数应该是 "2026-03-15"，高温下可能生成 "2026年3月15日" 导致工具执行失败。工具调用是确定性任务，不是创意任务。
</details>

**Q6：为什么必须设 MAX_ITERATIONS？**
<details><summary>参考答案</summary>
因为模型可能陷入循环：反复调用同一个工具（参数略微变化），或者调工具A失败→调工具B→又想调工具A，永远得不到最终答案。没有上限的话，token 会持续消耗直到失控。LangGraph 等框架默认上限是 25 次，但你必须理解这个机制并主动设置。同时应该加循环检测（最近 3 次调用完全相同就中断）。
</details>

**Q7：模型同时返回了 3 个工具调用，其中第 2 个需要第 1 个的结果。怎么办？**
<details><summary>参考答案</summary>
这是模型对依赖关系判断失误。处理方式：① **预防**——在工具描述里明确写"调用本工具前必须先获得 xxx"，引导模型正确排序；② **检测**——在代码里校验参数是否满足前置条件，不满足就返回错误"缺少必需参数 xxx，请先调用 yyy"；③ **兜底**——如果并发执行失败，把错误返回给模型让它重新规划。根本上，模型对依赖关系的判断不可靠，关键流程不应用并发的隐式依赖，应改成明确的多步串行设计。
</details>

**Q8：工具越多越好吗？有什么代价？**
<details><summary>参考答案</summary>
不是。代价有三：① **token 成本**——每个工具定义约 100–300 token，每次请求都要发送全部工具定义，20 个工具就是 4000+ token/请求；② **选择准确率下降**——候选太多时模型容易选错或选到相似的工具；③ **延迟增加**。建议 5–10 个为宜，超过 15 个要用分组加载（按场景只加载相关工具）、工具向量检索、或层级化（一个总入口逐步细化）。
</details>

**Q9：MCP 和 Function Calling 是什么关系？**
<details><summary>参考答案</summary>
Function Calling 是模型接口层的能力——让模型能表达"我要调这个工具、参数是这些"。MCP 是协议层的标准——规范工具如何被标准化地发现、描述、调用和复用。MCP 底层仍然使用 Function Calling 的机制。区别在于范围：Function Calling 是单次请求内的、你手动注册的工具；MCP 是跨进程跨服务的、可动态发现的工具生态。MCP 解决了"每个框架接入每个工具都要写适配代码"的重复劳动问题。
</details>

**Q10：一个操作要删数据库，怎么防止模型误操作？**
<details><summary>参考答案</summary>
三层防护：① **白名单**——如果这个 Agent 的业务不需要删库能力，就根本不要把该工具注册进模型可见的工具清单（最有效）；② **参数校验**——检查表名、条件是否在白名单内，是否带 WHERE 条件，影响行数是否超阈值；③ **人工确认**——标记为高风险工具，执行前暂停，把"即将执行什么、影响范围多大"清楚地展示给用户，必须显式确认才执行。另外必须记录审计日志（谁、何时、调了什么、结果），便于事后追溯。**永远不要给模型无限制的破坏性能力。**
</details>

**Q11：为什么工具的结果要做长度限制？**
<details><summary>参考答案</summary>
因为工具结果会进入模型上下文，占用 token。一个搜索工具如果返回 50 条完整网页内容，可能一次性灌入 10 万 token，导致：① 成本暴涨；② 超出上下文限制直接报错；③ 长上下文"中间遗忘"，关键信息被忽略。正确做法是在工具内部就做处理：只返回 Top-3 到 Top-5、每条截断到 300–500 字、只保留与查询最相关的片段。
</details>

---

## 八、延伸阅读

| 主题 | 资源 |
|---|---|
| OpenAI Function Calling 指南 | https://platform.openai.com/docs/guides/function-calling |
| DeepSeek Function Calling | https://api-docs.deepseek.com/guides/function_calling |
| **MCP 官方站点**（必看） | https://modelcontextprotocol.io/ |
| MCP 2026-07-28 规范发布说明 | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk |
| Anthropic Tool Use 文档（描述写法范例很好） | https://docs.anthropic.com/en/docs/build-with-claude/tool-use |

---

## 九、完成标志

- [ ] 能跑通最小工具调用，并能解释"2 次 API 请求"发生在哪
- [ ] 一个 3 工具 Agent，含并行调用、错误自愈、循环上限
- [ ] 三层权限控制 + 审计日志实现
- [ ] 一份"工具描述质量对比实验"记录（烂描述 vs 四要素描述的准确率差异）
- [ ] **项目 03 的工具部分完成**
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 05，学习 Agent 架构与编排——让模型自己拆解任务、多步执行。
