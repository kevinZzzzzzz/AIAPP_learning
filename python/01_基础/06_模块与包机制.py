"""
Python 模块与包机制 —— 面向前端开发者
======================================

前端开发者习惯了 ES Modules (import/export) 和 CommonJS (require)。
Python 的导入机制有些类似，但也有显著不同。特别是关于 `sys.path` 和 `__init__.py`。
"""

import sys

# ======================== 1. 基础导入 (对比 ES Modules) ========================

# JS: import os from 'os';
#     import * as os from 'os';
import os

# JS: import { path } from 'os';
from os import path

# JS: import { path as p } from 'os';
from os import path as p

def basic_import_demo():
    print("1. 基础导入")
    print("os.getcwd():", os.getcwd())
    print("path.exists():", path.exists("."))
    print("p.exists():", p.exists("."))
    print("-" * 40)


# ======================== 2. 包 (Package) 与 __init__.py ========================
"""
JS 中，一个包含 `package.json` 或 `index.js` 的文件夹可以作为一个模块被导入。
Python 中，一个包含 `__init__.py` (发音: dunder init) 的文件夹被称为一个「包 (Package)」。

虽然 Python 3.3 之后引入了“命名空间包” (可以没有 __init__.py)，
但为了兼容性和明确性，建议在每一个你想被 import 的文件夹下加上一个空的 `__init__.py`。

在 __init__.py 中定义的内容，可以在导入包本身时被访问到。
"""

# ======================== 3. 相对导入与绝对导入 ========================
"""
假设有如下目录结构：
my_project/
├── main.py
└── my_package/
    ├── __init__.py
    ├── module_a.py
    └── module_b.py

JS 习惯: 在 module_b.py 中引入 module_a.py
=> import { something } from './module_a.js';

Python 的相对导入 (只能在包内使用，直接运行脚本时会报错 "attempted relative import with no known parent package"):
=> from .module_a import something
=> from ..other_package import something_else

Python 推荐的绝对导入 (以项目根目录或 sys.path 为基准):
=> from my_package.module_a import something
"""


# ======================== 4. sys.path (模块搜索路径) ========================
"""
当你在 Python 中写 `import xxx` 时，它是去哪里找的呢？
前端的 node_modules 机制是从当前目录向上查找，直到根目录。
Python 则是按 `sys.path` 列表中的路径按顺序找。
"""
def search_path_demo():
    print("2. 模块搜索路径 (sys.path)")
    print("你当前的 sys.path 前 3 个路径是：")
    for p in sys.path[:3]:
        print("  -", p)
    print("如果你自己写了一个模块，但 Python 提示 ModuleNotFoundError，往往是因为你的工作目录不在 sys.path 中。")
    print("-" * 40)


# ======================== 5. 常见坑：循环导入 (Circular Import) ========================
"""
JS 中的循环导入（A 依赖 B，B 依赖 A）通常不会报错，只是可能会拿到 undefined。
Python 中，循环导入会在运行时直接引发 AttributeError 报错，这是新手最常踩的坑！

解决循环导入的方法：
1. 重构代码，把公共依赖提取到模块 C。
2. 将导入语句移到函数内部 (局部导入)，只有在函数调用时才执行 import。
3. 在文件底部导入（不推荐）。
"""

def avoid_circular_import_demo():
    # 局部导入，避免在模块顶层发生循环依赖
    import math
    print(f"局部导入 math: {math.pi}")

# ======================== 6. 如果这个文件作为脚本运行 ========================
"""
JS 的模块只要被 node 运行，里面的代码就会执行。
Python 也一样。但有时候我们写了一个模块文件，既希望它能被别人 import，
又希望能在直接运行它时跑一些测试代码。这时候就需要下面的魔法写法：

`__name__` 是 Python 的内置变量。
如果是被 `import` 进其他文件，它的值就是模块名（比如 "06_模块与包机制"）。
如果这个文件是被直接运行的（例如 `python 06_模块与包机制.py`），它的值就会被强制设为 "__main__"。
"""

if __name__ == "__main__":
    print(f"当前文件的 __name__ 是: {__name__}")
    basic_import_demo()
    search_path_demo()
    avoid_circular_import_demo()
    print("由于本文件是直接被运行的，所以这段代码执行了。如果它是被 import 的，这段不会执行。")
