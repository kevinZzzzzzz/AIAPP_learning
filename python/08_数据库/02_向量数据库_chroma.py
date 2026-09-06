# 注意：运行此文件需要先安装 chromadb: pip install chromadb
import chromadb

def main():
    print("--- 向量数据库 (ChromaDB) 示例：存储和检索文档片段 ---")
    
    # 初始化 ChromaDB 客户端（这里使用内存模式，数据在程序关闭后会丢失）
    client = chromadb.Client()
    
    # 创建一个 Collection（相当于关系型数据库中的表）
    # Chroma 默认会下载并使用 all-MiniLM-L6-v2 模型来自动对文档进行向量化（Embedding）
    # 第一次运行可能会因为下载模型而稍微有些慢
    collection = client.create_collection(name="ai_knowledge_base")
    
    # 准备一些文档，这些就像是你要让AI参考的“知识库”
    documents = [
        "前端开发主要关注用户界面和交互，常用技术包括 HTML, CSS, JavaScript, React, Vue 等。",
        "向量数据库是一种专门用于存储、管理和搜索高维向量数据的数据库，是 RAG 应用的核心基础设施。",
        "RAG（检索增强生成）结合了信息检索和生成模型，可以把私有数据喂给大模型，避免它胡说八道。",
        "关系型数据库如MySQL和PostgreSQL，通过表格结构组织数据，适合存储聊天记录和用户资料等结构化信息。"
    ]
    
    # 准备对应的元数据（可选，用于过滤）和唯一标识ID
    metadatas = [{"source": "web"}, {"source": "ai_db"}, {"source": "ai_concept"}, {"source": "traditional_db"}]
    ids = ["doc1", "doc2", "doc3", "doc4"]
    
    # 将文档存入向量数据库
    print("正在将文档向量化并存入 ChromaDB...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("存储完成！\n")
    
    # 进行语义相似度查询
    query_text = "什么是RAG？"
    print(f"查询问题: '{query_text}'")
    
    # 查询最相似的文档
    results = collection.query(
        query_texts=[query_text],
        n_results=2 # 限制返回最相关的2条结果
    )
    
    print("\n检索到的最相关文档:")
    for i, doc in enumerate(results['documents'][0]):
        print(f"{i+1}. {doc}")
        print(f"   (元数据: {results['metadatas'][0][i]}, 距离/相关度得分: {results['distances'][0][i]:.4f})")

if __name__ == "__main__":
    main()
