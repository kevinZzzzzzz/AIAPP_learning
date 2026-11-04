# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
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
        await asyncio.sleep(.1)
        # 必须严格遵守 SSE 数据格式规范
        yield f"{char}"
        
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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run('sseRequest:app', host="127.0.0.1", port=8080, reload=True)