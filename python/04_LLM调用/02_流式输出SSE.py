"""
SSE（Server-Sent Events）流式输出详解
=================================================================

这是 AI 聊天应用最核心的交互体验 —— ChatGPT 那样的逐字输出效果。
技术本质：HTTP 长连接 + 增量数据推送。

前端对比：
- JS EventSource API 可以直接消费 SSE
- 或者用 fetch + ReadableStream（更灵活）
"""

import asyncio
import json
from typing import AsyncGenerator


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
        await asyncio.sleep(delay)  # 模拟 token 生成耗时
        yield char


# ======================== 3. 转换为 SSE 格式 ========================

async def to_sse_format(
    token_stream: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
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
        client = AsyncOpenAI()
        
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "用3句话介绍FastAPI"}],
            stream=True,
        )
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                data = json.dumps({
                    "content": delta.content,
                    "finish_reason": chunk.choices[0].finish_reason,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except ImportError:
        yield f"data: {json.dumps({'error': '请安装 openai 库'})}\n\n"


# ======================== 5. 前端消费 SSE 的代码（供参考） ========================

"""
=== JavaScript/React 前端代码 ===

方式一：使用 EventSource（最简单，但不能 POST）

const eventSource = new EventSource('/api/chat/stream');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.done) {
        eventSource.close();
    } else {
        setContent(prev => prev + data.content);
    }
};

方式二：使用 fetch + ReadableStream（推荐，支持 POST）

async function streamChat(message) {
    const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                if (data.done) return;
                setContent(prev => prev + data.content);
            }
        }
    }
}

=== Vercel AI SDK（强烈推荐！）===

import { useChat } from 'ai/react';

function ChatComponent() {
    const { messages, input, handleInputChange, handleSubmit } = useChat({
        api: '/api/chat/stream',
    });
    
    return (
        <div>
            {messages.map(m => <div key={m.id}>{m.content}</div>)}
            <form onSubmit={handleSubmit}>
                <input value={input} onChange={handleInputChange} />
            </form>
        </div>
    );
}
"""


# ======================== 6. 完整的 SSE 聊天服务示例 ========================

async def full_sse_chat_service():
    """一个完整的 SSE 聊天流程 Demo
    
    包含：
    - 发送思考状态
    - 逐 token 返回
    - 返回元数据（token 数、模型等）
    """
    user_message = "什么是 RAG？"
    
    # 阶段1：发送"正在思考"状态
    yield f"data: {json.dumps({'status': 'thinking'})}\n\n"
    await asyncio.sleep(0.5)
    
    # 阶段2：逐 token 返回
    reply = "RAG（检索增强生成）是一种结合了信息检索和文本生成的技术..."
    for i, char in enumerate(reply):
        await asyncio.sleep(0.03)
        yield f"data: {json.dumps({'token': char, 'index': i})}\n\n"
    
    # 阶段3：返回元数据
    yield f"data: {json.dumps({
        'done': True,
        'model': 'gpt-4o-mini',
        'usage': {'prompt_tokens': 15, 'completion_tokens': 42},
    })}\n\n"


# ======================== 7. 错误处理 + SSE ========================

async def sse_with_error_handling():
    """在 SSE 流中优雅地传递错误"""
    try:
        # 模拟处理过程中的错误
        await asyncio.sleep(1)
        raise ValueError("模型服务暂时不可用")
        
    except Exception as e:
        # 把错误也作为 SSE 事件发送
        error_data = json.dumps({
            "error": True,
            "message": str(e),
            "code": "LLM_ERROR",
        }, ensure_ascii=False)
        yield f"data: {error_data}\n\n"


# ======================== 运行 Demo ========================

async def main():
    print("=== SSE 流式输出 Demo ===\n")
    
    # 演示模拟 token 流
    print("1. 模拟 LLM 流式输出:")
    async for token in simulate_llm_stream("Hello, AI 开发者！"):
        print(token, end="", flush=True)
    print("\n")
    
    # 演示 SSE 格式转换
    print("2. SSE 格式输出（原始格式）:")
    token_stream = simulate_llm_stream("Python很有趣", delay=0.1)
    async for sse_chunk in to_sse_format(token_stream):
        print(sse_chunk, end="")
    print()
    
    # 演示完整流程
    print("3. 完整 SSE 聊天服务:")
    async for event in full_sse_chat_service():
        if "thinking" in event:
            print("💭 思考中...")
        elif "token" in event:
            data = json.loads(event[6:].strip())
            print(data["token"], end="", flush=True)
        elif "done" in event:
            data = json.loads(event[6:].strip())
            if data.get("done"):
                print(f"\n✅ 完成 (tokens: {data.get('usage', {}).get('completion_tokens', '?')})")


if __name__ == "__main__":
    asyncio.run(main())
