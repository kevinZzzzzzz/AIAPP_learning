from typing import Final, Tuple, Dict, Any


def demo_1_variables_and_const():
    print("\n--- 1. 变量声明与常量 (let/const vs Python) ---")
    a = 10
    a = 15

    MAX_CONNECTIONS = 100

    API_KEY: Final[str] = 'sk-123456'
    
    print(f"a = {a}")
    print(f"常量 MAX_CONNECTIONS = {MAX_CONNECTIONS}")
    print(f"Final 提示常量 API_KEY = {API_KEY}")

def demo_2_destructuring_and_unpacking():
    print("\n--- 2. 解构赋值 (Destructuring vs Unpacking) ---")

    # === A. 数组/列表解构 ===
    point = [10, 20, 30, 40, 50]
    first, second, *rest = point
    print(f"解构列表 -> first: {first}, second: {second}, rest: {rest}")

    # 变量互换 (Swap)
    # JS: [x, y] = [y, x];
    x, y = 1, 9
    x, y = y, x
    print(f"变量互换后：x: {x}，y: {y}")

    # 忽略某些变量
    # JS: const [a, , c] = [1, 2, 3];
    a, _, c = [1, 2, 3]
    print(f"忽略中间值 a:{a} {_} c: {c}")

    # === B. 对象/字典解构 ===
    # JS: const user = { name: "Alice", age: 25, role: "admin" };
    # JS: const { name, age } = user;
    user: Dict[str, Any] = {"name": "Alice", "age": 25, "role": "admin"}
    name = user["name"]
    age = user.get("age", 19)
    print(f"提取字典字段 -> name: {name}, age: {age}")

    def print_user_info(name: str, age: int, role: str):
        print(f"User profile -> {name} {age} {role}")

    print_user_info(**user)

def demo_3_spread_operator():
    print("\n--- 3. 展开运算符 (Spread ... vs * 和 **) ---")
    
    # === A. 数组/列表展开 ===
    # JS: const list1 = [1, 2]; const list2 = [...list1, 3, 4];
    list1 = [1, 2]
    list2 = [*list1, 3, 4]
    print(f"列表展开结果：{list2}")

    # === B. 对象/字典合并 ===
    # JS: const defaultOpts = { theme: "dark", lang: "zh" };
    # JS: const customOpts = { ...defaultOpts, lang: "en" };
    default_opts = {"theme": "dark", "lang": "zh"}
    custom_opts = {**default_opts, "lang": "en"}
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
    print(f"arr1 == arr2 (内容相同？): {arr1 == arr2}")
    print(f"arr1 is arr2 (内存地址相同？): {arr1 is arr2}")

    # 三元运算符 (Ternary Operator)
    # JS: const status = score >= 60 ? "pass" : "fail";
    score = 99
    status = "excellent" if score >= 90 else "pass" if score >= 60 else "fail"
    print(f"三元运算符结果: {status}")

def demo_5_scope_and_closures():
    print("\n--- 5. 作用域与闭包 (Scope & Closures) ---")
    # JS: let counter = 0; function inc() { counter++; }
    counter = 1
    print(f"修改前的变量counter：{counter}")
    def increment_counter():
        nonlocal counter  # 修改父级函数作用域中的变量
        counter += 1
    
    increment_counter()
    print(f"修改后的变量counter：{counter}")

    # 闭包 (Closures)
    # JS:
    # function createCounter() {
    #   let count = 0;
    #   return () => ++count;
    # }
    def create_counter():
        count = 0
        def next_count():
            nonlocal count
            count += 2
            return count
        return next_count
    counter_func = create_counter()
    print(f"闭包调用1：{counter_func()}") # 2
    print(f"闭包调用2：{counter_func()}") # 4

if __name__ == "__main__":
    print("=================== pyton 基础===================")
    demo_1_variables_and_const()
    demo_2_destructuring_and_unpacking()
    demo_3_spread_operator()
    demo_4_operators_comparison()
    demo_5_scope_and_closures()
    