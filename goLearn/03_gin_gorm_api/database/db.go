package database

import (
	"log"
	"time"

	"github.com/glebarez/sqlite" // 纯 Go 实现的 SQLite 驱动，无 CGO 依赖，任何平台直接跑！
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"go-learn/03_gin_gorm_api/models"
)

var DB *gorm.DB

// InitDB 初始化数据库连接与连接池
func InitDB() *gorm.DB {
	var err error

	// 1. 打开数据库（本地开发默认使用嵌入式纯 Go SQLite 文件库 app.db）
	// 若切换为 MySQL，只需替换为:
	// dsn := "user:password@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=True&loc=Local"
	// DB, err = gorm.Open(mysql.Open(dsn), &gorm.Config{...})
	DB, err = gorm.Open(sqlite.Open("app.db"), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info), // 打印每条执行的 SQL
	})
	if err != nil {
		log.Fatalf("无法连接数据库: %v", err)
	}

	// 2. 自动迁移（Auto Migrate）表结构（类似 Prisma db push / TypeORM synchronize）
	err = DB.AutoMigrate(&models.User{}, &models.Article{})
	if err != nil {
		log.Fatalf("数据库模型自动迁移失败: %v", err)
	}
	log.Println("✅ 数据库表结构自动迁移成功！")

	// 3. 配置底层的 SQL 连接池 (Connection Pool)
	// 这对高并发服务极其关键！
	sqlDB, err := DB.DB()
	if err != nil {
		log.Fatalf("获取底层 sql.DB 失败: %v", err)
	}

	// 最大空闲连接数（保持在池中等待复用的空闲连接数量）
	sqlDB.SetMaxIdleConns(10)

	// 最大打开连接数（防止高并发瞬间把数据库物理连接数耗尽抛错）
	sqlDB.SetMaxOpenConns(100)

	// 单个连接的最大存活时间（超时自动回收重新建连，防止云服务防火墙单方面断开空闲连接）
	sqlDB.SetConnMaxLifetime(time.Hour)

	return DB
}
