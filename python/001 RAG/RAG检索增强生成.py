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
        with open(filepath, 'r', encoding="utf-8") as f:
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

    def __init__(self, chunk_size: int = 500, overlop: int = 100):
        self.chunk_size = chunk_size
        self.overlop = overlop
        self.separators = ["\n\n", "\n", "。", ".", "！", "？", " ", ""]

    def split_text(self, text: str) -> list[str]:
        """将长文本切成小段"""
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """递归切分"""
        if not separators:
            return self._split_by_length(text)
        
        separators = separators[0]
        remaining_separators = separators[1:]

        if separators == "":
            return self._split_by_length(text)


    def _split_by_length(self, text: str) -> 


async def main():
    """运行 RAG Demo"""
    print("=" * 60)
    print("RAG 系统 Demo")
    print("=" * 60)




if __name__ == "__main__":
    asyncio.run(main())