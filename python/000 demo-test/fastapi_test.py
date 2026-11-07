
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Query, Depends
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
import asyncio
import json
import os
from dotenv import load_dotenv, find_dotenv

# 创建FastAPI 应用
app = FastAPI(
    title = "AI 应用Demo API",
    description="一个用于学习 FastAPI + AI 的示例项目",
    version="0.1.0",
)
load_dotenv(find_dotenv())
api = os.getenv("AI_API_KET")
base_url = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL_NAME")

# 建议路由
@app.get('/')
async def root():
    return {"message": "Hello, AI Developer!", "status": "ok"}

@app.get('/health')
async def health_check():
    """健康检查接口 —— 部署时必备"""
    return {"status": "healthy", "version": "0.1.0"}


# 路径参数
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    users = {1: "Alice", 2: "Bob", 3: "Charlie"}
    if user_id not in users:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user_id, "name": users[user_id]}

# ======================== 4.  查询参数 ========================

@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=100, description="返回数量"),
    model: str = Query(default=AI_MODEL, description="使用的模型"),
):
    """查询参数 —— /search?q=python&limit=20&model=gpt-4"""
    return {"query": q, "limit": limit, "model": model, "results": []}



# ======================== 5. POST + Pydantic 请求体 ========================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default=AI_MODEL)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=4000)

class ChatResponse(BaseModel):
    reply: str
    model: str
    tokens_used: int

@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口 —— POST /chat，请求体是 JSON
    
    FastAPI 自动：
    1. 校验请求体是否符合 ChatRequest
    2. 校验响应是否符合 ChatResponse
    3. 生成 /docs 中的 Schema
    """
    await asyncio.sleep(1)
    return ChatResponse(
        reply=f"你说的是：{request.message}. 这是一个模拟回复。",
        model=request.model,
        tokens_used=len(request.message) + 50   
    )

# ========== 流式响应SSE =============
async def generate_stream_response(message: str):
    """生成器函数：逐字产出 token —— 模拟 ChatGPT 的流式输出
    SSE 格式：data: {json}\n\n
    """
    reply = f"这是对「{message}」的流式回答，每个字逐个输出，就像chatGPT一样"

    for i, chat in enumerate(reply):
        await asyncio.sleep(.5)
        chunk = {
            "index": i,
            "content": chat,
            "done": False
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
            "Conoention": "keep-alive",
            "X-Accel-Buffering": "no" # Nginx 代理时关缓冲
        }
    )

# ======================== 7. 依赖注入（Dependency Injection） ========================
def get_api_key():
    import os
    api_key = os.getenv('AI_API_KET', "demo-key")
    return api_key

@app.get('/check-auth')
async def check_auth(api_key: str = Depends(get_api_key)):
    is_valid = api.key.startsWith('sk-')
    return {"authticated": is_valid, "key_prefix": api_key[:10] + "..."}
    

# ======================== 8. 中间件（Middleware） ========================
from fastapi.middleware.cors import CORSMiddleware
# CORS 配置 —— 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:30000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware('http')
async def add_process_time_header(request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = str(process_time)
    return response

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

    """
    reload: 重启
    """
    uvicorn.run("fastapi_test:app", host="192.168.31.135", port=8080, reload=True)
