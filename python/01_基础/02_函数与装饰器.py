"""
Python 函数与装饰器详解
=================================================================

装饰器是 Python 最强大的特性之一，也是 AI 框架（如 LangChain）中大量使用的模式。
如果你会 JS 的 HOC（高阶组件）/ 装饰器提案，Python 装饰器思路类似但更灵活。
"""

from typing import Any, Callable
import time
import functools


# ======================== 1. 函数是一等公民 ========================

def add(a: int, b: int) -> int:
    return a + b

# 函数可以赋值给变量（和 JS 一样）
my_add = add
print(my_add(3, 5))  # 8

# 函数可以作为参数传递（和 JS 一样）
def apply(func: Callable, x: int, y: int) -> int:
    return func(x, y)


# ======================== 2. 位置参数 vs 关键字参数 ========================

def describe_person(name: str, age: int, city: str = "北京") -> str:
    """age 之前都是位置参数，city 是关键字参数（有默认值）"""
    return f"{name}, {age}岁, 来自{city}"

# 两种调用方式
print(describe_person("张三", 30))                    # 位置传参
print(describe_person(name="李四", age=25, city="上海"))  # 关键字传参


# ======================== 3. *args 和 **kwargs ========================

def log_all(*args: Any, **kwargs: Any) -> None:
    """*args: 接收任意数量的位置参数，打包成 tuple
       **kwargs: 接收任意数量的关键字参数，打包成 dict
    
    JS 等价：function log_all(...args) —— 但 Python 区分位置参数和命名参数
    """
    print(f"位置参数 args: {args}")      # tuple
    print(f"关键字参数 kwargs: {kwargs}")  # dict

# 常用模式：转发参数
def forward(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """将所有参数原封不动转发给另一个函数 —— AI 框架中极其常见"""
    return func(*args, **kwargs)


# ======================== 4. lambda 表达式 ========================

# Python lambda 只能写单行表达式（不如 JS 灵活）
square = lambda x: x * x

# 实际场景：排序 key
users = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
users.sort(key=lambda u: u["age"])  # 按年龄排序


# ======================== 5. 闭包 ========================

def make_multiplier(factor: int) -> Callable[[int], int]:
    """闭包：内层函数记住外层函数的变量
    
    JS 完全一样：const makeMultiplier = (n) => (x) => x * n
    """
    def multiplier(x: int) -> int:
        return x * factor
    return multiplier

double = make_multiplier(2)
print(double(5))  # 10


# ======================== 6. 装饰器基础 ========================

def simple_decorator(func: Callable) -> Callable:
    """装饰器 = 接收函数、返回新函数的高阶函数
    
    相当于 JS 中：
    const simpleDecorator = (fn) => (...args) => { ...; return fn(...args); }
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"[装饰器] 调用函数: {func.__name__}")
        result = func(*args, **kwargs)
        print(f"[装饰器] 函数返回: {result}")
        return result
    return wrapper


@simple_decorator  # 等价于 say_hello = simple_decorator(say_hello)
def say_hello(name: str) -> str:
    return f"Hello, {name}!"


# ======================== 7. 带参数的装饰器（三层嵌套） ========================

def repeat(times: int):
    """装饰器工厂：返回一个真正的装饰器
    
    用法 @repeat(3)，先执行 repeat(3) 得到装饰器，再用装饰器包装函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)  # 保留原函数的元信息（__name__ 等）
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


@repeat(3)
def greet(name: str) -> str:
    print(f"Hi {name}!")
    return f"Done: {name}"

# ======================== 8. 实战：计时装饰器（AI 开发常用） ========================

def timeit(func: Callable) -> Callable:
    """测量函数执行时间 —— 调试 LLM 调用延迟时极其有用"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[计时] {func.__name__} 耗时: {elapsed:.4f}秒")
        return result
    return wrapper


# ======================== 9. 实战：重试装饰器 ========================

def retry(max_attempts: int = 3, delay: float = 1.0):
    """失败自动重试 —— LLM API 调用中非常实用的模式"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time as _time
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"[重试] 第{attempt}次失败: {e}, {delay}秒后重试...")
                    _time.sleep(delay)
            return None
        return wrapper
    return decorator


# ======================== 10. cache / lru_cache（AI 开发神器） ========================

@functools.lru_cache(maxsize=128)
def expensive_embedding(text: str) -> float:
    """lru_cache 自动缓存函数结果 —— 相同输入直接返回缓存，不重复调用
    
    在 AI 开发中：缓存 embedding 结果、缓存 LLM 响应，节省大量成本
    """
    print(f"[计算] 正在为 '{text[:20]}...' 计算（模拟耗时操作）")
    time.sleep(0.5)  # 模拟耗时
    return len(text) * 0.01


# ======================== 11. 类装饰器 ========================

class Singleton:
    """让一个类变成单例模式"""
    _instances: dict = {}
    
    def __init__(self, cls):
        functools.update_wrapper(self, cls)
        self._cls = cls
    
    def __call__(self, *args, **kwargs):
        if self._cls not in self._instances:
            self._instances[self._cls] = self._cls(*args, **kwargs)
        return self._instances[self._cls]


@Singleton
class AppConfig:
    """这个类全局只有一个实例 —— 适合管理 LLM API Key 等全局配置"""
    def __init__(self):
        self.settings: dict[str, Any] = {}
    
    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)


if __name__ == "__main__":
    # 测试简单装饰器
    print(say_hello("World"))
    
    # 测试重复装饰器
    print("\n--- repeat(3) 测试 ---")
    greet("Python")
    
    # 测试缓存
    print("\n--- lru_cache 测试 ---")
    print(expensive_embedding("Hello World"))  # 第一次执行，有 [计算] 输出
    print(expensive_embedding("Hello World"))  # 第二次直接返回缓存，无 [计算] 输出
    
    # 测试单例
    print("\n--- 单例测试 ---")
    config1 = AppConfig()
    config2 = AppConfig()
    print(f"是同一个实例吗？{config1 is config2}")  # True
