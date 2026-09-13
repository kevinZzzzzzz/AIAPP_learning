# 模块 03：RAG 与向量检索

> 对应周次：**W3–W5**（跨 3 周，是全程最重要的模块之一）｜预计耗时：**35–45 小时**
> 前置要求：完成模块 01、02
>
> 本模块内容较多，按三部分学习：
> - **Part A（W3）**：向量与 Embedding 基础
> - **Part B（W4）**：RAG 完整链路
> - **Part C（W5）**：进阶优化与评估

---

## 一、这个模块要解决什么问题

**一句话**：让模型能够回答**它训练时没见过的、你私有的**知识——公司文档、产品手册、你的笔记。

学完这一模块，你应该能回答：

- 为什么不能把整本书塞进 Prompt 里？（除了贵）
- 文本怎么变成向量？为什么"意思相近"的文本向量也相近？
- 检索不准，是检索的问题还是生成的问题？怎么定位？
- 用户问"上个月花了多少"这种模糊问题，怎么检索？
- 怎么证明你的 RAG 系统比昨天更好了？

---

## 二、为什么需要 RAG

### 2.1 模型的三个知识盲区

| 盲区 | 说明 | 例子 |
|---|---|---|
| **时效性** | 训练数据有截止日期 | 问"我们公司上周发布的政策" |
| **私有性** | 训练数据里没有你的内部资料 | 问"我们的 API 限流规则是什么" |
| **准确性** | 模型记忆模糊，容易编造细节 | 问"合同第 3 条写了什么" |

### 2.2 三种解决思路及取舍

| 方案 | 做法 | 优点 | 缺点 | 适用 |
|---|---|---|---|---|
| **Prompt 塞全文** | 把资料全放 Prompt 里 | 最简单，无检索误差 | 贵、有长度上限、长上下文会"中间遗忘" | 资料很小（<10 页）且固定 |
| **RAG** | 检索相关内容再放进 Prompt | 成本可控、可更新、可溯源 | 检索可能不准 | **绝大多数场景** ✅ |
| **微调（Fine-tuning）** | 用你的数据继续训练模型 | 能学到风格/格式 | 贵、更新慢、需大量数据、仍会幻觉 | 需要固定输出风格/专业术语 |

**结论**：**90% 的场景用 RAG。** 微调解决的是"怎么说"（风格、格式），RAG 解决的是"说什么"（知识、事实）。这两个问题不一样，别混淆。

> **重要认知**：RAG **不能消除幻觉**，它只是把"凭空编造"变成"基于材料编造"。如果检索到的是错的内容，模型会自信地基于错内容回答。所以 RAG 系统里，**检索质量决定上限**。

---

## Part A（W3）：向量与 Embedding 基础

## 三、Embedding：把文本变成向量

### 3.1 核心概念

**一句话**：Embedding 把一段文本映射成一串数字（向量）。**语义相近的文本，映射后的向量在空间里也相近。**

```
"如何退款"    → [0.12, -0.45, 0.78, ..., 0.33]   （1024 个数字）
"怎么申请退货" → [0.11, -0.43, 0.75, ..., 0.31]   ← 很接近
"今天天气不错" → [-0.67, 0.22, -0.11, ..., 0.89]  ← 差很远
```

**关键点**：
- 向量维度通常是 512 / 768 / 1024 / 1536 / 2048，维度越高表达力越强但存储和计算成本越高
- 它是**语义**编码，不是关键词匹配。"退货"和"退款"字面不同，但向量很近
- 向量一旦生成，就是**固定的**，不会因为你换了 Prompt 而变

**为什么这很重要**：因为它是"用关键词搜不到但意思相关"的问题的解药。用户问"东西不想要了怎么办"，你的文档标题是"退款申请流程"——关键词搜不到，但向量能匹配上。

### 3.2 相似度计算

三种常用度量：

| 度量 | 公式直觉 | 特点 |
|---|---|---|
| **余弦相似度** | 看两个向量的**夹角** | **最常用**。范围 -1~1，只看方向不看长度 |
| 欧氏距离 | 看两个点的**直线距离** | 受向量长度影响 |
| 点积 | 长度 × 夹角 | 归一化后等价于余弦相似度 |

**为什么余弦相似度最常用**：因为它只关心方向（语义），不受文本长度影响。长文档和短句子的向量长度差异很大，但方向能反映出语义相似性。

**归一化（Normalization）**：把向量长度缩放到 1。归一化后，余弦相似度 = 点积，计算更快，且很多向量库默认要求归一化。

```python
import numpy as np

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """手写余弦相似度。面试可能会让你手写，务必理解。"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def normalize(v: np.ndarray) -> np.ndarray:
    """归一化：让向量长度为 1"""
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v
```

### 3.3 Embedding 模型选型

| 模型 | 提供方 | 维度 | 价格（每百万 token） | 备注 |
|---|---|---|---|---|
| `text-embedding-v4` | 阿里云百炼 | 64–2048 可选（默认 1024） | ¥0.5 | 中文强，新用户 90 天内 100 万 token 免费 👍 |
| `text-embedding-3-small` | OpenAI | 1536 | 约 $0.02 | 便宜够用 |
| `text-embedding-3-large` | OpenAI | 3072 | 约 $0.13 | 效果最好 |
| `bge-m3` / `bge-large-zh` | 开源（BAAI） | 1024 | 免费（自部署） | 中文优秀，可本地跑 |

**选型建议**：
- **学习阶段**：用百炼 `text-embedding-v4`（中文好、有免费额度）
- **生产环境**：先用云端 API 快速验证，量大或数据敏感再考虑自部署开源模型
- ⚠️ **关键约束**：**入库和查询必须用同一个 Embedding 模型**。换了模型，所有已有向量都要重新生成，否则相似度计算毫无意义

### 3.4 文本切片（Chunking）：最影响效果的一步

**为什么必须切片**：
- 模型上下文有限，不能整本书塞进去
- 一段太长的文本，向量会"语义模糊"（把多个主题平均成一个点，谁都不像）
- 检索需要精确到"段落级"，才能给出精准答案

**切片策略对比**：

| 策略 | 做法 | 优点 | 缺点 | 适用 |
|---|---|---|---|---|
| **固定长度** | 每 N 个字符切一刀 | 简单、可控 | 可能从句子中间切断 | 快速原型 |
| **固定长度 + 重叠** | 每 N 字符切，相邻块重叠 M 字符 | 缓解切断问题 | 存储冗余 | **默认推荐** |
| **按结构切** | 按 Markdown 标题 / 段落 / 代码块边界切 | 语义完整 | 块大小不均 | **结构化文档首选** |
| **语义切片** | 用模型判断语义边界 | 效果最好 | 慢、贵 | 高质量要求场景 |
| **父子切片** | 小块用于检索，大块（父块）喂给模型 | 检索准 + 上下文完整 | 实现复杂 | **进阶推荐方案** |

**参数经验值**（不是真理，要按你的数据实测）：

| 参数 | 建议起点 | 说明 |
|---|---|---|
| chunk_size | 中文 300–800 字 / 英文 500–1000 token | 太小语义不全，太大噪声多 |
| chunk_overlap | chunk_size 的 10%–20% | 缓解边界信息丢失 |

**按结构切片的实现（推荐）**：

```python
# src/chunker.py
import re
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    metadata: dict          # 保留来源、标题等，用于引用溯源

def chunk_by_markdown(text: str, source: str,
                      max_size: int = 800, overlap: int = 100) -> list[Chunk]:
    """按 Markdown 标题切分，超长的块再按长度二次切分。
    这是处理技术文档最实用的策略。
    """
    chunks = []
    # 按二级/三级标题切
    sections = re.split(r'\n(?=#{1,3} )', text)

    for sec in sections:
        if not sec.strip():
            continue
        # 提取标题作为 metadata，便于展示引用时显示"来自哪一节"
        title_match = re.match(r'^(#{1,3})\s+(.+)$', sec, re.MULTILINE)
        title = title_match.group(2).strip() if title_match else ""

        # 块太长，按长度二次切（带重叠）
        if len(sec) > max_size:
            for i in range(0, len(sec), max_size - overlap):
                piece = sec[i:i + max_size]
                if len(piece) > 50:      # 太短的碎片丢掉
                    chunks.append(Chunk(piece, {"source": source, "title": title}))
        else:
            if len(sec) > 50:
                chunks.append(Chunk(sec, {"source": source, "title": title}))

    return chunks
```

### 3.5 向量数据库

**是什么**：专门存向量、支持"找最相似的 K 个"这种查询的数据库。

**为什么普通数据库不行**：如果用普通数据库，要判断"这条数据的向量和查询向量的相似度"，得把全表算一遍（暴力搜索）。向量库用 **ANN（近似最近邻）** 算法，牺牲一点点精度换取巨大的速度提升。

**常见选择**：

| 数据库 | 类型 | 优点 | 缺点 | 适用 |
|---|---|---|---|---|
| **Chroma** | 嵌入式 / 独立服务 | 零配置，几行代码跑起来 | 大规模性能一般 | **学习、原型** ✅ |
| **pgvector** | PostgreSQL 扩展 | 和业务数据同一套库，事务一致 | 需要自己调索引参数 | **生产环境** ✅ |
| **Milvus** | 独立服务 | 大规模、高性能 | 部署运维复杂 | 亿级向量 |
| Qdrant / Weaviate | 独立服务 | 功能丰富 | 多一套系统要维护 | 中大型 |

**建议**：学习和项目用 **Chroma**，第 10 周做生产级项目时用 **pgvector**（复用你已经有的 Postgres）。

**核心 API 只有四个**：

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="my_docs",
    metadata={"hnsw:space": "cosine"},      # 用余弦距离
)

# 1. 增
collection.add(
    ids=["d1", "d2"],
    documents=["退款流程是...", "配送范围是..."],
    metadatas=[{"source": "faq.md"}, {"source": "faq.md"}],
)

# 2. 查（最核心）
results = collection.query(
    query_texts=["东西不想要了怎么办"],       # 会自动用同一个 embed 模型转向量
    n_results=3,
)
print(results["documents"][0])
print(results["distances"][0])              # 距离越小越相似
print(results["metadatas"][0])              # 用于引用溯源

# 3. 删
collection.delete(ids=["d1"])

# 4. 改（一般是先删再增）
```

---

## Part B（W4）：RAG 完整链路

## 四、RAG 的完整流程

### 4.1 两张流程图（务必背下来）

**索引阶段（离线，做一次）**：

```
原始文档 (PDF/MD/HTML)
    ↓ 解析（提取文本）
    ↓ 清洗（去页眉页脚、乱码、重复）
    ↓ 切片（Chunking）
    ↓ Embedding（转向量）
    ↓ 存入向量库（向量 + 原文 + metadata）
```

**查询阶段（在线，每次提问）**：

```
用户问题
    ↓ 查询改写（可选，把模糊问题变清晰）
    ↓ Embedding（转向量，必须和入库用同一个模型）
    ↓ 向量检索（召回 Top-K 候选）
    ↓ 重排 Rerank（可选，把最相关的排前面）
    ↓ 组装 Prompt（问题 + 检索到的上下文 + 约束）
    ↓ 模型生成
    ↓ 引用对齐 + 事实核查
    ↓ 返回（答案 + 引用来源）
```

**面试必答**：这两张图要能默画出来，并讲清每一步的作用和常见问题。

### 4.2 索引阶段的关键点

| 步骤 | 要点 | 常见问题 |
|---|---|---|
| 解析 | PDF 用 `pypdf`/`unstructured`；HTML 用 `trafilatura` | PDF 表格解析乱、扫描件需 OCR |
| 清洗 | 去页眉页脚、修断行、去重复 | 不清洗会引入大量噪声 |
| 切片 | 见 3.4 节 | 切太碎 or 太大 |
| Embedding | **批量调用**（一次传多条，省时间省钱） | 逐条调用慢十倍 |
| 存储 | 同时存向量、原文、metadata | 只存向量会导致无法展示引用 |

**metadata 为什么关键**：它决定了你能不能做**引用溯源**（"这句话来自哪份文档的第几页"）。没有引用，用户无法核实，RAG 的可信度就不成立。

### 4.3 查询阶段的关键点

**查询改写（Query Rewrite）**

用户的问题往往不适合直接检索：

| 问题类型 | 例子 | 改写后 |
|---|---|---|
| 指代不明 | "它多少钱？"（前文在说 A 产品） | "A 产品多少钱" |
| 太口语 | "那个啥 就是退钱的事" | "退款流程" |
| 太宽泛 | "介绍一下" | 需要先澄清具体想了解什么 |
| 多跳问题 | "比去年增长多少？" | 拆成"去年数据"→"今年数据"两跳 |

```python
# src/query_rewrite.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

REWRITE_PROMPT = """你是检索查询优化器。把用户问题改写成适合向量检索的形式。

规则：
1. 补全指代（"它""这个"替换成具体名词）
2. 去掉口语化表达，保留核心语义
3. 不要回答问题，只输出改写后的查询
4. 如果有多个子问题，输出多行，每行一个查询

对话历史：
{history}

用户问题：{question}

只输出改写后的查询，不要解释。"""

def rewrite_query(question: str, history: str = "") -> list[str]:
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user",
                   "content": REWRITE_PROMPT.format(history=history or "（无）", question=question)}],
        temperature=0,
    )
    # 可能输出多行（多查询）
    return [line.strip() for line in resp.choices[0].message.content.strip().split("\n") if line.strip()]
```

**注意代价**：改写多了一次模型调用，增加延迟和成本。**简单问答可以跳过，多轮对话和复杂问题才值得做。**

**组装 Prompt 的要点**

```python
# src/prompt_builder.py

RAG_PROMPT = """你是严谨的文档问答助手。

【规则】
1. 只依据 <context> 中的资料回答，不得使用资料外的知识
2. 资料中没有的信息，明确回答"文档中未提及"，绝不推测
3. 每个关键结论后标注来源编号，格式 [1] [2]
4. 如果资料之间互相矛盾，指出矛盾并说明各自出处

<context>
{context}
</context>

用户问题：{question}

请回答，并在关键信息后标注来源编号："""

def build_context(chunks: list[dict]) -> str:
    """把检索结果组装成带编号的上下文。编号用于后面的引用对齐。"""
    parts = []
    for i, c in enumerate(chunks, 1):
        src = c["metadata"].get("source", "未知")
        title = c["metadata"].get("title", "")
        parts.append(f"[{i}] 来源：{src} {title}\n{c['text']}")
    return "\n\n---\n\n".join(parts)
```

> **关键设计**：给每段上下文编号，并**要求模型引用编号**。这样前端才能把 `[1]` 渲染成可点击的原文出处。这是"可解释性"的落地方式，也是你前端能力可以发挥的地方。

### 4.4 "不知道就说不知道"怎么实现

RAG 系统最容易被忽略但极重要的能力。三种做法：

| 做法 | 实现 | 效果 |
|---|---|---|
| 提示词给逃逸出口 | 明确写"资料中没有就说未提及" | ⭐⭐⭐ 基础必备 |
| **相似度阈值过滤** | 检索结果距离超过阈值就不喂给模型，直接返回"未找到相关资料" | ⭐⭐⭐⭐ 更可靠 |
| 二次校验 | 让模型先判断检索内容和问题是否相关 | ⭐⭐⭐ 多一次调用 |

```python
# 相似度阈值过滤（推荐）
def retrieve_with_threshold(collection, query: str,
                            n_results: int = 5, max_distance: float = 0.5):
    """距离超过阈值的结果直接丢弃。宁可说不知道，也不要基于无关内容编造。"""
    results = collection.query(query_texts=[query], n_results=n_results)
    docs = results["documents"][0]
    distances = results["distances"][0]
    metas = results["metadatas"][0]

    kept = [{"text": d, "metadata": m, "distance": dist}
            for d, m, dist in zip(docs, distances, metas) if dist <= max_distance]

    if not kept:
        return []          # 调用方据此返回"未找到相关资料"
    return kept
```

> **阈值怎么定**：不能拍脑袋。跑一批测试问题，观察"相关问题"和"无关问题"的距离分布，找分界点。**这是需要实测调优的参数。**

### 4.5 引用溯源

**为什么要做**：RAG 的最大价值不是"回答更像样"，而是**答案可核实**。用户能点开看原文，才敢信任。

```python
# src/citation.py
import re

def extract_citations(answer: str) -> list[int]:
    """从答案里提取引用编号，如 [1] [2]"""
    return sorted(set(int(n) for n in re.findall(r'\[(\d+)\]', answer)))

def verify_citations(answer: str, chunks: list[dict]) -> dict:
    """校验引用是否有效，并构造前端可用的引用卡片。"""
    cited = extract_citations(answer)
    valid, invalid = [], []

    for idx in cited:
        if 1 <= idx <= len(chunks):
            c = chunks[idx - 1]
            valid.append({
                "index": idx,
                "source": c["metadata"].get("source"),
                "title":  c["metadata"].get("title"),
                "snippet": c["text"][:150] + "...",     # 给前端展示摘要
            })
        else:
            invalid.append(idx)      # 模型编造了不存在的引用编号！必须拦截

    return {"valid": valid, "invalid": invalid}
```

**⚠️ 这个校验非常重要**：模型会**编造引用编号**（引用 [5] 但只给了 3 段资料）。不做校验，前端就会出现"点击引用无反应"的 bug，甚至显示错误的原文。**任何声称有引用的系统，都必须在代码里校验引用有效性——不能信任模型自己标的引用。**

---

## Part C（W5）：进阶优化与评估

## 五、混合检索：纯向量不够用

### 5.1 纯向量检索的三个短板

| 短板 | 例子 | 后果 |
|---|---|---|
| **专有名词/编号** | 搜 "ERR-4021"、"型号 X200" | 向量模型没见过这个词，检索不到 |
| **精确匹配** | 搜 "第 3.2.1 条" | 语义相近的其他条款会被误召回 |
| **短查询** | 搜 "发票" | 信息太少，向量表达不明确 |

**根本原因**：向量检索找的是"语义相似"，不是"字面匹配"。而有些查询**就是需要字面匹配**。

### 5.2 混合检索（Hybrid Search）

**做法**：向量检索 + 关键词检索（BM25），两路并行，结果融合。

```
                         ┌─ 向量检索（语义）──→ Top 20
用户问题 ──┬─────────────┤
           │             └─ BM25 检索（关键词）→ Top 20
           └──→ 融合排序（RRF）──→ Top 5 ──→ 重排 ──→ 喂给模型
```

**融合算法 RRF（Reciprocal Rank Fusion）**：不比较分数（两路分数不可比），只看排名。

```
RRF得分(d) = Σ  1 / (k + rank_i(d))
```
其中 k 通常取 60。一个文档在两路里排名都靠前，得分就高。

```python
# src/hybrid.py
from rank_bm25 import BM25Okapi
import jieba

class HybridRetriever:
    """混合检索：向量 + BM25，用 RRF 融合。"""

    def __init__(self, collection, documents: list[str], metadatas: list[dict]):
        self.collection = collection
        self.documents = documents
        self.metadatas = metadatas
        # 中文需要分词
        self.tokenized = [list(jieba.cut(d)) for d in documents]
        self.bm25 = BM25Okapi(self.tokenized)

    def vector_search(self, query: str, top_k: int = 20) -> list[int]:
        """返回文档下标列表，按相似度排序"""
        res = self.collection.query(query_texts=[query], n_results=top_k)
        return [self.documents.index(d) for d in res["documents"][0]]

    def bm25_search(self, query: str, top_k: int = 20) -> list[int]:
        scores = self.bm25.get_scores(list(jieba.cut(query)))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        return ranked[:top_k]

    def rrf_fuse(self, rankings: list[list[int]], k: int = 60) -> list[int]:
        """RRF 融合。rankings 是多个排名列表。"""
        scores = {}
        for ranking in rankings:
            for rank, doc_idx in enumerate(ranking, start=1):
                scores[doc_idx] = scores.get(doc_idx, 0) + 1 / (k + rank)
        return sorted(scores, key=lambda i: -scores[i])

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        fused = self.rrf_fuse([self.vector_search(query), self.bm25_search(query)])
        return [{"text": self.documents[i], "metadata": self.metadatas[i]}
                for i in fused[:top_k]]
```

**效果**：混合检索通常能把召回率提升 10–25 个百分点。**代价**：多维护一套 BM25 索引，实现复杂度上升。

### 5.3 重排（Rerank）

**为什么需要**：第一步检索（召回）速度优先，用的是"粗略"的相似度计算。要精确排序，需要更重的模型。

| 阶段 | 目标 | 手段 | 数量级 |
|---|---|---|---|
| 召回（Retrieval） | 别漏掉（高召回率） | 向量 / BM25，快速 | 从 10 万 → 50 |
| 重排（Rerank） | 把最相关的排前面（高精度） | Cross-Encoder 模型，慢但准 | 从 50 → 5 |

**关键区别**：
- Embedding 是 Bi-Encoder：问题和文档**分别**编码，然后比向量距离。快，但精度有限
- Rerank 是 Cross-Encoder：把"问题 + 文档"**一起**送进模型打分。慢，但精度高得多

**所以流程是**：先用向量快速召回一堆（宁滥勿缺），再用 Rerank 精选。

```python
# 阿里云百炼的 gte-rerank / qwen3-rerank
import dashscope

def rerank(query: str, documents: list[str], top_n: int = 5) -> list[dict]:
    resp = dashscope.TextReRank.call(
        model="qwen3-rerank",
        query=query,
        documents=documents,
        top_n=top_n,
    )
    return [{"index": r.index, "score": r.relevance_score} for r in resp.output.results]
```

**代价评估**：

| 代价 | 量级 |
|---|---|
| 延迟 | 增加 100–500ms |
| 成本 | 重排模型按 token 计费，通常比 Embedding 贵 |
| 收益 | 检索精度显著提升（尤其 Top-3 准确率）|

**什么时候该上 Rerank**：① 检索结果里经常出现"相关但不该排第一"的情况；② 对答案准确率要求高；③ 能接受额外延迟。**简单 FAQ 场景可以不上。**

### 5.4 高级策略：父子切片与上下文扩展

**问题**：小块检索准，但语义不完整（可能只有半句话）；大块语义完整，但向量模糊。

**解法：父子结构**

```
索引时：
  父块（800 字，语义完整）→ 不作为检索单位
    ├─ 子块1（200 字）→ 向量化，用于检索
    ├─ 子块2（200 字）
    └─ 子块3（200 字）

查询时：
  用子块检索 → 命中子块2 → 返回它的父块（完整 800 字）给模型
```

**效果**：检索精度用小块，生成质量用大块。这是工业级 RAG 的常见做法。

### 5.5 上下文压缩

检索到 10 段但只有 2 段真正相关，全塞进去会：增加成本、引入噪声、导致"中间遗忘"。

| 手段 | 做法 |
|---|---|
| 条数控制 | 只取 Top-3 到 Top-5 |
| 重排筛选 | 用 Rerank 分数做阈值截断 |
| 句子级筛选 | 只保留与问题最相关的句子 |
| 模型压缩 | 用小模型把长文档压缩成要点（多一次调用，慎用）|

---

## 六、RAG 评估：本模块的分水岭

**这是"会写 RAG"和"会做好 RAG"的分界线。**

### 6.1 两个独立的指标：检索质量 vs 生成质量

**新手最大误区**：只看最终答案对不对，把问题归因错。

```
用户提问 → [检索] → 检索结果 → [生成] → 答案
              ↑                    ↑
          检索指标              生成指标
```

**必须分开评估**，因为它们的修法完全不同：

| 症状 | 真实原因 | 该改什么 |
|---|---|---|
| 答案缺失关键信息 | 检索没召回 | 改切片/加混合检索/加查询改写 |
| 答案提到资料里没有的内容 | 提示词没约束好 | 改 Prompt / 加引用校验 |
| 答案正确但引用错 | 引用对齐有问题 | 改 Prompt 的编号规则 |
| 检索到了但答案还是错 | 生成能力不足或上下文太长 | 换模型 / 压缩上下文 |

### 6.2 检索指标

| 指标 | 定义 | 怎么算 |
|---|---|---|
| **Recall@K** | 正确文档是否在前 K 个结果里 | 最常用。K 一般取 5 或 10 |
| **Precision@K** | 前 K 个里有多少是相关的 | 反映噪声程度 |
| **MRR** | 第一个正确结果的排名倒数的平均 | 反映"排得靠不靠前" |
| **命中率** | 至少召回一个正确文档的比例 | 最直观 |

### 6.3 构建评估集（必须动手做）

**第 1 步：造 20–50 个问题**

来源：① 真实用户会问的；② 从文档反推（读一段，问一个它应该能回答的问题）；③ 边界情况（文档里没有的）。

```python
# eval/rag_testset.json
[
  {
    "question": "退款需要几个工作日到账？",
    "relevant_doc_ids": ["faq.md#退款流程"],       ← 标注正确文档，用于算检索指标
    "expected_keywords": ["3-5", "工作日"],        ← 答案必须包含的关键词
    "should_refuse": false                          ← 文档里有答案
  },
  {
    "question": "你们支持比特币支付吗？",
    "relevant_doc_ids": [],
    "expected_keywords": [],
    "should_refuse": true                           ← 文档里没有，应该拒绝回答
  }
]
```

**第 2 步：跑批算指标**

```python
# eval/evaluate_rag.py
import json
from src.rag import RAGPipeline

def evaluate(testset_path: str = "eval/rag_testset.json"):
    cases = json.load(open(testset_path, encoding="utf-8"))
    rag = RAGPipeline()

    hit = 0
    correct_answer = 0
    correct_refusal = 0
    total_should_refuse = sum(1 for c in cases if c["should_refuse"])
    latencies = []

    for case in cases:
        import time
        t0 = time.time()
        result = rag.query(case["question"])
        latencies.append(time.time() - t0)

        # ---- 检索指标：Recall@5 ----
        retrieved_ids = [c["metadata"].get("id") for c in result["chunks"]]
        if any(rid in retrieved_ids for rid in case["relevant_doc_ids"]):
            hit += 1

        # ---- 生成指标 ----
        if case["should_refuse"]:
            # 该拒绝的，是否正确拒绝了？
            if "未提及" in result["answer"] or "没有相关" in result["answer"]:
                correct_refusal += 1
        else:
            # 该回答的，关键信息有没有出现？
            if all(kw in result["answer"] for kw in case["expected_keywords"]):
                correct_answer += 1

    n = len(cases)
    answerable = n - total_should_refuse
    print(f"检索命中率 (Recall@5): {hit/n:.1%}")
    print(f"答案正确率:           {correct_answer/answerable:.1%}")
    print(f"正确拒答率:           {correct_refusal/total_should_refuse:.1%}")
    print(f"平均延迟:             {sum(latencies)/n:.2f}s")
    print(f"P95 延迟:             {sorted(latencies)[int(n*0.95)]:.2f}s")

if __name__ == "__main__":
    evaluate()
```

**输出示例**：

```
检索命中率 (Recall@5): 68.0%        ← 只有 68%，说明检索有问题！优先改检索
答案正确率:           72.7%
正确拒答率:           40.0%         ← 拒答率太低，会大量瞎编，必须修
平均延迟:             2.31s
```

**这就是有价值的结论**：你不再是"感觉效果还行"，而是"检索命中率 68%，需优化；拒答率 40%，提示词约束不够"。**面试时能说出这些话，就是中级工程师水平。**

---

## 七、知识点清单

**Part A（向量基础）**
- [ ] Embedding 的概念、语义相似性原理
- [ ] 余弦相似度 / 欧氏距离 / 点积的区别，为什么要归一化
- [ ] 主流 Embedding 模型选型，以及"入库和查询必须同模型"的约束
- [ ] 五种切片策略的取舍，chunk_size / overlap 的经验值
- [ ] 向量库的定位、ANN 原理、Chroma 与 pgvector 的选择

**Part B（RAG 链路）**
- [ ] 索引阶段和查询阶段的完整流程（能默画）
- [ ] 文档解析、清洗的常见问题
- [ ] metadata 的作用与引用溯源的实现
- [ ] 查询改写的适用场景与代价
- [ ] RAG Prompt 的设计要点（编号引用、拒绝机制）
- [ ] "不知道就说不知道"的三种实现方式，相似度阈值怎么定
- [ ] 引用有效性校验为什么必须做

**Part C（进阶与评估）**
- [ ] 纯向量检索的三个短板
- [ ] 混合检索的架构，RRF 融合原理
- [ ] Bi-Encoder 与 Cross-Encoder 的区别（Rerank 为什么更准）
- [ ] 召回与重排的两阶段设计思想
- [ ] 父子切片的原理与收益
- [ ] 上下文压缩的四种手段
- [ ] 检索指标（Recall@K / MRR）与生成指标的区分
- [ ] 如何构建评估集，如何定位问题出在检索还是生成

---

## 八、常见坑

### 坑 1：检索不准就换模型
**后果**：换了三个模型，效果没变，浪费时间金钱。
**正确做法**：先算检索命中率。90% 的 RAG 问题在检索环节（切片、Embedding、查询改写），不在生成模型。

### 坑 2：切片太大或太小
**太大**：一个块里 5 个主题，向量表达模糊，谁都匹配一点但不精准。
**太小**：一句话被切断，语义不完整，检索到了也没用。
**正确做法**：中文 300–800 字起步，带 10–20% 重叠，然后**实测对比**不同参数的效果。

### 坑 3：入库用 A 模型，查询用 B 模型
**后果**：向量空间不一致，相似度计算完全失效，检索结果随机。
**正确做法**：**必须用同一个模型**。换模型要重新生成所有向量。这个约束写进项目文档里。

### 坑 4：检索到无关内容还是硬答
**后果**：模型基于无关内容编造答案，这是 RAG 幻觉的主要来源。
**正确做法**：加相似度阈值过滤 + 提示词逃逸出口 + 评估拒答率。

### 坑 5：不做引用校验
**后果**：模型编造 `[7]` 但只有 3 段资料，前端点了没反应或显示错误内容。
**正确做法**：代码里校验引用编号是否有效，无效则拦截或剔除。

### 坑 6：把所有检索结果都塞进 Prompt
**后果**：成本上升、噪声干扰、长上下文"中间遗忘"。
**正确做法**：Top-3 到 Top-5，配合 Rerank 做质量筛选。

### 坑 7：逐条调用 Embedding API
**后果**：1000 个块调用 1000 次，慢十倍，还可能触发限流。
**正确做法**：批量调用（一次传一个列表，通常单次上限 10–20 条）。

### 坑 8：忽略 metadata
**后果**：无法展示引用来源，用户无法核实，RAG 的可信度优势丧失。
**正确做法**：存向量时必须同时存 source、title、page 等信息。

### 坑 9：没有评估集，靠感觉判断效果
**后果**：改了两周，不知道到底有没有变好；改坏了也发现不了。
**正确做法**：第一天就建 20 条测试集，每次改动都跑一遍。**这是本模块最重要的习惯。**

### 坑 10：把 RAG 当作消除幻觉的银弹
**后果**：以为上了 RAG 就万事大吉，结果检索错内容时模型更自信地编造。
**正确做法**：理解 RAG 只是"把凭空的编造变成有依据的编造"。检索质量 + 引用校验 + 拒答机制，三者缺一不可。

---

## 九、练习任务

### Part A（W3）

| # | 任务 | 难度 |
|---|---|---|
| 1 | 手写余弦相似度函数，用 20 条中文句子验证"语义相近的向量更近" | ⭐ |
| 2 | 用固定长度 vs 按 Markdown 结构两种策略切同一份文档，对比切片结果 | ⭐⭐ |
| 3 | 用 Chroma 建一个 100 条数据的向量库，实现语义搜索 | ⭐⭐ |
| 4 | **对比实验（重要）**：同一条 query，用 chunk_size=200/500/1000 各检索一次，记录 Top-3 结果差异，写出结论 | ⭐⭐⭐ |
| 5 | 测出你所用 Embedding 模型的"距离分布"：找 5 个相关问题 + 5 个无关问题，看距离能否区分 | ⭐⭐⭐ |

### Part B（W4）

| # | 任务 | 难度 |
|---|---|---|
| 6 | 打通完整 RAG 链路（解析→切片→embedding→检索→生成） | ⭐⭐⭐ |
| 7 | 实现引用溯源：答案里的 `[1]` 能点开看到原文片段 | ⭐⭐⭐ |
| 8 | 实现引用有效性校验，并故意诱导模型编造引用，验证校验能拦住 | ⭐⭐⭐ |
| 9 | 实现相似度阈值过滤，测定你数据的合适阈值 | ⭐⭐⭐ |
| 10 | 测试"给逃逸出口"前后的拒答率变化（用 10 个文档里没有的问题测） | ⭐⭐⭐ |

### Part C（W5）

| # | 任务 | 难度 |
|---|---|---|
| 11 | 加 BM25 实现混合检索，用 RRF 融合，对比混合前后的召回率 | ⭐⭐⭐⭐ |
| 12 | 接入 Rerank 模型，对比加与不加的 Top-3 准确率和延迟 | ⭐⭐⭐⭐ |
| 13 | 实现父子切片（小块检索、大块生成），对比效果 | ⭐⭐⭐⭐ |
| 14 | **构建 20 条评估集**，算出检索命中率、答案正确率、正确拒答率 | ⭐⭐⭐⭐ |
| 15 | **优化实验（核心产出）**：记录优化前 vs 优化后的四项指标，写一份对比报告 | ⭐⭐⭐⭐⭐ |

**任务 15 是你项目 02 的核心交付物。** 一份"检索命中率从 X 提升到 Y"的报告，比十页代码更能证明你的能力。

---

## 十、自测题

**Q1：为什么需要 RAG？直接微调不行吗？**
<details><summary>参考答案</summary>
两者解决的问题不同。RAG 解决"说什么"（知识、事实、时效性），微调解决"怎么说"（风格、格式、术语）。RAG 的优势：知识可实时更新（改文档即可）、可溯源（能给出处）、成本低、不用训练。微调的问题：更新慢（要重训）、贵、需要大量标注数据、仍会幻觉、无法溯源。所以 90% 的知识型场景用 RAG。
</details>

**Q2：为什么"语义相近的文本向量也相近"？Embedding 是怎么做到的？**
<details><summary>参考答案</summary>
Embedding 模型（基于 Transformer）在海量文本上训练，训练目标是让"在相似语境中出现的文本"产生相近的向量表示。比如"退款"和"退货"经常出现在相似上下文里，模型就被训练成给它们相近的向量。所以相似度反映的是"在语料中的使用语境相似"，而不是词典定义相似。要注意：这是训练目标带来的性质，不是数学必然。
</details>

**Q3：召回和重排为什么要分两步？直接用一个更准的模型不行吗？**
<details><summary>参考答案</summary>
因为精度和速度的矛盾。Cross-Encoder（重排模型）要把"问题+每个文档"一起送进模型打分，如果对上百万文档都这么做，延迟无法接受。所以分两步：先用 Bi-Encoder（Embedding）快速从海量文档里筛出 50 个候选（宁滥勿缺），再用 Cross-Encoder 对这 50 个精排。这是"漏斗"式的工程取舍。
</details>

**Q4：你的 RAG 回答错了，怎么定位是检索问题还是生成问题？**
<details><summary>参考答案</summary>
看检索结果。① 如果正确文档没被检索到 → 检索问题（改切片、加混合检索、加查询改写）；② 如果正确文档检索到了但答案还是错 → 生成问题（改 Prompt、压缩上下文、换模型）；③ 如果检索到了无关内容 → 阈值过滤问题。关键是**分开评估**：算 Recall@K 判断检索，算答案正确率判断生成。只看最终答案会归因错误。
</details>

**Q5：混合检索为什么能提升效果？什么场景必须有它？**
<details><summary>参考答案</summary>
因为向量检索找语义相似，不擅长字面精确匹配。当查询包含专有名词、产品型号、错误码、条款编号（如"ERR-4021"、"第3.2.1条"）时，向量模型可能没见过这些词或语义表达不明确，导致检索失败。BM25 关键词检索恰好擅长字面匹配。两者互补。任何有大量专有名词/代码/编号的文档（技术文档、法律合同、产品手册）都应该上混合检索。
</details>

**Q6：为什么说 RAG 不能消除幻觉？**
<details><summary>参考答案</summary>
因为 RAG 只是给模型提供了"参考资料"，模型仍然是在做下一 token 预测。如果 ① 检索到的是错误内容；② 检索结果不完整；③ 资料之间有矛盾；④ 资料没覆盖用户问题——模型仍可能编造或答错。RAG 把"凭空的编造"变成"基于材料的编造"，是减轻而非消除。所以必须配合引用校验、拒答机制、人工核对入口。
</details>

**Q7：切片大小怎么定？有没有经验值？**
<details><summary>参考答案</summary>
中文建议 300–800 字，overlap 为 chunk_size 的 10–20%。但这只是起点，**必须实测**。判断方法：取 10 条测试问题，用不同 chunk_size 各跑一遍，算 Recall@K，选最好的。影响因素：① 文档类型（FAQ 可以小，技术文档要大）；② 检索粒度需求（要精确到条款就小一些）；③ 问题的复杂度。另一个好办法是用父子切片，兼顾两者。
</details>

**Q8：用户问"它多少钱"，这个问题直接拿去检索会怎样？**
<details><summary>参考答案</summary>
大概率检索失败。因为"它"没有指代对象，向量模型不知道在说什么，算出来的向量会非常泛化。需要做查询改写：结合对话历史，把"它"替换成具体名词（如"X200 型号的产品多少钱"）。改写需要额外一次模型调用，增加延迟成本，所以只对多轮对话和复杂问题做。
</details>

**Q9：metadata 有什么用？为什么不能只存向量和原文？**
<details><summary>参考答案</summary>
metadata 有三个关键作用：① **引用溯源**——告诉用户这段话来自哪个文件、哪一页、哪一节，用户才能核实；② **过滤检索**——可以做"只在某份文档里搜"或按时间/权限过滤；③ **调试排查**——出问题时能知道检索到了什么。没有 metadata，RAG 最大的优势（可核实）就不成立。
</details>

**Q10：你怎么衡量你的 RAG 系统好不好？**
<details><summary>参考答案</summary>
分三个层面。① **检索层**：Recall@5（正确文档是否在 Top5）、MRR（排得多靠前）；② **生成层**：答案正确率（关键信息是否出现）、引用准确率（引用是否有效且对得上）、正确拒答率（该说"不知道"时是否说了）；③ **工程层**：首字延迟、P95 延迟、单次成本、平均检索条数。建 20–50 条测试集跑批，优化前后对比。**能说出这套指标体系，就说明你真的做过 RAG。**
</details>

**Q11：为什么入库和查询必须用同一个 Embedding 模型？**
<details><summary>参考答案</summary>
因为不同模型把文本映射到**不同的向量空间**。模型 A 和模型 B 的向量空间没有可比性——用模型 B 生成的查询向量去和模型 A 生成的文档向量算余弦相似度，结果完全没有意义（可能随机排序）。所以换 Embedding 模型时，必须重新生成所有已入库文档的向量。这是 RAG 系统迁移时最容易被忽略的坑。
</details>

---

## 十一、延伸阅读

| 主题 | 资源 |
|---|---|
| Chroma 官方文档 | https://docs.trychroma.com/ |
| 阿里云百炼 Embedding 文档 | https://help.aliyun.com/zh/model-studio/embedding |
| BM25 与 rank_bm25 库 | https://github.com/dorianbrown/rank_bm25 |
| RAG 综述论文 | 搜 "Retrieval-Augmented Generation for Large Language Models: A Survey" |
| pgvector | https://github.com/pgvector/pgvector |
| LangChain RAG 教程 | https://python.langchain.com/docs/tutorials/rag/ |

---

## 十二、完成标志

- [ ] 一个能跑的语义搜索脚本（W3）
- [ ] 一个完整 RAG 系统，含引用溯源和有效性校验（W4）
- [ ] 一份检索参数对比实验报告（chunk_size 对比）
- [ ] **项目 02 完成**：RAG 文档助手 + 评估报告（含优化前后四项指标对比）
- [ ] 能默画 RAG 索引和查询两张流程图
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 04，学习 Tool Calling——让模型不只是"说"，而是能"做事"。
