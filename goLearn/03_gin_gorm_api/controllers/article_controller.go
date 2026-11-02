package controllers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"go-learn/03_gin_gorm_api/cache"
	"go-learn/03_gin_gorm_api/database"
	"go-learn/03_gin_gorm_api/models"
)

type CreateArticleInput struct {
	Title   string `json:"title" binding:"required,min=2,max=200"`
	Content string `json:"content" binding:"required"`
}

// CreateArticle 创建文章（需登录鉴权）
func CreateArticle(c *gin.Context) {
	var input CreateArticleInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "校验失败: " + err.Error()})
		return
	}

	// 从中间件存入的上下文中提取当前用户 ID
	userID := c.MustGet("userID").(uint)

	article := models.Article{
		Title:   input.Title,
		Content: input.Content,
		UserID:  userID,
	}

	if err := database.DB.Create(&article).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "创建文章失败: " + err.Error()})
		return
	}

	// 增删改后使列表缓存失效（Cache-Aside 经典策略：先写库，后删缓存）
	if cache.IsHealthy {
		ctx := context.Background()
		_ = cache.Rdb.Del(ctx, "cache:articles:list").Err()
	}

	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "文章创建成功",
		"data":    article,
	})
}

// GetArticles 获取文章列表（含分页 & Redis Cache-Aside 缓存实战）
func GetArticles(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("pageSize", "10"))
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 10
	}

	cacheKey := fmt.Sprintf("cache:articles:list:%d:%d", page, pageSize)
	ctx := context.Background()

	// 1. 尝试从 Redis 缓存读取
	if cache.IsHealthy {
		cachedJSON, err := cache.Rdb.Get(ctx, cacheKey).Result()
		if err == nil && cachedJSON != "" {
			var cachedList []models.Article
			if jsonErr := json.Unmarshal([]byte(cachedJSON), &cachedList); jsonErr == nil {
				c.Header("X-Cache-Status", "HIT") // 命中缓存
				c.JSON(http.StatusOK, gin.H{
					"code":    200,
					"message": "获取成功 (from Redis Cache)",
					"data":    cachedList,
				})
				return
			}
		}
	}

	// 2. 缓存未命中（Cache Miss），查询数据库
	var articles []models.Article
	offset := (page - 1) * pageSize

	// 联表预加载作者基础信息，防止 N+1 查询
	err := database.DB.Preload("Author").
		Limit(pageSize).
		Offset(offset).
		Order("created_at desc").
		Find(&articles).Error

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "查询数据库失败"})
		return
	}

	// 3. 将数据库查询结果回写到 Redis，设置 60 秒过期时间（防止冷数据常驻内存）
	if cache.IsHealthy {
		dataBytes, _ := json.Marshal(articles)
		_ = cache.Rdb.Set(ctx, cacheKey, string(dataBytes), 60*time.Second).Err()
	}

	c.Header("X-Cache-Status", "MISS")
	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "获取成功 (from Database)",
		"data":    articles,
	})
}

// GetArticleDetail 获取文章详情并增加浏览量
func GetArticleDetail(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "非法文章 ID"})
		return
	}

	var article models.Article
	if err := database.DB.Preload("Author").First(&article, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": 404, "message": "文章不存在"})
		return
	}

	// 原子递增浏览量：避免并发更新丢失
	database.DB.Model(&article).UpdateColumn("view_count", article.ViewCount+1)
	article.ViewCount++

	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "获取成功",
		"data":    article,
	})
}
