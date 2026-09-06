"""
Python 基础数据类型 —— 面向 JS/前端 开发者的对比指南
=====================================================

在前端，所有的数字都是 Number，所有的对象都是 Object。
但在 Python 中，内置的数据类型划分更加精细。
"""

def main():
    print("--- 1. 数字类型 (Numbers) ---")
    # JS: const a = 10; const b = 3.14; (都是 Number)
    # Python 区分整数 (int) 和浮点数 (float)
    a = 10        # int
    b = 3.14      # float
    
    # 💥 Python 特色：整数的大小没有限制！(不会出现 JS 里的 MAX_SAFE_INTEGER 精度丢失问题)
    huge_number = 9999999999999999999999999999999999999999
    print(f"超大整数: {huge_number + 1}")
    
    # 除法
    print(f"JS 除法 10/3: 3.3333333333333335")
    print(f"Python 浮点除法 (10 / 3): {10 / 3}")
    print(f"Python 整除 (10 // 3): {10 // 3}")  # 向下取整，等价于 Math.floor(10/3)


    print("\n--- 2. 字符串 (Strings) ---")
    # JS 模板字符串: `Hello ${name}`
    # Python 格式化字符串 (f-string) —— 开发 AI 应用最常用的语法，用于拼接 Prompt！
    name = "Kevin"
    prompt = f"你好，我叫 {name}，请帮我写一段代码。" 
    print(prompt)
    
    # Python 里的单引号和双引号完全一样，甚至三引号可以用来写多行字符串
    multi_line = '''
    这是第一行
    这是第二行
    '''


    print("\n--- 3. 空值 (Null & Undefined) ---")
    # JS: null (空对象) 和 undefined (未定义)
    # 💥 Python 只有 None！
    # 没有 undefined 这个概念。如果变量没赋值就直接用，Python 会直接报错 (NameError)。
    empty_val = None
    if empty_val is None:  # 判断是否为空，习惯用 is None (相当于 JS 的 === null)
        print("这个变量是空的")


    print("\n--- 4. 布尔值 (Booleans) ---")
    # JS: true, false (小写)
    # Python: True, False (首字母必须大写！)
    is_active = True
    is_deleted = False
    
    # 逻辑运算符不同：
    # JS: &&, ||, !
    # Python: and, or, not (非常语义化)
    if is_active and not is_deleted:
        print("用户状态正常")


    print("\n--- 5. 核心容器类型 (List, Tuple, Dict, Set) ---")
    
    # [List] 列表 -> 对应 JS 的 Array
    # 支持各种切片语法
    arr = [10, 20, 30, 40]
    print(f"列表切片 [1:3]: {arr[1:3]}")  # [20, 30]
    
    # [Tuple] 元组 -> JS 中没有，它是【不可变的列表】
    # 为什么需要它？因为它不可变，所以很安全，常用于函数返回多个值。
    coord = (100.5, 200.5)
    # coord[0] = 99.9  # ❌ 报错！元组一旦创建不能修改
    
    # [Dict] 字典 -> 对应 JS 的 Object / Map
    # 注意：JS 对象的 key 只能是字符串/Symbol，但 Python 字典的 key 可以是任何不可变类型 (如数字、元组)。
    user = {
        "name": "Kevin",
        "age": 28,
        1: "数字也能当 key" 
    }
    # 获取值推荐用 .get()，因为如果 key 不存在，.get() 返回 None，而 user['x'] 会直接抛错导致程序崩溃
    print(f"安全获取属性: {user.get('gender', '未知')}")
    
    # [Set] 集合 -> 对应 JS 的 Set
    # Python 的 Set 数学运算极其强大！在处理列表去重、找差异时非常好用。
    set_a = {1, 2, 3, 4}
    set_b = {3, 4, 5, 6}
    print(f"交集 (都有的): {set_a & set_b}")  # {3, 4}
    print(f"并集 (合并去重): {set_a | set_b}")  # {1, 2, 3, 4, 5, 6}
    print(f"差集 (A有B没有): {set_a - set_b}")  # {1, 2}

if __name__ == "__main__":
    main()
