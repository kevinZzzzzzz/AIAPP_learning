"""
FastAPI 入门实战 —— 搭建 AI 应用的后端接口
=================================================================

FastAPI 是 Python 最流行的现代 Web 框架，特点和优势：
- 原生 async/await 支持 → 适合 AI 应用（大量 IO 等待）
- 自动生成 OpenAPI/Swagger 文档 → /docs 路由直接看
- 基于 Pydantic → 请求/响应自动校验
- 性能 ≈ Node.js（基于 Starlette + Uvicorn）

JS 对比：
- FastAPI ≈ Express.js + TypeScript + Zod + Swagger 插件（一站式）

安装：pip install fastapi uvicorn
运行：uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal
import asyncio
import json

# ======================== 1. 创建 FastAPI 应用 ========================

app = FastAPI(
    title="AI 学习 Demo API",
    description="一个用于学习 FastAPI + AI 的示例项目",
    version="0.1.0",
)


# ======================== 2. 最简路由 ========================

@app.get("/")
async def root():
    """最简 GET 接口 —— 访问 http://localhost:8000/"""
    return {"message": "Hello, AI Developer!", "status": "ok"}


@app.get("/health")
async def health_check():
    """健康检查接口 —— 部署时必备"""
    return {"status": "healthy", "version": "0.1.0"}


# ======================== 3. 路径参数 ========================

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """路径参数 —— FastAPI 自动校验类型
    
    访问: /users/123  ✓（自动转 int）
    访问: /users/abc  ✗（返回 422 校验错误）
    """
    users = {1: "Alice", 2: "Bob", 3: "Charlie"}
    if user_id not in users:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user_id, "name": users[user_id]}


# ======================== 4. 查询参数 ========================

@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=100, description="返回数量"),
    model: str = Query(default="gpt-4o-mini", description="使用的模型"),
):
    """查询参数 —— /search?q=python&limit=20&model=gpt-4"""
    return {"query": q, "limit": limit, "model": model, "results": []}


# ======================== 5. POST + Pydantic 请求体 ========================

class ChatRequest(BaseModel):
    """聊天请求的 Pydantic 模型"""
    message: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0)


class ChatResponse(BaseModel):
    """聊天响应的 Pydantic 模型"""
    reply: str
    model: str
    tokens_used: int


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口 —— POST /chat，请求体是 JSON
    
    FastAPI 自动：
    1. 校验请求体是否符合 ChatRequest
    2. 校验响应是否符合 ChatResponse
    3. 生成 /docs 中的 Schema
    """
    # 这里是模拟，实际会调用 LLM API
    await asyncio.sleep(1)  # 模拟 LLM 延迟
    
    return ChatResponse(
        reply=f"你说的是: {request.message}。这是一个模拟回复。",
        model=request.model,
        tokens_used=len(request.message) + 50,
    )


# ======================== 6. 流式响应（SSE）── AI 聊天的核心 ========================

async def generate_stream_response(message: str):
    """生成器函数：逐字产出 token —— 模拟 ChatGPT 的流式输出
    
    SSE 格式：data: {json}\n\n
    """
    reply = f"这是对「{message}」的流式回复。每个字逐个输出，就像 ChatGPT 一样。"
    
    for i, char in enumerate(reply):
        await asyncio.sleep(0.05)  # 模拟 token 生成延迟
        
        chunk = {
            "index": i,
            "content": char,
            "done": False,
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    # 发送完成标记
    yield f"data: {json.dumps({'done': True})}\n\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口 —— 返回 Server-Sent Events (SSE) 格式
    
    前端用 EventSource 或 fetch + ReadableStream 接收
    """
    return StreamingResponse(
        generate_stream_response(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 代理时关缓冲
        },
    )


# ======================== 7. 依赖注入（Dependency Injection） ========================

def get_api_key():
    """依赖注入：获取 API Key —— FastAPI 的特色功能
    
    和 NestJS 的依赖注入类似，但更轻量
    """
    import os
    api_key = os.getenv("OPENAI_API_KEY", "demo-key")
    return api_key


@app.get("/check-auth")
async def check_auth(api_key: str = Depends(get_api_key)):
    """使用依赖注入获取 API Key"""
    is_valid = api_key.startswith("sk-")
    return {"authenticated": is_valid, "key_prefix": api_key[:10] + "..."}


# ======================== 8. 中间件（Middleware） ========================

from fastapi.middleware.cors import CORSMiddleware

# CORS 配置 —— 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request, call_next):
    """自定义中间件：记录每个请求的处理时间"""
    import time
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ======================== 9. AI 应用路由规划 ========================

# 一个好的 AI 应用后端通常有这么几个路由组：

"""
/api/v1/chat/              → 聊天对话
/api/v1/chat/stream        → 流式聊天
/api/v1/chat/history       → 对话历史
/api/v1/documents/         → 文档管理（上传、列表）
/api/v1/documents/upload   → 上传文件
/api/v1/rag/query          → RAG 问答
/api/v1/agents/run         → 运行 Agent
/api/v1/users/             → 用户管理
/api/v1/auth/              → 认证
"""


# ======================== 10. 启动说明 ========================

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════╗
    ║     FastAPI AI 学习 Demo 已启动          ║
    ║                                          ║
    ║  API 文档: http://localhost:8000/docs    ║
    ║  健康检查: http://localhost:8000/health  ║
    ║                                          ║
    ║  测试命令:                               ║
    ║  curl http://localhost:8000/             ║
    ║  curl http://localhost:8000/users/1      ║
    ║  curl -X POST http://localhost:8000/chat ║
    ║    -H "Content-Type: application/json"   ║
    ║    -d '{"message":"你好"}'               ║
    ╚══════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
