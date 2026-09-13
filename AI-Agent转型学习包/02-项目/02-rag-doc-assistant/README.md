# 项目 02：RAG 文档问答助手

> 对应模块：**模块 03（RAG 与向量检索）**｜建议在第 5 周完成后动手
> 难度：★★★☆☆｜代码量：约 900 行 Python

一个**不依赖任何 RAG 框架**、从零手写的文档问答系统。含混合检索（向量 + BM25）、RRF 融合、引用溯源、检索过程可视化。

---

## 为什么不用 LangChain / LlamaIndex

因为你的目标是**理解**，不是**跑通**。

调 `RetrievalQA.from_chain_type()` 用 5 行代码就能跑起来，但面试官问下面这些，你就答不上来了：

- 切片切多大合适？overlap 为什么要留？不留会怎样？
- 向量检索 10 万条数据要多久？瓶颈在哪？
- 为什么还要 BM25？只用向量不行吗？
- 检索不准，你怎么知道是检索的问题还是生成的问题？

**手写一遍之后再去看 LangChain 的源码，你会发现"原来它也就是这么干的"。** 这个顺序不能反。

---

## 项目结构

```
02-rag-doc-assistant/
├── main.py               # CLI 入口（index / ask / chat / debug / stats / reset）
├── pyproject.toml        # 依赖
├── .env.example          # 环境变量模板
├── data/                 # 示例知识库（两份虚构文档，可开箱测试）
│   ├── 云雀产品手册.md
│   └── 新员工入职答疑.md
└── src/
    ├── config.py         # 所有可调参数集中在此（切片/召回/融合）
    ├── store.py          # 向量库：sqlite 存向量+原文，numpy 算余弦相似度
    ├── embedder.py       # Embedding 封装：自动分批 + 重试 + 顺序保证
    ├── ingest.py         # 切片与入库：结构优先的递归切片
    ├── bm25.py           # BM25 关键词检索（jieba 分词）
    ├── retriever.py      # 混合检索 + RRF 融合 + 调试接口
    └── rag.py            # 组装 Prompt → 生成 → 带引用回答
```

**数据流**：

```
index:  .md 文件 → 清洗 → 切片 → Embedding API → sqlite（向量+原文）
ask:    问题 → Embedding → 向量检索 ┐
                    ↓              ├→ RRF 融合 → Prompt → 模型 → 带引用答案
        问题 → jieba 分词 → BM25 检索 ┘
```

---

## 快速开始

```bash
cd 02-项目/02-rag-doc-assistant

# 1. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 DASHSCOPE_API_KEY

# 2. 安装依赖（uv 会自动创建虚拟环境）
uv sync

# 3. 索引示例文档（首次会调用 Embedding API，约 100 个片段）
uv run main.py index ./data

# 4. 查看索引状态
uv run main.py stats

# 5. 提问
uv run main.py ask "退款需要几天到账？"

# 6. 看检索过程（强烈建议多做这一步）
uv run main.py debug "ERR_AUTH_4012 是什么意思？"

# 7. 交互式连续追问
uv run main.py chat
```

---

## 用哪些问题测出"向量 vs BM25"的差异

这是本项目最重要的练习。示例文档里故意埋了两类内容：

### 类型 A：只有精确匹配能召回 → BM25 会赢

```bash
uv run main.py debug "ERR_QUOTA_7003 怎么处理？"
uv run main.py debug "text-embedding-v4 单次最多几条？"   # 这个在模块文档里
uv run main.py debug "标准版一年多少钱？"
```

**观察点**：包含错误码的那一段，在 BM25 里应该排第 1，向量检索里可能排很后甚至不在前 12。

原因：`ERR_QUOTA_7003` 这个字符串在向量空间里没有"语义邻居"，模型没见过它，编码出来的向量不具备区分度。

### 类型 B：只有语义匹配能召回 → 向量会赢

```bash
uv run main.py debug "东西不想要了钱能退吗？"
uv run main.py debug "我不想干了要走人得提前多久说？"
```

**观察点**：文档里写的是"退款政策""解除劳动合同"，字面完全不重合，BM25 几乎召不到，但向量能匹配上。

**结论**：这就是为什么要混合检索。任何单一方案都会在某一类查询上瘸腿。

---

## 关键设计决策（面试会问）

### 1. 为什么自己写向量库，不用 Chroma？

为了看清 `collection.query()` 背后发生了什么。核心就是 `store.py` 里这 6 行：

```python
mat_norm = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-10)
q_norm = q / (np.linalg.norm(q) + 1e-10)
scores = mat_norm @ q_norm        # 一次矩阵乘算完所有相似度
top_idx = np.argsort(-scores)[:top_k]
```

**时间复杂度 O(N·D)**。1 万条 × 1024 维，numpy 向量化后约 5–10 ms，够用。但 100 万条就是 1 秒以上，扛不住——这时候才需要 HNSW / IVF 这类 ANN 索引（用 1% 的精度损失换 100 倍速度）。

**先知道为什么要用，才知道该用什么。**

### 2. 为什么用 RRF 融合，而不是分数加权？

两个分数量纲不同：余弦相似度在 [-1,1]，BM25 可以到几十。直接相加，BM25 会碾压。

RRF 只用**排名**不用分数：`score = Σ 1/(60 + rank)`。不需要归一化，不怕量纲差异，实现只有几行。

### 3. 为什么 embedding 模型不能随便换？

`store.py` 里的 `check_embedding_model()` 是一道防呆。真实事故场景：有人换了 embedding 模型没重建索引，**检索结果全是噪声但代码不报错**，排查了两天。

同理，`ingest.py` 里入库和 `embedder.py` 里查询必须用同一个模型——这个约束在代码里通过共用 `config.embed` 来保证。

### 4. 切片参数怎么调？

| 参数 | 默认 | 调大的后果 | 调小的后果 |
|---|---|---|---|
| `chunk_size` | 400 | 一片混多主题，语义被平均，检索不准 | 语义不完整，模型拼不出答案 |
| `chunk_overlap` | 80 | 索引体积和成本上升 | 答案容易卡在边界被切断 |
| `top_k` | 5 | 噪声变多，模型被干扰 | 漏掉关键信息 |

**别猜，用 `debug` 命令测。** 改 `src/config.py` 里的数字，重跑同一批问题，对比召回结果。这就是最原始的检索评估。

---

## 进阶练习

按难度排序，做完这些你就超过 90% 的"调包选手"：

1. **加 rerank（⭐️⭐️）**：召回 20 条后用模型重排取前 5。最简单的做法是让 LLM 给每条打分。对比开/关 rerank 的答案质量。
2. **查询改写（⭐️⭐️）**：`rag.py` 里已经写了 `ask_with_rewrite()`，接上 CLI 试试。观察"东西不想要了"这类模糊问题的召回率变化。
3. **加评估集（⭐️⭐️⭐️）**：手工标注 20 个"问题 → 正确片段"的对应关系，每次改参数跑一遍，算命中率（Hit Rate）和 MRR。**没有评估集的调参都是玄学。**
4. **换 ANN 索引（⭐️⭐️⭐️）**：把全量扫描换成 hnswlib，造 10 万条假数据，测一下延迟和召回率的差距。
5. **多轮对话（⭐️⭐️⭐️）**：现在每轮都是独立检索，追问"那它呢？"会失效。加上"用 LLM 把追问改写成独立问题"这一步（叫 query condensation）。

---

## 常见坑

| 现象 | 原因 | 解决 |
|---|---|---|
| `400 InvalidParameter: batch size` | 百炼单次最多 10 条文本 | `config.py` 里 `batch_size=10`，代码已自动分批 |
| `dimensions` 参数报错 | 部分模型不支持指定维度 | 删掉 `dimensions=` 参数，用模型默认维度 |
| 检索结果全是噪声 | embedding 模型被换了但没重建索引 | `main.py reset` 后重新 `index` |
| 中文检索效果差 | 没装 jieba，退化成了 bigram | `uv sync` 会装上；确认没报 ImportError |
| 答案里没有引用标注 | 模型没遵守 system prompt | 换 `pro` 模型，或在 prompt 里加 few-shot 示例 |
| 成本比预期高 | 每次 `index` 都重新 embedding 整个目录 | 代码已做去重跳过；改了 chunk 参数才需要 `--force` |

---

## 下一步

这个项目是**单 Agent + 检索工具**的雏形。接下来：

- **项目 03（工具调用 Agent）**：让模型能主动决定"要不要检索"，而不是每次都检索
- **模块 09**：给这个系统加上完整的评估体系（Hit Rate、MRR、忠实度）
- **模块 10**：部署成服务，用 pgvector 替换 sqlite 向量库

> 💡 **把 RAG 做成工具，交给 Agent 调用** —— 这是从"RAG 应用"走向"Agent 应用"的关键一步。项目 03 会做这件事。
