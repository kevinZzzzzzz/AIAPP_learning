package main

import (
	"encoding/json"
	"fmt"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：结构体与接口（面向对象核心）
================================================================================
1. 没有 class，只有结构体 (struct)：
   - JS/TS:
       class User {
         name: string;
         age: number;
         constructor(name: string, age: number) { this.name = name; this.age = age; }
         sayHello() { return `Hello, ${this.name}`; }
       }
   - Go:
       type User struct {
           Name string `json:"name"` // 结构体 Tag，用于 JSON 序列化映射
           Age  int    `json:"age"`
       }
       // 为结构体绑定方法（接收者 Receiver）
       func (u User) SayHello() string { ... }

2. 指针接收者 vs 值接收者：
   - 值接收者 `(u User)`：方法内部拿的是拷贝，修改里面的属性不会影响外部调用者。
   - 指针接收者 `(u *User)`：类似 JS 中修改 `this.age = 20`，能真正持久修改结构体属性！

3. 没有 extends 继承，只有结构体组合 (Composition)：
   - Go 哲学：「组合优于继承」。通过将一个结构体直接「内嵌 (Embed)」到另一个结构体中，
     子结构体自动继承父结构体的所有字段和方法！

4. 接口 (Interface) 与鸭子类型 (Duck Typing)：
   - TS 必须显式声明 `class EmailService implements Notifier`。
   - Go 采用鸭子类型（隐式实现）：“如果一只鸟走起来像鸭子、叫起来像鸭子，那它就是鸭子”。
     只要你的结构体实现了接口定义的所有函数签名，Go 编译器就自动认定你实现了该接口！
     零侵入、极度解耦！
================================================================================
*/

// 1. 定义结构体并打上 JSON Tag（类似 TS 的 interface / DTO）
type User struct {
	Name string `json:"name"`
	Age  int    `json:"age"`
}

// 2. 值接收者方法：只读操作，不修改结构体内部状态
func (u User) Greet() string {
	return fmt.Sprintf("你好，我是 %s，今年 %d 岁", u.Name, u.Age)
}

// 3. 指针接收者方法：修改结构体内部状态（必须传 *User 指针）
func (u *User) CelebrateBirthday() {
	u.Age++ // 成功修改原内存中的 Age
}

// 4. 结构体组合（代替传统面向对象的 extends 继承）
type AdminUser struct {
	User       // 匿名内嵌字段：自动拥有 Name、Age 以及 Greet()、CelebrateBirthday()
	SuperPower string
}

// 5. 定义接口（对比 TS Interface）
type Notifier interface {
	SendNotification(message string) error
}

// 6. 实现接口的具体类型 A：短信通知服务
type SMSNotifier struct {
	PhoneNumber string
}

// 只要实现了 SendNotification 方法，SMSNotifier 就隐式实现了 Notifier 接口，无需写 implements
func (s SMSNotifier) SendNotification(message string) error {
	fmt.Printf("[短信发送] 给 %s 发送通知: %s\n", s.PhoneNumber, message)
	return nil
}

// 7. 实现接口的具体类型 B：邮件通知服务
type EmailNotifier struct {
	EmailAddress string
}

func (e EmailNotifier) SendNotification(message string) error {
	fmt.Printf("[邮件发送] 给 %s 发送通知: %s\n", e.EmailAddress, message)
	return nil
}

// 业务函数：多态调用，面向接口编程
func BroadcastAlert(n Notifier, msg string) {
	_ = n.SendNotification(msg)
}

func main() {
	fmt.Println("======== 1. 结构体创建与方法调用 ========")
	u := User{Name: "Jack", Age: 28}
	fmt.Println(u.Greet())

	// 调用指针接收者方法，年龄自增
	u.CelebrateBirthday()
	fmt.Printf("过完生日后: %s\n", u.Greet())

	fmt.Println("\n======== 2. 结构体内嵌组合（继承模拟） ========")
	admin := AdminUser{
		User:       User{Name: "Root", Age: 35},
		SuperPower: "所有服务器一键重启",
	}
	// 可以直接访问内嵌结构体的字段和方法，无需 admin.User.Name
	fmt.Printf("管理员名字: %s, 年龄: %d, 特权: %s\n", admin.Name, admin.Age, admin.SuperPower)
	fmt.Printf("管理员打招呼: %s\n", admin.Greet())

	fmt.Println("\n======== 3. JSON 序列化与反序列化（前端最熟悉环节） ========")
	// 序列化（等同于 JSON.stringify）
	jsonData, err := json.Marshal(u)
	if err != nil {
		fmt.Println("序列化失败:", err)
		return
	}
	fmt.Printf("JSON 序列化字符串: %s\n", string(jsonData))

	// 反序列化（等同于 JSON.parse）
	jsonStr := `{"name":"Bob","age":22}`
	var newUser User
	// 必须传入 &newUser 指针，这样 json.Unmarshal 才能把解析结果写入 newUser 内存中
	if err := json.Unmarshal([]byte(jsonStr), &newUser); err == nil {
		fmt.Printf("JSON 反序列化成功: %+v\n", newUser)
	}

	fmt.Println("\n======== 4. 接口多态与鸭子类型（隐式实现） ========")
	sms := SMSNotifier{PhoneNumber: "13800138000"}
	email := EmailNotifier{EmailAddress: "admin@example.com"}

	// 面向接口传参，不同实现触发不同行为
	BroadcastAlert(sms, "服务器 CPU 占用超过 90%！")
	BroadcastAlert(email, "数据库主从同步延迟超过 5 秒！")

	fmt.Println("\n======== 5. 类型断言 (Type Assertion - 类似 TS as) ========")
	var anyNotifier Notifier = email

	// 尝试断言为 EmailNotifier
	if emailService, ok := anyNotifier.(EmailNotifier); ok {
		fmt.Printf("成功断言为邮件服务！邮箱地址是: %s\n", emailService.EmailAddress)
	}
}
