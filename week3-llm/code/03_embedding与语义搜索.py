"""
Embedding 向量与语义搜索
=========================

Embedding 是 RAG（检索增强生成）的核心基础。
本文件演示：
1. 文本 → 向量的转换过程
2. 语义相似度计算（余弦相似度）
3. 构建简单的语义搜索引擎
4. 向量数据库的模拟实现
5. 端到端的 RAG 查询流程

核心概念：
- Embedding = 把文本变成一串数字（向量），相似文本的向量距离近
- 维度通常 768（BERT）、1536（OpenAI）、1024（BGE）
- 这是 90% 的 AI 应用（RAG、推荐、聚类）的基石
"""

import math
import hashlib
import os
from typing import Optional


# ====================== 第1部分：理解 Embedding ======================

def demo_embedding_concept():
    """用最简单的例子理解 Embedding
    
    假设我们有一个 3 维向量（实际是 768~3072 维）：
    每个维度代表一个"意义特征"
    """
    print("="*60)
    print("第1部分：Embedding 概念")
    print("="*60)
    
    # 模拟：不同文本的 3 维向量（实际远不止3维）
    embeddings = {
        "猫":       [0.9, 0.3, 0.1],
        "小猫":     [0.85, 0.28, 0.12],
        "狗":       [0.88, 0.35, 0.15],
        "汽车":     [0.1, 0.85, 0.7],
        "奔驰车":   [0.12, 0.87, 0.68],
        "Python编程": [0.0, 0.1, 0.9],
        "编程语言":   [0.02, 0.08, 0.92],
    }

    def cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """余弦相似度 = 两个向量夹角的余弦值
        
        公式: dot(v1, v2) / (|v1| * |v2|)
        结果: -1(完全相反) ~ 0(无关) ~ 1(完全相同)
        """
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2)

    print("语义相似度矩阵：\n")
    pairs = [
        ("猫", "小猫"),
        ("猫", "狗"),
        ("猫", "汽车"),
        ("汽车", "奔驰车"),
        ("Python编程", "编程语言"),
        ("猫", "Python编程"),
    ]

    print(f"{'文本1':<12} {'文本2':<12} {'相似度':>8} {'含义'}")
    print("-" * 50)
    for t1, t2 in pairs:
        sim = cosine_similarity(embeddings[t1], embeddings[t2])
        meaning = "很相似" if sim > 0.9 else "比较相似" if sim > 0.7 else "无关"
        print(f"{t1:<12} {t2:<12} {sim:>8.4f}  {meaning}")

    """
    输出解读：
    - "猫"和"小猫"的相似度 > 0.95  → 非常相似
    - "猫"和"狗"的相似度 > 0.9    → 都是宠物，距离近
    - "猫"和"汽车"的相似度 ~0.5   → 不相关
    - "Python编程"和"编程语言"    → 语义相关

    这就是语义搜索的基础：
    搜索 "小猫"，能找到 "猫" 相关的内容，而不是死板匹配 "小猫" 这个词
    """
    print()


# ====================== 第2部分：Demo Embedding Client ======================

class DemoEmbeddingClient:
    """演示 Embedding 客户端
    
    实际项目用: from openai import OpenAI
                client = OpenAI()
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=["文本1", "文本2"],
                )
    """

    VECTOR_DIM = 512  # 简化维度

    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表（演示用确定性 hash）"""
        vectors = []
        for text in texts:
            # 用 hash 生成伪向量（确定性，相同文本永远得到相同向量）
            h = hashlib.sha256(text.encode("utf-8")).digest()
            vec = []
            for i in range(self.VECTOR_DIM):
                byte_val = h[i % len(h)] if i < len(h) * 2 else 0
                vec.append((byte_val / 255.0) * 2 - 1)  # 归一化到 [-1, 1]
            vectors.append(vec)
        return vectors

    def similarity(self, text1: str, text2: str) -> float:
        """直接计算两个文本的相似度"""
        v1, v2 = self.embed([text1, text2])
        return _cosine_sim(v1, v2)


def _cosine_sim(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def demo_similarity_calculation():
    """演示相似度计算"""
    print("="*60)
    print("第2部分：语义相似度计算")
    print("="*60)

    client = DemoEmbeddingClient()

    # 手动计算相似度（实际业务）
    test_cases = [
        ("如何使用Python进行数据分析", "Python数据分析教程"),
        ("如何使用Python进行数据分析", "今天天气真不错"),
        ("前端React框架入门", "Vue.js和React有什么区别"),
        ("Machine Learning basics", "深度学习入门指南"),
    ]

    print(f"{'文本1':<30} | {'文本2':<30} | {'相似度':>8}")
    print("-" * 75)
    for t1, t2 in test_cases:
        sim = client.similarity(t1, t2)
        bar = "█" * int(sim * 20)
        print(f"{t1:<30} | {t2:<30} | {sim:.4f} {bar}")
    print()


# ====================== 第3部分：简易向量数据库 ======================

class SimpleVectorStore:
    """简易向量存储 —— 模拟向量数据库（ChromaDB/Qdrant/Milvus）的核心逻辑
    
    三个核心操作：
    - add: 添加文档 + 向量
    - search: 向量相似度搜索（KNN）
    - delete: 删除文档
    """

    def __init__(self):
        self._docs: list[dict] = []          # 文档列表
        self._vectors: list[list[float]] = [] # 向量列表
        self._embed_client = DemoEmbeddingClient()

    def add(self, texts: list[str], metadatas: Optional[list[dict]] = None):
        """添加文档（自动计算 Embedding）"""
        vectors = self._embed_client.embed(texts)
        for i, text in enumerate(texts):
            self._docs.append({
                "id": len(self._docs),
                "text": text,
                "metadata": metadatas[i] if metadatas else {},
            })
            self._vectors.append(vectors[i])

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """搜索最相似的 top_k 个文档
        
        实际工作流程：
        1. query → embed()
        2. query_vector 与所有 doc_vectors 计算余弦相似度
        3. 排序取 top_k
        """
        query_vec = self._embed_client.embed([query])[0]
        
        # 计算相似度
        scores = [
            (i, _cosine_sim(query_vec, doc_vec))
            for i, doc_vec in enumerate(self._vectors)
        ]
        
        # 降序排序取 top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in scores[:top_k]:
            doc = self._docs[idx]
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "score": round(score, 4),
                "metadata": doc["metadata"],
            })
        return results

    def __len__(self):
        return len(self._docs)


def demo_vector_store():
    """演示向量存储的完整使用流程"""
    print("="*60)
    print("第3部分：简易向量数据库")
    print("="*60)

    store = SimpleVectorStore()

    # 1. 添加知识库文档
    print("存储文档...")
    store.add([
        "Python 是一种解释型、面向对象的高级编程语言",
        "JavaScript 是 Web 开发中最常用的脚本语言",
        "React 是 Facebook 推出的前端 UI 框架",
        "FastAPI 是一个现代、高性能的 Python Web 框架",
        "机器学习是人工智能的一个分支，通过数据训练模型",
        "深度学习使用多层神经网络处理复杂问题",
        "做红烧肉需要五花肉、冰糖、生抽、老抽、料酒",
        "北京今天天气晴朗，气温 25°C，适合户外运动",
    ])
    print(f"共存储 {len(store)} 条文档\n")

    # 2. 搜索
    queries = [
        "Python Web 框架",
        "前端开发技术",
        "AI 相关内容",
        "菜谱",
    ]

    for query in queries:
        print(f"搜索: {query}")
        results = store.search(query, top_k=3)
        for i, r in enumerate(results):
            print(f"  #{i+1} [{r['score']:.4f}] {r['text'][:50]}...")
        print()


# ====================== 第4部分：端到端 RAG 流程 ======================

def demo_end_to_end_rag():
    """演示：从文档存储到 RAG 检索的完整流程"""
    print("="*60)
    print("第4部分：端到端 RAG 流程")
    print("="*60)

    # 模拟知识库
    knowledge_base = [
        "Token 是 LLM 处理文本的最小单位。中文字通常 1-2 个 Token。",
        "OpenAI 的 GPT-4o-mini 价格是输入 $0.15/1M tokens，输出 $0.60/1M tokens。",
        "LangChain 是一个用于构建 LLM 应用的框架，提供了 Chain、Agent、Tool 等抽象。",
        "LangGraph 在 LangChain 的基础上增加了状态图和循环的支持，适合构建 Agent。",
        "Function Calling 允许 LLM 调用外部函数。适用于查天气、汇率、数据库等场景。",
        "RAG（Retrieval-Augmented Generation）先检索相关文档，再让 LLM 基于文档生成回答。",
        "Embedding 是将文本转为向量的技术。OpenAI 的 text-embedding-3-small 输出 1536 维。",
        "中国大模型：DeepSeek V3、Qwen 2.5、GLM-4。DeepSeek 性价比极高。",
        "Python 装饰器是一种在不修改原函数的情况下增加功能的语法糖。用 @ 符号标记。",
        "FastAPI 中 async/await 用于处理并发请求，适合 AI API 开发。",
    ]

    # Step 1: 构建向量数据库
    print("\n[Step 1] 构建向量数据库...")
    store = SimpleVectorStore()
    store.add(knowledge_base)
    print(f"已存储 {len(store)} 条文档")

    # Step 2: 用户提问 + 向量检索
    user_question = "LangChain 和 LangGraph 有什么区别？"
    print(f"\n[Step 2] 用户提问: {user_question}")
    
    retrieved = store.search(user_question, top_k=3)
    print("检索到的相关文档:")
    for r in retrieved:
        print(f"  [{r['score']:.4f}] {r['text']}")

    # Step 3: 构造 Prompt（把检索结果拼进去）
    context = "\n".join(r["text"] for r in retrieved)
    augmented_prompt = f"""基于以下参考文档回答用户问题。如果文档中没有相关信息，说你不知道。

参考文档：
{context}

用户问题：
{user_question}

回答："""
    
    print(f"\n[Step 3] 增强后的 Prompt 长度: {len(augmented_prompt)} 字符")
    print(f"前 200 字符:\n{augmented_prompt[:200]}...")

    # Step 4: 调用 LLM（在实际项目中）
    print("\n[Step 4] 调用 LLM 生成最终回答...")
    print("(在实际项目中，这里调用 client.chat.completions.create)")
    print(f"\n{'='*50}")
    print("总结 — RAG 工作流：")
    print("  1. 知识库文档 → 切片 → Embedding → 向量库")
    print("  2. 用户提问 → Embedding → 向量检索 → 相关文档")
    print("  3. 相关文档 + 用户提问 → Prompt 模板 → LLM → 回答")
    print(f"{'='*50}\n")


# ====================== 第5部分：Embedding 可视化概念 ======================

def demo_embedding_visualization():
    """用数字展示 Embedding 的"意义空间"概念"""
    print("="*60)
    print("第5部分：理解 Embedding 的意义空间")
    print("="*60)

    print("""
想象一个三维空间（实际是 1536 维）：

        学习/编程轴
            ↑
        [Python编程]
        [编程语言]      [机器学习]
            |
            |
    —————— + ——————→ 日常/生活轴
            |
            |   [天气]
            |   [菜谱]
            |       [做饭]
            |
        技术/科学轴

语义相近的词在空间中彼此靠近。
这就是"向量数据库搜索"的本质——
把用户查询也放到这个空间，找最近的文档点。
    """)


# ====================== 主入口 ======================

if __name__ == "__main__":
    demo_embedding_concept()
    demo_similarity_calculation()
    demo_vector_store()
    demo_end_to_end_rag()
    demo_embedding_visualization()

    print("\n关键记住: Embedding = 把文本变成数学坐标。")
    print("坐标越近 = 意思越像。")
    print("这是 RAG、推荐系统、语义搜索的底层技术。")
