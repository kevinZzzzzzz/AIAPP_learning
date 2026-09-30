"""
Python 高阶函数、列表推导式与数据处理 —— JS/TS 开发者对比学习指南
===================================================================
在前端开发中，我们天天使用 Array.prototype.map / filter / reduce。
在 Python 中，除了 map/filter 外，【列表推导式 (List Comprehension)】才是最地道、最优雅、也是 AI 开发中最常用的写法！

运行方法：python 02_高阶函数与列表推导式_JS对比.py
"""

from typing import List, Dict, Any
from functools import reduce


def demo_1_map_transform():
    print("\n--- 1. 数组转换 (Array.prototype.map vs 列表推导式) ---")
    
    scores = [60, 75, 88, 92, 100]
    
    # JS: const doubled = scores.map(x => x * 2);
    # Python 方式 A: 列表推导式 [表达式 for 变量 in 迭代对象] （🔥推荐！最 Pythonic）
    doubled = [x * 2 for x in scores]
    print(f"列表推导式 (x * 2): {doubled}")

    # Python 方式 B: map 函数配合 lambda (匿名函数)
    # JS: const doubled2 = scores.map(x => x * 2);
    doubled_map = list(map(lambda x: x * 2, scores))
    print(f"map + lambda 方式: {doubled_map}")

    # 实战 AI 场景：清洗用户输入的 Prompt 列表
    raw_prompts = ["  hello AI  ", "  Explain Quantum Physics ", "  write a python script  "]
    # JS: const clean = raw_prompts.map(p => p.trim().toLowerCase());
    clean_prompts = [p.strip().lower() for p in raw_prompts]
    print(f"Prompt 清洗结果: {clean_prompts}")


def demo_2_filter_selection():
    print("\n--- 2. 数组过滤 (Array.prototype.filter vs 带条件的推导式) ---")
    
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # JS: const evens = numbers.filter(n => n % 2 === 0);
    # Python 列表推导式 + if 条件: [表达式 for 变量 in 迭代对象 if 条件]
    evens = [n for n in numbers if n % 2 == 0]
    print(f"过滤偶数: {evens}")

    # 同时进行 map 和 filter：挑选偶数并取平方
    # JS: const evenSquares = numbers.filter(n => n % 2 === 0).map(n => n ** 2);
    even_squares = [n ** 2 for n in numbers if n % 2 == 0]
    print(f"过滤偶数并平方: {even_squares}")


def demo_3_find_some_every():
    print("\n--- 3. 数组查找与测试 (find, some, every vs Python 原生) ---")
    
    users = [
        {"id": 1, "name": "Alice", "role": "admin", "active": True},
        {"id": 2, "name": "Bob", "role": "user", "active": False},
        {"id": 3, "name": "Charlie", "role": "user", "active": True},
    ]

    # === A. Find (查找单个符合条件的元素) ===
    # JS: const admin = users.find(u => u.role === "admin");
    # Python: 使用 next() 结合生成器表达式 (如果找不到返回 None)
    admin = next((u for u in users if u["role"] == "admin"), None)
    print(f"find 查找 admin -> {admin}")

    # === B. Some (只要有一个满足条件就返回 True) ===
    # JS: const hasAdmin = users.some(u => u.role === "admin");
    has_admin = any(u["role"] == "admin" for u in users)
    print(f"some (是否存在 admin?): {has_admin}")

    # === C. Every (是否所有都满足条件) ===
    # JS: const allActive = users.every(u => u.active);
    all_active = all(u["active"] for u in users)
    print(f"every (所有人都是 active?): {all_active}")


def demo_4_reduce_accumulation():
    print("\n--- 4. 累加/归约 (Array.prototype.reduce vs functools.reduce & sum) ---")
    
    prices = [10.5, 20.0, 35.5, 5.0]

    # 求和 (在 Python 中极其简单，直接用内置函数 sum())
    # JS: const total = prices.reduce((acc, cur) => acc + cur, 0);
    total = sum(prices)
    print(f"求和 (sum): {total}")

    # 复杂归约：统计词频 (AI 应用中最常见的 Token 词频统计)
    words = ["apple", "banana", "apple", "orange", "banana", "apple"]
    
    # JS:
    # const count = words.reduce((acc, word) => {
    #   acc[word] = (acc[word] || 0) + 1;
    #   return acc;
    # }, {});
    
    # Python 推荐方式：Dict 推导式 或 collections.Counter
    from collections import Counter
    word_counts = Counter(words)
    print(f"词频统计 (Counter): {dict(word_counts)}")

    # 使用 reduce 实现累乘 (Python 中需要 from functools import reduce)
    product = reduce(lambda acc, cur: acc * cur, [1, 2, 3, 4], 1)
    print(f"累乘结果 (reduce): {product}")


def demo_5_sorting():
    print("\n--- 5. 数组排序 (Array.prototype.sort vs sorted/sort) ---")
    
    # 💥 注意区别：
    # JS 的 arr.sort() 会直接【改变原数组】！
    # Python 的 sorted(arr) 返回【全新排好序的列表】（不改变原数组）；而 arr.sort() 才是改变原数组。
    
    items = [
        {"name": "Document A", "tokens": 1500},
        {"name": "Document B", "tokens": 300},
        {"name": "Document C", "tokens": 800},
    ]

    # 根据 tokens 属性升序排序
    # JS: items.sort((a, b) => a.tokens - b.tokens);
    sorted_by_tokens = sorted(items, key=lambda item: item["tokens"])
    print(f"按 tokens 升序 (sorted): {sorted_by_tokens}")

    # 降序排序 (reverse=True)
    sorted_desc = sorted(items, key=lambda item: item["tokens"], reverse=True)
    print(f"按 tokens 降序: {sorted_desc}")


def demo_6_dict_comprehension():
    print("\n--- 6. 字典推导式 (Dict Comprehension —— Python 独有神技) ---")
    
    # 假设我们有一个用户列表，想快速构建一个 id -> user 的 Map (对象索引)
    # JS: const userMap = Object.fromEntries(users.map(u => [u.id, u]));
    users = [
        {"id": "usr_101", "name": "Alice"},
        {"id": "usr_102", "name": "Bob"},
    ]
    
    # Python 字典推导式: { key_expr: value_expr for item in iterable }
    user_map = {u["id"]: u for u in users}
    print(f"ID 到对象的字典映射: {user_map}")

    # 数据转换：将配置字典的 Key 统一转为大写
    config = {"env": "prod", "debug": "false", "version": "1.0"}
    upper_config = {k.upper(): v for k, v in config.items()}
    print(f"Key 转大写: {upper_config}")


if __name__ == "__main__":
    print("==================================================")
    print("  Python 高阶函数与数据处理 Demo (面向 JS/TS 开发者)")
    print("==================================================")
    demo_1_map_transform()
    demo_2_filter_selection()
    demo_3_find_some_every()
    demo_4_reduce_accumulation()
    demo_5_sorting()
    demo_6_dict_comprehension()
