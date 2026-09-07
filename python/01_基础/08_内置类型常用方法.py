"""
Python 内置数据类型常用方法 —— 面向 JS 开发者
==============================================

这个文件涵盖了日常开发中最常用的内置方法，并与 JS (ES6+) 进行了横向对比。
熟练掌握这些方法，能极大提升手写算法和业务代码的效率。
"""

def string_methods_demo():
    print("\n" + "="*40)
    print("1. 字符串 (String) 常用方法")
    print("="*40)
    
    text = "  Hello, Python World!  "
    
    # 1.1 修剪空白 (Trim)
    # JS: text.trim()
    print(f"strip(): '{text.strip()}'")           # 去除两端空格
    # print(f"lstrip(): '{text.lstrip()}'")       # 去除左侧空格 (JS: trimStart)
    # print(f"rstrip(): '{text.rstrip()}'")       # 去除右侧空格 (JS: trimEnd)
    
    clean_text = text.strip()
    
    # 1.2 拆分与拼接 (Split & Join)
    # JS: clean_text.split(", ")
    parts = clean_text.split(", ")
    print(f"split(): {parts}")
    
    # 💥 Python 的 join 用法和 JS 相反！
    # JS: parts.join(" - ")
    # Python 是用连接符去 join 数组：
    joined = " - ".join(parts)
    print(f"join(): {joined}")
    
    # 1.3 替换 (Replace)
    # JS: clean_text.replace("Python", "AI")
    print(f"replace(): {clean_text.replace('Python', 'AI')}")
    
    # 1.4 查找与判断 (Search)
    # JS: clean_text.startsWith("Hello")
    print(f"startswith(): {clean_text.startswith('Hello')}")
    # JS: clean_text.endsWith("!")
    print(f"endswith(): {clean_text.endswith('!')}")
    
    # JS: clean_text.includes("Python")
    # 💥 Python 使用 in 关键字进行包含判断！
    print(f"'in' 关键字: {'Python' in clean_text}")
    
    # JS: clean_text.indexOf("W")
    # Python 中 find 找不到返回 -1，index 找不到会报错 (ValueError)
    print(f"find(): 字母 W 的索引是 {clean_text.find('W')}")
    
    # 1.5 大小写 (Case)
    # JS: clean_text.toLowerCase() / toUpperCase()
    print(f"lower(): {clean_text.lower()}")
    print(f"upper(): {clean_text.upper()}")


def list_methods_demo():
    print("\n" + "="*40)
    print("2. 列表 (List) 常用方法")
    print("="*40)
    
    arr = [10, 20, 30]
    
    # 2.1 增 (Add)
    # JS: arr.push(40)
    arr.append(40)
    print(f"append(): {arr}")
    
    # 💥 JS: arr.push(...[50, 60]) 或 arr.concat([50, 60])
    # Python 使用 extend 将另一个列表的元素合并进来
    arr.extend([50, 60])
    print(f"extend(): {arr}")
    
    # JS: arr.splice(1, 0, 15)
    # Python insert(索引, 元素)
    arr.insert(1, 15)
    print(f"insert(): 在索引 1 插入 15 -> {arr}")
    
    # 2.2 删 (Remove)
    # JS: arr.pop() (删除并返回最后一个)
    last = arr.pop()
    print(f"pop(): 删除了 {last}，剩余 -> {arr}")
    
    # JS: 找出索引再 splice
    # Python remove 会删除第一个匹配的值，如果找不到会报错 ValueError
    arr.remove(20)
    print(f"remove(20): 删除了值为 20 的元素 -> {arr}")
    
    # 2.3 查 (Search)
    # JS: arr.indexOf(30)
    print(f"index(): 值 30 的索引是 {arr.index(30)}")
    # JS: arr.includes(30)
    print(f"'in' 关键字: 30 是否在列表中 -> {30 in arr}")
    
    # 统计出现次数 (JS 通常要用 filter(x=>x===n).length)
    print(f"count(): 10 出现了 {arr.count(10)} 次")
    
    # 2.4 排序与反转 (Sort & Reverse)
    # JS: arr.reverse()
    arr.reverse()
    print(f"reverse() 原地反转: {arr}")
    
    # JS: arr.sort((a,b) => a-b)
    # Python sort() 默认就是数值升序（原地排序）
    arr.sort(reverse=True) # 降序
    print(f"sort(reverse=True) 原地降序: {arr}")
    
    # 💥 内置函数 sorted(arr) 会返回一个新列表，不改变原列表 (类似 JS [...arr].sort())
    new_arr = sorted(arr)
    print(f"sorted() 返回新列表升序: {new_arr} (原列表不变: {arr})")


def dict_methods_demo():
    print("\n" + "="*40)
    print("3. 字典 (Dict) 常用方法")
    print("="*40)
    
    user = {"name": "Bob", "age": 28}
    
    # 3.1 视图对象 (Keys, Values, Items)
    # JS: Object.keys(user)
    print(f"keys(): {list(user.keys())}")
    # JS: Object.values(user)
    print(f"values(): {list(user.values())}")
    # JS: Object.entries(user)
    print(f"items(): {list(user.items())}")
    
    # 3.2 安全获取值 (Get)
    # JS: user.role || 'guest' 或 user?.role
    # Python: 直接用 user['role'] 会报 KeyError，推荐用 get(key, 默认值)
    print(f"get(): 获取 role (默认 guest) -> {user.get('role', 'guest')}")
    
    # 3.3 设置默认值 (SetDefault)
    # 如果键不存在，则插入该键并设为默认值；如果存在，则返回对应值
    role = user.setdefault("role", "admin")
    print(f"setdefault(): 获取/设置 role 为 {role} -> {user}")
    
    # 3.4 更新 (Update)
    # JS: Object.assign(user, {age: 29, city: 'NY'}) 或 user = {...user, age: 29}
    user.update({"age": 29, "city": "NY"})
    print(f"update(): 批量更新后 -> {user}")
    
    # 3.5 删除 (Pop)
    # JS: delete user.age
    age = user.pop("age")
    print(f"pop(): 删除了 age={age}，剩余 -> {user}")


def set_methods_demo():
    print("\n" + "="*40)
    print("4. 集合 (Set) 常用方法 (去重利器)")
    print("="*40)
    
    # 初始化
    s = {1, 2, 3}
    
    # 4.1 增 (Add)
    # JS: s.add(4)
    s.add(4)
    s.add(4) # 重复添加会被忽略
    print(f"add(): {s}")
    
    # 4.2 删 (Remove / Discard)
    # JS: s.delete(2)
    s.remove(2) # 删除 2，如果 2 不存在会报错 KeyError
    print(f"remove(): {s}")
    
    s.discard(99) # 尝试删除 99，不存在也不会报错（推荐使用）
    print(f"discard(): 尝试删除不存在的 99，无事发生 -> {s}")
    
    # 4.3 关系判断
    # 除了数学符号 & | - 以外，还有一些好用的判断方法
    a = {1, 2}
    b = {1, 2, 3, 4}
    print(f"a 是否为 b 的子集 (a <= b): {a.issubset(b)} {a & b}")
    print(f"b 是否为 a 的超集 (b >= a): {b.issuperset(a)} {b | a}")
    print(f"a 和 {5, 6} 是否没有交集: {a.isdisjoint({5, 6})} {b - a}")


if __name__ == "__main__":
    string_methods_demo()
    list_methods_demo()
    dict_methods_demo()
    set_methods_demo()
