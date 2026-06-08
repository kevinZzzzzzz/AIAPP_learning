"""
迭代器、生成器与列表推导式
=================================================================

Python 的迭代器和生成器是其数据处理能力的核心，
在 AI 开发中处理大量文本、token 流、向量时非常关键。
"""

from typing import Iterator, Generator
import sys


# ======================== 1. 列表推导式（List Comprehension） ========================

# 这是 Python 最具特色的语法之一，JS 要用 .map() + .filter() 组合实现

# 基础形式：[表达式 for 变量 in 可迭代对象 if 条件]
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# 平方列表
squares = [x ** 2 for x in numbers]

# 带过滤
evens = [x for x in numbers if x % 2 == 0]

# 带转换 + 过滤
even_squares = [x ** 2 for x in numbers if x % 2 == 0]

# 嵌套（扁平化）
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [num for row in matrix for num in row]  # [1,2,3,4,5,6,7,8,9]

# 字典推导式
name_lengths = {name: len(name) for name in ["Alice", "Bob", "Charlie"]}
# {'Alice': 5, 'Bob': 3, 'Charlie': 7}

# 集合推导式
unique_lengths = {len(name) for name in ["Alice", "Bob", "Charlie"]}  # {3, 5, 7}


# ======================== 2. 生成器表达式（懒加载版列表推导） ========================

# 把 [] 换成 () 就变成生成器表达式 —— 不立即计算，需要时才产出值
big_range = (x ** 2 for x in range(10_000_000))  # 几乎不占内存！

# 列表推导 vs 生成器表达式的内存对比
list_comp = [x ** 2 for x in range(10000)]  # 立即创建 10000 个元素的列表
gen_expr = (x ** 2 for x in range(10000))    # 只是创建了生成器对象，内存极小

print(f"列表占用: {sys.getsizeof(list_comp)} bytes")
print(f"生成器占用: {sys.getsizeof(gen_expr)} bytes")


# ======================== 3. 迭代器协议（__iter__ + __next__） ========================

class CountDown:
    """自定义迭代器：实现 __iter__ 和 __next__"""
    
    def __init__(self, start: int):
        self.current = start
    
    def __iter__(self) -> Iterator[int]:
        """返回迭代器自身"""
        return self
    
    def __next__(self) -> int:
        """每次调用返回下一个值，没有更多值时抛出 StopIteration"""
        if self.current < 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value


def demo_iterator():
    print("倒计时:", end=" ")
    for num in CountDown(5):
        print(num, end=" ")  # 5 4 3 2 1 0
    print()


# ======================== 4. 生成器函数（yield） ========================

def fibonacci(n: int) -> Generator[int, None, None]:
    """生成器函数：用 yield 产出值，函数状态保留
    
    与 JS 的区别：
    - Python: def* 不存在，用 def + yield 就行
    - JS: function* fib() { yield ...; }
    
    每次调用 next() 时执行到下一个 yield，暂停并返回值
    """
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def demo_generator():
    print("斐波那契:", list(fibonacci(10)))
    # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    
    # 生成器是惰性的 —— 可以处理无限序列
    def infinite_counter(start: int = 0):
        """无限生成器 —— 不会内存溢出"""
        while True:
            yield start
            start += 1
    
    counter = infinite_counter(100)
    print("取无限生成器的前5个:", [next(counter) for _ in range(5)])


# ======================== 5. yield from（委托生成器） ========================

def flatten_nested(nested_list: list) -> Generator:
    """yield from: 把迭代委托给另一个生成器
    
    等价于：
    for item in sub_gen:
        yield item
    但更简洁、更高效
    """
    for item in nested_list:
        if isinstance(item, list):
            yield from flatten_nested(item)  # 递归委托
        else:
            yield item


def demo_yield_from():
    nested = [1, [2, 3, [4, 5]], 6, [7, 8]]
    print("扁平化:", list(flatten_nested(nested)))
    # [1, 2, 3, 4, 5, 6, 7, 8]


# ======================== 6. itertools —— 迭代器神器 ========================

import itertools

def demo_itertools():
    """itertools 是 Python 内置的迭代器工具箱，超级实用"""
    
    # chain: 串联多个可迭代对象
    chained = itertools.chain([1, 2, 3], ['a', 'b', 'c'])
    print("chain:", list(chained))
    
    # islice: 懒加载切片（不创建新列表）
    sliced = itertools.islice(range(1000), 10, 20)
    print("islice:", list(sliced))  # [10, 11, ..., 19]
    
    # groupby: 按 key 分组（需要先排序）
    data = [("A", 1), ("A", 2), ("B", 3), ("B", 4)]
    grouped = itertools.groupby(data, key=lambda x: x[0])
    for key, group in grouped:
        print(f"groupby {key}: {list(group)}")
    
    # product: 笛卡尔积
    for combo in itertools.product("AB", "12"):
        print(f"product: {combo}", end=" ")  # ('A','1') ('A','2') ('B','1') ('B','2')
    print()


# ======================== 7. AI 实战：Token 分批处理 ========================

def batch_tokens(tokens: list[int], batch_size: int) -> Generator[list[int], None, None]:
    """将 token 列表按批次大小分组
    
    典型场景：LLM 有 context window 限制，需要分批处理长文本
    或者：embedding API 一次只能处理 N 个文本
    """
    for i in range(0, len(tokens), batch_size):
        yield tokens[i:i + batch_size]


def process_in_chunks(text: str, chunk_size: int) -> Generator[str, None, None]:
    """将长文本按字符数切片（简易版）—— RAG 文档处理的核心操作"""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


def sliding_window(text: str, window_size: int, overlap: int) -> Generator[str, None, None]:
    """滑动窗口切片 —— RAG 中常用的有重叠的文档切片方式
    
    例如：window_size=100, overlap=20 → 每段100字符，相邻段重叠20字符
    """
    if overlap >= window_size:
        raise ValueError("overlap must be smaller than window_size")
    
    step = window_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + window_size]
        if len(chunk) < window_size // 2:  # 最后一段太短就跳过
            break
        yield chunk


def demo_ai_chunking():
    """演示 AI 中的文本切片"""
    text = (
        "Python 是一种广泛使用的解释型、高级和通用的编程语言。"
        "Python 支持多种编程范型，包括结构化、过程式、面向对象和函数式编程。"
        "Python 拥有动态类型系统和垃圾回收功能。"
        "Guido van Rossum 于 1991 年首次发布 Python。"
        "今天 Python 是 AI 和机器学习领域最受欢迎的语言。"
    )
    
    print("\n=== 固定大小切片 ===")
    for i, chunk in enumerate(process_in_chunks(text, 50)):
        print(f"Chunk {i}: [{len(chunk)}字符] {chunk}")
    
    print("\n=== 滑动窗口切片 ===")
    for i, chunk in enumerate(sliding_window(text, 60, 15)):
        print(f"Window {i}: [{len(chunk)}字符] {chunk[:40]}...")


# ======================== 8. enumerate & zip —— 前端熟悉的搭档 ========================

def demo_builtins():
    """这些和 JS 的用法几乎一样"""
    
    # enumerate = 带索引的迭代（JS: arr.forEach((item, i) => ...))
    for i, name in enumerate(["Alice", "Bob", "Charlie"], start=1):
        print(f"User {i}: {name}")
    
    # zip = 并行迭代多个序列（JS 没有原生 zip）
    names = ["Alice", "Bob", "Charlie"]
    ages = [25, 30, 35]
    for name, age in zip(names, ages):
        print(f"{name} is {age} years old")
    
    # zip 可以"转置"
    matrix = [(1, 4), (2, 5), (3, 6)]
    transposed = list(zip(*matrix))  # [(1, 2, 3), (4, 5, 6)]


if __name__ == "__main__":
    demo_iterator()
    demo_generator()
    demo_yield_from()
    demo_itertools()
    demo_ai_chunking()
    demo_builtins()
    
    # 验证生成器惰性
    gen = fibonacci(5)
    print("\n手动迭代生成器:")
    print(next(gen))  # 0
    print(next(gen))  # 1
    print(next(gen))  # 1
    # 生成器状态保持！
