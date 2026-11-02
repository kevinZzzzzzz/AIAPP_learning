package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：企业级 Worker Pool (协程池) 模式
================================================================================
1. 为什么需要协程池？
   - 尽管 Go 协程很轻量（~2KB），但如果不加节制地瞬间起 100 万个协程去查数据库或发邮件，
     数据库连接池会瞬间被打满崩溃，甚至触发 OOM 宕机。
   - Worker Pool（工作池模式）通过控制固定数量的 Worker 协程消费有限长度的任务队列，
     实现「流量削峰」和「资源受控」，是高并发后端的最核心心法！

2. 模式要素：
   - 任务通道 `jobs := make(chan Job, bufferSize)`
   - 结果通道 `results := make(chan Result, bufferSize)`
   - N 个固定并发 Worker 协程，持续从 jobs 中拉取并处理任务
   - `context.Context` 支持超时或外部一键优雅取消
================================================================================
*/

// Job 代表一个待处理任务
type Job struct {
	ID       int
	Payload  string
	CostTime time.Duration
}

// Result 代表任务处理结果
type Result struct {
	JobID  int
	Worker int
	Output string
	Err    error
}

// Worker 工作单元：持续从 jobs 通道消费任务，直到通道关闭或收到 context 取消信号
func worker(ctx context.Context, workerID int, jobs <-chan Job, results chan<- Result, wg *sync.WaitGroup) {
	defer wg.Done()

	for {
		select {
		case <-ctx.Done():
			// 收到外部取消信号（如超时或收到系统退出信号）
			fmt.Printf("  [Worker %d] 收到取消信号，平稳退出。\n", workerID)
			return

		case job, ok := <-jobs:
			if !ok {
				// 通道已被关闭且任务已被取空，正常退出
				return
			}

			// 模拟处理耗时任务
			time.Sleep(job.CostTime)
			output := fmt.Sprintf("数据 [%s] 由 Worker-%d 转换完成", job.Payload, workerID)

			results <- Result{
				JobID:  job.ID,
				Worker: workerID,
				Output: output,
			}
		}
	}
}

func main() {
	fmt.Println("======== 企业级高并发 Worker Pool 启动 ========")

	const numJobs = 10
	const numWorkers = 3 // 限制只起 3 个并发工作协程，保护系统资源

	jobs := make(chan Job, numJobs)
	results := make(chan Result, numJobs)

	// 使用 Context 设置最长运行时间为 5 秒
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var wg sync.WaitGroup

	// 1. 启动 3 个 Worker 工作协程
	for w := 1; w <= numWorkers; w++ {
		wg.Add(1)
		go worker(ctx, w, jobs, results, &wg)
	}

	// 2. 模拟投递 10 个后端待处理任务（例如图片缩放、批量发送短信、异步数据清洗）
	for j := 1; j <= numJobs; j++ {
		jobs <- Job{
			ID:       j,
			Payload:  fmt.Sprintf("订单数据_%03d", j),
			CostTime: 100 * time.Millisecond,
		}
	}
	// 投递完成后关闭 jobs 管道（告知 worker 没有新任务了）
	close(jobs)
	fmt.Printf("-> 成功将 %d 个任务推入工作通道，Worker 正在并发消费中...\n\n", numJobs)

	// 3. 单独起一个协程等待所有 worker 退出，然后关闭 results 通道
	go func() {
		wg.Wait()
		close(results)
	}()

	// 4. 收集消费所有任务的处理结果
	for res := range results {
		fmt.Printf("✅ 任务 #%02d 达成: %s\n", res.JobID, res.Output)
	}

	fmt.Println("\n🎉 所有任务处理完毕，Worker 协程池优雅关闭！")
}
