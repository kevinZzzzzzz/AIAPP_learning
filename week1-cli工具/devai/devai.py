"""
devai — AI 开发者命令行工具
=============================

一个帮助前端开发者学习 Python 和 AI 的 CLI 工具。

功能：
  devai count      — 估算 Token 数量
  devai prompt     — 管理 Prompt 模板
  devai convert    — JS <-> Python 代码对照翻译
  devai explain    — 用大白话解释 Python 概念

每个命令都涉及：argparse 命令行解析、文件读写、字符串处理、类型注解等核心语法。

用法示例：
  python devai.py count "Hello World"
  python devai.py prompt list
  python devai.py convert js2py "const x = [1,2,3].map(n => n*2);"
  python devai.py explain "装饰器"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# ====================== 配置 ======================

DATA_DIR = Path(__file__).parent / "data"
PROMPTS_FILE = DATA_DIR / "prompts.json"


def ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(exist_ok=True)
    if not PROMPTS_FILE.exists():
        PROMPTS_FILE.write_text("{}", encoding="utf-8")


# ====================== 1. count 命令：Token 估算 ======================

def count_tokens(text: str) -> dict:
    """估算文本的 Token 数量
    
    简易规则（非精确，无网络依赖）：
    - 英文：大约 4 字符 = 1 token
    - 中文：大约 1 字符 = 1~2 token
    - 标点：约 1 token
    """
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_chinese = len(text) - chinese_chars
    
    # 中文按 1.5 token/字，英文按 0.25 token/字
    estimated = int(chinese_chars * 1.5 + non_chinese * 0.25)
    
    return {
        "text_length": len(text),
        "chinese_chars": chinese_chars,
        "non_chinese_chars": non_chinese,
        "estimated_tokens": estimated,
        "gpt4_cost_usd": round(estimated * 0.03 / 1000, 6),   # $0.03/1K input
        "gpt4o_cost_usd": round(estimated * 0.0025 / 1000, 6), # $0.0025/1K input
    }


def cmd_count(args):
    """执行 count 命令"""
    text = args.text
    
    # 如果传了文件路径
    if os.path.isfile(text):
        text = Path(text).read_text(encoding="utf-8")
    
    result = count_tokens(text)
    
    print(f"""
╔══════════════════════════════════╗
║        Token 估算结果            ║
╠══════════════════════════════════╣
║  文本长度:    {result['text_length']:>6} 字符         ║
║  中文字符:    {result['chinese_chars']:>6}              ║
║  非中文字符:  {result['non_chinese_chars']:>6}              ║
║  预估 Token:  {result['estimated_tokens']:>6}              ║
╠══════════════════════════════════╣
║  成本估算（仅供参考）:            ║
║  GPT-4:     ${result['gpt4_cost_usd']:<10}           ║
║  GPT-4o:    ${result['gpt4o_cost_usd']:<10}           ║
╚══════════════════════════════════╝
""")


# ====================== 2. prompt 命令：管理 Prompt 模板 ======================

def load_prompts() -> dict:
    """加载保存的 Prompt 模板"""
    ensure_data_dir()
    return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))


def save_prompts(data: dict):
    """保存 Prompt 模板"""
    ensure_data_dir()
    PROMPTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


DEFAULT_PROMPTS = {
    "翻译助手": {
        "system": "你是一个专业翻译，把用户输入翻译成英文。只输出译文。",
        "tags": ["翻译", "翻译"],
    },
    "代码审查": {
        "system": "你是一个资深代码审查员，请审查以下代码，指出问题和改进建议：",
        "tags": ["代码", "审查"],
    },
    "Python 导师": {
        "system": "你是一位耐心的 Python 导师，用通俗易懂的方式解释概念，配合代码示例。",
        "tags": ["学习", "Python"],
    },
}


def cmd_prompt(args):
    """执行 prompt 命令"""
    action = args.action
    prompts = load_prompts()
    
    # 首次使用时初始化默认模板
    if not prompts:
        prompts = DEFAULT_PROMPTS
        save_prompts(prompts)
    
    if action == "list":
        if not prompts:
            print("暂无保存的 Prompt 模板。")
            return
        
        print(f"\n{'名称':<16} {'标签':<20} {'内容预览'}")
        print("-" * 60)
        for name, data in prompts.items():
            preview = data["system"][:30] + "..." if len(data["system"]) > 30 else data["system"]
            tags = ", ".join(data.get("tags", []))
            print(f"{name:<16} {tags:<20} {preview}")
        print()
    
    elif action == "show":
        if not args.name:
            print("请指定要查看的模板名称: devai prompt show <名称>")
            return
        data = prompts.get(args.name)
        if not data:
            print(f"未找到模板: {args.name}")
            print(f"可用模板: {', '.join(prompts.keys())}")
            return
        print(f"\n--- {args.name} ---")
        print(f"标签: {', '.join(data.get('tags', []))}")
        print(f"System Prompt:\n{data['system']}\n")
    
    elif action == "add":
        if not args.name or not args.content:
            print("用法: devai prompt add <名称> <System Prompt 内容>")
            return
        prompts[args.name] = {
            "system": args.content,
            "tags": args.tags.split(",") if args.tags else [],
        }
        save_prompts(prompts)
        print(f"已添加模板: {args.name}")
    
    elif action == "delete":
        if not args.name:
            print("请指定要删除的模板名称")
            return
        if args.name in prompts:
            del prompts[args.name]
            save_prompts(prompts)
            print(f"已删除模板: {args.name}")
        else:
            print(f"未找到模板: {args.name}")
    
    elif action == "use":
        if not args.name:
            print("请指定要使用的模板名称")
            return
        data = prompts.get(args.name)
        if not data:
            print(f"未找到模板: {args.name}")
            return
        user_input = input("请输入你的问题: ")
        print(f"\n[System Prompt] {data['system']}")
        print(f"[User] {user_input}")
        print(f"\n提示: 将以上内容复制到 ChatGPT 或其他 LLM 中即可使用此模板。")


# ====================== 3. convert 命令：JS <-> Python 对照 ======================

CONVERSIONS = {
    # JS → Python
    "js2py": {
        "const/let/var": "# Python 没有 const/let/var，直接赋值即可",
        "const x = 1;": "x = 1",
        "let name = 'Alice';": "name = 'Alice'",
        "console.log(x)": "print(x)",
        "// 注释": "# 单行注释",
        "/* 多行注释 */": '""" 多行注释 """',
        "x === y": "x == y  # Python 没有 ===，== 即严格比较",
        "!x": "not x",
        "x && y": "x and y",
        "x || y": "x or y",
        "true / false": "True / False",
        "null / undefined": "None",
        "typeof x": "type(x)",
        "arr.length": "len(arr)",
        "arr.push(item)": "arr.append(item)",
        "arr.pop()": "arr.pop()  # 一样！",
        "arr.map(fn)": "[fn(x) for x in arr]  # 列表推导式",
        "arr.filter(fn)": "[x for x in arr if fn(x)]",
        "obj[key]": 'obj[key] 或 obj.get(key, default)',
        "Object.keys(obj)": "obj.keys()",
        "JSON.stringify(obj)": "json.dumps(obj)",
        "JSON.parse(str)": "json.loads(str)",
        '`Hello ${name}`': "f'Hello {name}'",
        "setTimeout(fn, 1000)": "time.sleep(1); fn()",
        "Promise / async/await": "asyncio + async/await（语法几乎一样）",
        "try-catch-finally": "try-except-finally",
        "class X extends Y": "class X(Y):",
        "new X()": "X()  # Python 不需要 new",
        "this": "self（需要显式传参）",
        "function fn() {}": "def fn():",
        "() => {} 箭头函数": "lambda x: x * 2  # 只支持单行表达式",
    },
    # Python → JS
    "py2js": {
        "x = 1": "let x = 1; 或 const x = 1;",
        "print(x)": "console.log(x)",
        "# 注释": "// 单行注释",
        '""" 多行注释 """': "/* 多行注释 */",
        "x == y": "x === y",
        "not x": "!x",
        "x and y": "x && y",
        "x or y": "x || y",
        "True / False": "true / false",
        "None": "null 或 undefined",
        "type(x)": "typeof x",
        "len(arr)": "arr.length",
        "arr.append(item)": "arr.push(item)",
        "[fn(x) for x in arr]": "arr.map(fn)",
        "[x for x in arr if fn(x)]": "arr.filter(fn)",
        "dict.get(key, default)": "obj[key] ?? default",
        "dict.keys()": "Object.keys(obj)",
        "json.dumps(obj)": "JSON.stringify(obj)",
        "json.loads(str)": "JSON.parse(str)",
        "f'Hello {name}'": "`Hello ${name}`",
        "asyncio + async/await": "Promise + async/await",
        "try-except-finally": "try-catch-finally",
        "class X(Y):": "class X extends Y {}",
        "self": "this（隐式，不需要传参）",
        "def fn():": "function fn() {} 或 const fn = () => {}",
        "lambda x: expr": "(x) => expr",
        "with open() as f:": 'fs.readFileSync() 或 fetch()',
        "from X import Y": "import { Y } from 'X'",
    },
}


def cmd_convert(args):
    """执行 convert 命令"""
    mode = args.mode
    code = args.code
    
    translations = CONVERSIONS.get(mode, {})
    
    print(f"\n{'='*60}")
    if mode == "js2py":
        print("JavaScript → Python 对照表")
    else:
        print("Python → JavaScript 对照表")
    print(f"{'='*60}")
    
    # 如果传了具体代码，尝试逐行翻译
    if code and code != "list":
        print(f"\n原始代码:\n  {code}\n")
        print("翻译思路:")
        found_any = False
        for key, value in translations.items():
            if key in code:
                print(f"  {key:<25} → {value}")
                found_any = True
        
        if not found_any:
            print("  (未找到精确匹配，以下是对照参考表)")
            cmd_convert_list(mode)
        return
    
    # 列出所有对照
    cmd_convert_list(mode)


def cmd_convert_list(mode: str):
    """打印完整的对照表"""
    translations = CONVERSIONS.get(mode, {})
    print(f"\n{'语法/概念':<30} {'对应写法'}")
    print("-" * 70)
    for key, value in translations.items():
        print(f"{key:<30} {value}")


# ====================== 4. explain 命令：大白话解释 Python 概念 ======================

EXPLANATIONS = {
    "装饰器": {
        "简介": "在不修改原函数的情况下，给函数增加额外功能",
        "大白话": "就像给手机套个壳——手机功能没变，但多了保护、支架等功能。@符号就是「套壳」这个动作。",
        "代码示例": '''
# 这是一个「计时壳」
import time

def timer(func):                    # 装饰器工厂
    def wrapper(*args, **kwargs):  # 壳
        start = time.time()
        result = func(*args, **kwargs)
        print(f"耗时: {time.time() - start:.2f}s")
        return result
    return wrapper

@timer  # ← 把 timer 当壳套在 greet 上
def greet(name):
    return f"Hello {name}"
''',
    },
    "异步": {
        "简介": "让程序在等待（IO、网络）时可以去干别的事",
        "大白话": "就像你在煮水（等待）的同时去切菜（做别的任务），而不是傻站着等水开。async/await 就是这个「同时做多件事」的语法。",
        "代码示例": '''
import asyncio

async def fetch_data(url):     # async = 这个函数可以"暂停等待"
    print(f"开始请求 {url}")
    await asyncio.sleep(1)     # await = "我先去忙别的，1秒后回来"
    return f"{url} 的数据"

async def main():
    # 同时请求3个URL —— 总共只花1秒，不是3秒
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )
    print(results)

asyncio.run(main())
''',
    },
    "生成器": {
        "简介": "一个可以暂停和恢复的函数，每次只产出一个值",
        "大白话": "就像自助餐厅的流水线——一次只出一个菜，而不是把所有菜一次性堆满桌子。用 yield 代替 return，函数就有了「暂停」功能。",
        "代码示例": '''
def fibonacci(n):
    """斐波那契生成器 —— 每次只算一个"""
    a, b = 0, 1
    for _ in range(n):
        yield a       # ← 暂停，返回值；下次从这继续
        a, b = b, a + b

for num in fibonacci(10):
    print(num)  # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34
''',
    },
    "列表推导式": {
        "简介": "一行代码生成新列表，替代 for 循环 + append",
        "大白话": "就像在超市里，你推着购物车说「把货架上所有红色的、价格低于50的东西装进车里」——一句话完成筛选+转换。",
        "代码示例": '''
# ❌ 传统写法（4行）
squares = []
for x in range(10):
    if x % 2 == 0:
        squares.append(x ** 2)

# ✅ 列表推导式（1行）
squares = [x ** 2 for x in range(10) if x % 2 == 0]

# JS 对照：arr.filter(x => x%2===0).map(x => x**2)
''',
    },
    "Pydantic": {
        "简介": "Python 的数据验证库，定义数据结构 + 自动校验",
        "大白话": "就像 TypeScript 的 interface，但它不是在编译时报错，而是在运行时真的检查数据——数据不对就直接拒绝，不给通过。",
        "代码示例": '''
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    age: int = Field(ge=0, le=150)  # 0-150岁
    email: str

# 自动校验
user = User(name="张三", age=25, email="test@qq.com")  # ✅
user = User(name="李四", age=-1, email="")              # ❌ 报错
''',
    },
    "上下文管理器": {
        "简介": "with 语句，自动管理资源的打开和关闭",
        "大白话": "就像住酒店——check-in（打开资源），退房时前台自动帮你 clean-up（关闭资源），你不需要记着关灯关空调。",
        "代码示例": '''
# ❌ 传统写法：需要手动关闭
f = open("file.txt")
content = f.read()
f.close()  # 容易忘！

# ✅ with 语句：自动关闭
with open("file.txt") as f:
    content = f.read()
# 离开 with 块时，无论是否有异常，文件都会自动关闭
''',
    },
}

def cmd_explain(args):
    """执行 explain 命令"""
    concept = args.concept
    
    # 模糊搜索
    data = None
    for key in EXPLANATIONS:
        if concept in key:
            data = EXPLANATIONS[key]
            concept = key
            break
    
    if not data:
        print(f"\n未找到概念: {args.concept}")
        print(f"可解释的概念: {', '.join(EXPLANATIONS.keys())}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  {concept}
╠══════════════════════════════════════════════════════════╣
║  {data['简介']}
║
║  💬 大白话: {data['大白话']}
║
║  📝 代码示例:
{data['代码示例']}
╚══════════════════════════════════════════════════════════╝
""")


# ====================== CLI 主入口 ======================

def main():
    parser = argparse.ArgumentParser(
        description="devai — AI 开发者命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python devai.py count "Hello World 你好世界"
  python devai.py prompt list
  python devai.py prompt add "代码助手" "你是一个代码助手..."
  python devai.py prompt use "翻译助手"
  python devai.py convert js2py "const x = 1"
  python devai.py explain 装饰器
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # ---- count 子命令 ----
    count_parser = subparsers.add_parser("count", help="估算文本 Token 数量")
    count_parser.add_argument("text", help="文本内容 或 文件路径")
    
    # ---- prompt 子命令 ----
    prompt_parser = subparsers.add_parser("prompt", help="管理 Prompt 模板")
    prompt_parser.add_argument(
        "action",
        choices=["list", "show", "add", "delete", "use"],
        help="操作: list(列表) show(查看) add(添加) delete(删除) use(使用)",
    )
    prompt_parser.add_argument("name", nargs="?", help="模板名称")
    prompt_parser.add_argument("content", nargs="?", help="模板内容（add 时使用）")
    prompt_parser.add_argument("--tags", help="标签，逗号分隔（add 时使用）")
    
    # ---- convert 子命令 ----
    convert_parser = subparsers.add_parser("convert", help="JS <-> Python 代码对照")
    convert_parser.add_argument(
        "mode",
        choices=["js2py", "py2js"],
        help="转换方向: js2py (JS→Python) | py2js (Python→JS)",
    )
    convert_parser.add_argument("code", nargs="?", help="要对照的代码片段（不传则列出完整对照表）")
    
    # ---- explain 子命令 ----
    explain_parser = subparsers.add_parser("explain", help="大白话解释 Python 概念")
    explain_parser.add_argument("concept", help="要解释的概念（如: 装饰器、异步、生成器）")
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 路由到对应命令
    commands = {
        "count": cmd_count,
        "prompt": cmd_prompt,
        "convert": cmd_convert,
        "explain": cmd_explain,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
