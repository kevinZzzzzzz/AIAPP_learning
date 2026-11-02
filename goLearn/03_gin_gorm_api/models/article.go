package models

import (
	"time"

	"gorm.io/gorm"
)

/*
💡 前端 vs Go 关系映射对比：
- 在 Prisma 中：author User @relation(fields: [authorId], references: [id])
- 在 GORM 中：
  `UserID uint` 作为外键字段
  `Author User` 作为外键关联结构体对象
  查询时可以使用 `.Preload("Author")` 一键联表加载（等同于 Prisma 的 include: { author: true }）
*/

type Article struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	Title     string         `gorm:"size:255;not null" json:"title" binding:"required"`
	Content   string         `gorm:"type:text;not null" json:"content" binding:"required"`
	ViewCount int            `gorm:"default:0" json:"view_count"`
	UserID    uint           `gorm:"index;not null" json:"user_id"`
	Author    User           `gorm:"foreignKey:UserID" json:"author"` // 关联 User 模型
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
}
