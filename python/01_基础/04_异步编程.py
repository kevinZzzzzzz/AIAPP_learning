"""
Python 异步编程详解
=================================================================

这是从 JS 转 Python 最需要认真学的一章！
Python 的 async/await 在**语法**上和 JS 几乎一样，但**运行时模型**完全不同。

核心差异：
- JS：事件循环是内置的，Promise 天生是异步的，你不需要手动启动
- Python：需要显式创建事件循环，用 asyncio.run() 启动

AI 开发中异步的重要性：
- 同时调用多个 LLM API（并行请求节省时间）
- 流式输出（SSE）需要异步处理
- FastAPI 框架天生异步
"""

import asyncio
import time
from typing import Any


# ======================== 1. 最基本的 async/await ========================

async def fetch_data(source: str, delay: float = 1.0) -> str:
    """async 定义协程函数（coroutine function）
    
    和 JS 的区别：
    - JS: async function fetchData() { await delay(1000); }
    - Python: async def fetch_data(): await asyncio.sleep(1)
    
    关键：await 后面必须是「可等待对象」（awaitable）
    - asyncio.sleep() ✓
    - time.sleep() ✗（会阻塞整个线程！）
    """
    print(f"[{source}] 开始请求...")
    await asyncio.sleep(delay)  # 模拟 IO 等待，不阻塞其他协程
    print(f"[{source}] 请求完成!")
    return f"Data from {source}"


async def demo_basic():
    """顺序执行（没用并发）—— 逐个等待"""
    # 和 JS 一样，await 会暂停当前协程，等结果
    result1 = await fetch_data("API-1")
    result2 = await fetch_data("API-2")
    print(result1, result2)
    # 总耗时 ≈ 2 秒（串行）


# ======================== 2. 并发：asyncio.gather ========================

async def demo_concurrent():
    """asyncio.gather = JS 的 Promise.all
    
    多个协程并发执行，总耗时 ≈ max(各任务)，而非 sum
    """
    results = await asyncio.gather(
        fetch_data("API-1", delay=1.0),
        fetch_data("API-2", delay=1.5),
        fetch_data("API-3", delay=0.5),
    )
    print(results)
    # 总耗时 ≈ 1.5 秒（取决于最慢的那个）


# ======================== 3. 创建任务：asyncio.create_task ========================

async def demo_tasks():
    """create_task = 不等待就启动协程，稍后再等结果
    
    类似 JS 中：const task = fetchData(); /* 不 await */ ... await task;
    """
    task1 = asyncio.create_task(fetch_data("DB", delay=2))
    task2 = asyncio.create_task(fetch_data("Cache", delay=1))
    
    # 任务已经在后台运行了！这里可以做其他事
    print("任务已启动，做点别的事...")
    await asyncio.sleep(0.5)
    
    # 等待所有任务完成
    result1 = await task1
    result2 = await task2
    print(result1, result2)


# ======================== 4. 超时控制：asyncio.wait_for ========================

async def demo_timeout():
    """设置超时：如果协程太久不完成，抛出 TimeoutError
    
    AI 开发必备：API 调用必须设超时，防止无限等待
    """
    try:
        result = await asyncio.wait_for(
            fetch_data("Slow-API", delay=3),
            timeout=1.0  # 1秒超时
        )
        print(result)
    except asyncio.TimeoutError:
        print("[错误] API 调用超时！")


# ======================== 5. 并发限制：Semaphore ========================

async def limited_fetch(sem: asyncio.Semaphore, url: str, delay: float) -> str:
    """信号量控制并发数 —— 防止同时发起太多请求打爆 API"""
    async with sem:  # 获取信号量（并发数+1）
        return await fetch_data(url, delay)


async def demo_semaphore():
    """限制最多同时 2 个并发请求"""
    sem = asyncio.Semaphore(2)  # 最多同时 2 个
    
    tasks = [
        limited_fetch(sem, f"URL-{i}", delay=1.0)
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)
    # 5 个任务，每次最多 2 个并发，总耗时 ≈ ceil(5/2) * 1 ≈ 3 秒
    print(results)


# ======================== 6. 异步生成器（Streaming 基础） ========================

async def async_range(n: int):
    """异步生成器：用 async for 迭代
    
    这是理解流式输出的基础！LLM 的 token-by-token 输出就是通过异步生成器实现的
    """
    for i in range(n):
        await asyncio.sleep(0.3)
        yield i


async def demo_async_generator():
    """async for 遍历异步生成器"""
    async for value in async_range(5):
        print(f"收到: {value}")
        # 每 0.3 秒输出一个值，就像 ChatGPT 逐字输出


# ======================== 7. 实战：模拟并行的 LLM API 调用 ========================

async def call_llm(provider: str, prompt: str, delay: float) -> dict:
    """模拟调用不同 LLM 提供商"""
    await asyncio.sleep(delay)  # 模拟网络延迟
    return {
        "provider": provider,
        "prompt": prompt[:30],
        "response": f"{provider}的回复: ...",
        "latency": delay,
    }


async def demo_llm_parallel():
    """同时向多个 LLM 发起请求 —— AI 应用开发中的真实场景"""
    providers = [
        ("OpenAI", "介绍一下 Python", 1.2),
        ("Claude", "介绍一下 Python", 1.5),
        ("Qwen", "介绍一下 Python", 0.8),
    ]
    
    tasks = [
        call_llm(name, prompt, delay)
        for name, prompt, delay in providers
    ]
    
    # return_exceptions=True: 某个请求失败不影响其他
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"请求失败: {result}")
        else:
            print(f"[{result['provider']}] 延迟={result['latency']}s")


# ======================== 8. asyncio.run() —— 启动入口 ========================

def run_demos():
    """asyncio.run() = Python 异步程序的入口
    
    重要规则：
    1. 一个程序只能有一个 asyncio.run()
    2. 不要在 asyncio.run() 内部再调用 asyncio.run()
    3. Jupyter Notebook 中不需要 asyncio.run()，因为事件循环已经在运行
    """
    print("\n========== 1. 顺序执行 ==========")
    asyncio.run(demo_basic())
    
    print("\n========== 2. 并发执行 ==========")
    asyncio.run(demo_concurrent())
    
    print("\n========== 3. 超时控制 ==========")
    asyncio.run(demo_timeout())
    
    print("\n========== 4. 异步生成器 ==========")
    asyncio.run(demo_async_generator())
    
    print("\n========== 5. 并行 LLM 调用 ==========")
    asyncio.run(demo_llm_parallel())


# ======================== 9. 关键坑：阻塞 vs 非阻塞 ========================

async def demo_blocking_pitfall():
    """常见错误：在 async 函数中用 time.sleep() 而不是 asyncio.sleep()
    
    time.sleep() 会阻塞整个事件循环！
    所有并发任务都会被卡住，这是从 JS 转 Python 最常犯的错误
    """
    # ✗ 错误：用 time.sleep
    start = time.time()
    await asyncio.gather(
        asyncio.to_thread(time.sleep, 1),  # 正确：把阻塞操作扔到线程池
        asyncio.to_thread(time.sleep, 1),
    )
    # ✓ 正确：用 asyncio.sleep
    print(f"耗时: {time.time() - start:.2f}s")


if __name__ == "__main__":
    run_demos()
