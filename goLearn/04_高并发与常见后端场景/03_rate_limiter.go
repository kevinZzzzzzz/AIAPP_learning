package main

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

/*
================================================================================
💡 前端转全栈必备：高并发接口限流利器（令牌桶算法）
================================================================================
1. 为什么后端必须做限流 (Rate Limiting)？
   - 防止爬虫和恶意流量把服务器打崩。
   - 防止秒杀大促流量超出数据库最大承载阈值（服务器拒绝一部分请求返回 429，
     也远比全盘崩溃 502/504 强得多）。
   - 保障大模型 API 调用配额不被瞬间刷爆。

2. 令牌桶算法 (Token Bucket) 核心原理：
   - 系统以恒定速率 `r`（如每秒 5 个）往桶里放入“令牌”。
   - 桶的最大容量为 `b`（Burst，突发流量容量，如最多存 10 个）。
   - 客户端每次发起请求，必须从桶里取走 1 个令牌：
     - 若桶里有令牌：放行，正常响应；
     - 若桶已空：直接拒绝请求（返回 HTTP 429 Too Many Requests）或排队等待。
   - 优点：既允许短时间内合法的“突发洪峰”，又能从宏观上严控长期速率！

3. Go 官方标准生产利器：
   - `golang.org/x/time/rate`：极其精简高效的令牌桶纯内存实现。
================================================================================
*/

// GinRateLimiterMiddleware 将令牌桶限流器包装为 Gin 中间件
func GinRateLimiterMiddleware(limiter *rate.Limiter) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Allow() 尝试立即获取 1 个令牌（非阻塞）
		if !limiter.Allow() {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"code":    429,
				"message": "⚠️ 系统当前访问过于火爆，请稍后再试！(Rate limit exceeded)",
			})
			return
		}

		c.Next()
	}
}

func main() {
	// 设置 Gin 为发布模式，保持日志清爽
	gin.SetMode(gin.ReleaseMode)

	fmt.Println("======== 1. 令牌桶限流算法基础演示 ========")
	// 创建一个限流器：每秒产生 3 个令牌 (rate.Limit(3))，桶最大容量为 5 个 (Burst = 5)
	limiter := rate.NewLimiter(rate.Limit(3), 5)

	fmt.Println("测试瞬时连续消费 8 个令牌（初始桶满 5 个）:")
	for i := 1; i <= 8; i++ {
		if limiter.Allow() {
			fmt.Printf("  请求 #%d: ✅ 成功取到令牌，接口放行！\n", i)
		} else {
			fmt.Printf("  请求 #%d: ❌ 桶已空无令牌，被立刻限流拦截！\n", i)
		}
	}

	fmt.Println("\n======== 2. 模拟真实 Gin HTTP 接口并发压测 ========")
	// 创建 Gin 引擎并挂载限流中间件：限制 QPS = 5，突发上限 = 3
	engine := gin.New()
	apiLimiter := rate.NewLimiter(rate.Limit(5), 3)
	engine.Use(GinRateLimiterMiddleware(apiLimiter))

	// 注册业务路由
	engine.GET("/api/ping", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "pong"})
	})

	var (
		wg           sync.WaitGroup
		successCount int
		limitedCount int
		mu           sync.Mutex
	)

	// 并发模拟 10 个客户端同一毫秒发起请求
	fmt.Println("模拟 10 个用户瞬间并发请求 /api/ping 接口:")
	for i := 1; i <= 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			// 使用 httptest 快速在内存中模拟发起真实 HTTP 请求
			req := httptest.NewRequest("GET", "/api/ping", nil)
			w := httptest.NewRecorder()
			engine.ServeHTTP(w, req)

			mu.Lock()
			defer mu.Unlock()
			if w.Code == http.StatusOK {
				successCount++
				fmt.Printf("  [客户端 %02d] -> 响应: 200 OK\n", id)
			} else if w.Code == http.StatusTooManyRequests {
				limitedCount++
				fmt.Printf("  [客户端 %02d] -> 响应: 429 Too Many Requests (被拦截保护)\n", id)
			}
		}(i)
	}

	wg.Wait()

	fmt.Printf("\n📊 压测统计：\n")
	fmt.Printf("  成功放行请求数: %d\n", successCount)
	fmt.Printf("  被限流保护请求数: %d\n", limitedCount)
	fmt.Println("🎉 令牌桶成功吸收了突发流量，并在超标时坚决守住了后端服务安全！")
}

func init() {
	_ = context.Background()
	_ = time.Second
}

