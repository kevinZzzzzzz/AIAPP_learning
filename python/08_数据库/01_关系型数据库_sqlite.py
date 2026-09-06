import sqlite3

def init_db():
    # 连接到SQLite数据库（如果在当前目录不存在则会自动创建）
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    # 创建一张表用于存储聊天记录
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def save_message(conn, session_id, role, content):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    print(f"[{role}] message saved!")

def get_history(conn, session_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    )
    return cursor.fetchall()

if __name__ == "__main__":
    print("--- 关系型数据库 (SQLite) 示例：存储聊天历史 ---")
    conn = init_db()
    
    session_id = "session_123"
    
    # 模拟保存对话
    save_message(conn, session_id, "user", "你好，请问前端学AI需要学数据库吗？")
    save_message(conn, session_id, "assistant", "非常需要，特别是向量数据库和用来存取上下文的关系型数据库！")
    
    # 获取并打印对话历史
    print("\n--- 获取到的历史对话 ---")
    history = get_history(conn, session_id)
    for role, content in history:
        print(f"{role.capitalize()}: {content}")
        
    conn.close()
