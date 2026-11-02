package main

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
)

/*
================================================================================
💡 前端转全栈必备：Redis 分布式锁核心原理与生产避坑
================================================================================
1. 为什么我们有了 sync.Mutex 还需要分布式锁？
   - 前面学的 `sync.Mutex` 是「进程内锁」，只对单机单个 Go 进程有效。
   - 当你的后端做微服务或在 K8s 中部署了 5 个 Pod 副本时，5 个进程的内存是完全隔离的！
   - 如果此时秒杀一件库存为 1 的商品，5 个 Pod 都会认为自己有库存，导致严重超卖！
   - 分布式锁：所有 Pod 共同向一个中央独立节点（如 Redis）竞态争抢同一把锁！

2. 工业级 Redis 分布式锁四大核心法则：
   ① 互斥性：同一时刻只能有一个客户端持有锁。
      - 原理：Redis `SET resource_name unique_token NX PX 30000`
      - `NX`：Not Exists，仅当 key 不存在时才允许设置（原子争锁）。
      - `PX 30000`：设置毫秒级超时时间，防止进程意外崩溃后永远死锁！

   ② 唯一凭据 (Unique Value)：
      - 必须为加锁者生成唯一的随机 UUID/Token 作为 Value。

   ③ 防误删（最容易踩的生产特大事故！）：
      - 场景：Worker-A 加锁 TTL 是 5 秒，但 Worker-A 业务慢花了 7 秒。
        第 5 秒时锁自动过期释放；Worker-B 趁机抢到了锁。
        第 7 秒 Worker-A 执行完毕，如果不校验直接执行 `DEL key`，
        就会把 Worker-B 的锁给删了！导致系统并发防线彻底瓦解。
      - 工业解法：释放锁必须使用 Lua 脚本！校验 Value 相等再删除，保证原子性：
        ```lua
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        ```

   ④ 锁续期（看门狗 Watchdog）：
      - 开启后台心跳协程，在业务执行期间每隔一段周期自动延长 TTL，防止业务未完锁被提前释放。
================================================================================
*/

// RedisLockSimulator 模拟分布式锁的完整核心逻辑
type RedisLockSimulator struct {
	mu        sync.Mutex
	store     map[string]string    // 模拟 Redis 的 Key-Value 存储
	expireMap map[string]time.Time // 模拟过期时间
}

func NewRedisLockSimulator() *RedisLockSimulator {
	return &RedisLockSimulator{
		store:     make(map[string]string),
		expireMap: make(map[string]time.Time),
	}
}

// TryLock 尝试获取分布式锁（模拟 SET key token NX PX ttl）
func (r *RedisLockSimulator) TryLock(key, token string, ttl time.Duration) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	// 检查 key 是否存在且未过期
	if exp, exists := r.expireMap[key]; exists {
		if time.Now().Before(exp) {
			// 锁依然被他人持有，抢锁失败
			return false
		}
	}

	// 成功获取锁（原子写入）
	r.store[key] = token
	r.expireMap[key] = time.Now().Add(ttl)
	return true
}

// Unlock 释放分布式锁（模拟 Lua 脚本：先比对 token，匹配才删除）
func (r *RedisLockSimulator) Unlock(key, token string) (bool, string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	currentOwnerToken, exists := r.store[key]
	if !exists {
		return false, "锁已自然过期或不存在"
	}

	// 关键防护：校验持有者身份！
	if currentOwnerToken != token {
		return false, fmt.Sprintf("⚠️ 危险拦截：试图删除非本协程持有的锁！当前锁属于: %s，而你的 token 是: %s", currentOwnerToken, token)
	}

	delete(r.store, key)
	delete(r.expireMap, key)
	return true, "成功释放锁"
}

func main() {
	fmt.Println("======== 1. 模拟 5 个微服务节点并发抢占秒杀活动锁 ========")
	redisMock := NewRedisLockSimulator()
	lockKey := "lock:seckill:iphone16"

	var wg sync.WaitGroup

	for nodeID := 1; nodeID <= 5; nodeID++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			// 生成当前节点的唯一身份标识
			nodeToken := fmt.Sprintf("node_%d_%s", id, uuid.New().String()[:8])

			// 尝试拿锁，TTL 设置为 500ms
			ok := redisMock.TryLock(lockKey, nodeToken, 500*time.Millisecond)
			if ok {
				fmt.Printf("🏆 [节点 %d] 成功抢到分布式锁！Token: %s。开始处理秒杀扣减库存...\n", id, nodeToken)
				time.Sleep(100 * time.Millisecond) // 模拟业务操作

				// 安全释放锁
				success, msg := redisMock.Unlock(lockKey, nodeToken)
				fmt.Printf("🔓 [节点 %d] 释放锁结果: %t (%s)\n", id, success, msg)
			} else {
				fmt.Printf("❌ [节点 %d] 抢锁失败，竞争已被其他节点抢先！\n", id)
			}
		}(nodeID)
	}

	wg.Wait()

	fmt.Println("\n======== 2. 模拟防误删安全防御机制 ========")
	tokenA := "owner_Alice_token"
	tokenB := "owner_Bob_token"

	// Alice 成功获得锁
	redisMock.TryLock("lock:order:1001", tokenA, 1*time.Second)
	fmt.Println("Alice 成功获取订单 1001 的锁")

	// 此时 Bob 试图冒充或因业务错乱尝试释放该锁
	ok, reason := redisMock.Unlock("lock:order:1001", tokenB)
	fmt.Printf("Bob 尝试释放 Alice 的锁 -> 拦截结果: %s\n", reason)

	// Alice 亲自正常释放
	ok, reason = redisMock.Unlock("lock:order:1001", tokenA)
	fmt.Printf("Alice 正常释放自己的锁 -> 结果: %t (%s)\n", ok, reason)
}

func init() {
	_ = context.Background()
}

