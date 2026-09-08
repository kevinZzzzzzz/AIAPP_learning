"""
网络与 API：Server-Sent Events (SSE) 流式传输

在开发 AI 应用时，大模型生成几百个字可能需要 10 秒钟。
如果等 10 秒再把结果一次性返回给前端，用户体验会极差。
目前的行业标准解决方案是：使用 SSE (Server-Sent Events) 实现“打字机”流式效果。

【与 WebSocket 的区别】
- WebSocket: 全双工（双向通信），常用于聊天室、实时游戏。较重。
- SSE: 单向通信（服务器单向推送给客户端），基于标准 HTTP 协议。对于 AI 对话（前端发一次请求，后端源源不断吐出文字）来说是最完美的方案。
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

# ======================== 1. 后端 SSE 接口 (FastAPI) ========================

async def fake_ai_streamer(prompt: str):
    """
    这是一个生成器函数 (Generator)，使用 yield 关键字。
    SSE 的标准格式是：每一行数据以 "data: " 开头，以 "\\n\\n" 结尾。
    """
    response_text = f"关于【{prompt}】的回答：人工智能（AI）正在迅速改变世界..."
    
    for char in response_text:
        # 模拟模型生成每个字的延迟
        await asyncio.sleep(0.1)
        # 必须严格遵守 SSE 数据格式规范
        yield f"data: {char}\\n\\n"
        
    # 通常会发送一个特殊的标记告诉前端结束了
    yield "data: [DONE]\\n\\n"


@app.get("/api/chat/stream")
async def chat_stream(prompt: str = "默认问题"):
    """
    使用 StreamingResponse 返回生成器，并设置正确的 Content-Type 为 text/event-stream
    """
    return StreamingResponse(
        fake_ai_streamer(prompt), 
        media_type="text/event-stream"
    )

# ======================== 2. 前端 JS 客户端示例 ========================
"""
在前端，你可以使用原生的 EventSource API，或者 fetch API 来接收 SSE。

【使用 fetch 接收 SSE 的 JS 示例代码】:

async function startStream() {
    const response = await fetch('http://localhost:8000/api/chat/stream?prompt=你好');
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码收到的块
        const chunk = decoder.decode(value);
        
        // 解析 "data: xxx\\n\\n" 格式
        const lines = chunk.split('\\n');
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                    console.log('流结束');
                    return;
                }
                // 这里将收到的文字追加到页面上
                process.stdout.write(data); 
            }
        }
    }
}
"""

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("02_SSE流式输出:app", host="127.0.0.1", port=8000, reload=True)
