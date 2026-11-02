package main

import "fmt"

/*
================================================================================
💡 前端 vs Go 核心对照卡片：流程控制
================================================================================
1. if 条件判断：
   - JS/TS:  if (score >= 60) { ... }
   - Go:     if score >= 60 { ... }   // 条件不要括号！左大括号 { 必须同行！
             // 支持带初始化短语句 (作用域仅在 if/else 内部，极其常用！)
             if err := doSomething(); err != nil { ... }

2. 循环机制：
   - JS/TS:  for(let i=0; i<n; i++), while(cond), do...while, for...of, for...in, forEach
   - Go:     **天下唯有 for！** 没有 while，没有 do-while。
             for i := 0; i < n; i++ { ... }       // 标准三段式
             for cond { ... }                    // 相当于 JS 的 while(cond)
             for { ... }                         // 相当于 JS 的 while(true) 死循环
             for index, val := range slice { ... } // 相当于 JS 的 for...of / entries()

3. switch-case 分支：
   - JS: 每个 case 必须手动加 break; 否则会穿透击穿执行下一个 case。
   - Go: 默认自带 break！无需手动写 break。如果真想穿透，必须显式声明 fallthrough。
         switch 甚至可以不跟表达式，直接替代冗长的 if-else 链。
================================================================================
*/

func main() {
	fmt.Println("======== 1. if-else 与初始化短语句 ========")
	score := 85

	// 方式一：标准 if-else（注意：条件表达式绝不加圆括号）
	if score >= 90 {
		fmt.Println("等级: A")
	} else if score >= 80 {
		fmt.Println("等级: B")
	} else {
		fmt.Println("等级: C")
	}

	// 方式二：Go 独有的 if 短变量初始化语句
	// 在进入条件判定前先执行一段语句，定义出来的变量只在当前 if-else 块有效，不污染外层作用域
	// 前端对比：在 JS 中，你通常需要在 if 外面 let res = calc(); 然后 if(res > 10) ...
	if result := calculateDiscount(score); result > 10 {
		fmt.Printf("命中大促折扣: %d%%\n", result)
	} else {
		fmt.Printf("未达到大促阈值，基础折扣: %d%%\n", result)
	}
	// fmt.Println(result) // 编译报错：undefined: result （作用域隔离非常干净）

	fmt.Println("\n======== 2. for 循环的四种形态（Go 唯有 for） ========")

	// 形态 1：经典三段式 (等同于 for (let i = 0; i < 3; i++))
	fmt.Print("标准三段式: ")
	for i := 0; i < 3; i++ {
		fmt.Printf("%d ", i)
	}
	fmt.Println()

	// 形态 2：条件循环 (等同于 JS while (count < 3))
	fmt.Print("while 形态: ")
	count := 0
	for count < 3 {
		fmt.Printf("%d ", count)
		count++
	}
	fmt.Println()

	// 形态 3：无限死循环 (等同于 JS while (true))
	fmt.Print("无限循环 + break 退出: ")
	n := 0
	for {
		if n >= 3 {
			break // 显式退出循环
		}
		fmt.Printf("%d ", n)
		n++
	}
	fmt.Println()

	// 形态 4：for-range 遍历切片/数组（等同于 JS 的 for...of 或 entries()）
	techStack := []string{"Vue", "React", "Node", "Go"}
	fmt.Println("for-range 遍历:")
	for index, item := range techStack {
		fmt.Printf("  索引 [%d] => 技术栈: %s\n", index, item)
	}

	// 如果只需要值，不需要索引，用空白标识符 _ 忽略它（Go 不允许定义无用变量）
	fmt.Print("忽略索引: ")
	for _, item := range techStack {
		fmt.Printf("[%s] ", item)
	}
	fmt.Println()

	fmt.Println("\n======== 3. switch-case 分支 ========")

	// 特性 A：默认自带 break，无需担心忘写 break 穿透！
	role := "admin"
	switch role {
	case "admin":
		fmt.Println("权限: 超级管理员，拥有全部权限")
	case "editor":
		fmt.Println("权限: 编辑员，仅文章发布权限")
	case "user", "guest": // 一个 case 匹配多个值，相当于 JS 的 if (role === 'user' || role === 'guest')
		fmt.Println("权限: 普通访客，仅只读权限")
	default:
		fmt.Println("权限: 未知角色")
	}

	// 特性 B：无表达式 switch，替代臃肿的 if-else-if
	hour := 14
	switch {
	case hour < 12:
		fmt.Println("上午好！精力充沛写前端")
	case hour < 18:
		fmt.Println("下午好！深入精进 Go 后端")
	default:
		fmt.Println("晚上好！高并发系统压测中")
	}
}

func calculateDiscount(score int) int {
	return score / 5
}
