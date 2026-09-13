"""具体工具实现。

工具设计的三条原则（比代码本身更重要）：

1. **description 写"什么时候用"，不是"它做什么"**
   ❌ "查询天气" —— 模型不知道该不该调
   ✅ "查询某个城市的实时天气。当用户问天气、气温、要不要带伞时调用。
       注意：只能查当天，查不了未来几天。"

2. **参数 description 要写格式和例子**
   ❌ "城市名"
   ✅ "城市名称，用中文，如「北京」「上海」。不要带「市」字。"

3. **错误信息要指导下一步**
   ❌ "FileNotFoundError"
   ✅ "文件不存在：/path/x.txt。请先用 list_files 查看目录下有哪些文件。"

第 3 点最容易被忽略但价值最高 —— 好的错误信息能让模型自己纠错，
而不是傻乎乎地重试同样的错误。
"""
import os
import re
import json
import math
import logging
from datetime import datetime
from pathlib import Path

from src.tools import ToolRegistry
from src import safety

logger = logging.getLogger(__name__)

# 工具操作的沙箱目录：限制文件工具只能在这个目录内活动
SANDBOX_DIR = Path(__file__).parent.parent / "sandbox"


def build_registry() -> ToolRegistry:
    """构造默认工具集。"""
    if not SANDBOX_DIR.exists():
        SANDBOX_DIR.mkdir(parents=True)
    reg = ToolRegistry()

    _register_calculator(reg)
    _register_time(reg)
    _register_weather(reg)
    _register_file_tools(reg)
    _register_knowledge_search(reg)
    return reg


# ---------------------------------------------------------------- 计算器
def _register_calculator(reg: ToolRegistry):
    @reg.tool(
        name="calculator",
        description=(
            "计算数学表达式。当用户需要做算术、百分比、幂运算时调用。"
            "支持 + - * / ** 和括号，以及 sqrt/log/sin/cos 等数学函数。"
            "注意：这是精确计算，比你自己心算可靠，涉及数字就调它。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '(15+27)*3/4' 或 'sqrt(144)'",
                }
            },
            "required": ["expression"],
        },
    )
    def calculator(expression: str) -> str:
        # 安全考量：绝不使用 eval()！
        # eval 能执行任意代码，模型被提示注入时会变成 RCE 漏洞。
        # 这里用 AST 白名单，只允许数学运算。
        if len(expression) > 200:
            return "表达式过长，请简化后重试"

        allowed_names = {
            "sqrt": math.sqrt, "abs": abs, "round": round,
            "log": math.log, "log10": math.log10, "exp": math.exp,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "pi": math.pi, "e": math.e,
            "pow": pow, "min": min, "max": max,
        }

        import ast
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return f"表达式语法错误：{expression}。请检查括号和运算符。"

        # 遍历 AST，只允许安全节点
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute,
                                 ast.Call) ):
                if isinstance(node, ast.Call):
                    # 函数调用只允许白名单内的名字
                    if not isinstance(node.func, ast.Name) or node.func.id not in allowed_names:
                        return "表达式中包含不被允许的函数调用"
                elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute)):
                    return "表达式中不允许导入或属性访问"
            elif isinstance(node, ast.Name):
                if node.id not in allowed_names:
                    return f"表达式中包含未知的名称：{node.id}"

        try:
            result = eval(compile(tree, "<calc>", "eval"),
                          {"__builtins__": {}}, allowed_names)
        except ZeroDivisionError:
            return "计算错误：除数为零"
        except Exception as ex:                     # noqa: BLE001
            return f"计算失败：{ex}"

        return f"{expression} = {result}"


# ---------------------------------------------------------------- 时间
def _register_time(reg: ToolRegistry):
    @reg.tool(
        name="get_current_time",
        description=(
            "获取当前日期和时间。当用户问「今天几号」「现在几点」「这周星期几」，"
            "或者你需要根据当前时间做计算时调用。"
            "重要：你的训练数据有截止日期，不知道现在是哪天，涉及日期必须调这个工具。"
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    )
    def get_current_time() -> str:
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return json.dumps({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": weekdays[now.weekday()],
            "timestamp": int(now.timestamp()),
        }, ensure_ascii=False)


# ---------------------------------------------------------------- 天气（模拟）
def _register_weather(reg: ToolRegistry):
    # 模拟数据。真实项目应该调高德/和风天气的 API。
    _FAKE = {
        "北京": ("晴", 24, 12), "上海": ("多云", 26, 18),
        "广州": ("小雨", 29, 23), "深圳": ("阴", 28, 22),
        "杭州": ("晴", 25, 15), "成都": ("阴", 21, 16),
    }

    @reg.tool(
        name="get_weather",
        description=(
            "查询城市天气【仅限今天】。当用户问天气、气温、要不要带伞、穿衣建议时调用。"
            "注意：只能查今天，查不了明天或未来几天。"
            "支持的模拟城市：北京、上海、广州、深圳、杭州、成都。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，用中文，如「北京」。不要带「市」字",
                }
            },
            "required": ["city"],
        },
    )
    def get_weather(city: str) -> str:
        city = city.strip().rstrip("市")
        if city not in _FAKE:
            # 错误信息指导下一步 —— 告诉模型有哪些可选值
            return (
                f"查询不到 {city} 的天气数据（这是模拟工具）。"
                f"支持的城市：{'、'.join(_FAKE.keys())}"
            )
        cond, high, low = _FAKE[city]
        return json.dumps({
            "city": city, "condition": cond,
            "temp_high": high, "temp_low": low,
            "note": "模拟数据，仅用于演示",
        }, ensure_ascii=False)


# ---------------------------------------------------------------- 文件工具
def _register_file_tools(reg: ToolRegistry):
    """文件工具。重点是**沙箱**：所有路径必须落在 SANDBOX_DIR 内。

    这是最典型的安全漏洞来源。如果直接接受模型给的路径，
    模型（或被注入的模型）可以传 "../../../etc/passwd" 读走系统文件。
    """

    def _safe_path(rel: str) -> Path:
        """把相对路径解析到沙箱内，并校验没有越界。"""
        # 拒绝绝对路径
        if os.path.isabs(rel):
            raise ValueError(f"不接受绝对路径：{rel}。请用相对于沙箱的路径，如 'notes.txt'")
        target = (SANDBOX_DIR / rel).resolve()
        sandbox = SANDBOX_DIR.resolve()
        # 关键校验：解析后的真实路径必须在沙箱内
        if sandbox != target and sandbox not in target.parents:
            raise ValueError(
                f"路径越界：{rel} 超出了允许的操作范围。你只能在沙箱目录内操作文件。"
            )
        return target

    @reg.tool(
        name="list_files",
        description=(
            "列出工作目录下的文件。当你不确定有哪些文件可操作时，先调这个。"
            "在报「文件不存在」之后，也应该用这个确认实际有哪些文件。"
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    )
    def list_files() -> str:
        if not SANDBOX_DIR.exists():
            return "工作目录为空"
        files = []
        for p in sorted(SANDBOX_DIR.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                files.append({"name": p.name, "size": p.stat().st_size})
        if not files:
            return "工作目录为空"
        return json.dumps(files, ensure_ascii=False)

    @reg.tool(
        name="read_file",
        description=(
            "读取工作目录下的文本文件内容。当用户要求查看、总结、分析某个文件时调用。"
            "先用 list_files 确认文件存在，再读。只能读文本文件。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名（不含路径），如 'notes.txt'",
                }
            },
            "required": ["filename"],
        },
    )
    def read_file(filename: str) -> str:
        try:
            path = _safe_path(filename)
        except ValueError as ex:
            return str(ex)
        if not path.exists():
            return (
                f"文件不存在：{filename}。"
                f"请先调用 list_files 查看工作目录下有哪些文件。"
            )
        if path.stat().st_size > 100_000:
            return f"文件过大（{path.stat().st_size} 字节），请指定读取范围"
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"{filename} 不是 UTF-8 文本文件，无法读取"

    @reg.tool(
        name="write_file",
        description=(
            "把内容写入工作目录下的文件。文件已存在时会覆盖。"
            "当用户要求记录、保存、生成文件时调用。"
            "写入前建议先读一下原文件，避免误覆盖重要内容。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名（不含路径），如 'summary.md'",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的完整内容",
                },
            },
            "required": ["filename", "content"],
        },
        # 写操作需要确认 —— 这是"人在环"的体现
        requires_confirm=True,
    )
    def write_file(filename: str, content: str) -> str:
        try:
            path = _safe_path(filename)
        except ValueError as ex:
            return str(ex)
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        action = "覆盖写入" if existed else "新建"
        return f"已{action} {filename}（{len(content)} 字符）"


# ---------------------------------------------------------------- 知识库检索
def _register_knowledge_search(reg: ToolRegistry):
    """把「检索」包装成一个工具 —— 这是从 RAG 应用走向 Agent 应用的关键一步。

    对比项目 02：那里是"每次都检索"，这里是"模型自己决定要不要检索"。
    好处：
    - 闲聊和常识问题不触发检索，省钱
    - 一个任务里可以检索多次，用不同的关键词（对应不同子问题）
    - 检索结果不满意时，模型可以换关键词再试一次

    这个思路叫 RAG-as-a-Tool，是当前 Agent 设计的推荐做法。
    """

    # 内置一小段知识，演示用。真实项目应接向量库。
    _KB = {
        "退款": "退款政策：7 天内无理由全额退款，超过 7 天按剩余天数比例退款。审核通过后 3-5 个工作日到账。",
        "试用期": "标准试用期 3 个月，薪资为标准薪资的 80%。表现优秀可提前转正，最早入职满 2 个月申请。",
        "报销": "报销周期：每月 25 日为当月截止日，次月 15 日发放。单笔超 2000 元需附消费明细。",
        "年假": "年假：入职满 1 年 5 天，逐年递增。当年有效，最多结转 5 天。请假需提前 1 个工作日提交。",
        "错误码": "ERR_AUTH_4012=账号锁定30分钟；ERR_UPLOAD_5001=文件超限；ERR_QUOTA_7003=API超配额，次日0点重置。",
        "价格": "套餐：免费版¥0（5人/2GB）；标准版¥39/人/月（50人/100GB）；专业版¥99/人/月（200人/1TB）。年付8.5折。",
    }

    @reg.tool(
        name="search_knowledge_base",
        description=(
            "在企业内部知识库中检索信息。当用户询问公司政策、产品规则、错误码、价格等"
            "【内部信息】时调用。这类信息你的训练数据里没有，必须检索。\n"
            "技巧：如果第一次检索没找到，换一个关键词再试，比如把「要花多少钱」换成「价格」。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索关键词，用简短的中文词组，如「退款」「年假」",
                }
            },
            "required": ["query"],
        },
    )
    def search_knowledge_base(query: str) -> str:
        hits = []
        for key, content in _KB.items():
            if key in query or query in key:
                hits.append({"topic": key, "content": content})
        # 再做一次模糊匹配：按字符重合度
        if not hits:
            q_chars = set(query)
            for key, content in _KB.items():
                if len(q_chars & set(key)) >= 2:
                    hits.append({"topic": key, "content": content})
        if not hits:
            return (
                f"知识库中没有找到与「{query}」相关的内容。"
                f"可尝试的关键词：{'、'.join(_KB.keys())}。"
                f"如果多次检索都没有，请直接告诉用户知识库里没有这个信息。"
            )
        return json.dumps(hits, ensure_ascii=False)
