"""
前端转全栈 02: 全栈 AI 流式打字机响应 (Server-Sent Events / SSE)
==================================================================
在 ChatGPT / DeepSeek 等 AI 应用中，全栈开发最关键的技术就是【流式响应 (Streaming Response)】。
前端不需要等待整个几千字的回答生成完，而是像打字机一样逐字实时渲染。

前端通信规范:
- HTTP 协议: `text/event-stream` (SSE) 或 `fetch()` 结合 `ReadableStream`
后端实现框架:
- FastAPI `StreamingResponse` + 异步生成器 (`async def generate()`)

运行方法：
1. 启动服务: python 02_全栈AI流式打字机_SSE后端实现.py
2. 在浏览器中打开测试前端页面进行实时调优与打字效果体验！
"""

import asyncio
import json
import time
from typing import AsyncGenerator

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 尚未安装 `fastapi` 和 `uvicorn`。可以通过 `pip install fastapi uvicorn` 安装。")


if HAS_FASTAPI:
    app = FastAPI(title="AI 流式打字机全栈 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class ChatRequest(BaseModel):
        prompt: str
        model: str = "deepseek-chat"


    # === 1. 核心: 异步生成器 (模拟大模型逐字吐出 Token) ===
    async def ai_stream_generator(user_prompt: str) -> AsyncGenerator[str, None]:
        """
        这个函数扮演大模型 API 调用的角色 (例如调用 OpenAI / DeepSeek API 的 stream=True)
        每次 yield 吐出一段符合 SSE 格式的数据: `data: {...}\n\n`
        """
        welcome_prefix = f"收到您的提问：'{user_prompt}'。\n我是 Python FastAPI 全栈 AI 助手，正在为您逐字生成回答：\n\n"
        answer_body = (
            "1. 作为前端开发者转型全栈，掌控 SSE 流式输出是极其关键的一环。\n"
            "2. 后端使用 FastAPI 的 `StreamingResponse` 搭配 `async generator` 实现高并发不阻塞。\n"
            "3. 前端使用 `fetch()` 的 `response.body.getReader()` 进行分块解析与 React/Vue 视图更新。\n"
            "4. 掌握了这个模式，你就具备了搭建独立 ChatGPT / DeepSeek UI 全栈应用的能力！"
        )
        
        full_text = welcome_prefix + answer_body
        
        # 逐字吐出 (模拟大模型打字)
        for char in full_text:
            await asyncio.sleep(0.04)  # 40ms 延迟，打字机节奏
            
            # SSE 协议格式要求: 每条消息以 `data: ` 开头，以 `\n\n` 结尾
            payload = json.dumps({"content": char, "timestamp": time.time()}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        
        # 结束标志 (很多 AI 接口约定以 [DONE] 代表流结束)
        yield "data: [DONE]\n\n"


    # === 2. SSE 接口路由 ===
    @app.post("/api/chat/stream")
    async def chat_stream_endpoint(body: ChatRequest):
        print(f"收到前端流式请求 Prompt: {body.prompt}")
        
        # 必须指定 media_type="text/event-stream"
        return StreamingResponse(
            ai_stream_generator(body.prompt),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no", # 禁用 Nginx 缓存，保证即时传输
            }
        )

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动流式 API 服务器: http://127.0.0.1:8000")
        print("📡 SSE 流式接口地址: POST http://127.0.0.1:8000/api/chat/stream")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        print("缺少依赖，无法启动。")
