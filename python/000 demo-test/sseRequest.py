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
    allow_origin=["*"]
)
# ======================== 1. 后端 SSE 接口 (FastAPI) ========================
async def fake_ai_streamer(prompt: str):
    response_text = f"关于【{prompt}】的回答：人工智能（AI）正在迅速改变世界..."

    for char in response_text:
        await asyncio.sleep(0.1)
        yield f"data: {char}\\n\\n"
    
    yield "data： [DONE]\\n\\n"

@app.get('/api/chat/stream')
async def chat_stream(prompt: str = "default question"):
    return StreamingResponse(
        fake_ai_streamer(prompt),
        media_type="text/event-stream"
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run('SSE流失输出', host="127.0.0.1", port=8080, reload=True)