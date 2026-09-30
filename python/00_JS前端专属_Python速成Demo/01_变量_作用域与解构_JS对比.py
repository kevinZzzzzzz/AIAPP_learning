"""
Python 变量、作用域、解构与运算符 —— JS/TS 开发者对比学习指南
============================================================
适合群体：具备 JavaScript / TypeScript 基础的前端工程师
运行方法：python 01_变量_作用域与解构_JS对比.py
"""

from typing import Final, Tuple, Dict, Any

def demo_1_variables_and_const():
    print("\n--- 1. 变量声明与常量 (let/const vs Python) ---")
    
    # -------------------------------------------------------------
    # JS/TS:
    # let a = 10;          // 可变变量
    # const b = 20;        # 不可变常量
    # -------------------------------------------------------------
    # Python:
    # 没有 let 和 const 关键字！声明直接赋值即可。
    a = 10
    a = 15  # 随时可以重新赋值
    
    # 习惯约定：全大写字母代表常量（Python 语言层面不强制禁止修改，只靠程序员自觉或静态检查工具）
    MAX_CONNECTIONS = 100 
    
    # TypeScript 中的 Final 声明（类型提示）：
    # TS: const API_KEY: string = "sk-xxx";
    API_KEY: Final[str] = "sk-123456"
    # API_KEY = "new-key"  # mypy 等类型检查器会警告，但运行期不会崩溃
    
    print(f"a = {a}")
    print(f"常量 MAX_CONNECTIONS = {MAX_CONNECTIONS}")
    print(f"Final 提示常量 API_KEY = {API_KEY}")


def demo_2_destructuring_and_unpacking():
    print("\n--- 2. 解构赋值 (Destructuring vs Unpacking) ---")
    
    # === A. 数组/列表解构 ===
    # JS: const [first, second, ...rest] = [10, 20, 30, 40, 50];
    point = [10, 20, 30, 40, 50]
    first, second, *rest = point  # Python 语法：使用 * 来接收剩余元素（相当于 JS 的 ...rest）
    print(f"解构列表 -> first: {first}, second: {second}, rest: {rest}")

    # 变量互换 (Swap)
    # JS: [x, y] = [y, x];
    x, y = 1, 9
    x, y = y, x
    print(f"变量互换后 -> x: {x}, y: {y}")

    # 忽略某些变量
    # JS: const [a, , c] = [1, 2, 3];
    a, _, c = [1, 2, 3]  # 习惯用下划线 _ 占位表示忽略的值
    print(f"忽略中间值 -> a: {a}, c: {c}")

    # === B. 对象/字典解构 ===
    # JS: const user = { name: "Alice", age: 25, role: "admin" };
    # JS: const { name, age } = user;
    user: Dict[str, Any] = {"name": "Alice", "age": 25, "role": "admin"}
    
    # Python 字典没有 `const { name } = dict` 这种直接语法，但可以通过以下常用写法提取：
    name = user["name"]
    age = user.get("age", 18)  # get() 相当于带有默认值的解构：const age = user.age ?? 18
    print(f"提取字典字段 -> name: {name}, age: {age}")

    # Python 的高级解构：在函数参数中使用关键字解构 (类似 JS 传配置对象)
    def print_user_info(name: str, age: int, role: str):
        print(f"User Profile -> {name} ({age}) - Role: {role}")
    
    # JS: printUserInfo({...user});
    print_user_info(**user)  # ** 语法将字典解构成关键字参数 (Keyword Arguments)


def demo_3_spread_operator():
    print("\n--- 3. 展开运算符 (Spread ... vs * 和 **) ---")
    
    # === A. 数组/列表展开 ===
    # JS: const list1 = [1, 2]; const list2 = [...list1, 3, 4];
    list1 = [1, 2]
    list2 = [*list1, 3, 4]  # * 用于解包列表/元组
    print(f"列表展开结果: {list2}")

    # === B. 对象/字典合并 ===
    # JS: const defaultOpts = { theme: "dark", lang: "zh" };
    # JS: const customOpts = { ...defaultOpts, lang: "en" };
    default_opts = {"theme": "dark", "lang": "zh"}
    custom_opts = {**default_opts, "lang": "en"}  # ** 用于解包字典（后面的覆盖前面的）
    print(f"字典合并结果: {custom_opts}")


def demo_4_operators_comparison():
    print("\n--- 4. 运算符对照表 ---")
    """
    JS 运算符           Python 运算符         说明
    ----------------------------------------------------------------------
    &&                  and                  逻辑与
    ||                  or                   逻辑或
    !                   not                  逻辑非
    === / ==            ==                   值是否相等 (Python == 比较内容)
    Object.is(a, b)     is                   引用地址是否相同 (内存地址)
    null ?? default     val or default       空值回退
    Math.pow(a, b)      a ** b               次方计算 (2 ** 3 = 8)
    Math.floor(a / b)   a // b               整除取整 (7 // 2 = 3)
    in (对象/数组包含)   in                   成员判断 (x in list / key in dict)
    """
    
    # 示例：is vs ==
    # JS 中: arr1 === arr2 (比地址)
    arr1 = [1, 2, 3]
    arr2 = [1, 2, 3]
    
    print(f"arr1 == arr2 (内容相同?): {arr1 == arr2}")  # True (像 JS 的 lodash.isEqual)
    print(f"arr1 is arr2 (内存相同?): {arr1 is arr2}")  # False (相当于 JS 的 === 比较引用)

    # 三元运算符 (Ternary Operator)
    # JS: const status = score >= 60 ? "pass" : "fail";
    score = 85
    status = "pass" if score >= 60 else "fail"  # Python 的写法是: 值1 if 条件 else 值2
    print(f"三元运算符结果: {status}")


def demo_5_scope_and_closures():
    print("\n--- 5. 作用域与闭包 (Scope & Closures) ---")
    
    # JS: let counter = 0; function inc() { counter++; }
    counter = 0

    def increment_counter():
        nonlocal counter  # 修改父级函数作用域中的变量
        counter += 1

    increment_counter()
    print(f"修改后的父级变量 counter: {counter}")

    # 闭包 (Closures)
    # JS:
    # function createCounter() {
    #   let count = 0;
    #   return () => ++count;
    # }
    def create_counter():
        count = 0
        def next_count():
            nonlocal count  # nonlocal 相当于修改上层函数作用域里的变量 (类似 JS 的闭包捕捉)
            count += 1
            return count
        return next_count

    counter_func = create_counter()
    print(f"闭包第1次调用: {counter_func()}")  # 1
    print(f"闭包第2次调用: {counter_func()}")  # 2


if __name__ == "__main__":
    print("==================================================")
    print("  Python 变量、解构与运算符 Demo (面向 JS/TS 开发者)")
    print("==================================================")
    demo_1_variables_and_const()
    demo_2_destructuring_and_unpacking()
    demo_3_spread_operator()
    demo_4_operators_comparison()
    demo_5_scope_and_closures()
