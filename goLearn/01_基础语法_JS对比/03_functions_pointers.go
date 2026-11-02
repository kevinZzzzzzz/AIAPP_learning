package main

import "fmt"

/*
================================================================================
💡 前端 vs Go 核心对照卡片：函数与指针（攻克前端最大心智关卡）
================================================================================
1. 多返回值机制：
   - JS: 函数只能 return 单个值（若要返回多个，必须包装成数组 [a, b] 或对象 {a, b}）。
   - Go: 原生支持多返回值！`func divide(a, b int) (int, error)`，是 Go 处理错误的核心基石。

2. defer 延迟执行机制：
   - JS: 类似 Promise.finally 或 try...finally。
   - Go: `defer` 语句会在当前外层函数「返回前一刻」逆序（后进先出 LIFO）执行。
         常用于：释放锁、关闭文件流、关闭网络连接、HTTP 响应体关闭。

3. 指针机制 (Pointer) —— 前端同学不要怕！用 JS 概念秒懂：
   - JS 中：基本类型 (number, string, boolean) 传值；对象、数组传的是「引用」（修改会影响原对象）。
   - Go 中：默认**全部是值传递（全量浅拷贝）**！即使你传一个巨大的结构体，也会完整复制一份。
   - 那么当你想在函数内部修改外层变量，或者不想深拷贝大对象时怎么办？
     答：传指针！
     - `&x`：取变量 x 的内存地址 (Address Of)
     - `*p`：解引用 (Dereference)，访问或修改指针指向的真正内存数据
================================================================================
*/

func main() {
	fmt.Println("======== 1. 多返回值与空白占位符 ========")
	quotient, remainder := divide(10, 3)
	fmt.Printf("10 / 3 = 商: %d, 余数: %d\n", quotient, remainder)

	// 如果只要余数，不需要商，用下划线 _ 忽略
	_, onlyRemainder := divide(17, 5)
	fmt.Printf("17 / 5 的余数是: %d\n", onlyRemainder)

	fmt.Println("\n======== 2. 函数是一等公民 & 闭包 (JS 同款爽感) ========")
	// Go 的闭包用法与 JS 完全一致，内层函数能够持有外层作用域的状态
	counter := makeCounter(100)
	fmt.Printf("计数器调用 1: %d\n", counter())
	fmt.Printf("计数器调用 2: %d\n", counter())
	fmt.Printf("计数器调用 3: %d\n", counter())

	fmt.Println("\n======== 3. defer 延迟执行与执行顺序 (LIFO 栈) ========")
	demonstrateDefer()

	fmt.Println("\n======== 4. 指针实战：值传递 vs 指针传递 ========")
	userAge := 20

	// 尝试值传递修改（类似 JS 传入原始 number）
	modifyByValue(userAge)
	fmt.Printf("值传递后 userAge: %d (原值未发生任何改变！)\n", userAge)

	// 指针传递修改：传入 userAge 的内存地址 &userAge
	modifyByPointer(&userAge)
	fmt.Printf("指针传递后 userAge: %d (原值被成功就地修改！)\n", userAge)

	fmt.Println("\n======== 5. 理解内存地址可视化 ========")
	score := 99
	scorePtr := &score // scorePtr 是一个 *int 类型指针
	fmt.Printf("变量 score 的值: %d\n", score)
	fmt.Printf("变量 score 的内存地址 (&score): %p\n", scorePtr)
	fmt.Printf("通过指针解引用 (*scorePtr) 取出值: %d\n", *scorePtr)

	// 直接通过指针修改底层内存的值
	*scorePtr = 100
	fmt.Printf("通过 *scorePtr = 100 修改后，原始 score 的值变为: %d\n", score)
}

// 多返回值函数
func divide(dividend, divisor int) (int, int) {
	q := dividend / divisor
	r := dividend % divisor
	return q, r
}

// 闭包生成器：返回一个返回 int 的函数 func() int
func makeCounter(initial int) func() int {
	count := initial
	return func() int {
		count++
		return count
	}
}

// defer 延迟调用演示
func demonstrateDefer() {
	fmt.Println("  函数开始执行...")

	// 注册 defer，这三句话会在函数即将 return 退出时，按「后进先出 (LIFO)」顺序执行
	defer fmt.Println("  [defer 1] 最先注册，最后执行")
	defer fmt.Println("  [defer 2] 中间注册，倒数第二执行")
	defer fmt.Println("  [defer 3] 最后注册，最先执行")

	fmt.Println("  函数业务逻辑执行完毕，准备返回...")
}

// 值传递：形参 age 是原始值的独立拷贝
func modifyByValue(age int) {
	age += 10
}

// 指针传递：形参 agePtr 是一个指向 int 内存的指针 (*int)
func modifyByPointer(agePtr *int) {
	// *agePtr 代表拿到这块内存里的值，并将其修改
	*agePtr += 10
}
