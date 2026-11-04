# 需要安装：pip install openai
# pyrefly: ignore [missing-import]
from openai import OpenAI
import os
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)

load_dotenv(find_dotenv())

api_key = os.getenv("AI_API_KEY")
base_url = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL_NAME")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

def chat_basic():
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个幽默的 AI 助手。"},
                {"role": "user", "content": "请用一句话解释什么是量子力学。"}
            ],
            temperature=0.7,
            max_tokens=100
        )

        answer = response.choices[0].message.content
        print(f"AI 的回答：\\n{answer}")
    
    except Exception as e:
        print(f"请求失败：{e}")

async def fake_ai_streamer(streamer: str):
    """
    这是一个生成器函数 (Generator)，使用 yield 关键字。
    SSE 的标准格式是：每一行数据以 "data: " 开头，以 "\\n\\n" 结尾。
    """
    response_text = streamer
    
    for char in response_text:
        # 模拟模型生成每个字的延迟
        await asyncio.sleep(.1)
        # 必须严格遵守 SSE 数据格式规范
        yield f"{char}"
        
    # 通常会发送一个特殊的标记告诉前端结束了
    yield ""

@app.get("/api/chatAI/stream")
def chat_stream():
    print("\\n--- 发送流式对话请求 (打字机效果) ---")
    try:
        response_stream = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "user", "content": "写一首描写赛博朋克城市的短诗。"}
            ],
            stream=True
        )
        print("AI 的回答: ", end="")
        contentT = ''
        for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                contentT += content
                print(content, end="", flush=True)
        
        
        return StreamingResponse(
            fake_ai_streamer(contentT), 
            media_type="text/event-stream"
        )

    except Exception as e:
         print(f"\\n请求失败: {e}")


if __name__ == "__main__":
    print("注意：要运行此脚本，请先设置好真实的 API_KEY")
    # chat_basic()
    # chat_stream()
    import uvicorn
    uvicorn.run('demo_ai_api:app', host="127.0.0.1", port=8080, reload=True)