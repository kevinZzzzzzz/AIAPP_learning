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
        # print(f"{i}-----{char}\n")
        await asyncio.sleep(delay)
        yield char


# ======================== 3. LLM流式token流 转换为 SSE 格式 ========================
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
        client = AsyncOpenAI(
            api_key=ai_api_key,
            base_url=ai_base_url
        )
        stream = await client.chat.completions.create(
            model=api_model_name,
            messages=[{"role": "user", "content": "用三句话介绍一下FastAPI"}],
            stream=True
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            # print(f"{delta}")
            if delta.content:
                data = json.dumps({
                    "content": delta.content,
                    "finish_reason": chunk.choices[0].finish_reason
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"
    except ImportError:
        yield f"data: {json.dumps({'error': '请安装openai库'})}\n\n"

# ======================== 6. 完整的 SSE 聊天服务示例 ========================
async def full_sse_chat_service():
    """一个完整的 SSE 聊天流程 Demo
    
    包含：
    - 发送思考状态
    - 逐 token 返回
    - 返回元数据（token 数、模型等）
    """
    user_message = "什么是 RAG?"
    
    # 阶段1：发送"正在思考"状态
    yield f"data: {json.dumps({'status': 'thinking'})}\n\n"
    await asyncio.sleep(1)

    # 阶段2：逐 token 返回
    reply = "RAG (检索增强生成) 是一种结合了信息检索和文本生成的技术..."
    for i, char in enumerate(reply):
        await asyncio.sleep(0.3)
        yield f"data: {json.dumps({'token': char, 'index': i})}\n\n"
    meta = {
        'done': True,
        'model': api_model_name,
        'usage': {'promt_token': 15, 'completion_tokens': 42},
    }
    # 阶段3：返回元数据
    yield f"data: {json.dumps(meta)}\n\n"




async def main():
    print("=== SSE 流式输出 Demo ===\n")
    # 演示模拟 token 流
 #    print("1. 模拟 LLM 流式输出:")
    # print(f"{simulate_llm_stream('hello, AI 开发者')}")
    # async for token in simulate_llm_stream("hello, AI 开发者"):
    #     print(f"{token}\n", end="", flush=True)

        
    # 演示 SSE 格式转换
    print("2. SSE 格式输出（原始格式）:")
    # token_stream = simulate_llm_stream("Python很有趣", delay=0.1)
    # async for sse_chunk in to_sse_format(token_stream):
    #     print(sse_chunk, end="")

    print("从 OpenAI SDK 获取 SSE 流")
    # token_stream2 = openai_stream_to_sse()
    # async for sse_chunk in token_stream2:
    #     print(f"{sse_chunk}", end="")
    # print()
    
    # 演示完整流程
    print("3. 完整 SSE 聊天服务:")
    async for event in full_sse_chat_service():
        print(f'event: {event}')
        if not event.startswith('data: '):
            continue
        data = json.loads(event[6:].strip())
        if "thinking" in event:
            print("💭 思考中...")
        elif "token" in data:
            print(f'{data["token"]}\n', end="", flush=True)
        elif "done" in data:
            if data.get("done"):
                print(f"\n✅完成(tokens: {data.get('usage', {}).get('completion_tokens', '?')})")

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())