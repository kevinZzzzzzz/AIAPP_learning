# 模块 09：评测、可观测性与成本控制

> 对应周次：**W12（前半）**｜预计耗时：**10–12 小时**
> 前置要求：完成模块 07、08，已有可运行的 Agent 系统
>
> **本模块是"能做出 Demo"和"能负责线上系统"的分界线。** 面试时，能说出指标体系的人，和只会说"我做了个 Agent"的人，是两个量级。

---

## 一、这个模块要解决什么问题

**一句话**：用数据证明你的 AI 系统做得好、花得少、出了问题能定位。

学完这一模块，你应该能回答：

- 怎么证明你改了 Prompt 之后效果真的变好了？
- 用户反馈"回答不对"，你怎么定位是哪一环出问题？
- 一次请求花多少钱？一天花多少？钱花在哪了？
- 上线前怎么知道质量没有下降？
- 怎么自动发现"模型输出格式突然不对了"？

---

## 二、为什么必须做评测

### 2.1 没有评测的四个后果

| 后果 | 具体表现 |
|---|---|
| **靠感觉优化** | "我觉得这个 Prompt 好一点"——改了三周，实际效果原地打转 |
| **回归无感知** | 优化了 A 场景，悄悄搞坏了 B 场景，上线才发现 |
| **无法归因** | 用户说答错了，你不知道是检索、Prompt、工具还是模型的问题 |
| **无法证明价值** | 面试/汇报时说不出量化结果，只能"我感觉挺好的" |

### 2.2 三类评测方法

| 方法 | 做法 | 成本 | 可靠性 | 适用 |
|---|---|---|---|---|
| **规则断言** | 检查关键词、JSON 格式、长度 | 极低 | 高（对格式类） | 格式、必含内容、拒答 |
| **LLM-as-Judge** | 用模型当裁判给答案打分 | 中 | 中（需校准） | 主观质量、相关性 |
| **人工评估** | 人工标注打分 | 高 | 最高 | 关键场景、校准 Judge |

**推荐组合**：规则断言（快速、每次改动都跑）+ LLM-as-Judge（阶段性评估）+ 人工抽检（校准）。

### 2.3 LLM-as-Judge 的正确用法

**新手做法（不可靠）**：

```
请给下面这个回答打分（1-10 分）。
```

模型给分很随机，不同批次的分数不可比。

**正确做法**：

```python
JUDGE_PROMPT = """你是严格的答案质量评估员。请从三个维度评估。

【输入】
问题：{question}
参考答案要点：{reference}
模型回答：{answer}

【评估维度】
1. 准确性（0-1）：回答是否与参考答案要点一致，无事实错误
2. 完整性（0-1）：是否覆盖了参考答案中的所有要点
3. 无幻觉（0-1）：是否包含参考答案之外的编造内容

【评分标准】
- 准确性：完全一致=1.0；部分正确=0.5；明显错误=0
- 完整性：全覆盖=1.0；覆盖一半=0.5；完全遗漏=0
- 无幻觉：无编造=1.0；轻微推测=0.5；明显编造=0

【重要】如果模型回答中出现"我不知道""资料中未提及"而参考答案确实没有对应内容，
应视为正确（准确性=1.0），不要扣分。

只输出 JSON，不要解释：
{"accuracy": 0.0, "completeness": 0.0, "faithfulness": 0.0, "reason": "一句话理由"}"""

def llm_judge(question: str, answer: str, reference: str) -> dict:
    resp = client.chat.completions.create(
        model="deepseek-v4-pro",          # Judge 要用更强的模型
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question, answer=answer, reference=reference)}],
        response_format={"type": "json_object"},
        temperature=0,                     # Judge 必须低温
    )
    return json.loads(resp.choices[0].message.content)
```

**LLM-as-Judge 的四个注意事项**（面试可能问）：

| 注意点 | 说明 |
|---|---|
| **用更强的模型当裁判** | 用便宜模型评判贵模型的输出，判断力不足 |
| **温度设 0** | 保证评分可复现 |
| **给出明确评分标准** | 不能只写"打分"，要写清什么情况得几分 |
| **防位置偏见** | 对比两个答案时，交换顺序各评一次，取平均（模型有"偏好第一个"的倾向）|
| **定期人工校准** | Judge 的分数要和人工标注对齐，不然越评越偏 |

---

## 三、可观测性：出问题怎么定位

### 3.1 要追踪什么

**一次 Agent 请求的完整链路**：

```
用户请求 (trace_id)
  ├─ 检索调用 (span 1)
  │    ├─ 输入: query, top_k
  │    ├─ 输出: 5 条片段
  │    └─ 耗时: 230ms
  ├─ 模型调用 1 (span 2)  ← 决定调工具
  │    ├─ 输入: messages, tools
  │    ├─ 输出: tool_call get_weather
  │    └─ token: 1200 in / 45 out, 耗时 890ms
  ├─ 工具执行 (span 3)
  │    ├─ 输入: {"city": "北京"}
  │    ├─ 输出: {"temp": 22}
  │    └─ 耗时: 150ms
  ├─ 模型调用 2 (span 4)  ← 生成最终答案
  │    ├─ token: 1350 in / 320 out, 耗时 2100ms
  └─ 总耗时: 3.4s  总成本: ¥0.0008
```

**没有这个链路，出问题时你只能猜。** 有了它，你能立刻看出"是检索慢还是模型慢，是哪个调用 token 异常多"。

### 3.2 LangSmith 接入（最简单）

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__你的key
LANGCHAIN_PROJECT=my-agent-project
```

**配置好环境变量后，LangGraph / LangChain 的调用会自动上报**，不需要改代码。在网页上能看到每次调用的完整链路、输入输出、耗时、token。

> **LangSmith** 有免费额度，学习阶段够用。替代方案是 **LangFuse**（开源，可自部署，数据不出本机）。

### 3.3 自建追踪（轻量方案）

如果不想依赖第三方，自己记结构化日志也能解决大部分问题：

```python
# observability/tracer.py
"""轻量级链路追踪。用结构化日志实现，配合 SQLite 存储。"""
import time, uuid, json, sqlite3, logging
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("tracer")

@dataclass
class Span:
    span_id: str
    trace_id: str
    name: str
    parent_id: str | None = None
    start_time: float = 0.0
    end_time: float = 0.0
    input: Any = None
    output: Any = None
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class Tracer:
    def __init__(self, db_path: str = "traces.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY, trace_id TEXT, parent_id TEXT,
                name TEXT, start_time REAL, duration_ms REAL,
                input TEXT, output TEXT, error TEXT,
                prompt_tokens INTEGER, completion_tokens INTEGER,
                cost REAL, metadata TEXT)""")

    @contextmanager
    def span(self, name: str, trace_id: str, parent_id: str | None = None, **metadata):
        """用法：
            with tracer.span("retrieve", trace_id) as s:
                s.output = chunks
        """
        s = Span(span_id=str(uuid.uuid4())[:8], trace_id=trace_id,
                 name=name, parent_id=parent_id, start_time=time.time(),
                 metadata=metadata)
        try:
            yield s
        except Exception as e:
            s.error = str(e)[:500]
            raise
        finally:
            s.end_time = time.time()
            self._save(s)

    def _save(self, s: Span):
        def trunc(v, n=2000):
            if v is None:
                return None
            text = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
            return text[:n]
        with sqlite3.connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO spans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (s.span_id, s.trace_id, s.parent_id, s.name, s.start_time,
                       s.duration_ms, trunc(s.input), trunc(s.output), s.error,
                       s.prompt_tokens, s.completion_tokens, s.cost,
                       json.dumps(s.metadata, ensure_ascii=False, default=str)))

    def get_trace(self, trace_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM spans WHERE trace_id=? ORDER BY start_time",
                             (trace_id,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self, hours: int = 24) -> dict:
        """统计最近 N 小时的指标。这是成本看板的数据源。"""
        since = time.time() - hours * 3600
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("""SELECT
                COUNT(DISTINCT trace_id) AS requests,
                SUM(prompt_tokens) AS pt, SUM(completion_tokens) AS ct,
                SUM(cost) AS total_cost,
                AVG(duration_ms) AS avg_ms,
                SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors
                FROM spans WHERE start_time > ?""", (since,)).fetchone()
            # 分阶段耗时（找出瓶颈在哪）
            by_name = c.execute("""SELECT name, AVG(duration_ms) AS avg_ms, COUNT(*) AS cnt
                FROM spans WHERE start_time > ? GROUP BY name
                ORDER BY avg_ms DESC""", (since,)).fetchall()

        return {
            "requests": row[0] or 0,
            "prompt_tokens": row[1] or 0,
            "completion_tokens": row[2] or 0,
            "total_cost": round(row[3] or 0, 6),
            "avg_duration_ms": round(row[4] or 0, 1),
            "error_count": row[5] or 0,
            "by_stage": [{"stage": r[0], "avg_ms": round(r[1], 1), "count": r[2]}
                         for r in by_name],
        }


tracer = Tracer()


# ============ 使用 ============
if __name__ == "__main__":
    import os
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com")

    trace_id = str(uuid.uuid4())[:8]

    with tracer.span("retrieve", trace_id) as s:
        s.input = "什么是 RAG"
        time.sleep(0.2)                          # 模拟检索
        s.output = ["RAG 是检索增强生成...", "RAG 的流程是..."]

    with tracer.span("llm_call", trace_id) as s:
        s.input = [{"role": "user", "content": "什么是 RAG"}]
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "用一句话解释 RAG"}],
        )
        s.output = resp.choices[0].message.content
        s.prompt_tokens = resp.usage.prompt_tokens
        s.completion_tokens = resp.usage.completion_tokens
        s.cost = s.prompt_tokens / 1e6 * 0.14 + s.completion_tokens / 1e6 * 0.28

    print(json.dumps(tracer.stats(), ensure_ascii=False, indent=2))
    for span in tracer.get_trace(trace_id):
        print(f"{span['name']:15s} {span['duration_ms']:7.1f}ms  "
              f"tokens={span['prompt_tokens']}+{span['completion_tokens']}")
```

---

## 四、成本控制

### 4.1 成本从哪里来

**成本公式**：

```
单次成本 = Σ(每轮 prompt_tokens × 输入单价 + completion_tokens × 输出单价)
```

**Agent 场景的成本特点**：

| 特点 | 说明 |
|---|---|
| **输入 token 会累积** | 第 5 轮的输入包含前 4 轮的所有消息和工具结果，不是恒定的 |
| **轮数与成本近似平方关系** | 轮数增加，每轮输入也在增加，总成本增长快于线性 |
| **工具定义是固定开销** | 每次请求都发，工具多则固定成本高 |
| **输出比输入贵** | 通常是 2–6 倍，所以要控制模型啰嗦 |

### 4.2 十项成本优化手段

| # | 手段 | 节省幅度 | 实现难度 | 副作用 |
|---|---|---|---|---|
| 1 | **模型分级路由**——简单任务用便宜模型 | 50–80% | 中 | 需判断任务复杂度 |
| 2 | **prompt caching**——固定内容放前面 | 30–90%（输入部分） | 低 | 无 |
| 3 | **控制上下文**——按需检索历史，不全量带 | 30–60% | 中 | 可能丢信息 |
| 4 | **限制输出长度** | 20–40% | 低 | 回答可能被截断 |
| 5 | **减少工具定义**——分组加载 | 10–30% | 中 | 需路由逻辑 |
| 6 | **结果缓存**——相同问题直接返回 | 视重复率 | 低 | 数据可能过时 |
| 7 | **结果截断**——工具返回只取 Top-N | 20–50% | 低 | 可能丢信息 |
| 8 | **摘要压缩**——旧对话压成要点 | 30–50% | 中 | 摘要丢细节 |
| 9 | **批量处理**——多个独立任务合并一次请求 | 20–40% | 中 | 延迟增加 |
| 10 | **关闭思考模式**（简单任务） | 30–60% | 低 | 推理能力下降 |

**最有效的三个**：模型分级路由、prompt caching、上下文控制。

### 4.3 模型分级路由（最有效）

```python
# cost/router.py
"""模型分级路由：简单任务用便宜模型，复杂任务用贵模型。
这是最有效的成本优化手段——通常能省 50-80%。
"""
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 价格表（美元/百万 token，2026-09 DeepSeek 官方）
PRICING = {
    "deepseek-v4-flash": {"in": 0.14,  "out": 0.28},
    "deepseek-v4-pro":   {"in": 0.435, "out": 0.87},
}

COMPLEXITY_PROMPT = """判断下面这个任务的复杂度。

简单：事实问答、格式转换、分类、简单摘要、闲聊
复杂：多步推理、代码生成、需要权衡的决策分析、长文档分析

只输出一个词：simple 或 complex"""

def route_model(question: str) -> str:
    """用最便宜的模型判断复杂度（这一步本身的成本要远小于省下的钱）"""
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": f"{COMPLEXITY_PROMPT}\n\n任务：{question[:500]}"}],
        temperature=0, max_tokens=10,
    )
    verdict = resp.choices[0].message.content.strip().lower()
    return "deepseek-v4-flash" if "simple" in verdict else "deepseek-v4-pro"


def smart_call(question: str) -> dict:
    model = route_model(question)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        temperature=0.3,
    )
    u = resp.usage
    price = PRICING[model]
    cost = u.prompt_tokens / 1e6 * price["in"] + u.completion_tokens / 1e6 * price["out"]

    return {
        "answer": resp.choices[0].message.content,
        "model": model,
        "cost": round(cost, 6),
        "tokens": f"{u.prompt_tokens}+{u.completion_tokens}",
    }


if __name__ == "__main__":
    for q in ["你好", "帮我分析一下我们的技术架构是否合理，要考虑成本、扩展性和团队能力"]:
        r = smart_call(q)
        print(f"[{r['model']}] {r['tokens']} token, ${r['cost']}")
        print(r["answer"][:150], "\n")
```

> **关键点**：路由判断本身也要花钱，所以**用最便宜的模型做判断**，并且判断的 token 要少（只输出一个词）。如果省下的钱少于判断成本，就不要做路由。
>
> **更省的做法**：用规则做路由（如消息长度 < 50 字且不含复杂关键词 → 用便宜模型），零成本。

### 4.4 结果缓存

```python
# cost/cache.py
"""语义缓存：相同或相似的问题直接返回缓存结果。"""
import hashlib, json, sqlite3, time, os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ResponseCache:
    """两层缓存：
    1. 精确命中（hash 相同）—— 零成本，最快
    2. 语义命中（向量相似度高）—— 需一次 embedding 调用，但远便宜于生成
    """
    def __init__(self, db_path: str = "cache.db", similarity_threshold: float = 0.95):
        self.db_path = db_path
        self.threshold = similarity_threshold
        with sqlite3.connect(db_path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY, question TEXT, answer TEXT,
                embedding TEXT, created_at REAL, hits INTEGER DEFAULT 0)""")

    @staticmethod
    def _key(question: str, model: str, temp: float) -> str:
        return hashlib.sha256(f"{question}|{model}|{temp}".encode()).hexdigest()

    def get(self, question: str, model: str, temperature: float):
        # 第 1 层：精确命中
        key = self._key(question, model, temperature)
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM cache WHERE key=?", (key,)).fetchone()
            if row:
                c.execute("UPDATE cache SET hits=hits+1 WHERE key=?", (key,))
                return {"answer": row["answer"], "type": "exact"}

        # 第 2 层：语义命中（需要 embedding，成本极低）
        # 注意：temperature > 0 时缓存语义匹配要谨慎（同样的输入本就可能有不同答案）
        if temperature > 0.5:
            return None
        return None          # 生产实现：算 embedding 后查向量库比对

    def set(self, question: str, model: str, temperature: float, answer: str):
        key = self._key(question, model, temperature)
        with sqlite3.connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?,0)",
                      (key, question, answer, None, time.time()))

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("SELECT COUNT(*), SUM(hits) FROM cache").fetchone()
        return {"entries": row[0] or 0, "total_hits": row[1] or 0}
```

> ⚠️ **缓存的三个坑**：① **数据时效性**——商品价格变了但缓存还是旧的，要设 TTL；② **个性化**——不同用户的答案可能不同（因为有用户记忆），缓存键必须包含 user_id；③ **temperature 高时不要缓存**——同样的输入本就该有不同答案，缓存会破坏多样性。

### 4.5 成本监控看板

```python
# cost/dashboard.py
"""输出成本监控报告。可以做成定时任务每天推送。"""
from observability.tracer import tracer
from observability.tracer import Tracer
import sqlite3, time

def cost_report(usage_db: str = "agent.db", hours: int = 24) -> str:
    with sqlite3.connect(usage_db) as c:
        row = c.execute("""SELECT
            COUNT(*) AS requests,
            SUM(prompt_tokens), SUM(completion_tokens), SUM(cost)
            FROM usage_log WHERE created_at > datetime('now', ?)""",
            (f"-{hours} hours",)).fetchone()
        top_users = c.execute("""SELECT user_id, SUM(cost) AS c, COUNT(*) AS n
            FROM usage_log WHERE created_at > datetime('now', ?)
            GROUP BY user_id ORDER BY c DESC LIMIT 5""", (f"-{hours} hours",)).fetchall()

    requests, pt, ct, cost = row
    if not requests:
        return f"最近 {hours} 小时无请求"

    avg_cost = cost / requests
    return f"""📊 成本报告（最近 {hours} 小时）

请求数：      {requests}
输入 token：  {pt:,}
输出 token：  {ct:,}
总成本：      ¥{cost * 7.2:.4f}
单次均成本：  ¥{avg_cost * 7.2:.4f}
单日预估：    ¥{avg_cost * requests * (24/hours) * 7.2:.2f}

Top 5 消耗用户：
""" + "\n".join(f"  {u[0][:12]:14s} ¥{u[1]*7.2:.4f}  ({u[2]} 次)"
                for u in top_users)


if __name__ == "__main__":
    print(cost_report())
    stats = tracer.stats(hours=24)
    print(f"\n链路统计：{stats['requests']} 请求，"
          f"平均 {stats['avg_duration_ms']}ms，错误 {stats['error_count']} 次")
    print("各阶段平均耗时（找瓶颈）：")
    for s in stats["by_stage"]:
        print(f"  {s['stage']:15s} {s['avg_ms']:8.1f}ms  ({s['count']} 次)")
```

> **注意币种**：上面按 1 USD ≈ 7.2 CNY 换算，实际汇率请以你的结算为准。DeepSeek 官方价格以美元计价。

---

## 五、五个核心指标（面试必答）

**面试官问"你怎么衡量你的 Agent 做得好不好"，你要能结构化地回答这五个维度。**

| 维度 | 核心指标 | 目标方向 | 怎么测 |
|---|---|---|---|
| **体验** | 首字延迟（TTFT）、P95 总耗时 | 越低越好 | 埋点统计 |
| **质量** | 任务成功率、答案正确率、引用准确率 | 越高越好 | 评估集跑批 |
| **稳定** | 错误率、重试率、可用率 | 越低越好 | 链路追踪 |
| **成本** | 单请求 token 成本、日成本 | 可控可预测 | usage 表统计 |
| **安全** | 越权拦截率、敏感信息泄露数、注入攻击成功率 | 趋近于 0 | 安全测试集 |

**能说出这五个维度 + 每个维度的具体指标 + 怎么测，就说明你真的运营过 AI 系统。**

---

## 六、知识点清单

- [ ] 没有评测的四个后果
- [ ] 三类评测方法（规则断言 / LLM-as-Judge / 人工）的取舍
- [ ] LLM-as-Judge 的正确做法与五个注意事项
- [ ] 位置偏见（position bias）及消除方法
- [ ] 可观测性要追踪的内容：trace / span / 输入输出 / token / 耗时
- [ ] LangSmith 与 LangFuse 的接入方式
- [ ] 自建轻量追踪（结构化日志 + SQLite）
- [ ] Agent 成本的特点（输入累积、近似平方增长）
- [ ] 十项成本优化手段及副作用
- [ ] 模型分级路由的实现与成本权衡
- [ ] 缓存的三个坑（时效性 / 个性化 / temperature）
- [ ] 五个核心指标体系

---

## 七、常见坑

### 坑 1：不做评估集，靠感觉优化
**后果**：改了三周没变好，或者改好了 A 搞坏了 B。
**正确做法**：第一天就建 20–50 条测试集，每次改动都跑。

### 坑 2：用便宜模型当 Judge
**后果**：评判能力不足，分数不可信。
**正确做法**：Judge 用比被评模型更强的模型，温度设 0，评分标准写细。

### 坑 3：对比评测时不消除位置偏见
**后果**：模型倾向给"第一个"答案更高分，导致 A/B 对比结果错误。
**正确做法**：交换顺序各评一次，取平均。

### 坑 4：只看最终答案对不对
**后果**：无法归因（不知道是检索还是生成的问题）。
**正确做法**：分阶段埋点，检索和生成分开评估。

### 坑 5：不记录 token 和成本
**后果**：账单突然飙高，完全不知道钱花在哪。
**正确做法**：每次调用都记 usage，做成本看板。

### 坑 6：Agent 成本失控
**后果**：一个复杂任务跑 20 轮，单次成本是预期的 10 倍。
**正确做法**：设轮数上限 + token 预算上限 + 单请求成本告警。**成本上限要像超时一样是硬性保护。**

### 坑 7：无脑加缓存
**后果**：用户看到过时的数据（价格、库存），或者不同用户看到别人的答案。
**正确做法**：设 TTL；缓存键包含 user_id 和影响结果的参数；temperature 高时不缓存。

### 坑 8：追踪日志里存了完整 Prompt
**后果**：日志里堆积用户隐私数据，合规风险。
**正确做法**：日志脱敏（只存长度、hash、ID），或加密存储并设访问权限和保留期。

### 坑 9：只看平均值不看 P95
**后果**：平均值 1.5s 看着很好，但 P95 是 12s，5% 的用户体验极差。
**正确做法**：监控 P95 / P99，它们才是用户体验的真实反映。

### 坑 10：没有回归测试
**后果**：换了模型版本或改了 Prompt，悄悄出问题，上线才发现。
**正确做法**：把评估集跑批做成 CI 步骤，或者至少每次重要改动都跑一遍并记录分数。

---

## 八、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 给你的 Agent 建一个 20 条测试集，实现规则断言评测脚本 | ⭐⭐⭐ |
| 2 | 实现 LLM-as-Judge，并做"交换顺序"消除位置偏见的对比实验 | ⭐⭐⭐⭐ |
| 3 | 接入 LangSmith（或自建追踪），跑一次请求，看完整链路 | ⭐⭐⭐ |
| 4 | 实现成本统计脚本，输出每日/单次成本报告 | ⭐⭐⭐ |
| 5 | 实现模型分级路由，对比路由前后的成本和质量 | ⭐⭐⭐⭐ |
| 6 | 实现 prompt caching 优化（调整消息顺序），对比成本变化 | ⭐⭐⭐ |
| 7 | 实现响应缓存，测量缓存命中率和节省的成本 | ⭐⭐⭐ |
| 8 | 做一次成本优化实验，记录优化前后的成本数据 | ⭐⭐⭐⭐ |
| 9 | **【项目任务】** 输出一份完整的评测报告（质量 + 成本 + 延迟） | ⭐⭐⭐⭐⭐ |

**任务 9 是你项目 04 的核心交付物。** 一份包含质量、成本、延迟三项数据的报告，是面试中最有说服力的材料。

---

## 九、自测题

**Q1：怎么证明你改了 Prompt 之后效果变好了？**
<details><summary>参考答案</summary>
建一个 20–50 条的测试集（含边界情况和"应该拒绝"的用例），跑批计算通过率，对比改动前后的分数。使用规则断言（检查关键词、格式、是否拒答）做快速验证，用 LLM-as-Judge 评估主观质量。只有分数提升才保留新版本。同时要检查失败案例，判断失败是格式问题还是理解问题——两者的修法完全不同。关键是**有数据、可复现、可对比**。
</details>

**Q2：LLM-as-Judge 有什么风险？怎么降低？**
<details><summary>参考答案</summary>
风险有四：① **评判能力不足**——用弱模型评判强模型的输出，标准不准（解法：Judge 用更强的模型）；② **评分不稳定**——温度不为 0 导致同一样本多次评分结果不同（解法：temperature=0）；③ **位置偏见**——对比两个答案时倾向给第一个高分（解法：交换顺序各评一次取平均）；④ **标准漂移**——Judge 的评分标准和人的标准逐渐偏离（解法：定期人工校准，抽检 Judge 的评分是否合理）。另外 Judge 的成本也要算进去，不能为了省钱评估而花更多钱。
</details>

**Q3：用户反馈"回答不对"，你怎么定位问题？**
<details><summary>参考答案</summary>
先看链路追踪（trace），逐环节排查：① **检索环节**——正确文档被检索到了吗？如果没检索到，是切片/Embedding/查询改写的问题；② **上下文组装**——检索到的内容是否正确放进了 Prompt？有没有被截断？③ **模型调用**——输入 token 是否异常？是否超出上下文限制？④ **工具调用**——工具是否被正确调用？返回结果是否正确？⑤ **输出解析**——格式是否正确？引用是否有效？**没有链路追踪就只能猜，有追踪就能在 1 分钟内定位到具体环节。** 这就是可观测性的价值。
</details>

**Q4：你的 Agent 单次请求成本突然从 ¥0.01 涨到 ¥0.5，可能是什么原因？**
<details><summary>参考答案</summary>
按可能性排查：① **轮数增加**——Agent 陷入循环或任务变复杂，导致模型调用轮数增加（每轮的输入还包含之前所有内容，成本近似平方增长）；② **上下文没控制**——历史消息或工具返回结果变得很长，输入 token 暴涨；③ **工具返回太大**——某个工具返回了超长内容（如完整网页）；④ **模型切换**——代码改动导致路由到了更贵的模型（pro 比 flash 贵约 3 倍）；⑤ **思考模式被打开**——推理 token 也算输出 token，成本显著上升；⑥ **缓存失效**——之前命中 prompt cache 的固定内容变了（缓存命中价是未命中的 1/50）；⑦ **重试放大**——大量失败重试。排查方法：看 trace 的每轮 token 分布，对比历史调用。
</details>

**Q5：怎么降低 Agent 的成本？**
<details><summary>参考答案</summary>
最有效的三项：① **模型分级路由**——简单任务用便宜模型（省 50–80%，但路由判断本身也有成本，要用最便宜的模型或规则判断）；② **prompt caching**——把长而固定内容（system prompt、工具定义、few-shot 示例）放在消息前面，命中缓存后输入价可降 30–90%；③ **上下文控制**——按需检索历史而不是全量带，工具返回做截断（只取 Top-N）。其他手段：限制输出长度、减少工具定义（分组加载）、结果缓存、摘要压缩、简单任务关闭思考模式、独立任务批量合并。**注意每项都有副作用，要评估对质量的影响。**
</details>

**Q6：为什么要监控 P95 而不只看平均值？**
<details><summary>参考答案</summary>
因为平均值会掩盖长尾问题。假设 95 个请求耗时 1 秒，5 个请求耗时 20 秒，平均是 2 秒（看着还行），但 P95 是 20 秒——意味着**每 20 个用户就有 1 个要等 20 秒**，体验极差，很可能直接流失。而且长尾请求往往占用连接资源，会影响整体吞吐。所以监控要看 P50（中位数，代表典型体验）、P95（代表较差体验）、P99（极端情况），平均值只作参考。
</details>

**Q7：缓存有什么坑？**
<details><summary>参考答案</summary>
三个主要坑：① **时效性**——数据变了但缓存还是旧的（商品价格、库存、政策），必须设 TTL 或订阅数据变更事件主动失效；② **个性化**——不同用户的答案依赖各自的记忆和权限，缓存键必须包含 user_id 等影响结果的参数，否则会导致数据泄露（A 看到 B 的答案）；③ **temperature 高时不宜缓存**——高温度下同样的输入本就该有不同输出（多样性是目的），缓存会破坏这个特性。另外语义缓存的相似度阈值要谨慎，阈值太松会把不同问题当成同一个（返回错误答案）。
</details>

**Q8：五个核心指标是什么？**
<details><summary>参考答案</summary>
① **体验**：首字延迟（TTFT）、P95 总耗时；② **质量**：任务成功率、答案正确率、引用准确率；③ **稳定**：错误率、重试率、可用率；④ **成本**：单请求 token 成本、日成本总额；⑤ **安全**：越权拦截率、敏感信息泄露数、注入攻击成功率。能结构化地说出这五个维度、每维度的具体指标、以及测量方法，就能证明你真的运营过 AI 系统而不是只写过 Demo。
</details>

---

## 十、延伸阅读

| 主题 | 资源 |
|---|---|
| LangSmith 文档 | https://docs.smith.langchain.com/ |
| LangFuse（开源替代） | https://langfuse.com/docs |
| OpenTelemetry（通用可观测性标准） | https://opentelemetry.io/docs/ |
| OpenAI Evals | https://github.com/openai/evals |
| RAGAS（RAG 评估框架） | https://docs.ragas.io/ |

---

## 十一、完成标志

- [ ] 一个 20+ 条的测试集和跑批脚本
- [ ] LLM-as-Judge 实现（含位置偏见处理）
- [ ] 链路追踪（LangSmith 或自建）
- [ ] 成本统计脚本 + 看板
- [ ] 至少一项成本优化实验（有数据对比）
- [ ] **一份完整的评测报告**（质量 + 成本 + 延迟）
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 10，部署上线。
