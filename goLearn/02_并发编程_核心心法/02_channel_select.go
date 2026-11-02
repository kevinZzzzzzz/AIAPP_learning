package main

import (
	"fmt"
	"time"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：通道 (Channel) 与 多路复用 (select)
================================================================================
1. 通信理念：
   - Go 的著名哲学："不要通过共享内存来通信，而要通过通信来共享内存"。
   - Channel（通道）就像一条传送带或专属消息管道，协程 A 往里面放数据，协程 B 从里面取数据。

2. 无缓冲通道 vs 有缓冲通道：
   - 无缓冲 `make(chan int)`：同步握手通道。发送方发送数据后会立即阻塞挂起，
     直到接收方把数据取走，两者才同时继续执行。
   - 有缓冲 `make(chan int, 3)`：异步缓冲队列。队列只要没满，发送方就不会阻塞；
     队列只要非空，接收方也不会阻塞。

3. select 机制（多路复用）：
   - 对比前端：类似增强版的 `Promise.race()`，但更强大。
   - select 会同时监听多个 channel 的读写就绪状态，哪个 channel 先就绪就执行哪个分支！
   - 配合 `time.After(timeout)` 可以极其优雅地实现「超时熔断」控制。
================================================================================
*/

func main() {
	fmt.Println("======== 1. 无缓冲 Channel：同步数据传递 ========")
	// 创建一个传输 string 的无缓冲 channel
	ch := make(chan string)

	go func() {
		fmt.Println("  [后台协程]: 正在生成报表...")
		time.Sleep(300 * time.Millisecond)
		// 向 channel 发送数据 (箭头指向 channel)
		ch <- "月度财务报表.xlsx"
		fmt.Println("  [后台协程]: 报表已送入管道！")
	}()

	// 主协程从 channel 接收数据 (从 channel 箭头流出)
	// 如果数据还没准备好，主协程会在这里优雅等待，绝不浪费 CPU
	report := <-ch
	fmt.Printf("-> [主协程]: 成功从通道接收到数据: %s\n", report)

	fmt.Println("\n======== 2. 有缓冲 Channel 与关闭通知 (range 消费) ========")
	// 容量为 3 的有缓冲 channel
	jobs := make(chan int, 3)

	// 生产者：推送 3 个任务后关闭通道
	go func() {
		for i := 1; i <= 3; i++ {
			jobs <- i
			fmt.Printf("  [生产者] 推送任务 ID: %d 到队列 (缓冲内任务数: %d)\n", i, len(jobs))
		}
		// 关闭通道：告知消费者任务发送完毕
		close(jobs)
		fmt.Println("  [生产者] 所有任务推送完毕，管道已关闭。")
	}()

	time.Sleep(100 * time.Millisecond)
	fmt.Println("-> [消费者] 使用 for-range 消费通道中的任务:")
	// 当 channel 被 close 且数据被取空后，for 循环会自动平稳退出，绝不死锁
	for jobID := range jobs {
		fmt.Printf("  正在执行任务: %d\n", jobID)
	}

	fmt.Println("\n======== 3. select 多路复用与超时熔断控制 (对比 Promise.race) ========")
	dataChan := make(chan string)

	// 模拟一个可能响应很慢的远程接口
	go func() {
		time.Sleep(600 * time.Millisecond) // 耗时 600ms
		dataChan <- "远程大型微服务返回的结果"
	}()

	// 使用 select 设置 400ms 超时熔断
	timeoutLimit := 400 * time.Millisecond
	fmt.Printf("-> 设定超时阈值为: %v，发起竞速监听...\n", timeoutLimit)

	select {
	case res := <-dataChan:
		// 正常情况下如果数据在 400ms 内返回，走此分支
		fmt.Printf("🎉 接口在规定时间内正常返回: %s\n", res)

	case <-time.After(timeoutLimit):
		// time.After 会在到达指定时间后往其内置 channel 发送当前时间
		// 如果此时 dataChan 还没数据，就会触发超时分支！
		fmt.Println("⚠️ [超时熔断警告]: 接口响应超过 400ms，触发超时降级策略！")
	}
}
