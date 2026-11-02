import requests
from typing import Optional, Any

def demo_request_basic():
    response = requests.get(
        "https://httpbin.org/get",
        params={"name": "张三", "age": 30},
        timeout=10
    )
    print(f"Get状态码： {response.status_code}")
    print(f"响应体： {response.json()}")

    # POST请求
    response1 = requests.post(
       "https://httpbin.org/post",
       json={"message": "Hello，AI！"},
       timeout=10,
    )
    print(f"Get状态码： {response1.status_code}")
    print(f"响应体： {response1.json()}"
    )
# ======================== 3. requests 流式响应（LLM SSE 的基础） ========================
def demo_requests_stream():
    response = requests.get(
        "https://httpbin.org/stream/5",
        stream=True,
        timeout=10
    )
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            print(f"收到 chunk: {chunk.strip()}")

# ======================== 4. httpx 异步客户端（推荐用于 AI 开发） ========================
# pyrefly: ignore[missing-import]
import httpx
async def demo_httpx_async():
    async with httpx.AsyncClient(timeout=30.0) as client:
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
        response1 = await asyncio.gather(*tasks, return_exceptions=True)

        for i, resp in enumerate(response1):
            if isinstance(resp, Exception):
                print(f"请求{i}失败：{resp}")
            else:
                print(f"请求{i}完成：{resp.status_code}")
    
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

if __name__ == "__main__":
    # 运行同步示例
    print("=== requests 基础 ===")
    demo_request_basic()
    print("===requests 流式响应（LLM SSE 的基础===")
    # demo_requests_stream()
    import asyncio
    asyncio.run(demo_httpx_async())

    asyncio.run(call_openai_chat_stream())