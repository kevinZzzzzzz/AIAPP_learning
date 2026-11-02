package main

import (
	"context"
	"fmt"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"

	"golang.org/x/sync/singleflight"
)

/*
================================================================================
💡 前端转全栈必备：Redis 三大缓存灾难与生产级解法
================================================================================
在前端单机开发中，我们很少考虑成千上万个并发。但在后端，当每秒 10 万人涌入时，
如果 Redis 缓存失效，海量流量会像海啸一样冲垮下游数据库（MySQL 支撑数千 QPS 就会报警）！

1. 缓存穿透 (Cache Penetration)：
   - 现象：黑客或前端请求一个根本不存在的 ID（如 id = -9999）。
     Redis 没有该缓存 -> 请求直接穿透去查 DB -> DB 也没有 -> 无法写入缓存。
     下一次请求依然穿透！导致 DB 被恶意刷崩。
   - 解法：
     ① 缓存空对象 (Cache Null / Empty Object)：DB 查不到也存一个 "NULL"，设短 TTL（如 30s）。
     ② 布隆过滤器 (Bloom Filter)：在访问 Redis 前用极小的二进制位图先判定 ID 是否存在。

2. 缓存击穿 (Cache Breakdown)：
   - 现象：某个“超级微博热搜”或“爆款商品”的缓存刚好到期失效的那 1 毫秒内，
     正好有 10000 个并发请求涌入！10000 个请求同时发现无缓存，同时跑去查 DB，瞬间击穿 DB。
   - 解法：
     ① 互斥锁加载 / SingleFlight（Go 语言的王牌绝技！）：
        利用 singleflight 将并发访问同一 Key 的 10000 个请求合并为 1 个真正的 DB 查询！
     ② 热点数据永不过期 + 后台异步定时刷新。

3. 缓存雪崩 (Cache Avalanche)：
   - 现象：大量的缓存数据设置了「相同的过期时间」（例如都在晚上 12 点统一失效，或 Redis 宕机）。
     导致某一时刻成千上万个 Key 同时失效，全量流量瞬间打向数据库。
   - 解法：
     ① 过期时间加随机扰动 (TTL + Random Jitter)：每个 Key 的 TTL 加上 1~5 分钟随机数，打散失效时间。
     ② 构建 Redis 高可用哨兵/集群架构，做好多级降级兜底。
================================================================================
*/

var (
	dbQueryCount int64 // 记录数据库被真实查询了多少次
	g            singleflight.Group
)

// 模拟数据库查询（耗时 200ms）
func queryDatabase(key string) (string, error) {
	atomic.AddInt64(&dbQueryCount, 1)
	time.Sleep(200 * time.Millisecond) // 模拟数据库 I/O 耗时
	return fmt.Sprintf("【DB数据: %s】", key), nil
}

// 模拟带有 SingleFlight 防击穿机制的缓存读取
func getDataWithSingleFlight(key string) (string, error) {
	// 假定此时 Redis 缓存已经失效

	// 利用 singleflight.Group.Do：
	// 如果此时有 100 个协程同时以相同的 key 调用 Do()，
	// 只有第 1 个协程会真正执行闭包函数，其余 99 个协程会原地等待复用第 1 个协程返回的结果！
	val, err, shared := g.Do(key, func() (interface{}, error) {
		fmt.Printf("🔥 [SingleFlight 真正穿透触发 DB 查询]: 正在查询 key: %s\n", key)
		return queryDatabase(key)
	})

	if err != nil {
		return "", err
	}

	if shared {
		// 表示本次返回是与其他并发请求共享的
	}

	return val.(string), nil
}

// 缓存雪崩解决方案：生成带随机扰动的过期时间
func generateJitterTTL(baseSeconds int) time.Duration {
	// 随机在 baseSeconds 基础上增加 0 ~ 30 秒的波动
	jitter := rand.Intn(30)
	totalSeconds := baseSeconds + jitter
	return time.Duration(totalSeconds) * time.Second
}

func main() {
	rand.Seed(time.Now().UnixNano())

	fmt.Println("======== 1. 模拟缓存击穿防御：SingleFlight 请求合并技术 ========")
	fmt.Println("模拟场景：热点 Key 'hot_article_888' 缓存刚刚到期，瞬间涌入 10 个并发请求拉取数据...")

	var wg sync.WaitGroup
	start := time.Now()

	for i := 1; i <= 10; i++ {
		wg.Add(1)
		go func(requestID int) {
			defer wg.Done()

			data, err := getDataWithSingleFlight("hot_article_888")
			if err != nil {
				fmt.Printf("  请求 #%d 失败: %v\n", requestID, err)
				return
			}
			fmt.Printf("  ✅ 请求 #%d 成功拿到结果: %s\n", requestID, data)
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)

	fmt.Printf("\n📊 测试汇总：\n")
	fmt.Printf("  10 个高并发请求全部完成，总耗时: %v\n", duration)
	fmt.Printf("  数据库真实被执行查询的次数: %d 次！（如果没有 SingleFlight，DB 会被轰炸 10 次）\n", atomic.LoadInt64(&dbQueryCount))

	fmt.Println("\n======== 2. 模拟缓存雪崩防御：TTL 随机抖动打散机制 ========")
	fmt.Println("模拟为 5 个批量写入的热门缓存配置过期时间:")
	for i := 1; i <= 5; i++ {
		ttl := generateJitterTTL(300) // 基础 TTL 为 300 秒 (5分钟)
		fmt.Printf("  Key-%d 过期时间打散为: %v (有效避免同一时刻集中失效！)\n", i, ttl)
	}

	fmt.Println("\n======== 3. 模拟缓存穿透防御：空值占位策略 (Cache Null) ========")
	fakeCache := make(map[string]string)
	nonExistentID := "user_-999"

	fmt.Printf("用户请求不存在的 ID: %s\n", nonExistentID)
	// 第一次查询：缓存未命中，查 DB
	if _, ok := fakeCache[nonExistentID]; !ok {
		fmt.Println("  [Step 1] 缓存未命中，查 DB 确认记录确实不存在")
		// 关键防穿透动作：将空值存入缓存，并赋予较短的 TTL
		fakeCache[nonExistentID] = "@@EMPTY_VAL@@"
		fmt.Println("  [Step 2] 将空值占位符写入缓存，设定短 TTL (如 30 秒)")
	}

	// 第二次恶意再次请求：
	if val, ok := fakeCache[nonExistentID]; ok {
		if val == "@@EMPTY_VAL@@" {
			fmt.Println("  [Step 3] 第二次请求命中空值缓存，直接拦截并向客户端返回 404，数据库完全零压力！")
		}
	}
}

// 避免未使用 context 的编译提示
func init() {
	_ = context.Background()
}

