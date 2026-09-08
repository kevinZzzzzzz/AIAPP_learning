"""
Python 工程化：异步编程 (Asyncio)

在 AI/Web 后端开发中，网络 I/O 是最耗时的部分（比如等待大模型 API 响应、查询数据库）。
普通的同步编程会阻塞整个线程，而异步编程（async/await）可以让程序在等待时去处理其他任务，极大提高并发能力。

核心概念：
1. async def: 定义一个协程函数 (Coroutine)
2. await: 挂起当前协程，等待一个耗时操作完成（必须在 async 函数内部使用）
3. asyncio.run(): 运行最高层级的异步入口函数
"""

import asyncio
import time

# ======================== 1. 基础异步函数 ========================

async def fetch_data(task_id: int, delay: int):
    print(f"任务 {task_id}: 开始执行，预计耗时 {delay} 秒...")
    
    # 【注意】这里必须使用 asyncio.sleep 而不是 time.sleep
    # time.sleep 是阻塞的，会让整个线程停下来，违背了异步的初衷
    # asyncio.sleep 是非阻塞的，它会告诉事件循环：“我先歇会儿，你去干别的吧”
    await asyncio.sleep(delay)
    
    print(f"任务 {task_id}: 执行完成！")
    return f"结果 {task_id}"


# ======================== 2. 并发执行多个任务 ========================

async def main():
    start_time = time.time()
    
    # 场景：我们需要向 3 个不同的大模型供应商发起请求
    # 如果是同步编程，耗时将是 2 + 3 + 1 = 6 秒
    
    print("--- 准备并发执行 3 个任务 ---")
    
    # asyncio.gather 会并发执行传入的所有协程，并等待它们全部完成
    # 耗时将取决于最慢的那个任务（这里是 3 秒）
    results = await asyncio.gather(
        fetch_data(1, 2),
        fetch_data(2, 3),
        fetch_data(3, 1)
    )
    
    end_time = time.time()
    
    print(f"--- 所有任务执行完毕 ---")
    print(f"获取到的结果: {results}")
    print(f"总计耗时: {end_time - start_time:.2f} 秒 (如果是同步则需要 6 秒)")


if __name__ == "__main__":
    # 使用 asyncio.run 来启动事件循环并运行主入口协程
    asyncio.run(main())
