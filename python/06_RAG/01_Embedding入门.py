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
from typing import list as ListType


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


# ======================== 2. 向量相似度计算 ========================

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


# ======================== 3. 模拟 Embedding 向量 ========================

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


# ======================== 4. 调用 OpenAI Embedding API ========================

async def get_embeddings(texts: list[str], model: str = "text-embedding-3-small"):
    """获取文本的 Embedding 向量"""
    try:
        from openai import AsyncOpenAI
        import os
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "demo-key"))
        
        response = await client.embeddings.create(
            model=model,
            input=texts,
        )
        
        return [item.embedding for item in response.data]
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
        
        # 计算每个文档与查询的相似度
        scored = [
            (doc, cosine_similarity(query_embedding, emb))
            for doc, emb in zip(self.documents, self.embeddings)
        ]
        
        # 按相似度降序排列
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[:top_k]


def demo_semantic_search():
    """演示语义搜索"""
    # 模拟文档和 Embedding
    docs = [
        "Python 是一种高级编程语言，广泛用于 AI 开发",
        "JavaScript 主要用于 Web 前端开发",
        "机器学习是人工智能的一个子领域",
        "React 是一个流行的前端框架",
        "Transformer 架构是 LLM 的核心基础",
    ]
    
    # 模拟 Embedding（实际应用中使用真实模型）
    embeddings = [
        [0.8, 0.6, 0.1, 0.0, 0.2],  # Python + AI
        [0.2, 0.1, 0.9, 0.7, 0.1],  # JS + Web
        [0.7, 0.8, 0.0, 0.0, 0.3],  # ML + AI
        [0.1, 0.0, 0.8, 0.9, 0.0],  # React + 前端
        [0.6, 0.7, 0.1, 0.0, 0.5],  # Transformer + LLM
    ]
    
    engine = SimpleSemanticSearch()
    engine.add_documents(docs, embeddings)
    
    # 查询
    queries = [
        ([0.9, 0.5, 0.0, 0.0, 0.1], "AI 编程相关"),
        ([0.0, 0.0, 0.9, 0.8, 0.0], "前端开发相关"),
    ]
    
    for query_vec, desc in queries:
        print(f"\n查询: {desc}")
        results = engine.search(query_vec, top_k=3)
        for doc, score in results:
            print(f"  [{score:.3f}] {doc}")


# ======================== 7. 实战：文档切片 + Embedding ========================

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """简单文档切片 —— RAG 的第一步
    
    实际生产建议用 LangChain 的 RecursiveCharacterTextSplitter
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += (chunk_size - overlap)  # 有重叠地滑动
    
    return chunks


def demo_chunk_and_embed():
    """演示文档切片 + Embedding 的完整流程"""
    
    document = """
    Python 是一种解释型、面向对象的高级编程语言。它由 Guido van Rossum 
    于 1991 年首次发布。Python 的设计哲学强调代码的可读性和简洁的语法。
    
    Python 在数据科学和人工智能领域应用广泛。TensorFlow、PyTorch、Scikit-learn 
    等机器学习框架都基于 Python。OpenAI 的 GPT 系列模型的 API 也优先支持 Python。
    
    Python 的生态系统非常丰富，包括 Web 开发框架 Django 和 FastAPI、
    数据分析库 Pandas、科学计算库 NumPy、以及可视化库 Matplotlib。
    """
    
    # 1. 切片
    chunks = chunk_text(document, chunk_size=150, overlap=30)
    print(f"文档被分成 {len(chunks)} 个切片:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: [{len(chunk)}字符] {chunk[:50]}...")
    
    # 2. Embedding（生产环境调用 API 或本地模型）
    # embeddings = await get_embeddings(chunks)
    
    print(f"\n提示: 生产环境中，每个切片会生成一个 Embedding 向量存入向量数据库")


# ======================== 8. Token 数与成本的估算 ========================

def estimate_embedding_cost(texts: list[str], model: str = "text-embedding-3-small"):
    """估算 Embedding API 成本"""
    import tiktoken
    
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")  # 近似
    
    total_tokens = sum(len(encoding.encode(text)) for text in texts)
    
    # OpenAI 2024 定价（近似）
    pricing = {
        "text-embedding-3-small": 0.02 / 1_000_000,   # $0.02/百万token
        "text-embedding-3-large": 0.13 / 1_000_000,   # $0.13/百万token
        "text-embedding-ada-002": 0.10 / 1_000_000,   # $0.10/百万token
    }
    
    cost_per_m = pricing.get(model, 0.02 / 1_000_000)
    cost = total_tokens * cost_per_m
    
    print(f"模型: {model}")
    print(f"总 tokens: {total_tokens}")
    print(f"预估成本: ${cost:.6f}")
    
    return cost


if __name__ == "__main__":
    print("=== Embedding 入门 Demo ===\n")
    
    print("1. 向量相似度计算")
    demo_vector_similarity()
    
    print("\n2. 语义搜索")
    demo_semantic_search()
    
    print("\n3. 文档切片 + Embedding 流程")
    demo_chunk_and_embed()
