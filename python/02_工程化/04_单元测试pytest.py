"""
Python 单元测试 pytest —— 面向前端开发者
==========================================

前端写测试首选 Jest 或 Vitest。
在 Python 领域，标准库有 `unittest`，但社区目前的绝对主流和事实标准是 `pytest`。

相比 Jest，pytest 的特点：
1. 不需要写冗长的 `expect(a).toBe(b)`，直接使用原生的 `assert a == b` 即可。
2. 没有 `beforeEach/afterEach`，取而代之的是极其强大的 `fixture` 机制。
"""

# ================= 1. 被测试的函数 =================

def add(a: int, b: int) -> int:
    return a + b

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# ================= 2. 基础测试用例 =================
# pytest 约定：测试文件名必须以 test_ 开头或 _test 结尾。
# 测试函数名也必须以 test_ 开头。

def test_add():
    # JS: expect(add(1, 2)).toBe(3);
    assert add(1, 2) == 3
    assert add(-1, 1) == 0

def test_divide():
    assert divide(10, 2) == 5.0
    
# 测试抛出异常
# JS: expect(() => divide(1, 0)).toThrow('Cannot divide by zero');
# pyrefly: ignore [missing-import]
import pytest
def test_divide_by_zero():
    # 使用 pytest.raises 上下文管理器来捕获预期中的异常
    with pytest.raises(ValueError) as exc_info:
        divide(10, 0)
    assert str(exc_info.value) == "Cannot divide by zero"


# ================= 3. Fixture (环境依赖注入) =================
# Fixture 是 pytest 的核心。它比 beforeEach 更灵活，基于参数注入。

# 假设这是一个伪造的数据库连接
class FakeDB:
    def connect(self): return "connected"
    def disconnect(self): return "disconnected"

# 定义一个 fixture
@pytest.fixture
def db_session():
    # setup 逻辑 (类似 beforeEach)
    db = FakeDB()
    db.connect()
    
    yield db  # 交出控制权给测试函数
    
    # teardown 逻辑 (类似 afterEach)
    db.disconnect()

# 测试函数只需在参数里写上 fixture 的名字，pytest 就会自动注入！
def test_db_operation(db_session):
    # db_session 已经是 connect 状态了
    assert db_session.connect() == "connected"


# ================= 4. 参数化测试 =================
# Jest 中有 test.each()。pytest 对应的是 @pytest.mark.parametrize

@pytest.mark.parametrize("a, b, expected", [
    (1, 1, 2),
    (2, 3, 5),
    (10, -1, 9),
])
def test_add_parametrized(a, b, expected):
    assert add(a, b) == expected


"""
运行测试的方法：
在终端中执行：
$ pip install pytest
$ pytest 04_单元测试pytest.py -v
"""
