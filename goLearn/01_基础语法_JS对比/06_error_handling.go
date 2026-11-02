package main

import (
	"errors"
	"fmt"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：错误处理机制
================================================================================
1. 错误理念：
   - JS/TS: `try { ... } catch (err) { ... }`
     缺点是调用方常常不知道这个函数到底会不会抛错，容易漏 catch 导致进程 crash。
   - Go: **错误是普通的值 (Errors are values)**！
     函数的最后一个返回值通常是 `error` 接口。调用者必须显式判断 `if err != nil`。
     虽然被戏称为 "if err != nil 地狱"，但这强制保证了代码的健壮性，99% 的潜在漏洞在编写时就被消灭。

2. panic 与 recover (致命异常兜底)：
   - `panic`：相当于 JS 的 `throw new Error("fatal")`，导致当前 Goroutine 崩溃中断。
   - `recover`：必须在 `defer` 函数中调用，能拦截捕获当前协程的 panic，让程序恢复正常！
     （在 Gin 等 Web 框架中，Recovery 中间件就是靠这个防止单个接口报错搞垮整个 Web 服务）。
================================================================================
*/

// 自定义哨兵错误（Sentinel Errors）
var (
	ErrUserNotFound    = errors.New("用户不存在")
	ErrInvalidPassword = errors.New("密码错误，请输入至少 6 位字符")
)

// 模拟登录业务：返回 token 和 error
func Login(username, password string) (string, error) {
	if username == "" {
		return "", errors.New("用户名不能为空")
	}
	if username != "admin" {
		// 返回预定义的哨兵错误
		return "", ErrUserNotFound
	}
	if len(password) < 6 {
		return "", ErrInvalidPassword
	}

	// 成功：返回 token，错误为 nil
	return "mock_jwt_token_header.payload.signature", nil
}

// 模拟可能发生 panic 的底层操作
func dangerousOperation(divisor int) int {
	// 注册 defer recover 兜底拦截 panic（等同于外层 try-catch）
	defer func() {
		if r := recover(); r != nil {
			fmt.Printf("  [recover 拦截到崩溃 panic]: %v (服务安然无恙，继续执行！)\n", r)
		}
	}()

	if divisor == 0 {
		// 主动触发致命异常 panic
		panic("除数绝对不能为 0，触发紧急 panic！")
	}

	return 100 / divisor
}

func main() {
	fmt.Println("======== 1. Go 标准的错误处理 (if err != nil) ========")

	// 场景 A：登录成功
	token, err := Login("admin", "123456")
	if err != nil {
		fmt.Println("登录失败:", err)
	} else {
		fmt.Printf("登录成功！Token: %s\n", token)
	}

	// 场景 B：密码过短
	_, err = Login("admin", "123")
	if err != nil {
		// errors.Is 相当于比对错误类型是否为特定错误
		if errors.Is(err, ErrInvalidPassword) {
			fmt.Println("捕获到特定业务错误: 密码太短！")
		} else {
			fmt.Println("其他错误:", err)
		}
	}

	// 场景 C：用户不存在
	_, err = Login("stranger", "123456")
	if errors.Is(err, ErrUserNotFound) {
		fmt.Println("捕获到特定业务错误: 该用户名未注册！")
	}

	fmt.Println("\n======== 2. panic 与 recover 兜底防御机制 ========")
	fmt.Println("调用正常除法:")
	res := dangerousOperation(5)
	fmt.Printf("5 分之一结果: %d\n", res)

	fmt.Println("调用除以 0 的非法除法 (将触发 panic):")
	_ = dangerousOperation(0)

	fmt.Println("\n======== 3. 证明程序没有崩盘，主流程继续执行！ ========")
	fmt.Println("🎉 Web 服务主线程依然健康运行中，这就是 recover 的作用！")
}
