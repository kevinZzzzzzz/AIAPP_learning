# 01_基础语法_列表推导式与集合.py

"""
第 1-2 天：基础核心语法
作为前端开发，你不需要死记硬背 Python 的所有方法，只需要掌握与 JS 高频操作对应的核心能力。
重点：列表推导式（替代 map/filter）、字典安全取值、集合运算（RAG必备）。
"""

def list_comprehension_demo():
    print("--- 1. 列表推导式 (替代 JS 的 map 和 filter) ---")
    
    # 模拟数据：AI 聊天记录
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！请问有什么可以帮您？"},
        {"role": "user", "content": "今天天气"},
        {"role": "system", "content": "你是一个助手"},
    ]
    
    # JS 中的 filter + map: 
    # messages.filter(m => m.role === 'user').map(m => m.content)
    
    # Python 的列表推导式 (非常高频，代码极其优雅！)
    # 语法：[加工后的结果 for 元素 in 列表 if 条件]
    user_contents = [msg["content"] for msg in messages if msg["role"] == "user"]
    print(f"提取出的用户消息: {user_contents}\n")


def dict_demo():
    print("--- 2. 字典安全操作 (替代 JS Object) ---")
    
    # 模拟 API 返回数据
    response = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"content": "Hello", "role": "assistant"}}]
    }
    
    # JS 中经常用 optional chaining: response?.usage?.total_tokens
    # Python 中，直接 response['usage'] 如果 key 不存在会抛出 KeyError 导致程序崩溃
    
    # 正确的做法 1：使用 .get()，第二个参数是默认值
    total_tokens = response.get("usage", {}).get("total_tokens", 0)
    print(f"安全获取 token: {total_tokens}")
    
    # 正确的做法 2：使用 Pydantic (下一节会讲，这是终极解决方案)
    print()


def set_demo():
    print("--- 3. 集合运算 (RAG 检索去重、对比差异必备) ---")
    
    # 在 RAG 中，我们经常会从不同的向量库中检索出文档片段的 ID
    # Python 的 Set 提供了数学级别的集合运算，比 JS 的 Set 强大得多
    
    doc_ids_from_vector_db = {"doc1", "doc2", "doc3", "doc5"}
    doc_ids_from_keyword_search = {"doc2", "doc3", "doc4"}
    
    # 交集 (&)：同时被两种方式检索到的核心文档
    core_docs = doc_ids_from_vector_db & doc_ids_from_keyword_search
    print(f"交集 (同时命中): {core_docs}")
    
    # 并集 (|)：合并所有检索结果并自动去重
    all_docs = doc_ids_from_vector_db | doc_ids_from_keyword_search
    print(f"并集 (合并去重): {all_docs}")
    
    # 差集 (-)：向量库搜到了但关键词没搜到的文档
    vector_only_docs = doc_ids_from_vector_db - doc_ids_from_keyword_search
    print(f"差集 (仅向量搜到): {vector_only_docs}\n")


if __name__ == "__main__":
    list_comprehension_demo()
    dict_demo()
    set_demo()
