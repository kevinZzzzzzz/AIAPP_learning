"""
Python 工程化：类型提示进阶 (Advanced Type Hinting)

Python 3.5 引入了类型提示 (Type Hints)，在 3.9/3.10+ 得到了极大的增强。
虽然它不会影响代码的实际运行（Python 依然是动态语言），
但它是现代 Python 工程化的基石，能让 IDE 提供精准补全，配合静态检查工具（Mypy）可以在运行前发现大量 Bug。
前端对比：相当于 TypeScript 替代了 JavaScript。
"""

from typing import Any, Callable, TypeVar, Literal
import json

# ======================== 1. 联合类型与可选类型 ========================

# Python 3.10+ 的新语法：使用 | 表示联合类型 (Union)
def process_id(item_id: int | str):
    if isinstance(item_id, int):
        print(f"处理数字 ID: {item_id * 2}")
    else:
        print(f"处理字符 ID: {item_id.upper()}")

# 可选类型：参数可以是字符串，也可以是不传（None）
# 等价于 name: Optional[str] = None
def greet(name: str | None = None):
    if name is None:
        return "Hello, Guest!"
    return f"Hello, {name}!"


# ======================== 2. 集合类型的内建泛型 ========================

# Python 3.9+ 不再需要从 typing 导入 List, Dict，直接使用内建类型即可
def process_users(
    user_names: list[str],            # 字符串列表
    scores: dict[str, float],         # 键是字符串，值是浮点数的字典
    coordinates: tuple[float, float]  # 明确长度为 2 的元组（例如经纬度）
):
    pass


# ======================== 3. Callable 与字面量类型 ========================

# Literal 限制参数只能是特定的几个值，非常适合做枚举
def set_status(status: Literal["running", "stopped", "failed"]):
    print(f"状态已更新为: {status}")

# set_status("sleeping")  # IDE 会在这行画红线，因为 "sleeping" 不在可选值内

# Callable 用于标注函数类型的回调参数
# Callable[[参数1类型, 参数2类型], 返回值类型]
def execute_with_retry(
    action: Callable[[int], bool], 
    max_retries: int = 3
) -> bool:
    for i in range(max_retries):
        if action(i):
            return True
    return False


# ======================== 4. 泛型 (Generics) ========================

# 定义一个泛型变量 T
T = TypeVar('T')

# 这个函数接收什么类型的列表，就返回什么类型的元素
def get_first_item(items: list[T]) -> T | None:
    if not items:
        return None
    return items[0]

# IDE 可以准确推断出 first_num 是 int，first_str 是 str
first_num = get_first_item([1, 2, 3]) 
first_str = get_first_item(["a", "b", "c"])


# ======================== 5. Any 与 TypeAlias ========================

# Any 表示放弃类型检查（类似于 TS 的 any，尽量少用）
def parse_json(data: str) -> Any:
    return json.loads(data)

# TypeAlias 类型别名，给复杂的类型起个好记的名字
# Python 3.12+ 可以直接使用 type 关键字，例如：type JSONDict = dict[str, Any]
JSONDict = dict[str, Any]

def process_api_response(response: JSONDict):
    pass
