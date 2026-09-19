# 06_数据库与持久化_SQLite与向量库.py

"""
第 6 课：数据库连接与持久化
对应前端/Node：Local Storage / Prisma / Mongoose
重要性：⭐⭐⭐⭐
AI Agent 开发中主要有两种数据库需求：
1. 关系型/文档型数据库：用来保存“用户的对话历史 (Memory)”和“业务数据”。
2. 向量数据库 (Vector DB)：用来保存“文档切片后的 Embedding 向量”，用于语义检索 (RAG)。
"""

import sqlite3
import json

def sqlite_memory_demo():
    print("--- 1. 使用 SQLite 保存 Agent 对话历史 ---")
    # 为什么教 SQLite？
    # 因为在 Agent 本地开发时，极其轻量，不需要像 MySQL/Postgres 那样装环境。
    # LangChain 和 LangGraph 的本地 Checkpointer 大量使用 SQLite。
    
    # 1. 连接数据库 (如果文件不存在会自动创建，这里用 :memory: 表示在内存中建库，程序结束即销毁)
    # 真实项目中可以填 "agent_memory.db" 会生成一个本地文件。
    conn = sqlite3.connect(":memory:") 
    
    # 创建游标 (相当于执行 SQL 的遥控器)
    cursor = conn.cursor()
    
    # 2. 建表：创建一个叫 messages 的表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    
    # 3. 插入数据 (模拟 Agent 产生了一轮对话)
    session = "session_123"
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", 
                   (session, "user", "今天天气怎么样？"))
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", 
                   (session, "assistant", "今天是晴天，气温25度。"))
    
    # 必须 commit 才能真正写入数据库
    conn.commit() 
    
    # 4. 查询数据 (当用户刷新页面，你需要恢复历史上下文喂给大模型时)
    cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session,))
    history = cursor.fetchall()  # 返回一个数组： [('user', '今天天气...'), ('assistant', '今天...')]
    
    print("🧠 从数据库恢复的对话历史:")
    # 将其转回大模型需要的 dict 格式
    formatted_history = [{"role": row[0], "content": row[1]} for row in history]
    print(json.dumps(formatted_history, ensure_ascii=False, indent=2))
    
    # 关闭连接
    conn.close()


def vector_db_concept():
    print("\n--- 2. 关于 向量数据库 (Vector Database) 的概念 ---")
    print("""
作为前端开发，你可能习惯了 MySQL(精确匹配) 或 MongoDB(文档匹配)。
但在 AI Agent(尤其是 RAG) 开发中，你需要连接 向量数据库 (如 ChromaDB, Qdrant, Milvus)。

它们的作用是：
当你输入“苹果的营养价值”时，它能帮你找出“这颗水果富含维生素C”的段落。
（因为它们在语义/高维空间上的向量距离很近）

在 Python 中连接向量库，通常不需要写 SQL，而是调用该库提供的专门 SDK。
例如 ChromaDB 的伪代码：
```python
import chromadb

# 1. 连接本地库
client = chromadb.PersistentClient(path="./rag_db")
collection = client.get_or_create_collection(name="docs")

# 2. 插入文档 (它会自动调用 Embedding 模型变成向量存进去)
collection.add(
    documents=["苹果富含维生素", "马斯克收购了推特"],
    ids=["doc1", "doc2"]
)

# 3. 语义搜索
results = collection.query(
    query_texts=["水果对身体有什么好处？"],
    n_results=1
)
# 结果会精准命中 doc1
```
    """)


if __name__ == "__main__":
    sqlite_memory_demo()
    vector_db_concept()
