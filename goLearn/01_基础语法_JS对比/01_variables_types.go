package main

import (
	"fmt"
	"reflect"
)

/*
================================================================================
💡 前端 vs Go 核心对照卡片：变量与类型
================================================================================
1. 声明方式：
   - JS/TS:  let a = 1; const b = "hello"; var c = true;
   - Go:     var a int = 1         // 显式声明类型
             var a = 1             // 类型推导
             a := 1                // 短变量声明 (只能在函数体内使用，最常用！)
             const B = "hello"     // 常量声明

2. 零值机制 (Zero Value) - [极重要差异]：
   - JS: 声明不赋值是 `undefined`，访问对象不存在属性也是 `undefined`。
   - Go: 没有 `undefined`！所有类型声明后都有确定的「零值」：
         int/float -> 0
         string    -> "" (空字符串)
         bool      -> false
         pointer/slice/map/channel/interface -> nil

3. 类型转换：
   - JS: 隐式类型转换臭名昭著 (例如 `1 + "2" = "12"`，`[] == false` 为 true)。
   - Go: 绝无隐式转换！必须显式强转，例如 `int64(a)`、`float64(b)`。
================================================================================
*/

func main() {
	fmt.Println("======== 1. 变量声明与短变量语法 ========")

	// 方式一：标准声明
	var username string = "Alice"

	// 方式二：类型推导（类似 TS 的推导）
	var age = 25

	// 方式三：短变量声明 := （最地道、最常用的写法）
	isFrontendDev := true

	fmt.Printf("username: %s (类型: %T)\n", username, username)
	fmt.Printf("age: %d (类型: %T)\n", age, age)
	fmt.Printf("isFrontendDev: %t (类型: %T)\n", isFrontendDev, isFrontendDev)

	fmt.Println("\n======== 2. Go 的「零值」机制 vs JS undefined ========")
	var defaultInt int
	var defaultFloat float64
	var defaultBool bool
	var defaultString string
	var defaultPointer *int

	// 在 JS 中，let a; console.log(a) -> undefined
	// 在 Go 中永远有安全默认值，绝对不会产生 "undefined is not a function"
	fmt.Printf("默认 int: [%d]\n", defaultInt)
	fmt.Printf("默认 float: [%.2f]\n", defaultFloat)
	fmt.Printf("默认 bool: [%t]\n", defaultBool)
	fmt.Printf("默认 string: [%s] (长度: %d)\n", defaultString, len(defaultString))
	fmt.Printf("默认 指针: [%v] (类似 JS 的 null)\n", defaultPointer)

	fmt.Println("\n======== 3. 常量声明与 iota 枚举 ========")
	// JS: const HTTP_OK = 200;
	// TS: enum Role { User, Admin }
	const (
		StatusOK       = 200
		StatusNotFound = 404
	)

	// Go 没有 enum 关键字，通过 const + iota 优雅实现枚举自增
	const (
		RoleGuest = iota // 0
		RoleUser         // 1
		RoleAdmin        // 2
	)
	fmt.Printf("StatusOK: %d, RoleUser: %d, RoleAdmin: %d\n", StatusOK, RoleUser, RoleAdmin)

	fmt.Println("\n======== 4. 显式类型转换 (拒绝隐式转换) ========")
	var intVal int = 100
	var floatVal float64 = 3.14

	// 下面这句若不强转直接相加，Go 编译器会报错：invalid operation (mismatched types)
	// var sum = intVal + floatVal // 编译报错！
	var sum = float64(intVal) + floatVal // 必须显式转换
	fmt.Printf("显式转换后的计算结果: %.2f\n", sum)

	fmt.Println("\n======== 5. 动态类型检测（类似 JS typeof） ========")
	var genericVal interface{} = "I am Fullstack" // interface{} 类似于 TS 的 any 或 unknown
	fmt.Printf("值: %v, 类型: %v\n", genericVal, reflect.TypeOf(genericVal))
}
