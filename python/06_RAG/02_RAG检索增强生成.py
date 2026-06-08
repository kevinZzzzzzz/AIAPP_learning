"""
RAG 完整实战 —— 检索增强生成
=================================================================

RAG（Retrieval-Augmented Generation）的完整流程：

用户提问 → 检索相关文档 → 将文档作为上下文拼入 Prompt → LLM 生成回答

这解决了 LLM 的两大问题：
1. 知识截止日期（训练数据是旧的）
2. 幻觉（没有的事实会编造）

本章实现一个迷你的 RAG 系统，使用本地向量检索。
生产环境推荐：ChromaDB / Pinecone / Weaviate / pgvector
"""

import json
import os
from typing import Optional
import asyncio


# ======================== 1. 文档加载器 ========================

class DocumentLoader:
    """文档加载器 —— 支持 TXT、Markdown、JSON 等格式"""
    
    @staticmethod
    def load_text(filepath: str) -> str:
        """加载纯文本文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    
    @staticmethod
    def load_json(filepath: str) -> list[dict]:
        """加载 JSON 文档（假设是列表格式）"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @staticmethod
    def from_strings(texts: list[str]) -> list[dict]:
        """从字符串列表创建文档"""
        return [
            {"id": str(i), "content": text, "metadata": {}}
            for i, text in enumerate(texts)
        ]


# ======================== 2. 文档切片器 ========================

class RecursiveCharacterSplitter:
    """递归字符分割器 —— LangChain 同名组件的简化实现
    
    策略：按优先级从高到低尝试分割符
    1. 段落 (\\n\\n)
    2. 换行 (\\n)
    3. 句子结束标记 (.。！？)
    4. 空格
    5. 字符级别
    """
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = ["\n\n", "\n", "。", ".", "！", "？", " ", ""]
    
    def split_text(self, text: str) -> list[str]:
        """将长文本切成小段"""
        return self._split_recursive(text, self.separators)
    
    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """递归切分"""
        if not separators:
            # 最后手段：按字符切
            return self._split_by_length(text)
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            return self._split_by_length(text)
        
        splits = text.split(separator)
        
        chunks = []
        current_chunk = ""
        
        for split in splits:
            new_chunk = current_chunk + (separator if current_chunk else "") + split
            
            if len(new_chunk) <= self.chunk_size:
                current_chunk = new_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                if len(split) > self.chunk_size:
                    # 子段仍然太长，用下一级分隔符递归
                    sub_chunks = self._split_recursive(split, remaining_separators)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 处理 overlap（简化实现）
        if self.overlap > 0 and len(chunks) > 1:
            overlapped = []
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # 从前一个 chunk 末尾取 overlap 个字符加到开头
                    prev_end = chunks[i-1][-self.overlap:] if len(chunks[i-1]) > self.overlap else chunks[i-1]
                    chunk = prev_end + chunk
                overlapped.append(chunk)
            return overlapped
        
        return chunks
    
    def _split_by_length(self, text: str) -> list[str]:
        """按固定长度切分（最后手段）"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.overlap):
            chunks.append(text[i:i + self.chunk_size])
        return chunks
    
    def split_documents(self, documents: list[dict]) -> list[dict]:
        """切分整个文档列表"""
        result = []
        for doc in documents:
            chunks = self.split_text(doc["content"])
            for i, chunk in enumerate(chunks):
                result.append({
                    "id": f"{doc['id']}_chunk_{i}",
                    "content": chunk,
                    "metadata": {**doc.get("metadata", {}), "source_id": doc["id"]},
                })
        return result


# ======================== 3. 简易向量存储 ========================

import numpy as np

class SimpleVectorStore:
    """简易向量存储 —— 用 NumPy 实现，生产环境用 ChromaDB 等"""
    
    def __init__(self):
        self.documents: list[dict] = []
        self.vectors: Optional[np.ndarray] = None  # shape: (n_docs, embedding_dim)
    
    def add(self, documents: list[dict], embeddings: list[list[float]]):
        """添加文档及其 Embedding"""
        self.documents.extend(documents)
        emb_array = np.array(embeddings)
        if self.vectors is None:
            self.vectors = emb_array
        else:
            self.vectors = np.vstack([self.vectors, emb_array])
    
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[dict, float]]:
        """余弦相似度搜索"""
        if self.vectors is None:
            return []
        
        query_vec = np.array(query_embedding)
        
        # 批量计算余弦相似度
        dot = np.dot(self.vectors, query_vec)
        norms = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec)
        similarities = dot / (norms + 1e-10)  # 防止除零
        
        # 取 top_k
        top_indices = np.argsort(similarities)[-top_k:][::-1]  # 降序
        
        return [
            (self.documents[i], float(similarities[i]))
            for i in top_indices
        ]
    
    def __len__(self):
        return len(self.documents)


# ======================== 4. RAG 引擎 ========================

class RAGEngine:
    """RAG 引擎 —— 整合检索 + 生成"""
    
    def __init__(
        self,
        vector_store: SimpleVectorStore,
        model_name: str = "gpt-4o-mini",
    ):
        self.vector_store = vector_store
        self.model_name = model_name
    
    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """获取 Embedding（可替换为真实 API）"""
        # 生产环境替换为真实 Embedding API
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception:
            # fallback: 伪随机向量（仅供演示）
            import random
            random.seed(hash(texts[0]) % (2**32))
            return [
                [random.random() for _ in range(10)]
                for _ in texts
            ]
    
    def build_prompt(
        self,
        query: str,
        retrieved_docs: list[tuple[dict, float]],
    ) -> str:
        """构建 RAG Prompt —— 将检索到的文档作为上下文"""
        
        context_parts = []
        for i, (doc, score) in enumerate(retrieved_docs):
            context_parts.append(
                f"[资料{i+1}] (相关度: {score:.2f})\n{doc['content']}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = f"""请根据以下参考资料回答用户问题。
如果资料中没有相关信息，请明确说明「参考资料中未找到相关信息」。
不要编造不存在的事实。

=== 参考资料 ===
{context}

=== 用户问题 ===
{query}

=== 回答 ==="""
        
        return prompt
    
    async def query(self, user_query: str, top_k: int = 3) -> dict:
        """执行 RAG 查询的完整流程"""
        
        # Step 1: 获取 query 的 Embedding
        query_embeddings = await self._get_embeddings([user_query])
        query_vec = query_embeddings[0]
        
        # Step 2: 检索相关文档
        results = self.vector_store.search(query_vec, top_k=top_k)
        
        # Step 3: 构建 Prompt
        prompt = self.build_prompt(user_query, results)
        
        # Step 4: 调用 LLM（这里返回 prompt 作为演示）
        # 实际调用：response = await openai_client.chat.completions.create(...)
        
        return {
            "query": user_query,
            "retrieved_count": len(results),
            "retrieved_docs": [
                {
                    "content": doc["content"][:100] + "...",
                    "score": score,
                }
                for doc, score in results
            ],
            "prompt": prompt[:500] + "...",  # 截断显示
        }


# ======================== 5. 构建知识库的完整流程 ========================

async def build_knowledge_base(
    documents: list[dict],
    chunk_size: int = 500,
    top_k: int = 3,
) -> RAGEngine:
    """构建知识库的完整流程"""
    
    # Step 1: 文档切片
    print("[1/3] 正在切片文档...")
    splitter = RecursiveCharacterSplitter(chunk_size=chunk_size, overlap=50)
    chunks = splitter.split_documents(documents)
    print(f"  产生了 {len(chunks)} 个文档片段")
    
    # Step 2: 创建向量存储
    print("[2/3] 创建向量存储...")
    vector_store = SimpleVectorStore()
    
    # Step 3: 生成 Embedding 并存储
    print("[3/3] 生成 Embedding...（生产环境会调用 API）")
    # 演示：使用伪随机向量代替真实 Embedding
    import random
    embeddings = []
    for chunk in chunks:
        random.seed(hash(chunk["content"]) % (2**32))
        embeddings.append([random.random() for _ in range(10)])
    
    vector_store.add(chunks, embeddings)
    print(f"  已存储 {len(vector_store)} 个向量")
    
    return RAGEngine(vector_store=vector_store)


# ======================== 6. 文档索引 Demo ========================

DEMO_DOCUMENTS = [
    {
        "id": "python_intro",
        "content": (
            "Python 是一种解释型、面向对象的高级编程语言。"
            "它由 Guido van Rossum 于 1991 年首次发布。"
            "Python 的设计哲学强调代码的可读性和简洁的语法结构。"
            "它使用缩进来定义代码块，而不是花括号或关键词。"
            "Python 是动态类型语言，支持垃圾回收。"
        ),
    },
    {
        "id": "python_ecosystem",
        "content": (
            "Python 的生态系统非常丰富。Web 开发方面有 Django、FastAPI、Flask。"
            "数据科学方面有 NumPy、Pandas、Matplotlib。"
            "机器学习方面有 TensorFlow、PyTorch、Scikit-learn。"
            "FastAPI 是一个现代高性能的 Web 框架，支持异步处理和自动 API 文档生成。"
        ),
    },
    {
        "id": "ai_basics",
        "content": (
            "人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。"
            "机器学习是 AI 的重要子领域，通过数据训练模型来做出预测和决策。"
            "深度学习使用多层神经网络处理复杂问题，在图像识别、自然语言处理等领域表现优异。"
            "大语言模型（LLM）如 GPT-4 是深度学习的最新成果，能够理解和生成人类语言。"
        ),
    },
    {
        "id": "rag_intro",
        "content": (
            "RAG（Retrieval-Augmented Generation）是一种结合信息检索和文本生成的 AI 技术。"
            "RAG 的流程是：先将用户问题转为向量，在知识库中检索相关文档，"
            "将检索到的文档拼入 Prompt，最后让 LLM 基于参考文档生成回答。"
            "RAG 可以有效减少大模型的幻觉问题，并让模型能够使用最新的外部知识。"
            "常用的向量数据库有 ChromaDB、Pinecone、Weaviate 和 Milvus。"
        ),
    },
]


async def main():
    """运行 RAG Demo"""
    print("=" * 60)
    print("RAG 系统 Demo")
    print("=" * 60)
    
    # 构建知识库
    rag_engine = await build_knowledge_base(
        DocumentLoader.from_strings(
            [doc["content"] for doc in DEMO_DOCUMENTS]
        ),
    )
    
    # 测试查询
    test_queries = [
        "Python 是什么时候发布的？",
        "FastAPI 有什么特点？",
        "什么是 RAG？它如何减少幻觉？",
        "今天天气怎么样？",  # 知识库中不存在的
    ]
    
    for query in test_queries:
        print(f"\n{'='*40}")
        print(f"用户问题: {query}")
        print("-" * 40)
        
        result = await rag_engine.query(query)
        
        print(f"检索到 {result['retrieved_count']} 条相关文档:")
        for doc in result["retrieved_docs"]:
            print(f"  [{doc['score']:.3f}] {doc['content'][:60]}...")
        
        print(f"\n生成的 Prompt（前200字符）:")
        print(result["prompt"][:200])


if __name__ == "__main__":
    asyncio.run(main())
