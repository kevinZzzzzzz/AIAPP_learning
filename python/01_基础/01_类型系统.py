"""
Python 类型系统详解 —— 面向 JavaScript/TypeScript 开发者
=================================================================

对比视角：Python 的类型系统和 TS 很像，但有一些关键差异。
- TS 的 `string | null`  ≈  Python 的 `Optional[str]`
- TS 的 `any`            ≈  Python 的 `Any`
- TS 的 `Array<T>`       ≈  Python 的 `list[T]`
"""

from typing import Optional, Union, Any, Literal, TypedDict
from dataclasses import dataclass


# ======================== 1. 基本类型标注（Python 3.10+） ========================

def greet(name: str, age: int) -> str:
    """参数和返回值都有类型标注。注意：这只是标注，运行时不会做类型检查。"""
    return f"Hello {name}, you are {age} years old"


# JS 对比：function greet(name: string, age: number): string


def process(data: Any) -> Any:
    """Any = 放弃类型检查。尽量少用，类似 TS 的 any。"""
    return data


# ======================== 2. Optional（可为空） ========================

def find_user(user_id: int) -> Optional[str]:
    """Optional[X] 等价于 Union[X, None]，即「可能是 X，也可能是 None」
    
    TS 等价：string | null
    """
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id)  # dict.get 返回 None 如果 key 不存在


# ======================== 3. Union（联合类型） ========================

def parse_value(value: Union[str, int, float]) -> float:
    """Union[X, Y] 表示「X 或 Y」
    
    Python 3.10+ 可以写成 str | int | float
    """
    return float(value)


# ======================== 4. Literal（字面量类型） ========================

Role = Literal["admin", "user", "guest"]

def check_permission(role: Role) -> bool:
    """Literal 限制参数只能是这几个字符串之一
    
    TS 等价：type Role = 'admin' | 'user' | 'guest'
    """
    return role == "admin"


# ======================== 5. TypedDict（带类型的字典） ========================

class UserDict(TypedDict):
    """TypedDict = TS 的 interface/type（对象结构定义）"""
    name: str
    age: int
    email: Optional[str]

def print_user(user: UserDict) -> None:
    """None 返回值 ≈ TS 的 void"""
    print(f"User: {user['name']}, Age: {user['age']}")


# ======================== 6. dataclass（数据类） ========================

@dataclass
class User:
    """dataclass 自动生成 __init__、__repr__、__eq__ 等方法
    
    TS 等价：class User { constructor(public name: string, ...) {} }
    """
    name: str
    age: int
    email: Optional[str] = None  # 有默认值

    def is_adult(self) -> bool:
        return self.age >= 18


# ======================== 7. 常用容器类型 ========================

# List —— 有序可变序列
names: list[str] = ["Alice", "Bob", "Charlie"]

# Tuple —— 固定长度的不可变序列
point: tuple[float, float, float] = (1.0, 2.0, 3.0)

# Dict —— 键值对
config: dict[str, Union[str, int]] = {"host": "localhost", "port": 8000}

# Set —— 无序不重复集合
tags: set[str] = {"python", "ai", "llm"}

# FrozenSet —— 不可变集合
ALLOWED_ROLES: frozenset[str] = frozenset({"admin", "user"})


# ======================== 8. Callable（可调用类型） ========================

from typing import Callable

def execute_callback(callback: Callable[[str, int], bool], name: str, age: int) -> bool:
    """Callable[[参数类型...], 返回值类型]
    
    这里表示：callback 接收 (str, int) 两个参数，返回 bool
    """
    return callback(name, age)


# ======================== 实践：一个 AI 应用中的类型示例 ========================

@dataclass
class ChatMessage:
    """聊天消息的数据结构 —— AI 聊天中的核心类型"""
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass  
class LLMResponse:
    """LLM API 返回的数据结构"""
    content: str
    model: str
    tokens_used: int
    finish_reason: Optional[str] = None


if __name__ == "__main__":
    # 运行 demo
    print(greet("张三", 30))
    
    user = User(name="李四", age=25)
    print(user)  # User(name='李四', age=25, email=None)
    print(f"Is adult: {user.is_adult()}")
    
    msg = ChatMessage(role="user", content="hello")
    print(msg)
