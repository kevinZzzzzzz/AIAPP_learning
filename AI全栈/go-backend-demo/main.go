package main

import (
	"fmt"

	"go-backend-demo/controllers"
	"go-backend-demo/models"

	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

// CorsMiddleware 跨域 CORS 中间件
func CorsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(240)
			return
		}
		c.Next()
	}
}

func main() {
	// 1. 初始化本地 SQLite 数据库 (自动新建 gorm_demo.db)
	db, err := gorm.Open(sqlite.Open("gorm_demo.db"), &gorm.Config{})
	if err != nil {
		panic("连接数据库失败: " + err.Error())
	}

	// 2. GORM 自动建表 (AutoMigrate)
	db.AutoMigrate(&models.User{}, &models.Appointment{})

	// 3. 装载默认测试数据 (如果表为空)
	var userCount int64
	db.Model(&models.User{}).Count(&userCount)
	if userCount == 0 {
		db.Create(&models.User{Username: "admin", Nickname: "Go全栈超级管理员", Role: "ADMIN"})
		db.Create(&models.User{Username: "kevin", Nickname: "Go前端全栈工程师", Role: "USER"})
		db.Create(&models.User{Username: "alice", Nickname: "AI 智能体开发员", Role: "USER"})

		db.Create(&models.Appointment{UserID: 2, Title: "Go + Gin 高并发全栈架构探究", Description: "探讨单文件极速部署优势", Status: "CONFIRMED"})
		db.Create(&models.Appointment{UserID: 3, Title: "Gin 框架与 React/Vue 接口调试", Description: "前端请求对接", Status: "PENDING"})
		fmt.Println("🌱 Go Gin Backend: 自动初始化默认测试数据成功！")
	}

	// 4. 初始化 Gin 引擎
	r := gin.Default()
	r.Use(CorsMiddleware())

	// 5. 注册 Controllers
	userCtrl := controllers.NewUserController(db)
	apptCtrl := controllers.NewAppointmentController(db)

	r.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"code":    200,
			"message": "🚀 Go Gin 全栈后端服务运行正常！",
			"port":    8081,
		})
	})

	// 注册 API 路由
	api := r.Group("/api")
	{
		// Users
		api.GET("/users", userCtrl.GetUsers)
		api.GET("/users/:id", userCtrl.GetUserByID)
		api.POST("/users", userCtrl.CreateUser)
		api.DELETE("/users/:id", userCtrl.DeleteUser)

		// Appointments
		api.GET("/appointments", apptCtrl.GetAppointments)
		api.POST("/appointments", apptCtrl.CreateAppointment)
	}

	fmt.Println("==================================================")
	fmt.Println("🚀 Go Gin 全栈后端服务已成功启动！")
	fmt.Println("端口: 8081")
	fmt.Println("基础 API: http://localhost:8081/api/users")
	fmt.Println("==================================================")

	// 启动 HTTP 服务，运行在 8081 端口 (避免与 Java/Python 8080/8000 端口冲突)
	r.Run(":8081")
}
