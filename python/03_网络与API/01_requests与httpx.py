"""
HTTP 请求：requests 库（同步）vs httpx 库（异步）
=================================================================

对比 JS：
- requests  ≈  axios（同步版本）/ fetch（但同步）
- httpx      ≈  axios（支持 async/await）

AI 开发中：
- 简单脚本、Jupyter Notebook → requests 够用
- 生产级服务、FastAPI → httpx 异步版本
"""

import requests
from typing import Optional, Any


# ======================== 1. requests 基础 ========================

def demo_requests_basic():
    """requests 基本 CRUD"""
    
    # GET 请求
    response = requests.get(
        "https://httpbin.org/get",
        params={"name": "张三", "age": 30},  # URL 查询参数
        timeout=10,  # 超时非常重要！
    )
    print(f"GET 状态码: {response.status_code}")
    print(f"响应体: {response.json()}")
    
    # POST 请求
    response = requests.post(
        "https://httpbin.org/post",
        json={"message": "Hello, AI!"},  # 自动设 Content-Type: application/json
        timeout=10,
    )
    
    # 自定义 Headers
    response = requests.get(
        "https://httpbin.org/headers",
        headers={
            "Authorization": "Bearer sk-xxx",
            "User-Agent": "MyAIApp/1.0",
        },
        timeout=10,
    )


# ======================== 2. requests Session（复用连接） ========================

def demo_requests_session():
    """Session 保持连接，减少 TCP 握手开销 —— 类似浏览器的 keep-alive"""
    session = requests.Session()
    
    # 设置全局 headers
    session.headers.update({
        "Authorization": "Bearer sk-xxx",
        "User-Agent": "MyAIApp/1.0",
    })
    
    # 设置重试策略
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retry_strategy = Retry(
        total=3,                  # 最多重试 3 次
        backoff_factor=1,         # 退避因子：1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码才重试
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    
    try:
        response = session.get("https://httpbin.org/get", timeout=10)
        print(f"Session GET: {response.status_code}")
    finally:
        session.close()


# ======================== 3. requests 流式响应（LLM SSE 的基础） ========================

def demo_requests_stream():
    """流式读取响应 —— 理解 LLM 流式输出的底层原理"""
    response = requests.get(
        "https://httpbin.org/stream/5",
        stream=True,  # 关键：启用流式
        timeout=10,
    )
    
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            print(f"收到 chunk: {chunk.strip()}")


# ======================== 4. httpx 异步客户端（推荐用于 AI 开发） ========================

import httpx

async def demo_httpx_async():
    """httpx 异步用法 —— 和 requests 几乎一样的 API，但支持 async/await"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 基本 GET
        response = await client.get(
            "https://httpbin.org/get",
            params={"query": "test"},
        )
        print(f"httpx 状态码: {response.status_code}")
        
        # 并发请求（这才是 httpx 的真正威力）
        urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2",
            "https://httpbin.org/delay/1",
        ]
        
        import asyncio
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                print(f"请求 {i} 失败: {resp}")
            else:
                print(f"请求 {i} 完成: {resp.status_code}")


# ======================== 5. httpx 流式响应 ========================

async def demo_httpx_stream():
    """httpx 流式响应 —— FastAPI 中调用 LLM 的标配"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", "https://httpbin.org/stream/3") as response:
            async for line in response.aiter_lines():
                if line:
                    print(f"httpx 流式: {line}")


# ======================== 6. 实战：模拟 OpenAI API 调用 ========================

async def call_openai_chat(
    api_key: str,
    messages: list[dict],
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
) -> dict:
    """用 httpx 直接调用 OpenAI Chat API（不用 openai 库）"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
            },
        )
        response.raise_for_status()  # 非 2xx 抛异常
        return response.json()


async def call_openai_chat_stream(
    api_key: str,
    messages: list[dict],
    model: str = "gpt-4o-mini",
):
    """流式调用 —— 逐 token 返回，就像 ChatGPT 打字效果"""
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "stream": True,  # 关键
            },
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # 去掉 "data: " 前缀
                    if data == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]


# ======================== 7. 使用 openai 官方库（推荐） ========================

"""
安装：pip install openai

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-xxx")

# 普通调用
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "你好"}],
)
print(response.choices[0].message.content)

# 流式调用
stream = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "讲个故事"}],
    stream=True,
)
async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
"""


if __name__ == "__main__":
    # 运行同步示例
    print("=== requests 基础 ===")
    demo_requests_basic()
    
    print("\n=== requests 流式 ===")
    demo_requests_stream()
    
    # 运行异步示例
    import asyncio
    
    print("\n=== httpx 异步 ===")
    asyncio.run(demo_httpx_async())
    
    print("\n=== httpx 流式 ===")
    asyncio.run(demo_httpx_stream())
