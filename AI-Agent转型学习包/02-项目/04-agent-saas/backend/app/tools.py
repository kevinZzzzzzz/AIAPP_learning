"""后端工具集（精简版）。

与项目 03 的区别：这里的工具是给 Web 服务用的，
所以要注意：不能有阻塞操作（会卡住事件循环）、不能有需要终端交互的确认。

关于"人在环"在 Web 场景怎么做：
不能像 CLI 那样 input() 等待。正确做法是：
    1. 后端检测到敏感操作 → 推送一个 requires_confirm 事件 → 暂停该会话
    2. 前端弹出确认框 → 用户点击 → 调用 /api/confirm 接口
    3. 后端收到确认 → 继续执行

这需要 Agent 支持"暂停/恢复"（LangGraph 的 interrupt 就是干这个的）。
本项目为了聚焦 SSE 流式，先只保留只读工具，把写操作留作练习。
"""
import json
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 模拟知识库
_KB = {
    "退款": "退款政策：7 天内无理由全额退款，超过 7 天按剩余天数比例退款，审核通过后 3-5 个工作日到账。",
    "年假": "年假：入职满 1 年 5 天，逐年递增。当年有效，最多结转 5 天。请假需提前 1 个工作日提交。",
    "报销": "报销周期：每月 25 日为当月截止日，次月 15 日发放报销款。单笔超 2000 元需附消费明细。",
    "价格": "套餐：免费版¥0（5人/2GB）；标准版¥39/人/月（50人/100GB）；专业版¥99/人/月（200人/1TB）。年付 8.5 折。",
    "错误码": "ERR_AUTH_4012=账号锁定30分钟；ERR_UPLOAD_5001=文件超限；ERR_QUOTA_7003=API超配额，次日0点重置。",
    "天气": "查询城市天气：支持北京、上海、广州、深圳、杭州、成都。",
}
_WEATHER = {
    "北京": ("晴", 24, 12), "上海": ("多云", 26, 18), "广州": ("小雨", 29, 23),
    "深圳": ("阴", 28, 22), "杭州": ("晴", 25, 15), "成都": ("阴", 21, 16),
}


# 工具 schema（发给模型的格式）
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": (
                "获取当前日期和时间。当用户问今天几号、现在几点，"
                "或需要基于当前时间计算时调用。你的训练数据有截止日期，涉及日期必须调这个。"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式。涉及算术、百分比、幂运算时调用。支持 + - * / ** 和 sqrt/log 等函数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 '(15+27)*3/4'"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "查询城市天气（仅限今天）。当用户问天气、气温、要不要带伞时调用。"
                "支持城市：北京、上海、广州、深圳、杭州、成都。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，中文，如「北京」"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "在企业内部知识库检索。用户询问公司政策、产品规则、价格、错误码等内部信息时调用。"
                "如果一次没找到，换个关键词再试。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，简短中文词组"}
                },
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------- 执行
def execute_tool(name: str, args: dict) -> str:
    """执行工具。返回字符串结果。异常不抛出，转为错误文本。

    注意：这里必须保证所有操作都是【非阻塞】的。
    如果在 async 函数里调用 requests.get()，会阻塞整个事件循环，
    导致所有其他用户的请求都卡住。IO 密集操作要用 httpx.AsyncClient。
    """
    try:
        if name == "get_current_time":
            now = datetime.now()
            wd = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return json.dumps({
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": wd[now.weekday()],
            }, ensure_ascii=False)

        if name == "calculator":
            expr = args.get("expression", "")
            if not expr:
                return "参数错误：缺少 expression"
            if len(expr) > 200:
                return "表达式过长"
            # AST 白名单，禁用 eval 的危险用法
            import ast
            allowed = {
                "sqrt": math.sqrt, "abs": abs, "round": round, "log": math.log,
                "log10": math.log10, "exp": math.exp, "sin": math.sin,
                "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e,
                "pow": pow, "min": min, "max": max,
            }
            try:
                tree = ast.parse(expr, mode="eval")
            except SyntaxError:
                return f"表达式语法错误：{expr}"
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if not isinstance(node.func, ast.Name) or node.func.id not in allowed:
                        return "表达式中包含不被允许的函数调用"
                elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute)):
                    return "表达式中不允许导入或属性访问"
                elif isinstance(node, ast.Name) and node.id not in allowed:
                    return f"表达式中包含未知名称：{node.id}"
            try:
                val = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, allowed)
            except ZeroDivisionError:
                return "计算错误：除数为零"
            return f"{expr} = {val}"

        if name == "get_weather":
            city = (args.get("city") or "").strip().rstrip("市")
            if city not in _WEATHER:
                return f"查不到 {city} 的天气。支持：{'、'.join(_WEATHER.keys())}"
            cond, hi, lo = _WEATHER[city]
            return json.dumps({"city": city, "condition": cond,
                               "temp_high": hi, "temp_low": lo}, ensure_ascii=False)

        if name == "search_knowledge_base":
            q = args.get("query", "")
            hits = [{"topic": k, "content": v} for k, v in _KB.items()
                    if k in q or q in k]
            if not hits:
                qc = set(q)
                hits = [{"topic": k, "content": v} for k, v in _KB.items()
                        if len(qc & set(k)) >= 2]
            if not hits:
                return f"知识库没有「{q}」相关内容。可试关键词：{'、'.join(_KB.keys())}"
            return json.dumps(hits, ensure_ascii=False)

        return f"错误：不存在名为 {name} 的工具"

    except Exception as ex:                     # noqa: BLE001
        logger.exception(f"工具 {name} 执行异常")
        return f"工具执行失败：{type(ex).__name__}: {ex}"
