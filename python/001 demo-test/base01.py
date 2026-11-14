def list_comprehension_demo():
    print("--- 1. 列表推导式 (替代 JS 的 map 和 filter) ---")
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！请问有什么可以帮您？"},
        {"role": "user", "content": "今天天气"},
        {"role": "system", "content": "你是一个助手"},
    ]

    user_contents = [msg["content"] for msg in messages if msg["role"] == "user"]
    print(f"提取出用户的信息: {user_contents}\n")

def dict_demo():
    print("--- 2. 字典安全操作 (替代 JS Object) ---")
    response = {
        "id": "chatCmpl-123",
        "choices": [{"message": {"content": "Hello", "role": "assistant"}}]
    }

    total_tokens = response.get("user", {}).get("total_token", 0)
    print(f"安全获取 totens: {total_tokens}")


def set_demo():
    print("--- 3. 集合运算 (RAG 检索去重、对比差异必备) ---")

    doc_ids_from_vector_db = {"doc1", "doc2", "doc3", "doc4"}
    doc_ids_from_keyword_search = {"doc2", "doc3", "doc4"}

    # 交集 (&)：同时被两种方式检索到的核心文档
    core_docs = doc_ids_from_vector_db & doc_ids_from_keyword_search
    print(f"交集(同时命中): {core_docs}")

    # 并集 (|)：合并所有检索结果并自动去重
    all_docs = doc_ids_from_vector_db | doc_ids_from_keyword_search
    print(f"并集(合并去重): {all_docs}")

    # 差集 (-)：向量库搜到了但关键词没搜到的文档
    vector_only_docs = doc_ids_from_vector_db - doc_ids_from_keyword_search
    print(f"差集 (仅向量搜到): {vector_only_docs}\n")


if __name__ == "__main__":
    list_comprehension_demo()
    dict_demo()
    set_demo()

