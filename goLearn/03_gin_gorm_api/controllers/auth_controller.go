package controllers

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"go-learn/03_gin_gorm_api/database"
	"go-learn/03_gin_gorm_api/middlewares"
	"go-learn/03_gin_gorm_api/models"
)

// RegisterInput 前端注册入参结构体 (Gin 配合 validator 自动参数校验)
type RegisterInput struct {
	Username string `json:"username" binding:"required,min=3,max=32"`
	Password string `json:"password" binding:"required,min=6,max=32"`
	Email    string `json:"email" binding:"omitempty,email"`
}

// LoginInput 前端登录入参结构体
type LoginInput struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// Register 用户注册接口
func Register(c *gin.Context) {
	var input RegisterInput
	// ShouldBindJSON 会自动解析 body JSON，并基于 binding 标签校验字段
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "入参校验失败: " + err.Error()})
		return
	}

	// 检查用户名是否已存在
	var count int64
	database.DB.Model(&models.User{}).Where("username = ?", input.Username).Count(&count)
	if count > 0 {
		c.JSON(http.StatusConflict, gin.H{"code": 409, "message": "用户名已被注册"})
		return
	}

	// 创建新用户并哈希密码
	user := models.User{
		Username: input.Username,
		Email:    input.Email,
	}
	if err := user.SetPassword(input.Password); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "密码加密异常"})
		return
	}

	// 插入数据库
	if err := database.DB.Create(&user).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "保存用户失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "注册成功",
		"data": gin.H{
			"id":       user.ID,
			"username": user.Username,
			"email":    user.Email,
		},
	})
}

// Login 用户登录接口，返回 JWT Token
func Login(c *gin.Context) {
	var input LoginInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": "入参格式错误"})
		return
	}

	var user models.User
	if err := database.DB.Where("username = ?", input.Username).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "用户不存在或密码错误"})
		return
	}

	// 校验哈希密码
	if !user.CheckPassword(input.Password) {
		c.JSON(http.StatusUnauthorized, gin.H{"code": 401, "message": "用户不存在或密码错误"})
		return
	}

	// 颁发 JWT
	token, err := middlewares.GenerateToken(user.ID, user.Username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": 500, "message": "Token 颁发失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code":    200,
		"message": "登录成功",
		"data": gin.H{
			"token":    token,
			"user_id":  user.ID,
			"username": user.Username,
		},
	})
}
