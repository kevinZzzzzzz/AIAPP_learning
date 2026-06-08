"""
Function Calling 实战
======================

Function Calling 是 LLM 开发的"分水岭"——从这里开始，LLM 不再只是聊天，
而是能"干活"了。核心原理：

  用户输入 → LLM 判断需要哪个工具 → 返回函数名+参数(JSON) 
  → 你的代码执行函数 → 把结果发回 LLM → LLM 生成自然语言回复

本文件演示：
1. 单工具调用        — 天气查询
2. 多工具并行调用    — 同时查天气+算汇率
3. Tool 定义规范     — JSON Schema 写法
4. 完整的 Agent 循环  — 多次调用直到得到最终答案
"""

import json
import asyncio
import os
from datetime import datetime
from typing import Optional


# ====================== 模拟工具函数 ======================

def get_weather(city: str, date: Optional[str] = None) -> dict:
    """获取天气（模拟）
    
    Args:
        city: 城市名
        date: 日期，默认为今天
    """
    weather_data = {
        "北京": {"temp": 22, "desc": "晴", "humidity": 45},
        "上海": {"temp": 28, "desc": "阴转小雨", "humidity": 70},
        "广州": {"temp": 32, "desc": "雷阵雨", "humidity": 85},
        "深圳": {"temp": 30, "desc": "多云", "humidity": 65},
    }
    info = weather_data.get(city, {"temp": 20, "desc": "未知", "humidity": 50})
    return {
        "city": city,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "temperature": info["temp"],
        "description": info["desc"],
        "humidity": info["humidity"],
    }


def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
    """获取汇率（模拟）"""
    rates = {
        ("USD", "CNY"): 7.25,
        ("CNY", "USD"): 0.138,
        ("EUR", "CNY"): 7.90,
        ("JPY", "CNY"): 0.048,
    }
    rate = rates.get((from_currency.upper(), to_currency.upper()), 1.0)
    return {
        "from": from_currency,
        "to": to_currency,
        "rate": rate,
        "timestamp": datetime.now().isoformat(),
    }


def calculate(expression: str) -> dict:
    """执行数学计算（安全版本，仅允许基本运算）"""
    # 只允许数字和基本运算符
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return {"error": "表达式包含不允许的字符"}
    try:
        result = eval(expression)  # 生产环境建议用 ast.literal_eval 或更安全的方式
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e)}


def search_docs(query: str) -> dict:
    """搜索文档库（模拟 RAG 检索）"""
    docs = {
        "token": "Token 是 LLM 处理的最小文本单位。中文约1字=1.5个token，英文约1词=1个token。",
        "temperature": "Temperature 控制输出随机性，0=确定性，1=正常，2=高随机。代码建议0~0.3。",
        "function calling": "Function Calling 允许 LLM 调用外部函数。LLM 返回 JSON，程序执行并把结果发回。",
        "embedding": "Embedding 将文本转为高维向量，相似文本向量距离近。用于语义搜索和 RAG。",
    }
    for key, content in docs.items():
        if key in query.lower():
            return {"query": query, "found": True, "content": content}
    return {"query": query, "found": False, "content": "未找到相关文档"}


# ====================== Tool 的 JSON Schema 定义 ======================

# 这是 OpenAI Function Calling 的标准格式。
# 每个 Tool 需要定义: name、description、parameters (JSON Schema)
#
# 关键：description 写得好不好，直接决定 LLM 会不会调用这个工具！

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息。当用户询问天气、气温、是否下雨等问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'、'上海'",
                    },
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。默认为今天。",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "获取两种货币之间的汇率。当用户询问汇率、换算、多少钱等问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {
                        "type": "string",
                        "description": "源货币代码，如 USD、CNY、EUR、JPY",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "目标货币代码，如 USD、CNY、EUR、JPY",
                    },
                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算。当用户需要计算、算术运算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '(100 + 50) * 3'",
                    },
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "搜索知识库文档。当用户询问技术概念、定义、原理等问题时使用，而不是直接用 LLM 自己的知识。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# 工具函数映射表
TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "get_exchange_rate": get_exchange_rate,
    "calculate": calculate,
    "search_docs": search_docs,
}


# ====================== 演示客户端 ======================

class DemoAgentClient:
    """演示客户端 —— 模拟 LLM 的 Function Calling 返回
    
    在实际应用中，这是由 OpenAI API 返回的：
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
    )
    """

    def __init__(self, mode: str = "auto"):
        self.mode = mode

    def chat(self, messages, tools=None):
        """模拟 LLM 调用
        
        根据最后一条用户消息，返回：
        1. 直接回答（不需要工具时）
        2. tool_calls（需要工具时）
        """
        last_msg = messages[-1]["content"] if messages else ""

        # 判断是否需要工具
        tc = self._tool_choice(last_msg)
        if tc:
            # 返回 tool_calls（模拟 OpenAI 响应格式）
            return type("r", (), {
                "choices": [type("c", (), {
                    "message": type("m", (), {
                        "content": None,
                        "tool_calls": [type("tc", (), {
                            "id": "call_001",
                            "function": type("f", (), {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                            })(),
                        })],
                    })(),
                })()],
            })()

        # 直接回答
        return type("r", (), {
            "choices": [type("c", (), {
                "message": type("m", (), {
                    "content": self._direct_answer(last_msg),
                    "tool_calls": None,
                })(),
            })()],
        })()

    def _tool_choice(self, msg: str) -> Optional[dict]:
        """根据消息选择工具（模拟 LLM 的判断）"""
        msg_l = msg.lower()
        if any(w in msg_l for w in ["天气", "气温", "下雨", "多少度"]):
            city = "北京" if "北京" in msg else "上海" if "上海" in msg else "深圳"
            return {"name": "get_weather", "arguments": {"city": city}}
        if any(w in msg_l for w in ["汇率", "兑换", "多少钱", "换算"]):
            return {"name": "get_exchange_rate", "arguments": {"from_currency": "USD", "to_currency": "CNY"}}
        if any(c.isdigit() for c in msg) and any(w in msg_l for w in ["+", "-", "*", "/", "算", "计算", "等于"]):
            expr = "".join(c for c in msg if c.isdigit() or c in "+-*/.()")
            return {"name": "calculate", "arguments": {"expression": expr}}
        if any(w in msg_l for w in ["是什么", "什么是", "解释", "定义", "token", "temperature", "embedding"]):
            return {"name": "search_docs", "arguments": {"query": msg}}
        return None

    def _direct_answer(self, msg: str) -> str:
        return f"收到你的问题：「{msg[:30]}...」。这是一个直接回答（无需调用工具）。"


# ====================== 完整的 Agent 执行循环 ======================

def run_agent(user_input: str, verbose: bool = True):
    """Agent 执行循环 —— Function Calling 的完整流程
    
    流程：
    1. 用户输入
    2. LLM 返回 tool_calls（或直接回答）
    3. 如果有 tool_calls，执行工具，把结果加入 messages
    4. 回到步骤 2，直到 LLM 直接回答
    
    这就是 ReAct 模式的基础：
    Think → Act → Observe → Think → Act → ... → Answer
    """
    client = DemoAgentClient()
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个智能助手，可以调用工具来回答用户问题。"
                "当需要查询天气、汇率、计算或搜索文档时，使用对应的工具。"
                "获得工具结果后，用自然语言向用户回复。"
                "回复时用中文。"
            ),
        },
        {"role": "user", "content": user_input},
    ]

    max_turns = 5  # 防止死循环
    for turn in range(max_turns):
        if verbose:
            print(f"\n{'='*50}")
            print(f"Turn {turn + 1}")

        # 1. 调用 LLM
        response = client.chat(messages, tools=TOOLS)
        msg = response.choices[0].message

        # 2. 如果有 tool_calls，执行工具
        if msg.tool_calls:
            if verbose:
                print(f"[LLM 决定调用工具]")

            # 添加 assistant 消息（包含 tool_calls）
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # 执行每个 tool_call
            for tc in msg.tool_calls:
                func_name = tc.function.name
                arguments = json.loads(tc.function.arguments)

                if verbose:
                    print(f"  工具: {func_name}")
                    print(f"  参数: {json.dumps(arguments, ensure_ascii=False)}")

                # 执行工具函数
                func = TOOL_FUNCTIONS.get(func_name)
                if func:
                    result = func(**arguments)
                else:
                    result = {"error": f"未知工具: {func_name}"}

                if verbose:
                    print(f"  结果: {json.dumps(result, ensure_ascii=False)}")

                # 添加 tool 消息（包含执行结果）
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # 循环继续，LLM 会基于工具结果再判断
            continue

        # 3. 直接回答 → 结束
        if verbose:
            print(f"[LLM 直接回答]")
        return msg.content

    return "达到最大轮数，未能获得最终答案。"


# ====================== 演示场景 ======================

def demo_weather():
    """场景1：单工具调用 —— 查天气"""
    print("\n" + "="*60)
    print("场景1：查天气（单工具调用）")
    print("="*60)
    print("用户: 北京今天天气怎么样？\n")
    answer = run_agent("北京今天天气怎么样？")
    print(f"\n最终回答: {answer}")


def demo_calculation():
    """场景2：单工具调用 —— 数学计算"""
    print("\n" + "="*60)
    print("场景2：数学计算")
    print("="*60)
    print("用户: 帮我算一下 (100 + 50) * 3 等于多少？\n")
    answer = run_agent("帮我算一下 (100 + 50) * 3 等于多少？")
    print(f"\n最终回答: {answer}")


def demo_direct_answer():
    """场景3：不需要工具 —— 直接回答"""
    print("\n" + "="*60)
    print("场景3：不需要工具（直接回答）")
    print("="*60)
    print("用户: 你好，你是谁？\n")
    answer = run_agent("你好，你是谁？")
    print(f"\n最终回答: {answer}")


def demo_manual_flow():
    """场景4：手动演示完整的调用链
    
    这是在你自己的代码中使用 Function Calling 的标准模式。
    """
    print("\n" + "="*60)
    print("场景4：手动调用链（最底层的方式）")
    print("="*60)

    messages = [
        {"role": "system", "content": "你是助手，可以调用工具。"},
        {"role": "user", "content": "北京天气如何？"},
    ]

    # Step 1: 第一次调用 LLM
    print("\nStep 1: 第一次调用 LLM...")
    print(f"  Messages: {len(messages)} 条")

    # 实际代码中：
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini", messages=messages, tools=TOOLS,
    # )
    # tool_calls = response.choices[0].message.tool_calls

    # 模拟 LLM 返回了 tool_call
    tool_call = {
        "id": "call_001",
        "function": {"name": "get_weather", "arguments": '{"city": "北京"}'},
    }
    print(f"  LLM 返回: 需要调用 {tool_call['function']['name']}")

    # Step 2: 执行工具
    print("\nStep 2: 执行工具...")
    args = json.loads(tool_call["function"]["arguments"])
    result = get_weather(**args)
    print(f"  工具结果: {json.dumps(result, ensure_ascii=False)}")

    # Step 3: 把结果发回 LLM
    messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
    messages.append({"role": "tool", "tool_call_id": "call_001", "content": json.dumps(result, ensure_ascii=False)})

    print("\nStep 3: 把工具结果发回 LLM...")
    print(f"  Messages: {len(messages)} 条")
    print(f"  LLM 最终会基于工具结果生成自然语言回答")


# ====================== 主入口 ======================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║      Function Calling 实战                   ║
╚══════════════════════════════════════════════╝
    """)

    demo_weather()
    demo_calculation()
    demo_direct_answer()
    demo_manual_flow()

    print("\n\n总结：")
    print("  Function Calling 的核心流程：")
    print("  用户输入 → LLM 判断 → (需要工具?) → 返回函数名+参数")
    print("  → 你的代码执行 → 结果发回 LLM → LLM 生成回复")
    print()
    print("  这是 Agent、RAG、ChatGPT Plugins 的底层机制。")
