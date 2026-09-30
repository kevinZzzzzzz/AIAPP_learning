"""
Python HTTP 请求与 API 对接 —— JS fetch / axios 对比指南
======================================================
在前端，我们使用 window.fetch() 或 axios 请求后端。
在 Python 中，调 AI 接口、做爬虫或请求第三方服务：
- 同步请求：最常用 `requests` 库 (写法极其人性化)
- 异步请求：最常用 `httpx` 库 (支持 async/await，支持 HTTP/2 和流式 SSE)

运行方法：python 08_HTTP请求与API调用_JS对比.py
"""

from typing import Dict, Any, Optional
import json


# === 1. 同步请求 (requests) 与 JS fetch 的映射 ===
"""
JS Axios 写法:
const response = await axios.post("https://api.openai.com/v1/chat/completions", {
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello" }]
}, {
  headers: { "Authorization": `Bearer ${apiKey}` }
});
console.log(response.data);
"""

def demo_sync_http_requests():
    print("\n--- 1. 同步 HTTP 请求 (requests 模块概念) ---")
    
    # 模拟请求参数
    url = "https://httpbin.org/post"  # httpbin 是专用于测试 HTTP 请求的免费接口
    headers = {
        "Authorization": "Bearer sk-demo-key-123",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "用 Python 写一个 Hello World"}]
    }

    print(f"正在发送 POST 请求至: {url}")

    # 注释说明：在真实环境下安装 requests 后 (pip install requests):
    """
    import requests

    try:
        # requests.post(url, json=payload) 会自动把 Python 字典序列化为 JSON 字符串并添加 Content-Type: application/json！
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # 抛出 HTTP 4xx / 5xx 异常 (相当于 JS 里判断 res.ok)
        response.raise_for_status()
        
        # 解析 JSON (相当于 JS 中的 await res.json() 或 axios res.data)
        data = response.json()
        print("请求成功，收到的 JSON 数据:")
        print(data)

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {e}")
    """
    print("💡 [提示] Python requests 库比 JS fetch 更简洁：用 json=dict 参数即可自动处理序列化！")


# === 2. 异步 HTTP 请求 (httpx) 与 JS fetch/axios 对比 ===
"""
在 FastAPI / LangChain 异步框架中，我们必须使用异步 HTTP 客户端，否则会阻塞事件循环！
推荐使用 `httpx` 库。
"""

async def demo_async_httpx_requests():
    print("\n--- 2. 异步 HTTP 请求 (httpx 模块概念) ---")
    
    """
    import httpx

    # httpx.AsyncClient 相当于 axios.create({ baseURL: ... }) 实例
    async with httpx.AsyncClient(timeout=30.0) as client:
        # GET 请求 (带 Query Params)
        # JS: await client.get("/v1/models", { params: { limit: 10 } });
        res = await client.get("https://httpbin.org/get", params={"limit": 10})
        print("Async GET Status:", res.status_code)
        print("Async GET Response:", res.json())

        # POST 请求
        res_post = await client.post("https://httpbin.org/post", json={"prompt": "Hi"})
        print("Async POST Response:", res_post.json())
    """
    print("💡 [提示] `async with httpx.AsyncClient()` 可以像 JS 的 axios 实例一样保持 HTTP 长连接，提升 AI API 连续调用的性能！")


# === 3. 大模型 SSE 流式 Response 接收模式对比 ===
"""
在前端，我们接收 OpenAI 流式 API 是通过 ReadableStream:
const response = await fetch(url, { method: "POST", body });
const reader = response.body.getReader();

在 Python (httpx) 中：
async with client.stream("POST", url, json=payload) as response:
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            chunk = line[6:]
            print(chunk)
"""

def demo_summary():
    print("\n--- 3. 前端与 Python HTTP 库核心对照表 ---")
    print("""
    JS/TS (Axios / Fetch)             Python (requests / httpx)
    -----------------------------------------------------------------------------
    fetch(url, { method: 'POST' })    requests.post(url, json=data)
    await res.json()                  res.json()
    res.ok (status 200-299)           res.raise_for_status()
    axios.create({ headers })         client = httpx.AsyncClient(headers=...)
    response.body (Stream)            response.aiter_lines() / aiter_bytes()
    """)


if __name__ == "__main__":
    print("==================================================")
    print("  Python HTTP 请求与 API 对接 Demo (面向 JS 开发者)")
    print("==================================================")
    demo_sync_http_requests()
    demo_summary()
