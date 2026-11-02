package models

import (
	"time"

	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

/*
💡 前端 vs Go 模型层对比：
- 在 TypeORM/Prisma 中：定义 @Entity() / model User { id, email, password }
- 在 GORM 中：使用 struct + 结构体 Tag：
  `gorm:"primaryKey"`：主键
  `gorm:"uniqueIndex"`：唯一约束
  `json:"-"`：JSON 序列化忽略字段（密码绝不能返回给前端！）
*/

type User struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	Username  string         `gorm:"size:64;uniqueIndex;not null" json:"username"`
	Password  string         `gorm:"size:255;not null" json:"-"` // 关键：json:"-" 避免密码泄露
	Email     string         `gorm:"size:128" json:"email"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"` // GORM 软删除（Soft Delete）
}

// SetPassword 使用 bcrypt 强哈希加密明文密码
func (u *User) SetPassword(plainPassword string) error {
	hashedBytes, err := bcrypt.GenerateFromPassword([]byte(plainPassword), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	u.Password = string(hashedBytes)
	return nil
}

// CheckPassword 校验前端输入的明文密码与哈希密文是否匹配
func (u *User) CheckPassword(plainPassword string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(u.Password), []byte(plainPassword))
	return err == nil
}
