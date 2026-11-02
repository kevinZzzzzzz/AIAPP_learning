package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go-learn/03_gin_gorm_api/cache"
	"go-learn/03_gin_gorm_api/database"
	"go-learn/03_gin_gorm_api/routes"
)

/*
================================================================================
💡 前端转全栈：企业级生产服务生命周期管理（优雅停机 Graceful Shutdown）
================================================================================
为什么后端开发必须掌握优雅停机？
- 传统开发中如果直接杀死进程（如 Docker 缩容、CI/CD 重新发布版本），正在执行中的
  数据库事务、支付回调请求会被强行掐断，导致数据损坏或前端收到 502 报错。
- Go 生产实践：
  1. 拦截操作系统终止信号（SIGINT, SIGTERM）
  2. 停止接收新的 HTTP 连接
  3. 给现有正在处理的请求 5 秒缓冲时间优雅完成
  4. 关闭数据库与 Redis 连接，安全释放系统资源
================================================================================
*/

func main() {
	log.Println("🚀 正在启动 Go 全栈后端服务...")

	// 1. 初始化数据库连接与连接池
	database.InitDB()

	// 2. 初始化 Redis 客户端连接
	cache.InitRedis()

	// 3. 注册 API 路由
	router := routes.SetupRouter()

	// 4. 配置 HTTP 服务器
	srv := &http.Server{
		Addr:           ":8080",
		Handler:        router,
		ReadTimeout:    10 * time.Second, // 避免慢客户端慢速攻击挂起连接
		WriteTimeout:   10 * time.Second,
		MaxHeaderBytes: 1 << 20, // 1MB 最大请求头
	}

	// 5. 将 HTTP 服务置于单独协程中非阻塞启动
	go func() {
		log.Println("⚡ API 服务已就绪，正在监听端口 http://127.0.0.1:8080")
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("HTTP 服务异常崩溃: %v", err)
		}
	}()

	// 6. 优雅停机信号监听（系统级保护）
	quit := make(chan os.Signal, 1)
	// 捕获 Ctrl+C (SIGINT) 以及 kill / docker stop 发送的 SIGTERM 信号
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	// 阻塞在此，直到捕获到退出信号
	sig := <-quit
	log.Printf("收到操作系统终止信号 [%v]，准备启动优雅停机流程...", sig)

	// 设置 5 秒的强制超时 Context
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// 通知 HTTP Server 停止接客，并等待已有请求完成
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("优雅停机超时，强制终止: %v", err)
	}

	log.Println("🎉 HTTP 服务已平稳安全关闭，零丢单、零脏数据！")
}
