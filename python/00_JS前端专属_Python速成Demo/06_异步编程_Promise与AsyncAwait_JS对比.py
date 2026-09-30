"""
Python 异步编程 (asyncio) 与 JS Promise / async-await 对比指南
================================================================
在前端，异步几乎无处不在（fetch, setTimeout, 事件响应）。JS 环境默认由事件循环 (Event Loop) 驱动。
而在 Python 中，默认是同步阻塞的！如果要写异步代码，必须使用 `asyncio` 模块，并用 `asyncio.run()` 启动事件循环。

运行方法：python 06_异步编程_Promise与AsyncAwait_JS对比.py
"""

import asyncio
import time
from typing import AsyncGenerator


# === 1. 模拟网络请求 (setTimeout vs asyncio.sleep) ===
"""
JS 写法:
async function mockFetch(id: number, delayMs: number): Promise<string> {
  await new Promise(resolve => setTimeout(resolve, delayMs));
  return `Response from Task ${id}`;
}
"""

async def mock_fetch(task_id: int, delay_seconds: float) -> str:
    # 💥 注意：绝对不能在 async 函数里使用 time.sleep()！那会阻塞整个线程！
    # 必须使用 asyncio.sleep()（相当于 await new Promise(res => setTimeout(res, ms))）
    await asyncio.sleep(delay_seconds)
    return f"任务 #{task_id} 结果 (延迟 {delay_seconds}s)"


# === 2. 基础 async / await 调用 ===
async def demo_basic_async():
    print("\n--- 1. 顺序执行 async/await ---")
    start_time = time.time()
    
    # 顺序等待 (Sequential)
    res1 = await mock_fetch(1, 1.0)
    res2 = await mock_fetch(2, 0.5)
    
    elapsed = time.time() - start_time
    print(f"结果 1: {res1}")
    print(f"结果 2: {res2}")
    print(f"顺序执行耗时: {elapsed:.2f} 秒 (1.0 + 0.5 = 1.5s)")


# === 3. 并行并发执行 (Promise.all vs asyncio.gather) ===
async def demo_parallel_async():
    print("\n--- 2. 并行执行 (Promise.all vs asyncio.gather) ---")
    start_time = time.time()
    
    # JS: const results = await Promise.all([mockFetch(1, 1.0), mockFetch(2, 0.5), mockFetch(3, 0.8)]);
    # Python asyncio.gather(*tasks)
    results = await asyncio.gather(
        mock_fetch(1, 1.0),
        mock_fetch(2, 0.5),
        mock_fetch(3, 0.8)
    )
    
    elapsed = time.time() - start_time
    print("并发返回结果:", results)
    print(f"并发执行耗时: {elapsed:.2f} 秒 (取决于最慢的那个，约 1.0s)")


# === 4. 创建后台任务 (不阻塞主流程，类似 JS 触发 Promise 不 await) ===
async def demo_background_task():
    print("\n--- 3. 创建后台任务 (asyncio.create_task) ---")
    
    # JS: mockFetch(99, 2.0).then(res => console.log(res)); // 后台异步跑
    # Python asyncio.create_task()
    task = asyncio.create_task(mock_fetch(99, 0.5))
    
    print("主流程继续向下执行...")
    await asyncio.sleep(0.1)
    print("主流程完成，现在等待后台任务...")
    
    res = await task
    print(f"后台任务完成: {res}")


# === 5. 实战 AI 场景：异步生成器处理 LLM 流式输出 (Streaming Response) ===
"""
前端开发大模型应用最常见的需求：打字机流式效果 (Server-Sent Events / SSE)
JS 中通过 response.body.getReader() 或 async iterator:
for await (const chunk of stream) { ... }
"""

async def mock_llm_stream(prompt: str) -> AsyncGenerator[str, None]:
    """模拟大模型流式吐出 Token"""
    tokens = ["你好！", "我是", "DeepSeek", "AI", "助手。", "很高兴", "为你", "解答", "Python", "问题！"]
    for token in tokens:
        await asyncio.sleep(0.1)  # 模拟网络吐字延迟
        yield token  # 使用 yield 变成异步生成器


async def demo_llm_streaming():
    print("\n--- 4. 流式输出体验 (for await ... of vs async for ... in) ---")
    print("AI 回复: ", end="", flush=True)
    
    # JS: for await (const chunk of mockLlmStream("hi")) { process.stdout.write(chunk); }
    # Python: async for 语法
    async for chunk in mock_llm_stream("hi"):
        print(chunk, end="", flush=True)
    print("\n[流式传输结束]")


# === 主入口 ===
async def main():
    await demo_basic_async()
    await demo_parallel_async()
    await demo_background_task()
    await demo_llm_streaming()


if __name__ == "__main__":
    print("==================================================")
    print("  Python 异步编程 asyncio 与 JS Promise 对比 Demo")
    print("==================================================")
    
    # 💥 必须由 asyncio.run() 作为顶级入口启动事件循环！
    # 相当于在 JS 中直接运行主文件
    asyncio.run(main())
