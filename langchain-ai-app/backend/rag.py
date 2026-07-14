"""
RAG 文档问答模块 - 文章 2.4 实操4
实现上传文档 -> 向量化存储 -> 检索回答的完整流程
"""
import os
import shutil
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    LLM_MODEL,
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    KNOWLEDGE_BASE_DIR,
)


def get_embeddings():
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
    )


def get_vector_store(collection_name: str = "default"):
    """获取或创建向量存储"""
    persist_dir = os.path.join(CHROMA_PERSIST_DIR, collection_name)
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def load_document(file_path: str) -> list:
    """
    加载单个文档
    支持 .txt, .md, .pdf 格式
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in (".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    return loader.load()


def split_documents(documents: list, chunk_size: int = 500, chunk_overlap: int = 50):
    """将文档切分成小块"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return text_splitter.split_documents(documents)


def add_document_to_knowledge_base(file_path: str, collection_name: str = "default") -> dict:
    """
    将文档添加到知识库（向量数据库）
    流程：加载 -> 切分 -> 向量化 -> 存储
    """
    documents = load_document(file_path)
    chunks = split_documents(documents)

    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks)

    return {
        "file_name": Path(file_path).name,
        "chunks_count": len(chunks),
        "status": "success",
    }


def query_knowledge_base(question: str, collection_name: str = "default") -> dict:
    """
    基于知识库进行问答（RAG）
    流程：检索相关文档 + LLM 生成回答
    """
    vector_store = get_vector_store(collection_name)

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4},
    )

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
        temperature=0.3,
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )

    result = qa_chain.invoke({"query": question})

    sources = []
    for doc in result.get("source_documents", []):
        source_info = {
            "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
        }
        if source_info not in sources:
            sources.append(source_info)

    return {
        "question": question,
        "answer": result["result"],
        "sources": sources,
    }


def list_collections() -> list:
    """列出所有知识库集合"""
    persist_dir = Path(CHROMA_PERSIST_DIR)
    if not persist_dir.exists():
        return []
    return [d.name for d in persist_dir.iterdir() if d.is_dir()]


def list_knowledge_files() -> list:
    """列出知识库目录中的文件"""
    kb_dir = Path(KNOWLEDGE_BASE_DIR)
    if not kb_dir.exists():
        return []
    files = []
    for f in kb_dir.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "path": str(f),
            })
    return files
