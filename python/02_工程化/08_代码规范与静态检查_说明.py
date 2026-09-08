"""
Python 工程化：代码规范与静态检查工具

在团队协作或大型开源项目中，光有好的代码逻辑是不够的。
我们需要自动化工具来保证代码风格的一致性，并在代码运行前就发现潜在的低级错误。
对于现代 Python 开发，我们推荐以下工具组合（类似于前端的 ESLint + Prettier）：

======================== 1. 代码格式化与规范 (Ruff) ========================

过去，Python 社区流行使用多个工具：
- Flake8 (检查代码规范，如变量未使用)
- Black (强制代码格式化)
- isort (自动排序 import 导入)

【现在：推荐使用 Ruff】
Ruff 是一个用 Rust 编写的 Python Linter 和 Formatter。
- 极快：比上面提到的传统工具快数十倍到上百倍。
- 全能：它可以取代 Flake8, Black, isort 等数十个工具。
- 流行：FastAPI、Pydantic、HuggingFace 等顶级开源项目都在迁移到 Ruff。

如何使用 Ruff：
1. 安装： `pip install ruff`
2. 检查代码规范： `ruff check .`
3. 自动修复规范（如删除未使用的导入）： `ruff check . --fix`
4. 格式化代码（代替 Black）： `ruff format .`

(IDE 集成：在 VSCode/Cursor/Windsurf 中安装 Ruff 插件即可实现保存时自动格式化)


======================== 2. 静态类型检查 (Mypy / Pyright) ========================

你在 07_类型提示进阶.py 中写了大量的类型标注 (如 x: int, -> str)。
但是，Python 解释器在运行时是忽略这些类型的。
为了真正利用这些类型提示发现 Bug，我们需要使用静态检查工具。

【推荐工具 1：Mypy】
Python 官方支持的最老牌的类型检查工具。
- 安装： `pip install mypy`
- 运行： `mypy your_script.py`
- 效果：如果你的函数参数要求 int，你传了 str，Mypy 会在终端里报错阻止你。

【推荐工具 2：Pyright / Pylance】
微软开发的基于 Node.js 的极速类型检查工具。
它是 VSCode (Pylance 插件) 底层默认使用的类型推导引擎。
如果你使用 VSCode 类的编辑器，你已经在无形中享受了它的好处（给你画红线报错）。

======================== 3. 典型的现代化 pyproject.toml 配置示例 ========================
现在所有的工程化配置，不再散落到处，而是统一写在项目根目录的 pyproject.toml 中：

[tool.ruff]
# 允许的最大行宽
line-length = 88
# 假设是 Python 3.10+
target-version = "py310"

[tool.ruff.lint]
# 开启常用规则
select = ["E", "F", "I"] 
# E: pycodestyle (风格错误)
# F: Pyflakes (逻辑错误)
# I: isort (导入排序)

[tool.mypy]
# 强制要求写函数返回值类型
disallow_untyped_defs = true
# 忽略缺少类型提示的第三方库报错
ignore_missing_imports = true
"""

def example_bad_code():
    # 这是一个反面示例
    import os, sys # 规范要求：每个 import 应该占一行，且未使用的话 Ruff 会报错
    
    # Mypy 会在这里报错：Incompatible types in assignment (expression has type "str", variable has type "int")
    x: int = "hello" 
    
    # 格式化问题：缩进不规范，冒号后没空格
    if x==1:print(x)
