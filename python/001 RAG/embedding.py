"""
Embedding 入门 —— 文本转向量的核心概念
=================================================================

Embedding = 把文本转换成固定长度的数字向量
语义相近的文本 → 向量距离近，语义相反 → 向量距离远

这是 RAG（检索增强生成）的数学基础。

前端类比：就像 CSS 中的颜色可以用 RGB 三个数字表示一样，
Embedding 用几百到几千个数字来表示一段文本的"含义"。
"""
import numpy as np
import os
import json
import asyncio
from typing import List as ListType
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
ai_api_key=os.getenv("AI_API_KEY")
ai_base_url=os.getenv("AI_BASE_URL")
api_model_name=os.getenv("API_MODEL_NAME")

# ======================== 1. 理解 Embedding 的概念 ========================

"""
想象一个三维空间（实际是 768-4096 维）：
- "国王" 和 "女王" 的向量距离很近
- "国王" 和 "披萨" 的向量距离很远
- "男人→国王" ≈ "女人→女王"  （向量运算！）

常用 Embedding 模型：
- OpenAI: text-embedding-3-small (1536维) / text-embedding-3-large (3072维)
- 开源: BGE-M3, text2vec-large-chinese, m3e-base
"""

# ======================== 2. 向量相似度计算 ====================================
def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """余弦相似度 —— 最常用的向量相似度度量
    
    取值范围：[-1, 1]，越接近 1 越相似
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))

def euclidean_distance(vec_a: list[float], vec_b: list[float]) -> float:
    """欧几里得距离 —— 越小越相似"""
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.linalg.norm(a - b))

def dot_product(vec_a: list[float], vec_b: list[float]) -> float:
    """点积 —— 越大越相似（向量已归一化时等价于余弦相似度）"""
    return float(np.dot(np.array(vec_a), np.array(vec_b)))


# ======================== 3. 模拟 Embedding 向量 ===============================
def demo_vector_similarity():
    """用简单数字演示向量相似度"""
    # 模拟两个相似的文本
    text1_vec = [0.8, 0.6, 0.1]  # "Python 编程语言"
    text2_vec = [0.7, 0.5, 0.2]  # "Python 开发"
    text3_vec = [0.1, 0.2, 0.9]  # "披萨食谱"
    
    sim_12 = cosine_similarity(text1_vec, text2_vec)
    sim_13 = cosine_similarity(text1_vec, text3_vec)
    print(f"「Python 编程语言」vs「Python 开发」: {sim_12:.4f}")  # 应该很高
    print(f"「Python 编程语言」vs「披萨食谱」: {sim_13:.4f}")      # 应该很低

# # ======================== 4. 调用 OpenAI Embedding API ========================
async def get_embeddings(texts: list[str], model: str = api_model_name):
    """获取文本的 Embedding 向量"""
    try:
        from openai import AsyncOpenAI
        import os

        client = AsyncOpenAI(api_key=ai_api_key, base_url=ai_base_url)

        response = await client.embeddings.create(
            model=model,
            input=texts
        )
        return [items.embedding for item in response.data]
    except ImportError:
        print("请安装 openai: pip install openai")
        return []
    except Exception as e:
        print(f"API 调用失败: {e}")
        # 返回模拟数据用于演示
        return [[0.1 * (i+1) * (j+1) for j in range(10)] for i in range(len(texts))]


# ======================== 5. 本地 Embedding 模型（离线方案） ========================

"""
使用 sentence-transformers 库在本地运行 Embedding 模型：

安装：pip install sentence-transformers

from sentence_transformers import SentenceTransformer

# 加载模型（首次会自动下载，约 400MB）
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

# 中文 Embedding
texts = ["Python 是一门编程语言", "今天天气真好", "编程语言有哪些"]
embeddings = model.encode(texts, normalize_embeddings=True)

# 计算相似度
similarities = model.similarity(embeddings, embeddings)
print(similarities)
"""
# ======================== 6. 语义搜索 Demo ========================
class SimpleSemanticSearch:
    """最简单的语义搜索引擎 —— 理解 RAG 检索的本质"""
    def __init__(self):
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []
    
    def add_documents(self, docs: list[str], embeddings: list[list[float]]):
        """添加文档及其 Embedding"""
        self.documents.extend(docs)
        self.embeddings.extend(embeddings)
    def search(self, query_embedding: list[float], top_k: int = 3) -> list[tuple[str, float]]:
        """搜索与 query 最相似的 top_k 个文档"""
        if not self.embeddings:
            return []

        scored = [
            (doc, cosine_similarity(query_embedding, emb))
            for doc, emb in zip(self.documents, self,embeddings)
        ]

        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_k]


if __name__ == "__main__":
    print("=== Embedding 入门 Demo ===\n")
    
    print("1. 向量相似度计算")
    # demo_vector_similarity()

    # print("2调用 OpenAI Embedding API")
    # data = asyncio.run(get_embeddings(["Python 编程语言"], model="text-embedding-3-small"))
    # print(json.dumps(data))

    print("\n2. 语义搜索")
    demo_semantic_search()