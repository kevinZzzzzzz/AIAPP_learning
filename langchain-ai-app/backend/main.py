"""
FastAPI 后端服务入口
+ 提供基础对话、Prompt模板、链式调用、RAG文档问答等 API
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import chat
import prompts
import chains
import rag
from config import APP_HOST, APP_PORT, KNOWLEDGE_BASE_DIR

app = FastAPI(
    title="LangChain AI 应用",
    description="基于 LangChain 构建的 AI 应用后端（前端开发程序员版）",
    version="1.0.0",
)

# CORS - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 数据模型 ==========

class ChatRequest(BaseModel):
    messages: list[dict]


class PromptTemplateRequest(BaseModel):
    template_id: str
    variables: dict


class ChainRequest(BaseModel):
    chain_id: str
    variables: dict


class RAGQueryRequest(BaseModel):
    question: str
    collection_name: str = "default"


# ========== API 路由 ==========

@app.get("/")
def root():
    return {
        "service": "LangChain AI App Backend",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat - POST 基础对话",
            "chat_stream": "/api/chat/stream - POST 流式对话",
            "prompt_templates": "/api/prompts - GET 获取模板列表",
            "apply_prompt": "/api/prompts/apply - POST 应用模板",
            "chains": "/api/chains - GET 获取链列表",
            "run_chain": "/api/chains/run - POST 运行链",
            "rag_upload": "/api/rag/upload - POST 上传文档",
            "rag_query": "/api/rag/query - POST 文档问答",
            "rag_files": "/api/rag/files - GET 知识库文件列表",
        },
    }


# ---------- 基础对话 ----------

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """基础对话 - 文章 2.1"""
    try:
        reply = chat.chat_with_history(req.messages)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """流式对话 - 文章进阶方向1"""
    try:
        generator = chat.stream_chat(req.messages)

        async def event_stream():
            for chunk in generator:
                if chunk.content:
                    yield f"data: {chunk.content}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Prompt 模板 ----------

@app.get("/api/prompts")
async def list_prompts():
    """获取可用 Prompt 模板列表 - 文章 2.2"""
    return {"templates": prompts.get_available_templates()}


@app.post("/api/prompts/apply")
async def apply_prompt(req: PromptTemplateRequest):
    """应用 Prompt 模板并调用 LLM"""
    try:
        result = prompts.run_template_with_llm(req.template_id, req.variables)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 链式调用 ----------

@app.get("/api/chains")
async def list_chains():
    """获取可用链列表 - 文章 2.3"""
    return {"chains": chains.get_available_chains()}


@app.post("/api/chains/run")
async def run_chain(req: ChainRequest):
    """运行指定的链"""
    try:
        if req.chain_id == "brainstorm":
            result = chains.brainstorm_and_evaluate(req.variables.get("topic", ""))
        elif req.chain_id == "code_gen_opt":
            result = chains.generate_and_optimize(
                req.variables.get("language", ""),
                req.variables.get("description", ""),
            )
        else:
            raise HTTPException(status_code=400, detail=f"未知的链ID: {req.chain_id}")
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- RAG 文档问答 ----------

@app.post("/api/rag/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
):
    """上传文档到知识库 - 文章 2.4"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    supported_ext = (".txt", ".md", ".pdf", ".py", ".js", ".ts", ".jsx", ".tsx")
    ext = Path(file.filename).suffix.lower()
    if ext not in supported_ext:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，支持: {supported_ext}")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = rag.add_document_to_knowledge_base(tmp_path, collection_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.post("/api/rag/query")
async def query_knowledge(req: RAGQueryRequest):
    """基于知识库进行问答（RAG）"""
    try:
        result = rag.query_knowledge_base(req.question, req.collection_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/files")
async def list_knowledge_files():
    """列出知识库中的文件"""
    return {"files": rag.list_knowledge_files()}


@app.get("/api/rag/collections")
async def list_collections():
    """列出所有知识库集合"""
    return {"collections": rag.list_collections()}


# ========== 启动入口 ==========

if __name__ == "__main__":
    import uvicorn

    # 确保必要目录存在
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

    print(f"  Backend: http://{APP_HOST}:{APP_PORT}")
    print(f"  API Docs: http://{APP_HOST}:{APP_PORT}/docs")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
