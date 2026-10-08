package models

import "time"

// User GORM 数据库结构体
type User struct {
	ID        uint      `gorm:"primaryKey;autoIncrement" json:"id"`
	Username  string    `gorm:"type:varchar(50);uniqueIndex;not null" json:"username"`
	Nickname  string    `gorm:"type:varchar(100);not null" json:"nickname"`
	Role      string    `gorm:"type:varchar(50);default:'USER'" json:"role"`
	CreatedAt time.Time `json:"created_at"`
}
