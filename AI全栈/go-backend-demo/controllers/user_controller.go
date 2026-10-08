package controllers

import (
	"strconv"

	"go-backend-demo/common"
	"go-backend-demo/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type UserController struct {
	DB *gorm.DB
}

func NewUserController(db *gorm.DB) *UserController {
	return &UserController{DB: db}
}

// GetUsers GET /api/users
func (uc *UserController) GetUsers(c *gin.Context) {
	var users []models.User
	uc.DB.Find(&users)
	common.Success(c, users)
}

// GetUserByID GET /api/users/:id
func (uc *UserController) GetUserByID(c *gin.Context) {
	idStr := c.Param("id")
	id, _ := strconv.Atoi(idStr)

	var user models.User
	if err := uc.DB.First(&user, id).Error; err != nil {
		common.Error(c, 404, "找不到该用户")
		return
	}
	common.Success(c, user)
}

// CreateUser POST /api/users
func (uc *UserController) CreateUser(c *gin.Context) {
	var user models.User
	if err := c.ShouldBindJSON(&user); err != nil {
		common.Error(c, 400, "参数解析失败: "+err.Error())
		return
	}
	uc.DB.Create(&user)
	common.SuccessWithMessage(c, "用户创建成功", user)
}

// DeleteUser DELETE /api/users/:id
func (uc *UserController) DeleteUser(c *gin.Context) {
	idStr := c.Param("id")
	id, _ := strconv.Atoi(idStr)

	uc.DB.Delete(&models.User{}, id)
	common.SuccessWithMessage(c, "成功删除用户", nil)
}
