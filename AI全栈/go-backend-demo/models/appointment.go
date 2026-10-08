package models

import "time"

// Appointment GORM 数据库结构体
type Appointment struct {
	ID          uint      `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID      uint      `gorm:"not null" json:"user_id"`
	Title       string    `gorm:"type:varchar(100);not null" json:"title"`
	Description string    `gorm:"type:varchar(500)" json:"description"`
	Status      string    `gorm:"type:varchar(20);default:'PENDING'" json:"status"`
	CreatedAt   time.Time `json:"created_at"`
}
