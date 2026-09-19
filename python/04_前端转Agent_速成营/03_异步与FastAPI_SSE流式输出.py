# 03_异步与FastAPI_SSE流式输出.py

"""
第 6-7 天：FastAPI 与 SSE 流式响应
对标前端：Express/NestJS 中的 async route + res.write()
重要性：⭐⭐⭐⭐⭐ (极高)
AI 聊天界面必须要有“打字机”效果，这就要求后端必须提供 SSE (Server-Sent Events) 接口。
FastAPI 是目前 Python 最火的异步 Web 框架。

运行方式：
uv run uvicorn 03_异步与FastAPI_SSE流式输出:app --reload --port 8000
"""

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AI Agent Backend API")

# 配置跨域 (前端本地开发必备)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 定义请求体结构 (使用 Pydantic)
class ChatRequest(BaseModel):
    message: str
    stream: bool = True

# 模拟一个大模型的异步生成器
async def fake_llm_generator(prompt: str):
    """
    这是一个异步生成器 (Async Generator)，对应 JS 的 async generator。
    在 Python 里，用 yield 返回中间结果。
    """
    mock_reply = f"收到你的消息：'{prompt}'。我是一个模拟的 AI Agent，正在逐字给你回复..."
    
    for char in mock_reply:
        # asyncio.sleep(0.05) 模拟网络延迟或模型生成延迟 (注意千万不能用 time.sleep，会阻塞整个事件循环)
        await asyncio.sleep(0.05)
        
        # SSE (Server-Sent Events) 的标准格式： "data: 内容\n\n"
        yield f"data: {char}\n\n"
        
    yield "data: [DONE]\n\n"


# 2. 定义流式接口
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    处理聊天的接口。根据前端请求决定是否使用流式返回。
    """
    if request.stream:
        # 如果要求流式，返回 StreamingResponse，传入异步生成器
        # media_type 必须是 text/event-stream，这样前端才能通过 Fetch/EventSource 解析
        return StreamingResponse(
            fake_llm_generator(request.message),
            media_type="text/event-stream"
        )
    else:
        # 非流式直接返回 JSON
        return {"reply": f"收到你的消息：{request.message}。这是非流式一次性返回。"}


# 3. 健康检查接口
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}

# ---
# 前端调用示例 (在 JS 中)：
# const response = await fetch("http://localhost:8000/api/chat", {
#     method: "POST",
#     headers: { "Content-Type": "application/json" },
#     body: JSON.stringify({ message: "Hello", stream: true })
# });
# const reader = response.body.getReader();
# // 然后在一个 while(true) 循环里 reader.read() 即可读取流式块
