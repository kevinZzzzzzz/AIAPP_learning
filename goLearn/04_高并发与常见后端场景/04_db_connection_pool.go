package main

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

/*
================================================================================
💡 前端转全栈必备：数据库连接池 (Connection Pool) 深度调优
================================================================================
1. 为什么不能“来一个请求就连一次数据库”？
   - 建立一次 TCP 握手 + TLS 认证 + 数据库身份认证通常需要 20ms ~ 50ms。
   - MySQL 默认的最大连接数通常只有 151 个。如果并发 500 个请求同时新建连接，
     数据库会直接抛出致命错误：`Error 1040: Too many connections`，导致全站瘫痪！
   - 连接池就像一个「共享租借站」：预先建立好一批长连接，请求来了借一个用，用完立即归还复用！

2. Go 标准库 sql.DB 四大黄金参数：
   - `SetMaxOpenConns(n)`：最大打开连接数（正在使用 + 空闲总和）。
     - 生产建议：根据数据库规格设置。例如 4 核 8G MySQL，设为 100 ~ 200 左右即可，
       绝不是设得越大越好（过大反而引起数据库剧烈上下文切换）。
   - `SetMaxIdleConns(n)`：最大空闲连接数。
     - 生产建议：尽量接近 MaxOpenConns（如 50 ~ 100），避免请求洪峰过后连接被频繁销毁又重建。
   - `SetConnMaxLifetime(d)`：单个连接的最长生命周期。
     - 生产建议：设为 30分钟 ~ 1小时。防止阿里云/腾讯云负载均衡或交换机防火墙
       单方面静默断开长时间空闲的 TCP 连接，引发 `invalid connection` 错误。
   - `SetConnMaxIdleTime(d)`：连接最大空闲时间。超过该时间未被使用的空闲连接将被自动释放。

3. 运行时监控指标 (db.Stats)：
   - `OpenConnections`：当前存活连接总数
   - `InUse`：当前正在执行 SQL 的忙碌连接数
   - `Idle`：当前正在池中待命的空闲连接数
   - `WaitCount`：当连接池被借空时，后面排队等待借连接的请求次数
   - `WaitDuration`：累计排队等待总耗时
================================================================================
*/

type BenchmarkLog struct {
	ID        uint `gorm:"primaryKey"`
	Message   string
	CreatedAt time.Time
}

func main() {
	fmt.Println("======== 1. 初始化数据库与连接池配置 ========")
	// 初始化 SQLite 内存数据库作为实验环境
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent), // 静默模式
	})
	if err != nil {
		log.Fatalf("连接数据库失败: %v", err)
	}

	_ = db.AutoMigrate(&BenchmarkLog{})

	// 获取底层的 *sql.DB 进行连接池参数调优
	sqlDB, err := db.DB()
	if err != nil {
		log.Fatalf("获取 sql.DB 失败: %v", err)
	}

	// 调优参数设定：限制最大只能同时开 5 个连接，空闲保留 2 个
	sqlDB.SetMaxOpenConns(5)
	sqlDB.SetMaxIdleConns(2)
	sqlDB.SetConnMaxLifetime(10 * time.Minute)
	sqlDB.SetConnMaxIdleTime(3 * time.Minute)

	fmt.Println("连接池参数设定完毕: MaxOpenConns = 5, MaxIdleConns = 2")

	fmt.Println("\n======== 2. 并发模拟 20 个请求争抢有限的 5 个连接 ========")
	var wg sync.WaitGroup

	for i := 1; i <= 20; i++ {
		wg.Add(1)
		go func(taskID int) {
			defer wg.Done()

			// 执行数据库插入操作（内部会自动从连接池借出连接，执行完毕自动归还）
			record := BenchmarkLog{
				Message:   fmt.Sprintf("日志记录_%02d", taskID),
				CreatedAt: time.Now(),
			}
			_ = db.Create(&record).Error

			// 模拟微小的耗时
			time.Sleep(10 * time.Millisecond)
		}(i)
	}

	// 采样打印当前连接池的实时状态
	for i := 0; i < 3; i++ {
		stats := sqlDB.Stats()
		fmt.Printf("  [连接池监控采样] 存活连接: %d | 正在使用(InUse): %d | 闲置待命(Idle): %d | 排队等待次数: %d\n",
			stats.OpenConnections,
			stats.InUse,
			stats.Idle,
			stats.WaitCount,
		)
		time.Sleep(15 * time.Millisecond)
	}

	wg.Wait()

	fmt.Println("\n======== 3. 并发执行完成后的连接池最终状态 ========")
	finalStats := sqlDB.Stats()
	fmt.Printf("最终连接状态：\n")
	fmt.Printf("  当前连接总数: %d\n", finalStats.OpenConnections)
	fmt.Printf("  正在使用的连接: %d (所有连接已安全归还！)\n", finalStats.InUse)
	fmt.Printf("  处于池中的空闲连接: %d (严格受控在 MaxIdleConns = 2 之内！)\n", finalStats.Idle)
	fmt.Printf("  发生排队借连接的总次数: %d\n", finalStats.WaitCount)
	fmt.Printf("  排队累计总耗时: %v\n", finalStats.WaitDuration)
	fmt.Println("🎉 连接池调优成功：既扛住了高并发，又没有无限制膨胀挤爆数据库！")
}

