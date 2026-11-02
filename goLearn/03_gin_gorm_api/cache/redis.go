package cache

import (
	"context"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

var (
	Rdb       *redis.Client
	IsHealthy bool // 标记 Redis 服务是否可用
)

// InitRedis 初始化 Redis 客户端连接
func InitRedis() {
	Rdb = redis.NewClient(&redis.Options{
		Addr:         "127.0.0.1:6379", // 默认本地 Redis 地址
		Password:     "",               // 无密码
		DB:           0,                // 默认使用 DB 0
		DialTimeout:  1 * time.Second,  // 快速超时判定
		ReadTimeout:  1 * time.Second,
		WriteTimeout: 1 * time.Second,
		PoolSize:     50, // Redis 连接池大小
	})

	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	// 发送 Ping 验证心跳
	_, err := Rdb.Ping(ctx).Result()
	if err != nil {
		log.Printf("⚠️ [Redis 提示]: 本地 127.0.0.1:6379 未开启或连接超时: %v", err)
		log.Println("👉 提示：系统已开启降级容灾模式，接口将直接穿透查库，不影响基础功能演示！")
		IsHealthy = false
		return
	}

	IsHealthy = true
	log.Println("✅ Redis 缓存连接成功！")
}
