"""LangGraph 版本对照 —— 看清框架帮你做了什么。

## 使用前提

需要额外安装：
    uv add langgraph langchain-core langchain-deepseek

## 手写版 vs LangGraph 版对照表

| 能力 | 手写版（agent.py） | LangGraph | 谁更好 |
|---|---|---|---|
| ReAct 循环 | 自己写 while | 框架提供 | LangGraph 省事 |
| 状态管理 | 自己维护 messages 列表 | StateGraph 自动管理 | LangGraph |
| 持久化/断点续跑 | 无 | Checkpointer 一行接入 | LangGraph 完胜 |
| 人在环中断 | 回调函数硬编码 | interrupt() 原生支持 | LangGraph 完胜 |
| 条件分支 | if/else 堆砌 | 声明式条件边 | LangGraph 更清晰 |
| 调试可见性 | 完全可控，打印任何东西 | 需要理解框架抽象 | 手写版更透明 |
| 依赖体积 | 0 额外依赖 | 一堆依赖 | 手写版更轻 |
| 学习价值 | 理解本质 | 用得快 | **都要会** |

**结论**：先手写理解本质，再用框架提效。
但注意一个坑：LangGraph 的抽象会在出问题时挡住你 ——
如果你不懂下面的 ReAct 循环，遇到诡异行为时你无从下手。

## ⚠️ API 版本提醒（2026-09 核实）

LangGraph 1.0 已经废弃了 `langgraph.prebuilt.create_react_agent`。
新写法用 `langchain.agents.create_agent`。网上大量教程还是旧写法，
照着抄会看到弃用警告甚至报错。
"""
import logging

logger = logging.getLogger(__name__)


def build_langgraph_agent(tools: list, model_name: str = "deepseek-v4-flash"):
    """用 LangGraph 构建等价的 ReAct Agent。

    注意：这个函数需要额外依赖，缺依赖时给出清晰提示而不是直接 ImportError。
    """
    try:
        from langchain.agents import create_agent
        from langchain_deepseek import ChatDeepSeek
    except ImportError as ex:
        raise RuntimeError(
            f"缺少依赖：{ex}\n"
            f"请先安装：uv add langgraph langchain-core langchain-deepseek"
        ) from ex

    import os

    model = ChatDeepSeek(
        model=model_name,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0.1,
    )

    # 就这一行，等价于我们手写的 150 行 ReAct 循环。
    # 框架的价值就在这里：把循环、状态、错误处理都封装好了。
    # 但代价是你不知道里面发生了什么 —— 所以先手写是对的。
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "你是一个可以调用工具的助手。先判断是否需要工具，"
            "需要时一次调一个，拿到结果后再决定下一步。用中文简洁回答。"
        ),
    )
    return agent


def langchain_tool_example():
    """把我们的手写工具转成 LangChain 工具。

    对照点：LangChain 用 @tool 装饰器 + docstring 自动生成 Schema。
    这比我们手写 JSON Schema 舒服，但本质完全一样 ——
    都是生成「名称 + 描述 + 参数 Schema」三件套发给模型。
    """
    from langchain_core.tools import tool

    @tool
    def get_weather(city: str) -> str:
        """查询指定城市的天气。

        Args:
            city: 城市名称，如「北京」
        """
        # docstring 会自动变成 description，类型注解会自动变成参数 Schema。
        # 所以写 LangChain 工具时，docstring 质量直接决定工具调用质量。
        return f"{city}：晴，24℃"

    return get_weather


# ---------------------------------------------------------------- 使用示例
USAGE_DEMO = '''
# 方式一：直接用（最简）
import asyncio
from src.langgraph_version import build_langgraph_agent, langchain_tool_example

tools = [langchain_tool_example()]
agent = build_langgraph_agent(tools)

result = agent.invoke({
    "messages": [{"role": "user", "content": "北京天气怎么样？"}]
})
print(result["messages"][-1].content)


# 方式二：加持久化（这是 LangGraph 最大的价值）
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.db") as memory:
    agent = create_agent(model=model, tools=tools, checkpointer=memory)

    # thread_id 就是"会话 ID"，不同 ID 完全隔离
    cfg = {"configurable": {"thread_id": "user-123"}}
    agent.invoke({"messages": [{"role": "user", "content": "我叫张三"}]}, cfg)
    r = agent.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, cfg)
    print(r["messages"][-1].content)   # → 张三

    # 进程重启后，用同样的 thread_id 还能接上 —— 这是手写版做不到的


# 方式三：人在环（interrupt）
from langgraph.types import interrupt

# 在需要审批的节点里调用 interrupt()，图会暂停，
# 把决定权交出去，用户批准后再 resume。
# 这比自己写回调函数干净得多，尤其适合 Web 场景（异步等待）。
'''

if __name__ == "__main__":
    print(USAGE_DEMO)
