# 模块 06：多 Agent 协作与工作流

> 对应周次：**W9**｜预计耗时：**12–15 小时**
> 前置要求：完成模块 05
>
> ⚠️ **心态提醒**：本模块是**知识面扩展**，不是能力跃升。多 Agent 在真实业务里用得很克制——**大部分场景单 Agent 就够了**。学它是为了知道"什么时候该用、什么时候是过度设计"。

---

## 一、这个模块要解决什么问题

**一句话**：知道复杂任务怎么拆给多个角色协作——但也知道**什么时候拆是错的**。

学完这一模块，你应该能回答：

- 什么时候该用多 Agent？单 Agent 不够用的信号是什么？
- Supervisor 模式是怎么运作的？
- 多 Agent 的成本代价有多大？
- 并行执行怎么实现？什么时候能并行？
- 常见的多 Agent 框架各有什么取舍？

---

## 二、核心概念

### 2.1 先泼冷水：多 Agent 的三个真实代价

**在你决定用多 Agent 之前，必须先知道要付什么。**

| 代价 | 具体表现 |
|---|---|
| **成本成倍增长** | 每个 Agent 都要带自己的 system prompt + 工具定义 + 上下文。一个 4 Agent 系统，token 消耗可能是单 Agent 的 3–5 倍。而且 Agent 间通信的内容也要计费 |
| **延迟累加** | 串行协作时延迟叠加。主管要等下属完成，下属之间可能还有依赖 |
| **调试难度爆炸** | 出问题时，你不知道是哪个 Agent 的判断错了、还是通信信息丢了、还是路由规则有问题。错误在 Agent 之间传播和放大 |

**所以决策原则是**：

> **能用上下文隔离（不同的 system prompt + 工具集）解决的，不要用多 Agent。**
> 大多数"需要多角色"的场景，其实一个 Agent 配上清晰的角色切换提示词就够了。

**"真的需要多 Agent"的四个信号**：

| 信号 | 说明 |
|---|---|
| 子任务**需要不同的工具集**且**不能混用** | 权限隔离（比如有些 Agent 不能访问财务数据） |
| 子任务需要**并行执行**且互不依赖 | 并行调研 5 个竞品 |
| 子任务**上下文差异极大** | 一个要读 10 万字合同，一个要查实时行情，混在一起上下文爆炸 |
| 需要**独立的失败隔离** | 一个子任务失败不该拖垮整体 |

**不该用多 Agent 的信号**：

- 只是"角色扮演"（"你是产品经理、你是工程师"）——用一个 Agent 切换提示词即可
- 任务可以顺序完成且上下文可以共用
- 团队没有能力监控多 Agent 系统的调试

### 2.2 四种多 Agent 架构

#### 架构 1：Supervisor（主管调度）——最常用

```
              ┌──────────────┐
              │  Supervisor  │  ← 决定下一个交给谁
              │   （主管）    │
              └──────┬───────┘
         ┌───────────┼───────────┐
         ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ 调研员    │ │ 分析师    │ │ 撰写员    │
   │ Researcher│ │ Analyst  │ │ Writer   │
   └──────────┘ └──────────┘ └──────────┘
         │           │           │
         └───────────┴───────────┘
                     ▼
               回到 Supervisor 判断是否完成
```

**机制**：主管节点读取当前状态，决定下一步交给哪个下属，或判断任务完成。下属执行完把结果交回主管。

**优点**：控制集中、流程可预测、容易调试（每步都有主管把关）。
**缺点**：主管是瓶颈（所有决策过一遍）；主管上下文会累积所有下属的输出。

**适用**：任务可分解为明确的若干环节，且需要统一调度。

#### 架构 2：网络式（Network / Peer-to-Peer）

Agent 之间可以直接互相调用，没有中心调度。

**优点**：灵活。
**缺点**：**极难调试**，容易互相调用形成死循环，成本不可控。
**建议**：学习阶段不要用。生产环境慎用。

#### 架构 3：层级式（Hierarchical）

主管下面还有主管（树形结构）。适合超大任务。

**代价**：层级越多，延迟和成本越夸张，调试越难。**几乎不该在中小项目里用。**

#### 架构 4：并行 + 汇总（Map-Reduce / Fan-out-Fan-in）

```
              ┌──────────┐
              │  Splitter │  拆分任务
              └─────┬─────┘
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │Worker 1│ │Worker 2│ │Worker 3│  并行执行（互不依赖）
   └────┬───┘ └────┬───┘ └────┬───┘
        └───────────┼───────────┘
                    ▼
              ┌──────────┐
              │ Aggregator│  汇总
              └──────────┘
```

**这是多 Agent 里收益最明显、最值得用的模式。** 因为并行真正降低了延迟，而且逻辑简单可控。

**适用**：分析 10 份文档、调研 5 个竞品、批量处理数据。

### 2.3 工作流编排 vs 多 Agent

**关键区分**：你写死的流程叫工作流，模型自己决定的叫 Agent。**两者可以混合**。

| 编排方式 | 谁决定下一步 | 可靠性 | 成本 | 适用 |
|---|---|---|---|---|
| 固定工作流 | 开发者 | 高 | 低 | 流程确定 |
| 条件工作流（模型选分支） | 模型（受限于预设分支） | 较高 | 中 | 分支有限且可枚举 |
| Supervisor Agent | 模型 | 中 | 高 | 无法枚举步骤 |

**最推荐的实践：以工作流为骨架，在需要判断的节点用模型决策。**

```python
# 推荐模式：工作流骨架 + 模型决策节点
def workflow(question: str):
    # 步骤 1：固定 —— 先分类问题类型（模型决策，但只有 3 个预设分支）
    category = classify(question)

    # 步骤 2：根据分类走不同路径（开发者写死的分支）
    if category == "factual":
        docs = retrieve(question)            # 固定：检索
        answer = generate(question, docs)    # 固定：生成
    elif category == "calculation":
        answer = calculate_flow(question)    # 固定：走计算流程
    elif category == "open_ended":
        answer = run_agent(question)         # 这里才放开给 Agent

    # 步骤 3：固定 —— 质量校验
    return qa_check(answer)
```

**为什么这样更好**：把不确定性限制在最小的范围（分类节点），其他环节保持确定性。既灵活又可控。

---

## 三、代码示例

### 3.1 Supervisor 模式（LangGraph 实现）

```python
# src/supervisor.py
"""Supervisor 多 Agent 模式。
依赖：uv add langgraph langchain-openai
"""
import os, json
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatOpenAI(model="deepseek-v4-flash",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 base_url="https://api.deepseek.com",
                 temperature=0)

# ============ State ============
class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str                      # 原始任务
    next_agent: str                # 主管决定的下一个执行者
    research_notes: str            # 调研员产出
    analysis: str                  # 分析师产出
    final_report: str              # 最终产出
    history: list[str]             # 执行历史（防止无限调度）


# ============ 主管节点 ============
SUPERVISOR_PROMPT = """你是一个任务调度主管。你的团队有：
- researcher：负责搜集资料和事实
- analyst：负责数据分析、逻辑推理
- writer：负责撰写最终报告
- FINISH：任务已完成

根据当前进展，决定下一步交给谁。

规则：
1. 需要外部资料 → researcher
2. 已有资料需要分析 → analyst
3. 分析和资料都齐了 → writer
4. writer 已产出报告 → FINISH
5. 同一个成员不要连续调度超过 2 次（避免死循环）

只输出成员名称（researcher / analyst / writer / FINISH），不要其他内容。

当前进展：
- 调研笔记：{research}
- 分析结果：{analysis}
- 报告：{report}
- 调度历史：{history}"""

def supervisor_node(state: TeamState) -> dict:
    history = state.get("history", [])

    # 硬性保护：调度次数上限（防止无限循环烧钱）
    if len(history) >= 8:
        print("[主管] 达到调度上限，强制结束")
        return {"next_agent": "FINISH", "history": history}

    prompt = SUPERVISOR_PROMPT.format(
        research=state.get("research_notes") or "（无）",
        analysis=state.get("analysis") or "（无）",
        report=state.get("final_report") or "（无）",
        history=history[-5:],
    )
    resp = llm.invoke([SystemMessage(content=prompt),
                       HumanMessage(content=f"原始任务：{state['task']}")])

    next_agent = resp.content.strip().split()[0].strip("：:.")
    if next_agent not in ("researcher", "analyst", "writer", "FINISH"):
        next_agent = "FINISH"       # 输出异常时安全退出

    print(f"[主管] 决定交给 → {next_agent}")
    return {"next_agent": next_agent, "history": history + [next_agent]}


# ============ 三个下属 Agent ============
def researcher_node(state: TeamState) -> dict:
    """调研员：只做资料搜集，不做分析。注意——它的职责边界很清晰。"""
    resp = llm.invoke([
        SystemMessage(content="""你是资料调研员。职责：搜集与任务相关的事实、数据、背景信息。

要求：
- 只陈述事实，不做推断和分析
- 输出结构化的调研笔记
- 明确标注哪些信息是不确定的"""),
        HumanMessage(content=f"任务：{state['task']}\n\n请输出调研笔记。"),
    ])
    print(f"[调研员] 完成调研（{len(resp.content)} 字）")
    return {"research_notes": resp.content}


def analyst_node(state: TeamState) -> dict:
    """分析师：基于调研笔记做分析，不引入新事实。"""
    resp = llm.invoke([
        SystemMessage(content="""你是数据分析师。职责：基于调研笔记进行分析推理。

要求：
- 只使用调研笔记中的信息，不得引入新事实
- 指出关键发现、矛盾之处、不确定项
- 给出清晰的逻辑链条"""),
        HumanMessage(content=f"""任务：{state['task']}

调研笔记：
{state.get('research_notes') or '（调研员未提供）'}

请输出分析结果。"""),
    ])
    print(f"[分析师] 完成分析")
    return {"analysis": resp.content}


def writer_node(state: TeamState) -> dict:
    """撰写员：整合成最终报告。"""
    resp = llm.invoke([
        SystemMessage(content="""你是报告撰写员。职责：把调研和分析整合成清晰可读的报告。

要求：
- 结构清晰（有标题、分段）
- 结论先行
- 只用提供的材料，不编造
- 标注不确定的信息"""),
        HumanMessage(content=f"""任务：{state['task']}

调研笔记：
{state.get('research_notes') or '（无）'}

分析结果：
{state.get('analysis') or '（无）'}

请输出最终报告。"""),
    ])
    print(f"[撰写员] 完成报告")
    return {"final_report": resp.content, "messages": [resp]}


# ============ 路由函数 ============
def route_from_supervisor(state: TeamState) -> Literal["researcher", "analyst", "writer", "__end__"]:
    nxt = state.get("next_agent", "FINISH")
    return END if nxt == "FINISH" else nxt


# ============ 组装图 ============
builder = StateGraph(TeamState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("researcher", researcher_node)
builder.add_node("analyst", analyst_node)
builder.add_node("writer", writer_node)

builder.add_edge(START, "supervisor")

# 从主管出发的条件路由
builder.add_conditional_edges("supervisor", route_from_supervisor, {
    "researcher": "researcher",
    "analyst": "analyst",
    "writer": "writer",
    END: END,
})

# 所有下属执行完都回到主管（关键：形成中心调度结构）
builder.add_edge("researcher", "supervisor")
builder.add_edge("analyst", "supervisor")
builder.add_edge("writer", "supervisor")

graph = builder.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "team-1"}}
    result = graph.invoke(
        {"task": "分析一下 2026 年 AI Agent 开发的就业前景，给出一份简报",
         "history": []},
        config=config,
    )
    print("\n" + "=" * 60)
    print("【最终报告】")
    print("=" * 60)
    print(result.get("final_report") or result["messages"][-1].content)
    print(f"\n调度历史：{result['history']}")
```

**注意这个实现的三个工程细节**：
1. **职责边界写得很明确**（调研员"不做分析"、分析师"不引入新事实"）——这是多 Agent 能工作的关键
2. **硬性调度上限**（`len(history) >= 8`）——防止主管无限调度
3. **输出异常兜底**（主管输出不合规就 `FINISH`）——防止路由到不存在的节点

### 3.2 并行 Map-Reduce（最值得用的多 Agent 模式）

```python
# src/map_reduce.py
"""并行调研多个目标，再汇总。
这是多 Agent 里收益最明显的模式：并行真正降低延迟。
"""
import os, asyncio, operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send          # 动态并行分支的关键
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatOpenAI(model="deepseek-v4-flash",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 base_url="https://api.deepseek.com",
                 temperature=0.3)


class State(TypedDict):
    competitors: list[str]                       # 要调研的竞品列表
    results: Annotated[list[str], operator.add]  # 各分支结果汇总（operator.add 是 reducer）
    summary: str


class WorkerState(TypedDict):
    competitor: str                              # 单个分支的输入


def plan_node(state: State) -> dict:
    """拆分节点：确定要调研哪些目标。"""
    print(f"[规划] 待调研：{state['competitors']}")
    return {}


def dispatch(state: State):
    """关键：用 Send 动态生成并行分支。几个目标就开几个分支。"""
    return [Send("research_one", {"competitor": c}) for c in state["competitors"]]


def research_one(state: WorkerState) -> dict:
    """单个调研分支（会并行执行多份）"""
    comp = state["competitor"]
    print(f"  [并行分支] 开始调研 {comp}")
    resp = llm.invoke([
        SystemMessage(content="你是竞品分析师。用 3 句话总结该产品的定位、核心功能、目标用户。"),
        HumanMessage(content=f"竞品：{comp}"),
    ])
    print(f"  [并行分支] 完成 {comp}")
    return {"results": [f"## {comp}\n{resp.content}"]}


def aggregate_node(state: State) -> dict:
    """汇总节点"""
    merged = "\n\n".join(state["results"])
    resp = llm.invoke([
        SystemMessage(content="你是行业分析师。把各竞品的调研结果整合成一份对比报告，用表格呈现差异。"),
        HumanMessage(content=merged),
    ])
    return {"summary": resp.content, "results": []}


builder = StateGraph(State)
builder.add_node("plan", plan_node)
builder.add_node("research_one", research_one)
builder.add_node("aggregate", aggregate_node)

builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", dispatch, ["research_one"])   # 动态并行
builder.add_edge("research_one", "aggregate")                      # 所有分支完成后汇总
builder.add_edge("aggregate", END)

graph = builder.compile()


if __name__ == "__main__":
    import time
    t0 = time.time()
    result = graph.invoke({"competitors": ["产品A", "产品B", "产品C", "产品D", "产品E"],
                           "results": []})
    print(f"\n总耗时 {time.time()-t0:.1f}s（5 个分支并行）")
    print("\n" + result["summary"])
```

**`Send` 是这里的关键**：它让分支数量在运行时动态决定（有几个竞品就开几个分支）。这是 LangGraph 表达"Map-Reduce"的机制。

### 3.3 条件路由：模型决策 + 代码分支

```python
# src/router.py
"""路由模式：先用模型分类，再按类别走不同处理链路。
这是最推荐的"可控 Agent"实践。
"""
import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-flash",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 base_url="https://api.deepseek.com", temperature=0)


class State(TypedDict):
    question: str
    category: str
    answer: str


def classify(state: State) -> dict:
    """分类节点：模型只做一件事——分类。范围极小，可靠。"""
    resp = llm.invoke([
        SystemMessage(content="""把用户问题分类。类别只能是：
- factual：需要查资料的事实性问题
- calculation：需要计算的问题
- chitchat：闲聊或简单问答
- sensitive：涉及敏感信息或越权的问题

只输出类别名称。"""),
        HumanMessage(content=state["question"]),
    ])
    cat = resp.content.strip().split()[0].strip("：:。.")
    if cat not in ("factual", "calculation", "chitchat", "sensitive"):
        cat = "chitchat"
    print(f"[分类] {cat}")
    return {"category": cat}


def handle_factual(state: State) -> dict:
    # 真实场景这里接模块 03 的 RAG
    return {"answer": f"[检索回答] 针对「{state['question']}」，根据知识库资料..."}

def handle_calculation(state: State) -> dict:
    return {"answer": f"[计算回答] 针对「{state['question']}」的计算结果..."}

def handle_chitchat(state: State) -> dict:
    resp = llm.invoke([HumanMessage(content=state["question"])])
    return {"answer": resp.content}

def handle_sensitive(state: State) -> dict:
    """敏感问题直接拒绝，不交给模型自由发挥"""
    return {"answer": "抱歉，这个问题涉及敏感内容，我无法回答。请换一个问法或联系人工客服。"}


def route(state: State) -> Literal["factual", "calculation", "chitchat", "sensitive"]:
    return state["category"]


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("factual", handle_factual)
builder.add_node("calculation", handle_calculation)
builder.add_node("chitchat", handle_chitchat)
builder.add_node("sensitive", handle_sensitive)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route,
                              ["factual", "calculation", "chitchat", "sensitive"])
for n in ("factual", "calculation", "chitchat", "sensitive"):
    builder.add_edge(n, END)

graph = builder.compile()

if __name__ == "__main__":
    for q in ["2026年AI就业前景如何", "365*24等于多少", "你好呀", "帮我查一下老板的工资"]:
        print(f"\nQ: {q}")
        print(f"A: {graph.invoke({'question': q})['answer']}")
```

**这个模式为什么重要**：它把"模型的不确定性"限制在**分类**这一个环节（只有 4 个选项），后续流程完全确定。**这比让模型自由发挥要可靠得多，也比纯工作流灵活。**

**面试时这是很好的答案**："我不会让 Agent 完全自主，我会用路由器把请求分发到确定的处理链路，只在需要判断的地方用模型。"

---

## 四、框架选型

| 框架 | 定位 | 优点 | 缺点 | 建议 |
|---|---|---|---|---|
| **LangGraph** | 图编排，状态机 | 可控、可持久化、人在环完善、生产验证多 | 学习曲线陡 | **主学这个** ✅ |
| CrewAI | 角色化多 Agent | API 直观、上手快（role/goal/backstory 声明式） | 精细控制弱，1.x 有 API 变化 | 想快速做角色协作 demo 时用 |
| LlamaIndex Workflows | 事件驱动工作流 | RAG 生态强 | 多 Agent 能力一般 | RAG 重的工作流可用 |
| AutoGen | 会话式多 Agent | 微软背书，对话式协作 | **0.7.x 已进维护模式**，新项目应转向 Microsoft Agent Framework | 学习阶段可用 0.7.x 做原型 |

> ⚠️ **版本提醒**：
> - LangGraph 1.0 是生产标准，0.4 维护至 2026-12-31
> - CrewAI `>=1.0` 与旧版教程 API 有差异（2025 年 10 月前的教程可能不适用）
> - AutoGen 0.7.x 已进维护模式，新生产系统建议用 Microsoft Agent Framework 1.0（2026-04 GA）

**选型建议**：**深入一个就够了。** 本包选 LangGraph。其他框架知道定位和取舍即可，面试问到能说清"为什么选 LangGraph"（可控性、持久化、人在环、生态成熟）就够。

---

## 五、知识点清单

- [ ] 多 Agent 的三个真实代价（成本/延迟/调试）
- [ ] "真的需要多 Agent"的四个信号
- [ ] 角色扮演 ≠ 多 Agent（能用提示词切换解决的不要拆）
- [ ] 四种架构：Supervisor / Network / Hierarchical / Map-Reduce
- [ ] Supervisor 模式的机制、优缺点
- [ ] Map-Reduce 为什么是收益最明显的模式
- [ ] 工作流 vs 多 Agent 的混合实践（骨架 + 决策节点）
- [ ] 职责边界清晰化是多 Agent 能工作的前提
- [ ] 调度上限、输出异常兜底等工程保护
- [ ] `Send` 实现动态并行分支
- [ ] 路由模式：把不确定性限制在分类环节
- [ ] 主流框架选型对比

---

## 六、常见坑

### 坑 1：用多 Agent 做"角色扮演"
**后果**：成本翻倍、延迟增加，效果和单 Agent 换提示词没区别。
**正确做法**：先试单 Agent + 角色切换提示词。只在需要工具隔离、并行、独立上下文时才拆。

### 坑 2：没有调度上限
**后果**：主管反复调度同一个 Agent，或 Agent 之间互相调用形成环，token 疯狂消耗。
**正确做法**：设调度次数上限 + 记录调度历史（同一成员连续调度不超过 2 次）。

### 坑 3：职责边界模糊
**后果**：调研员开始做分析，分析师开始编造事实，输出互相矛盾。
**正确做法**：每个 Agent 的 system prompt 里明确写"你只做什么、不做什么"。

### 坑 4：主管上下文无限累积
**后果**：主管要读所有下属的完整输出，上下文迅速爆炸。
**正确做法**：下属之间传递**摘要**而不是全文；主管只读关键结构字段（如上面的 State 用独立字段而非堆在 messages 里）。

### 坑 5：该并行的做成串行
**后果**：10 份文档串行分析，延迟是并行的 10 倍。
**正确做法**：识别无依赖的子任务，用 `Send` 或 `asyncio.gather` 并行。

### 坑 6：并行分支有依赖还强行并行
**后果**：分支间需要共享中间结果，并发执行导致数据不一致。
**正确做法**：明确依赖关系。有依赖的必须串行，或先把依赖项作为输入传下去。

### 坑 7：为了技术炫技上多 Agent
**后果**：系统不稳定、成本高、维护困难，最后被业务方砍掉。
**正确做法**：**从最简单的方案开始。** 单 Agent → 工作流 + 单 Agent → 多 Agent。每步都要有数据证明"必须升级"。

### 坑 8：不做失败隔离
**后果**：一个并行分支报错，整个图执行失败。
**正确做法**：分支节点内部做 try/except，失败时返回降级结果（如"该目标调研失败"），不中断整体。

---

## 七、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 实现 Supervisor 三 Agent 系统（调研/分析/撰写） | ⭐⭐⭐⭐ |
| 2 | 给 Supervisor 加调度上限和循环检测，构造一个死循环场景验证保护生效 | ⭐⭐⭐ |
| 3 | 实现 Map-Reduce：并行调研 5 个目标，测量并行 vs 串行的延迟差异 | ⭐⭐⭐⭐ |
| 4 | 实现路由模式（分类 → 四路分发），测试 30 条问题的分类准确率 | ⭐⭐⭐ |
| 5 | **对比实验（核心）**：同一个任务分别用 ① 单 Agent ② 工作流+单 Agent ③ 多 Agent 实现，对比成本、延迟、质量、可调试性，写一份结论报告 | ⭐⭐⭐⭐⭐ |
| 6 | 让一个 Agent 故意抛出异常，验证失败隔离机制（其他分支不受影响） | ⭐⭐⭐ |

**任务 5 是本模块的真正价值所在。** 做完这个实验，你会有数据支撑"什么时候用多 Agent"的判断——这在面试中比"我会用 CrewAI"有价值得多。

---

## 八、自测题

**Q1：什么时候该用多 Agent？**
<details><summary>参考答案</summary>
四个信号：① 子任务需要**不同的工具集且不能混用**（权限隔离）；② 子任务需要**并行执行**且互不依赖（并行降延迟）；③ 子任务**上下文差异极大**（混在一起会爆炸）；④ 需要**独立的失败隔离**。如果没有这些信号，用单 Agent + 角色切换提示词就够了。核心原则：**从最简单的方案开始，用数据证明必须升级。**
</details>

**Q2：为什么说"角色扮演"不等于多 Agent？**
<details><summary>参考答案</summary>
因为多 Agent 的本质是**上下文和工具的隔离**，不是"换个身份说话"。如果你只是让一个模型"先是产品经理、再是工程师"，那全程是同一个上下文、同一套工具，本质还是单次调用——用提示词切换角色即可，不需要拆成多个 Agent（拆了反而增加成本和延迟，还让上下文传递变复杂）。真正的多 Agent 意味着：每个 Agent 有自己的 system prompt、工具集、独立的上下文窗口，彼此之间通过明确的消息/状态传递协作。
</details>

**Q3：Supervisor 模式的优缺点？**
<details><summary>参考答案</summary>
优点：控制集中（每个决策都过主管，流程可预测）、容易调试（每步有明确的责任人）、容易加保护（在主管处统一做调度上限和异常兜底）。缺点：① 主管是瓶颈，所有决策串行过一遍；② 主管的上下文会累积所有下属的输出，容易膨胀；③ 多一次模型调用（主管的决策）增加成本和延迟。适用：任务可分解为明确环节且需要统一调度的场景。
</details>

**Q4：多 Agent 的成本为什么是单 Agent 的好几倍？**
<details><summary>参考答案</summary>
三个原因：① 每个 Agent 都要带自己的 system prompt（角色定义通常较长）+ 工具定义，这部分是重复的固定开销；② Agent 之间的通信内容（传摘要、传结果）也要计费；③ Supervisor 的决策调用是一次额外的模型调用，且主管上下文累积所有下属输出。实测中 4 Agent 系统的 token 消耗常是单 Agent 的 3–5 倍。所以多 Agent 必须有明确的收益（并行降延迟、权限隔离）才值得。
</details>

**Q5：Map-Reduce 模式为什么是收益最明显的？**
<details><summary>参考答案</summary>
因为它真正降低了**延迟**：无依赖的 N 个子任务并行执行，总耗时接近单个任务而非 N 倍。同时逻辑简单可控（拆分 → 并行 → 汇总，没有复杂的路由决策），调试难度低。其他多 Agent 模式（如 Supervisor、Network）主要是增加灵活性，但引入了额外的模型调用和通信开销，而并行是实打实的性能收益。适用场景：批量分析文档、调研多个竞品、并行数据处理。
</details>

**Q6：`Send` 在 LangGraph 里是干什么的？**
<details><summary>参考答案</summary>
`Send` 用于实现**动态并行分支**。普通条件边的分支数量在编译时确定（写死几条），而 `Send` 可以在运行时根据 state 内容动态生成任意数量的分支——比如要调研 5 个竞品就生成 5 个分支，10 个就生成 10 个。它是 LangGraph 表达 Map-Reduce 模式的机制。配合 `Annotated[list, operator.add]` 这类 reducer，各分支的结果会自动汇总。
</details>

**Q7：多 Agent 系统最难的问题是什么？**
<details><summary>参考答案</summary>
**调试**。当输出不对时，你需要定位：是哪个 Agent 判断错了？是 Agent 间传递信息时丢了关键内容？还是路由规则有问题？错误在多 Agent 之间会传播和放大——上游一个小的判断偏差，到下游可能变成完全无关的输出。所以工程实践上要做：① 完整记录每个 Agent 的输入输出（可观测性）；② 职责边界写清晰（减少相互推诿）；③ 加调度上限和循环检测；④ 用持久化 checkpointer，支持"回到某一步重跑"。
</details>

**Q8：如果业务方说"要一个智能客服团队"，你会怎么做？**
<details><summary>参考答案</summary>
不会直接上多 Agent。先问清楚：① 有多少类问题？② 各类问题需要的工具是否重叠？③ 有没有需要并行的场景？大概率结论是：用一个 Agent + 问题分类路由 + 分场景的工具集（按意图只加载相关工具）就够了，成本低、可控、好调试。只有在明确需要权限隔离（比如财务 Agent 不能看用户隐私数据）或并行处理场景时，才拆成多个 Agent。这个回答的关键是展示**不会为了技术炫技而过度设计**。
</details>

---

## 九、延伸阅读

| 主题 | 资源 |
|---|---|
| LangGraph 多 Agent 文档 | https://langchain-ai.github.io/langgraph/concepts/multi_agent/ |
| LangGraph `Send` API | https://langchain-ai.github.io/langgraph/concepts/low_level/#send |
| CrewAI 文档 | https://docs.crewai.com/ |
| Anthropic: Building Effective Agents（**强烈推荐**） | https://www.anthropic.com/engineering/building-effective-agents |
| Microsoft Agent Framework | 搜 "Microsoft Agent Framework" |

---

## 十、完成标志

- [ ] 一个 Supervisor 三 Agent 系统，含调度上限保护
- [ ] 一个 Map-Reduce 并行实现，有延迟对比数据
- [ ] 一个路由模式实现，有分类准确率数据
- [ ] **一份"单 Agent vs 工作流 vs 多 Agent"对比报告**（核心产出）
- [ ] **项目 03 完成**
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 07，学习后端工程化——把 Demo 变成扛得住的服务。
