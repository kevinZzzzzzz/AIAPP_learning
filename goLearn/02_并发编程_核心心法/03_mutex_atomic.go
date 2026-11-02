package main

import (
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：竞态条件、互斥锁 (Mutex) 与原子操作
================================================================================
1. 为什么前端极少遇到数据竞态 (Data Race)？
   - JS 运行在单线程主循环中，`count++` 在底层是连续不可被其他 JS 代码切入的。
   - Go 的协程是真正并行在多个物理 CPU 核心上的！如果 1000 个协程同时操作 `count++`，
     底层汇编的「读-改-写」指令会互相踩踏，导致计数严重丢失！

2. 锁方案对比：
   - `sync.Mutex`（互斥锁）：任何人要读写都必须排队拿锁。
   - `sync.RWMutex`（读写互斥锁）：读多写少场景神兵利器！
     - 允许多个协程同时读（`RLock`），完全不互斥；
     - 当有协程要写时（`Lock`），排他独占。
   - `sync/atomic`（原子操作）：利用底层 CPU 硬件级指令保证原子性，免去锁的开销，性能最极致。
================================================================================
*/

func main() {
	fmt.Println("======== 1. 互斥锁 sync.Mutex 保护临界资源 ========")

	var (
		counterWithLock int
		lock            sync.Mutex
		wgLock          sync.WaitGroup
	)

	// 模拟 1000 个高并发请求同时递增计数器
	for i := 0; i < 1000; i++ {
		wgLock.Add(1)
		go func() {
			defer wgLock.Done()

			// 进入临界区前加锁
			lock.Lock()
			// 退出临界区时解锁（defer 保证即使发生 panic 也能释放锁，避免死锁）
			defer lock.Unlock()

			counterWithLock++
		}()
	}

	wgLock.Wait()
	fmt.Printf("1000 个并发协程加锁递增结果: %d (100% 精确，无任何数据丢失！)\n", counterWithLock)

	fmt.Println("\n======== 2. 读写锁 sync.RWMutex（高并发读场景极佳性能） ========")
	// 场景：后端商品库存或热点缓存，每秒 10000 次读，10 次写
	cacheData := map[string]string{"title": "Go 从入门到精通"}
	var rwLock sync.RWMutex
	var wgRW sync.WaitGroup

	// 并发启动 5 个并发读取操作
	for i := 1; i <= 5; i++ {
		wgRW.Add(1)
		go func(readerID int) {
			defer wgRW.Done()

			// 读锁：可以同时有成千上万个协程一起 RLock()，彼此完全互不阻塞！
			rwLock.RLock()
			defer rwLock.RUnlock()

			val := cacheData["title"]
			fmt.Printf("  [读协程 %d] 并发读取缓存: %s\n", readerID, val)
		}(i)
	}

	// 启动 1 个并发写入更新操作
	wgRW.Add(1)
	go func() {
		defer wgRW.Done()
		time.Sleep(10 * time.Millisecond)

		// 写锁：排他性独占，此时其他读协程和写协程都会等待写入完成
		rwLock.Lock()
		defer rwLock.Unlock()

		cacheData["title"] = "Go 全栈高并发架构实战"
		fmt.Println("  🔥 [写协程] 独占写入更新缓存成功！")
	}()

	wgRW.Wait()

	fmt.Println("\n======== 3. 原子操作 sync/atomic（无锁编程极速性能） ========")
	var atomicCounter int64 // 必须使用 int32 或 int64
	var wgAtomic sync.WaitGroup

	for i := 0; i < 1000; i++ {
		wgAtomic.Add(1)
		go func() {
			defer wgAtomic.Done()
			// 底层使用 CPU 的 LOCK CMPXCHG 等硬件指令，无需加锁，性能秒杀互斥锁！
			atomic.AddInt64(&atomicCounter, 1)
		}()
	}

	wgAtomic.Wait()
	fmt.Printf("1000 个并发原子操作累加结果: %d\n", atomic.LoadInt64(&atomicCounter))
}
