package controllers

import (
	"strconv"

	"go-backend-demo/common"
	"go-backend-demo/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AppointmentController struct {
	DB *gorm.DB
}

func NewAppointmentController(db *gorm.DB) *AppointmentController {
	return &AppointmentController{DB: db}
}

// GetAppointments GET /api/appointments
func (ac *AppointmentController) GetAppointments(c *gin.Context) {
	userIDStr := c.Query("userId")
	var appointments []models.Appointment

	if userIDStr != "" {
		userID, _ := strconv.Atoi(userIDStr)
		ac.DB.Where("user_id = ?", userID).Find(&appointments)
	} else {
		ac.DB.Find(&appointments)
	}

	common.Success(c, appointments)
}

// CreateAppointment POST /api/appointments
func (ac *AppointmentController) CreateAppointment(c *gin.Context) {
	var appt models.Appointment
	if err := c.ShouldBindJSON(&appt); err != nil {
		common.Error(c, 400, "参数解析失败: "+err.Error())
		return
	}
	if appt.Status == "" {
		appt.Status = "PENDING"
	}
	ac.DB.Create(&appt)
	common.SuccessWithMessage(c, "预约创建成功", appt)
}
