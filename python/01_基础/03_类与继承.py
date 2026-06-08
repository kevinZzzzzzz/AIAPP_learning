"""
Python 类与继承详解
=================================================================

Python 的面向对象和 JS/TS 的 class 语法很像，但有一些重要差异。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


# ======================== 1. 基本类定义 ========================

class Animal:
    """Python 类的 self === JS 的 this，但 self 是显式传参的"""
    
    # 类变量（所有实例共享）≈ JS 的 static 属性
    species_count: ClassVar[int] = 0
    
    def __init__(self, name: str):
        """__init__ = constructor，self 必须显式写出来"""
        self.name = name          # 实例变量
        Animal.species_count += 1
    
    def speak(self) -> str:
        return f"{self.name} makes a sound"
    
    @classmethod
    def get_count(cls) -> int:
        """类方法：第一个参数是类本身（不是实例）
        类似 JS 的 static 方法，但可以被子类继承并知道自己的类名
        """
        return cls.species_count
    
    @staticmethod
    def is_warm_blooded() -> bool:
        """静态方法：不需要 self 也不需要 cls
        和 JS 的 static 完全一样
        """
        return True


# ======================== 2. 继承 ========================

class Dog(Animal):
    """继承：class 子类(父类)  ——  和 TS 的 extends 一样"""
    
    def __init__(self, name: str, breed: str):
        super().__init__(name)  # 调用父类构造器
        self.breed = breed
    
    def speak(self) -> str:  # 方法重写
        return f"{self.name} says: Woof!"
    
    def fetch(self) -> str:
        return f"{self.name} fetches the ball"


# ======================== 3. 多重继承 + MRO ========================

class Flyer:
    def fly(self) -> str:
        return "Flying..."

class Swimmer:
    def swim(self) -> str:
        return "Swimming..."

class Duck(Animal, Flyer, Swimmer):
    """Python 支持多重继承！JS 只支持单继承（用 mixin 模式模拟）
    
    MRO（方法解析顺序）：Duck -> Animal -> Flyer -> Swimmer -> object
    可用 Duck.__mro__ 查看
    """
    def speak(self) -> str:
        return f"{self.name} says: Quack!"


# ======================== 4. 属性装饰器 @property ========================

class Temperature:
    """@property 把方法变成属性访问 —— 类似 JS 的 getter/setter 但更优雅"""
    
    def __init__(self, celsius: float):
        self._celsius = celsius
    
    @property
    def celsius(self) -> float:
        """getter: obj.celsius（不用加括号）"""
        return self._celsius
    
    @celsius.setter
    def celsius(self, value: float):
        """setter: obj.celsius = 20"""
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度")
        self._celsius = value
    
    @property
    def fahrenheit(self) -> float:
        """计算属性：无需存储，使用时计算"""
        return self._celsius * 9/5 + 32


# ======================== 5. 魔法方法（Dunder Methods） ========================

class Vector:
    """魔法方法 = Python 中双下划线开头结尾的方法
    
    实现它们能让你的类支持运算符、迭代、上下文管理等
    """
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __repr__(self) -> str:
        """repr: 给开发者看的字符串表示，用于调试"""
        return f"Vector(x={self.x}, y={self.y})"
    
    def __str__(self) -> str:
        """str: 给用户看的字符串表示，print() 调用"""
        return f"({self.x}, {self.y})"
    
    def __add__(self, other: "Vector") -> "Vector":
        """运算符重载：支持 v1 + v2"""
        return Vector(self.x + other.x, self.y + other.y)
    
    def __eq__(self, other: object) -> bool:
        """相等判断：支持 v1 == v2"""
        if not isinstance(other, Vector):
            return NotImplemented
        return self.x == other.x and self.y == other.y
    
    def __len__(self) -> int:
        """len() 支持"""
        return 2
    
    def __getitem__(self, index: int) -> float:
        """支持 v[0]、v[1] 下标访问"""
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Vector index out of range")
    
    def __iter__(self):
        """支持 for val in vector"""
        yield self.x
        yield self.y


# ======================== 6. 上下文管理器（__enter__ / __exit__） ========================

class DatabaseConnection:
    """实现上下文管理器，支持 with 语句
    
    JS 等价：using 声明（ES2022+）或 try-finally 模式
    AI 开发中：管理 LLM 客户端连接、数据库连接、文件句柄
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connected = False
    
    def __enter__(self):
        """进入 with 块时执行"""
        print(f"连接数据库: {self.db_url}")
        self.connected = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 块时执行（即使有异常也会执行）"""
        print("关闭数据库连接")
        self.connected = False
        # 返回 True 可以吞掉异常，返回 None/False 则继续抛出
    
    def query(self, sql: str) -> str:
        if not self.connected:
            raise RuntimeError("未连接数据库")
        return f"执行: {sql} -- 返回结果"


# ======================== 7. 抽象基类（ABC） ========================

class LLMProvider(ABC):
    """抽象基类：定义接口，强制子类实现
    
    TS 等价：abstract class LLMProvider { abstract chat(): string; }
    
    在 AI 开发中极其重要：统一 OpenAI、Claude、本地模型的接口
    """
    
    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """所有 LLM 提供商必须实现 chat 方法"""
        ...
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """所有 LLM 提供商必须实现 embed 方法"""
        ...
    
    def count_tokens(self, text: str) -> int:
        """具体方法：有默认实现，子类可以选择重写"""
        return len(text)  # 简易估算


# ======================== 8. 实战：AI 工具类设计 ========================

from typing import Protocol

class ToolProtocol(Protocol):
    """Protocol = 结构化子类型（鸭子类型），比 ABC 更轻量
    
    不需要显式继承，只要对象有对应方法就算「实现」了这个协议
    TS 等价：interface ToolProtocol { name: string; execute(input: string): string }
    """
    name: str
    def execute(self, input_str: str) -> str: ...


class SearchTool:
    """搜索工具 —— 自动满足 ToolProtocol，无需继承"""
    name: str = "search"
    
    def execute(self, input_str: str) -> str:
        return f"搜索结果: 关于'{input_str}'的搜索结果..."


class CalculatorTool:
    """计算器工具 —— 同样自动满足 ToolProtocol"""
    name: str = "calculator"
    
    def execute(self, input_str: str) -> str:
        try:
            result = eval(input_str)  # 仅为演示，生产环境需安全处理
            return f"计算结果: {result}"
        except Exception:
            return "计算失败"


def use_tool(tool: ToolProtocol, query: str) -> str:
    """任何满足 ToolProtocol 的对象都可以传入"""
    return tool.execute(query)


if __name__ == "__main__":
    # 测试继承
    dog = Dog("旺财", "金毛")
    print(dog.speak())       # 旺财 says: Woof!
    print(dog.fetch())       # 旺财 fetches the ball
    
    # 测试 @property
    t = Temperature(25)
    print(f"{t.celsius}°C = {t.fahrenheit}°F")
    
    # 测试魔法方法
    v1 = Vector(1, 2)
    v2 = Vector(3, 4)
    print(v1 + v2)           # Vector(x=4, y=6)
    print(v1 == v2)          # False
    
    # 测试上下文管理器
    with DatabaseConnection("postgresql://localhost/mydb") as db:
        print(db.query("SELECT * FROM users"))
    
    # 测试 Protocol（鸭子类型）
    search = SearchTool()
    calc = CalculatorTool()
    print(use_tool(search, "Python 教程"))
    print(use_tool(calc, "3 + 5 * 2"))
