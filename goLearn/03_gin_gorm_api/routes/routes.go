package routes

import (
	"github.com/gin-gonic/gin"

	"go-learn/03_gin_gorm_api/controllers"
	"go-learn/03_gin_gorm_api/middlewares"
)

// SetupRouter 注册所有 API 路由与中间件
func SetupRouter() *gin.Engine {
	// 创建 Gin 引擎
	r := gin.New()

	// 挂载全局中间件
	r.Use(gin.Recovery())                 // 捕获 panic 防止服务崩溃
	r.Use(middlewares.LoggerMiddleware()) // 请求耗时与链路日志
	r.Use(middlewares.CORSMiddleware())   // 前端跨域支持

	// 健康检查接口（容器部署与探针必用）
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "UP",
			"time":   "2026-11-02",
		})
	})

	// 统一 API 路由版本前缀
	v1 := r.Group("/api/v1")
	{
		// 1. 认证模块（无需鉴权）
		authGroup := v1.Group("/auth")
		{
			authGroup.POST("/register", controllers.Register)
			authGroup.POST("/login", controllers.Login)
		}

		// 2. 文章模块
		articleGroup := v1.Group("/articles")
		{
			// 公开接口：读列表、读详情
			articleGroup.GET("", controllers.GetArticles)
			articleGroup.GET("/:id", controllers.GetArticleDetail)

			// 受保护接口：必须携带有效 JWT Token
			authorized := articleGroup.Group("")
			authorized.Use(middlewares.AuthRequired())
			{
				authorized.POST("", controllers.CreateArticle)
			}
		}
	}

	return r
}
