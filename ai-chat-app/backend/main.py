"""
AI Chat 应用 —— FastAPI 后端
=============================
提供 SSE 流式聊天接口，支持 OpenAI 兼容 API。
同时内置一个离线模拟模式，无需 API Key 也能运行。

启动：uvicorn main:app --reload --port 8000
"""

import os
import json
import asyncio
import logging
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

# ====================== 日志 ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ai-chat")


# ====================== FastAPI 应用 ======================

app = FastAPI(
    title="AI Chat API",
    description="一个支持流式输出的 AI 聊天后端，基于 FastAPI + SSE",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite / Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================== 中间件 ======================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录每个请求"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


# ====================== 数据模型 ======================

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    history: list[ChatMessage] = Field(default_factory=list, description="对话历史")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = Field(default=True, description="是否流式输出")


class HealthResponse(BaseModel):
    status: str
    mode: str  # "openai" 或 "mock"
    model: str


# ====================== 路由 ======================

@app.get("/", response_model=HealthResponse)
async def root():
    """健康检查 + 运行模式"""
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "running",
        "mode": "openai" if has_api_key else "mock",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


# ====================== 流式聊天端点 ======================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """聊天接口 —— 支持流式和非流式"""
    if request.stream:
        return StreamingResponse(
            _stream_chat(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        content = await _chat_non_stream(request)
        return {"reply": content, "model": request.model}


# ====================== 核心聊天逻辑 ======================

async def _chat_non_stream(request: ChatRequest) -> str:
    """非流式聊天"""
    full_response = ""
    async for token in _generate_response(request):
        full_response += token
    return full_response


async def _stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """SSE 流式输出"""
    try:
        # 发送开始信号
        yield _sse_event({"status": "started", "model": request.model})
        
        # 逐 token 输出
        async for token in _generate_response(request):
            yield _sse_event({"token": token, "done": False})
        
        # 发送结束信号
        yield _sse_event({"done": True})
        
    except Exception as e:
        logger.error(f"流式输出错误: {e}")
        yield _sse_event({"error": True, "message": str(e)})


async def _generate_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """生成回复 —— 优先使用 OpenAI API，否则使用模拟模式"""
    if os.getenv("OPENAI_API_KEY"):
        async for token in _openai_stream(request):
            yield token
    else:
        async for token in _mock_stream(request):
            yield token


# ====================== OpenAI API 调用 ======================

async def _openai_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    """通过 OpenAI 兼容 API 获取流式响应"""
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
        
        # 构建消息列表
        messages = _build_messages(request)
        
        # 调用流式 API
        stream = await client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            stream=True,
        )
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
                
    except ImportError:
        logger.warning("未安装 openai 库，切换到模拟模式。安装: pip install openai")
        async for token in _mock_stream(request):
            yield token
    except Exception as e:
        logger.error(f"OpenAI API 调用失败: {e}")
        yield f"\n\n[API 错误: {str(e)}]"


# ====================== 模拟模式（无需 API Key） ======================

_MOCK_RESPONSES = {
    "python": (
        "Python 是一门非常优雅的编程语言！\n\n"
        "作为前端开发者转 AI，你已经有了很好的基础：\n"
        "1. **语法相似性**：Python 的 async/await、类型标注和 JS/TS 很像\n"
        "2. **生态丰富**：FastAPI、LangChain、PyTorch 等框架让 AI 开发变得简单\n"
        "3. **学习曲线平缓**：Python 以简洁著称，入门很快\n\n"
        "建议先从 FastAPI + OpenAI API 开始，快速构建你的第一个 AI 应用！"
    ),
    "fastapi": (
        "FastAPI 是一个现代高性能的 Python Web 框架。\n\n"
        "核心特点：\n"
        "- 原生 async/await，性能接近 Node.js\n"
        "- 自动生成 OpenAPI/Swagger 文档（/docs）\n"
        "- 基于 Pydantic 的请求校验\n"
        "- 支持 WebSocket 和 SSE 流式响应\n\n"
        "非常适合用来构建 AI 应用的后端！"
    ),
    "rag": (
        "RAG（Retrieval-Augmented Generation）是当前 AI 应用开发的核心技术。\n\n"
        "流程：\n"
        "1. 文档切片 → 生成 Embedding → 存入向量数据库\n"
        "2. 用户提问 → 生成问题 Embedding → 向量检索\n"
        "3. 将检索结果拼入 Prompt → LLM 生成答案\n\n"
        "这能有效解决 LLM 的「知识截止」和「幻觉」问题！"
    ),
}

async def _mock_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    """模拟 LLM 流式输出 —— 用于离线开发调试"""
    msg = request.message.lower()
    
    # 查找匹配的预设回复
    reply = None
    for keyword, response in _MOCK_RESPONSES.items():
        if keyword in msg:
            reply = response
            break
    
    if not reply:
        reply = (
            f"你好！你问的是：「{request.message}」\n\n"
            f"这是一个**离线模拟回复**。配置 OpenAI API Key 后可获得真实 AI 回复。\n\n"
            f"配置方法：在 `backend/.env` 文件中设置：\n"
            f"```\nOPENAI_API_KEY=sk-your-key-here\n```\n\n"
            f"支持 OpenAI 及所有兼容接口（DeepSeek、Qwen、GLM 等）。"
        )
    
    # 逐字输出，模拟 ChatGPT 的打字效果
    for char in reply:
        await asyncio.sleep(0.03)  # 模拟 token 生成延迟
        yield char


# ====================== 工具函数 ======================

def _build_messages(request: ChatRequest) -> list[dict]:
    """构建发送给 LLM 的消息列表"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个友善、知识渊博的 AI 助手，特别擅长帮助开发者学习 Python 和 AI 技术。"
                "用中文回答，使用 Markdown 格式使回答更易读。"
            ),
        }
    ]
    
    # 添加历史消息
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # 添加当前消息
    messages.append({"role": "user", "content": request.message})
    
    return messages


def _sse_event(data: dict) -> str:
    """将 dict 转换为 SSE 格式"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ====================== 错误处理 ======================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未捕获的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": "服务器内部错误"},
    )


# ====================== 启动入口 ======================

if __name__ == "__main__":
    import uvicorn
    
    mode = "OpenAI API" if os.getenv("OPENAI_API_KEY") else "模拟模式"
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║       AI Chat API 已启动                     ║
    ║                                               ║
    ║  📡 API:    http://localhost:8000             ║
    ║  📖 文档:   http://localhost:8000/docs        ║
    ║  🔧 模式:   {mode:<35}║
    ║                                               ║
    ║  前端需运行在 http://localhost:5173           ║
    ╚══════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
