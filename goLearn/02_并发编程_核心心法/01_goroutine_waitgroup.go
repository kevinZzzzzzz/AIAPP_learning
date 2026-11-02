package main

import (
	"fmt"
	"sync"
	"time"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：Goroutine (协程) 与 sync.WaitGroup
================================================================================
1. 并发模型差异：
   - JS/Node: 单线程事件循环 (Event Loop)。虽然非阻塞 I/O 很强，但遇到 CPU 密集型计算
     就会卡死主线程；Node 的 worker_threads 创建成本极高（几十兆内存，独立 V8 实例）。
   - Go: 基于著名的 GMP 调度模型。
     启动一个协程只需要关键字 `go func()`！
     一个协程内存占用初始仅 ~2KB，一台普通 8GB 内存电脑可轻松并发起 100,000+ 个协程！

2. 等待多个并发任务完成：
   - JS/TS:  `await Promise.all([task1(), task2(), task3()])`
   - Go:     使用标准库 `sync.WaitGroup`：
             - `wg.Add(n)`：注册等待的任务数量
             - `wg.Done()`：单个协程完成时调用（计数减 1），通常用 `defer wg.Done()`
             - `wg.Wait()`：主线程阻塞等待，直到计数器减为 0
================================================================================
*/

// 模拟异步耗时任务（例如查询远程微服务、请求第三方 API）
func fetchRemoteData(serviceID int, delay time.Duration, wg *sync.WaitGroup) {
	// 在函数退出时务必通知 WaitGroup 计数器 -1
	defer wg.Done()

	fmt.Printf("[协程 %d] 开始请求远程服务...\n", serviceID)
	time.Sleep(delay) // 模拟网络延迟
	fmt.Printf("[协程 %d] 请求成功，耗时 %v！\n", serviceID, delay)
}

func main() {
	fmt.Println("======== 1. 对比串行耗时 vs Goroutine 并发耗时 ========")

	// 场景：我们需要并发向 3 个不同的数据服务拉取数据
	tasks := []struct {
		id    int
		delay time.Duration
	}{
		{id: 1, delay: 300 * time.Millisecond},
		{id: 2, delay: 500 * time.Millisecond},
		{id: 3, delay: 200 * time.Millisecond},
	}

	startTime := time.Now()

	// 创建 sync.WaitGroup（对比前端 Promise.all）
	var wg sync.WaitGroup

	for _, task := range tasks {
		// 每准备启动一个任务，计数器 +1
		wg.Add(1)

		// 使用 go 关键字，瞬间在后台协程中异步非阻塞启动！
		// 注意：这里把 task 变量通过形参显式传入，避免闭包变量捕获陷阱！
		go fetchRemoteData(task.id, task.delay, &wg)
	}

	fmt.Println("-> 主线程：所有协程已下发，现在调用 wg.Wait() 等待它们全部完成...")

	// 阻塞等待，直到所有的 wg.Done() 都被调用完毕
	wg.Wait()

	totalDuration := time.Since(startTime)
	fmt.Printf("\n🎉 所有并发请求全部完成！总耗时: %v\n", totalDuration)
	fmt.Println("（如果是传统串行执行，总耗时将是 300+500+200 = 1000ms；并发执行只取决于最慢的那个，仅约 500ms！）")

	fmt.Println("\n======== 2. 闭包与 Goroutine 经典面试坑点 ========")
	var loopWg sync.WaitGroup

	fmt.Println("错误示例防范演示：正确将循环变量传入参数")
	for i := 1; i <= 3; i++ {
		loopWg.Add(1)
		// 正确姿势：将 i 作为实参传入匿名函数形参 val
		go func(val int) {
			defer loopWg.Done()
			fmt.Printf("  当前并发协程处理序号: %d\n", val)
		}(i)
	}
	loopWg.Wait()
}
