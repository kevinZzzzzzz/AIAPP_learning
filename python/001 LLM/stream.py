"""
SSE（Server-Sent Events）流式输出详解
=================================================================

这是 AI 聊天应用最核心的交互体验 —— ChatGPT 那样的逐字输出效果。
技术本质：HTTP 长连接 + 增量数据推送。

前端对比：
- JS EventSource API 可以直接消费 SSE
- 或者用 fetch + ReadableStream（更灵活）
"""

from anyio.functools import AsyncCacheInfo
import asyncio
import os
import json
from typing import AsyncGenerator
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
ai_api_key = os.getenv("AI_API_KEY")
ai_base_url = os.getenv("AI_BASE_URL")
api_model_name = os.getenv("AI_MODEL_NAME")

# ======================== 1. SSE 协议格式 ========================

"""
SSE 的 HTTP 响应格式：

Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"token": "你", "index": 0}

data: {"token": "好", "index": 1}

data: {"token": "！", "index": 2}

data: [DONE]


规则：
1. 每个消息以 "data: " 开头
2. 消息内容为字符串（通常是 JSON）
3. 消息以 "\n\n" 结尾（双换行）
4. [DONE] 表示流结束（OpenAI 的惯例）
"""

# ======================== 2. 模拟 LLM 流式输出生成器 ========================
async def simulate_llm_stream(text: str, delay: float = 0.05) -> AsyncGenerator[str, None]:
    """模拟 LLM 逐 token 输出
    
    真实场景：这个生成器会被 OpenAI SDK 的 stream 替代
    """
    for i, char in enumerate(text):
        await asyncio.sleep(delay)
        yield char


# ======================== 3. 转换为 SSE 格式 ========================
async def to_sse_format(token_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """把 token 流转换成标准的 SSE 格式字符串
    前端可以直接用 EventSource 或 fetch 消费这个输出
    """
    async for token in token_stream:
        sse_data = json.dumps({"content": token, "done": False}, ensure_ascii=False)
        yield f"data: {sse_data}\n\n"

    # 发送结束标记
    yield f"data: {json.dumps({'done': True})}\n\n"

# ======================== 4. 从 OpenAI SDK 获取 SSE 流 ========================
async def openai_stream_to_sse():
    """把 OpenAI 的 Stream 对象转成 SSE 格式
    
    这是 FastAPI 后端最常见的模式：
    1. 调用 OpenAI streaming API
    2. 把每个 chunk 转成 SSE 格式
    3. 通过 StreamingResponse 返回给前端
    """
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI
        stream = await client.chat.completions.create(
            model=api_model_name,
            messages=[{"role": "user", "content": "用三句话介绍一下FastAPI"}],
            stream=True
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                data = json.dumps({
                    "content": delta.content,
                    "finish_reason": chunk.choices[0].finish_reason
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"
    except ImportError:
        yield f"data: {json.dumps({'error': '请安装openai库'})}\n\n"



async def main():
    print("=== SSE 流式输出 Demo ===\n")
    # 演示模拟 token 流
    print("1. 模拟 LLM 流式输出:")
    async for token in simulate_llm_stream("hello, AI 开发者"):
        print(token, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())