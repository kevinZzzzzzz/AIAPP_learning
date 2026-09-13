"""RAG 文档助手 —— 模块 03 配套项目。

模块划分（自上而下是数据的流向）：
    ingest.py    → 读文件 → 切片 → 算向量 → 入库
    store.py     → 向量库（sqlite 存取）
    bm25.py      → 关键词检索（与向量检索互补）
    retriever.py → 两种检索 + RRF 融合
    rag.py       → 组装 Prompt → 调模型 → 带引用回答
"""
