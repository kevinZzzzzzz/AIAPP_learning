package main

import "fmt"

/*
================================================================================
💡 前端 vs Go 核心对照卡片：切片 (Slice) 与 哈希表 (Map)
================================================================================
1. 数组 (Array) vs 切片 (Slice)：
   - JS: 只有动态数组 `let arr = [1, 2, 3]`，长度可变，自带 push/pop/splice。
   - Go:
     - 数组是固定长度的：`var arr [5]int`，长度是类型的一部分，实际开发很少直接用。
     - 切片 (Slice) 是动态数组：`s := []int{1, 2, 3}`。切片本质是一个包含
       「指向底层数组的指针、长度 len、容量 cap」的三元结构体。
     - 追加元素必须用内置函数 `append`：`s = append(s, 4)` （类似 JS 的 arr.push(4)）。

2. 哈希表 (Map) vs JS Object / ES6 Map：
   - JS: 普通对象 `{ name: "Tom", age: 18 }` 或 `new Map()`。
   - Go: `map[KeyType]ValueType`，键必须支持 `==` 比较（如 string, int）。
   - 注意坑点：未初始化的 map 是 `nil`，读取不会报错，但**向 nil map 写入会直接 panic crash**！
     因此声明后务必用 `make(map[string]int)` 初始化！
   - 判断键是否存在（Comma-ok 惯用法）：
     - JS: `if ('age' in obj)` 或 `if (map.has('age'))`
     - Go: `val, ok := userMap["age"]`，如果 ok 为 false 说明键根本不存在。
================================================================================
*/

func main() {
	fmt.Println("======== 1. 切片 Slice 的创建与操作（对比 JS Array） ========")

	// 方式 A：字面量创建切片（类似 JS let list = ["React", "Vue", "Angular"]）
	frameworks := []string{"React", "Vue", "Angular"}
	fmt.Printf("初始切片: %v, 长度 len: %d, 容量 cap: %d\n", frameworks, len(frameworks), cap(frameworks))

	// 类似 JS push: 使用 append 追加元素（注意必须重新赋值回原切片）
	frameworks = append(frameworks, "Next.js", "Nuxt.js")
	fmt.Printf("追加后切片: %v, 新长度: %d\n", frameworks, len(frameworks))

	// 方式 B：使用 make 创建预分配容量的切片（后端性能优化的核心技巧）
	// make([]类型, 初始长度 len, 预留容量 cap)
	// 如果知道大约有 1000 个元素，预先 make 可以避免底层数组频繁重新扩容分配内存
	users := make([]string, 0, 10)
	users = append(users, "User_01", "User_02")
	fmt.Printf("make 切片: %v (len: %d, cap: %d)\n", users, len(users), cap(users))

	// 切片截取（类似 JS 的 slice(start, end)，左闭右开区间）
	subList := frameworks[1:3] // 索引 1 到 2
	fmt.Printf("frameworks[1:3] 截取结果: %v\n", subList)

	// 切片删除指定索引的元素（Go 没有 splice，利用 append 巧妙组合）
	// 例如删除索引为 2 的元素 ("Angular")
	indexToRemove := 2
	frameworks = append(frameworks[:indexToRemove], frameworks[indexToRemove+1:]...)
	fmt.Printf("删除索引 2 后的切片: %v\n", frameworks)

	fmt.Println("\n======== 2. 映射 Map 的创建与操作（对比 JS Object / Map） ========")

	// 方式 A：使用 make 初始化空 map
	scoreMap := make(map[string]int)
	scoreMap["Alice"] = 95
	scoreMap["Bob"] = 88
	scoreMap["Charlie"] = 72

	// 方式 B：字面量直接初始化
	userRoles := map[string]string{
		"admin":  "全站读写",
		"editor": "文章管理",
		"viewer": "只读访客",
	}
	fmt.Printf("userRoles: %v\n", userRoles)

	// 读取不存在的 key：Go 会返回该类型的「零值」（不会报错也不会返回 undefined）
	fmt.Printf("读取不存在的 key 'guest': [%s]\n", userRoles["guest"]) // 输出空字符串 ""

	// Comma-ok 惯用法：优雅判断 key 是否真正存在
	if desc, exists := userRoles["admin"]; exists {
		fmt.Printf("找到角色 'admin': %s\n", desc)
	}

	if _, exists := userRoles["superadmin"]; !exists {
		fmt.Println("角色 'superadmin' 不存在！")
	}

	// 删除 key（等同于 JS 的 delete obj.key 或 map.delete(key)）
	delete(scoreMap, "Charlie")
	fmt.Printf("删除 Charlie 后的 scoreMap: %v\n", scoreMap)

	fmt.Println("\n======== 3. for-range 遍历 Map ========")
	// 注意：Go 的 map 遍历顺序是无序的（底层哈希随机化保证安全）
	for name, score := range scoreMap {
		fmt.Printf("  学生: %s => 分数: %d\n", name, score)
	}
}
