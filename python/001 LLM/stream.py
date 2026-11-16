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
        await asyncio.sleep(delay)
        yield char



async def main():
    print("=== SSE 流式输出 Demo ===\n")
    # 演示模拟 token 流
    print("1. 模拟 LLM 流式输出:")


if __name__ == "__main__":
    asyncio.run(main())