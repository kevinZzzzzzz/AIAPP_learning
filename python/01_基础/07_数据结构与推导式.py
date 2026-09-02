"""
Python 数据结构与推导式 —— 面向前端开发者
============================================

前端开发者极其依赖 Array 上的方法：map, filter, reduce, forEach，以及扩展运算符 `...`。
Python 实现这些操作的方式更加简洁、"Pythonic" (符合 Python 哲学)。
"""

def list_operations_demo():
    print("\n--- 1. 列表操作 (对应 JS Array map/filter) ---")
    
    # 基础数据
    nums = [1, 2, 3, 4, 5]
    
    # JS: const squares = nums.map(n => n ** 2);
    # Python 列表推导式 (List Comprehension)
    squares = [n ** 2 for n in nums]
    print(f"Map (推导式): {squares}")

    # JS: const evens = nums.filter(n => n % 2 === 0);
    # Python 推导式 + 条件
    evens = [n for n in nums if n % 2 == 0]
    print(f"Filter (推导式): {evens}")

    # JS: const mix = nums.filter(n => n % 2 !== 0).map(n => n * 10);
    # Python 结合 Map 和 Filter
    mix = [n * 10 for n in nums if n % 2 != 0]
    print(f"Filter + Map: {mix}")


def dict_operations_demo():
    print("\n--- 2. 字典操作 (对应 JS Object) ---")
    
    user = {"name": "Alice", "age": 25, "role": "admin"}

    # JS: Object.keys(user)
    print(f"Keys: {list(user.keys())}")
    
    # JS: Object.values(user)
    print(f"Values: {list(user.values())}")
    
    # JS: Object.entries(user)
    # Python: user.items() 非常重要，常用于遍历字典
    print("Entries:")
    for key, value in user.items():
        print(f"  {key}: {value}")

    # 字典推导式 (Dictionary Comprehension)
    # 假设我们想把所有值都转成字符串
    stringified_user = {k: str(v) for k, v in user.items()}
    print(f"字典推导式: {stringified_user}")


def unpack_demo():
    print("\n--- 3. 解包操作 (对应 JS 扩展运算符 ...) ---")
    
    # 1. 数组解包合并
    # JS: const arr3 = [...arr1, ...arr2];
    arr1 = [1, 2]
    arr2 = [3, 4]
    arr3 = [*arr1, *arr2]  # Python 的解包语法也是用星号，只不过是单星号 `*`
    print(f"列表合并: {arr3}")

    # 2. 对象解包合并
    # JS: const obj3 = { ...obj1, ...obj2 };
    obj1 = {"a": 1, "b": 2}
    obj2 = {"c": 3, "d": 4}
    # Python 中字典解包使用双星号 `**`
    obj3 = {**obj1, **obj2} 
    # Python 3.9+ 还可以直接使用 `|` 运算符合并字典: obj3 = obj1 | obj2
    print(f"字典合并: {obj3}")

    # 3. 函数参数解包
    def print_coord(x, y, z):
        print(f"Coordinate: x={x}, y={y}, z={z}")

    coord_list = [10, 20, 30]
    print_coord(*coord_list)  # 把列表解包成了 3 个参数

    coord_dict = {"y": 200, "z": 300, "x": 100}
    print_coord(**coord_dict) # 把字典解包成具名参数 (关键字参数)


def zip_demo():
    print("\n--- 4. zip 组合 (Python 特色) ---")
    # Python 提供了一个极其好用的 zip 函数，用于把两个列表像拉链一样拼起来
    # JS 中要实现这个通常需要使用 map 和 index
    
    names = ["Alice", "Bob", "Charlie"]
    ages = [25, 30, 35]

    # [(Alice, 25), (Bob, 30), (Charlie, 35)]
    combined = list(zip(names, ages))
    print(f"Zip 结果: {combined}")

    # 常用于把两个列表变成字典
    user_dict = dict(zip(names, ages))
    print(f"转换为字典: {user_dict}")


if __name__ == "__main__":
    list_operations_demo()
    dict_operations_demo()
    unpack_demo()
    zip_demo()
