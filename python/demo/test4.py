from os import write
from typing import (List, Dict, Tuple, Set, Optional, Union, Callable, Literal, Any, TypedDict)


# TS: const username: string = "Alice";
username: str = "Alice"
age: int = 25
score: float = 98.5
is_active: bool = True
anything: Any = "can be whatever"


# === 2. 数组与字典结构类型 ===
# TS: const tags: string[] = ["AI", "React", "Python"];
# TS: const scoreMap: Record<string, number> = { math: 90, english: 85 };
tags: list[str] = ["AI", "React", "Python"]  # Python 3.9+ 写法
score_map: dict[str, int] = {"math": 90, "english": 85}

# 元组 (固定长度与类型的数组)
# TS: type Point = [number, number, string];
point: tuple[float, int, str] = (11.11, 2.1, "kevinzzzzzzz")
print(f"{point}")

# === 3. 联合类型与可选类型 (Union & Optional) ===
# TS: type ID = string | number;
# TS: type UserEmail = string | undefined | null;

# Python 3.10+ 直接用 | (强烈推荐，和 TS 语法一模一样！)
# Optional[T] 等价于 T | None (相当于 TS 中的 T | null)
UserID = str | int
def fetch_user_by_id(user_id: UserID) -> Optional[dict[str, Any]]:
    if user_id == "1" or user_id == 101:
        return {"id": user_id, "name": "kevinzzzzzzz"}
    return None
print(f"{fetch_user_by_id('3')}")


# === 4. 字面量类型 (Literal Types) —— 大模型开发最常用！ ===
# TS: type LLMRole = "system" | "user" | "assistant" | "tool";
LLMRole = Literal["system", "user", "assistant", "tool"]

def format_chat_message(role: LLMRole, content: str) -> dict[str, str]:
    return {"role": role, "content": content}
print(f"{format_chat_message('user', 'Hello')}")



# === 5. 函数类型声明 (Function Signatures) ===
# TS: type Multiplier = (val: number, factor: number) => number;
# Python: Callable[[参数类型列表], 返回值类型]
CalculatorFunc = Callable[[float, float], float]
def execute_calc(fn: CalculatorFunc, a: float, b:float) -> float:
    return fn(a, b)
    

# === 6. TypedDict (相当于 TS 的 Interface 对象结构) ===
# TS:
# interface LLMRequestPayload {
#   model: string;
#   temperature?: number;
#   messages: { role: string; content: string }[];
# }

class messageDict(TypedDict):
    role: str
    content: str

class LLMRequestPayload(TypedDict, total=False):
     # total=False 相当于所有字段均为可选字段 (?)
    model: str
    temperarure: float
    messages: list[messageDict]


def demo_type_hints_in_action():
    print("\n--- TS 与 Python Type Hints 运行测试 ---")
    msg = format_chat_message("user", "Hello Deepseek")
    print(f"1. Literal 限制调用消息： {msg}")
    
    payload: LLMRequestPayload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a Python mentor."},
            {"role": "user", "content": "Teach me Type Hints."}
        ]
    }
    print(f"2. TypedDict 构建结构化数据: {payload}")

    # 调用计算函数
    multiply: CalculatorFunc = lambda x, y: x * y
    res = execute_calc(multiply, 2.3, 4.2)
    print(f"3. Callable 回调函数计算结果： {res}")


if __name__ == "__main__":
    print("==================================================")
    print("  TS 类型系统与 Python Type Hints 对比 Demo")
    print("==================================================")
    demo_type_hints_in_action()
