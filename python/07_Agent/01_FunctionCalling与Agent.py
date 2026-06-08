"""
Function Calling + Agent 实战
=================================================================

Function Calling 是 LLM 从"聊天机器人"进化为"AI Agent"的关键技术。

工作原理：
1. 定义可用的工具（函数）及其描述
2. 用户提问时，LLM 判断是否需要调用工具
3. 如果需要，LLM 返回要调用的函数名和参数
4. 开发者执行函数，把结果返回给 LLM
5. LLM 基于工具结果生成最终答案

前端类比：就像组件可以 emit 事件给父组件处理，
LLM 通过 Function Calling "emit" 一个工具调用请求给开发者处理。
"""

import json
from typing import Any, Callable
from dataclasses import dataclass, field


# ======================== 1. 定义工具 ========================

@dataclass
class Tool:
    """工具定义 —— 和 OpenAI Function Calling 格式一致"""
    name: str
    description: str
    parameters: dict  # JSON Schema 格式
    handler: Callable  # 实际执行函数

    def to_openai_schema(self) -> dict:
        """转换为 OpenAI Function Calling 的 Schema 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ======================== 2. 创建一组实用工具 ========================

def get_current_weather(city: str, unit: str = "celsius") -> str:
    """获取天气（模拟）"""
    weather_data = {
        "北京": {"celsius": "25°C，晴天", "fahrenheit": "77°F，晴天"},
        "上海": {"celsius": "30°C，多云", "fahrenheit": "86°F，多云"},
        "深圳": {"celsius": "28°C，阵雨", "fahrenheit": "82°F，阵雨"},
        "东京": {"celsius": "22°C，多云", "fahrenheit": "72°F，多云"},
    }
    city_weather = weather_data.get(city, {"celsius": "数据不可用", "fahrenheit": "数据不可用"})
    return city_weather.get(unit, city_weather["celsius"])


def search_web(query: str) -> str:
    """搜索互联网（模拟）"""
    results = {
        "python": "Python 3.12 是最新稳定版本，引入了新的 f-string 语法和更好的错误提示。",
        "fastapi": "FastAPI 0.111 于 2024 年发布，新增对 Pydantic v2 的完整支持。",
        "langchain": "LangChain 最新版本为 0.2.x，引入了 LangGraph 用于构建复杂 Agent 工作流。",
        "rag": "RAG 技术的最新趋势包括：Agent-RAG 结合、Graph RAG、多模态 RAG。",
    }
    
    for key, value in results.items():
        if key in query.lower():
            return value
    
    return f"关于「{query}」的搜索结果：这是一项正在快速发展的 AI 技术..."

import math

def calculator(expression: str) -> str:
    """安全的数学计算器"""
    allowed = set("0123456789+-*/(). sqrt")
    
    # 安全检查
    if not all(c in allowed or c.isspace() for c in expression):
        return "错误：表达式包含不允许的字符"
    
    # 防止过长的表达式
    if len(expression) > 200:
        return "错误：表达式过长"
    
    try:
        # 使用安全的 eval 环境
        safe_dict = {"sqrt": math.sqrt}
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {e}"


def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


# 注册所有工具
def create_tools() -> list[Tool]:
    """创建工具注册表"""
    return [
        Tool(
            name="get_current_weather",
            description="获取指定城市的当前天气信息",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、深圳",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认为 celsius",
                    },
                },
                "required": ["city"],
            },
            handler=get_current_weather,
        ),
        Tool(
            name="search_web",
            description="搜索互联网获取最新信息，当用户询问实时信息或未知知识时使用",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                },
                "required": ["query"],
            },
            handler=search_web,
        ),
        Tool(
            name="calculator",
            description="执行数学计算，支持 + - * / () 和 sqrt。例如：'2 + 3 * 4' 或 'sqrt(16)'",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式",
                    },
                },
                "required": ["expression"],
            },
            handler=calculator,
        ),
        Tool(
            name="get_current_time",
            description="获取当前的日期和时间",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=get_current_time,
        ),
    ]


# ======================== 3. Agent 循环 ========================

@dataclass
class ToolCall:
    """LLM 返回的工具调用"""
    id: str
    name: str
    arguments: dict


@dataclass
class AgentStep:
    """Agent 执行的一步"""
    thought: str = ""  # LLM 的思考过程
    tool_call: ToolCall | None = None
    tool_result: str = ""
    final_answer: str = ""


@dataclass
class AgentState:
    """Agent 的状态"""
    messages: list[dict] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    max_iterations: int = 10


class Agent:
    """简易 AI Agent —— 实现 ReAct 模式的核心循环
    
    ReAct = Reasoning（推理） + Acting（执行）
    
    伪代码：
    while not finished and iterations < max:
        LLM.think(user_input, tool_results) → next_action
        if next_action == answer:
            return answer
        elif next_action == tool_call:
            result = execute_tool(tool_name, args)
            continue loop
    """
    
    def __init__(self, tools: list[Tool], model: str = "gpt-4o-mini"):
        self.tools = {tool.name: tool for tool in tools}
        self.tool_schemas = [tool.to_openai_schema() for tool in tools]
        self.model = model
    
    def get_tool_help(self) -> str:
        """生成工具帮助信息"""
        lines = ["可用工具："]
        for tool in self.tools.values():
            lines.append(f"  - {tool.name}: {tool.description}")
        return "\n".join(lines)
    
    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行一个工具"""
        if tool_name not in self.tools:
            return f"错误：未知工具 {tool_name}"
        
        tool = self.tools[tool_name]
        try:
            result = tool.handler(**arguments)
            return str(result)
        except Exception as e:
            return f"工具执行错误: {e}"
    
    def build_system_prompt(self) -> str:
        """构建 Agent 的 System Prompt"""
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])
        
        return f"""你是一个智能助手，可以调用工具来完成任务。

{tool_descriptions}

回答格式：
1. 如果需要调用工具，只输出工具调用的 JSON：
   {{"action": "tool_call", "tool": "工具名", "args": {{"参数名": "参数值"}}}}

2. 如果可以直接回答，输出：
   {{"action": "answer", "content": "你的回答"}}

3. 收到工具结果后，综合所有信息给出最终答案。

注意：
- 每次只能调用一个工具
- 尽量少调用工具，能一次回答的不要调用
"""
    
    async def run(self, user_input: str) -> AgentState:
        """运行 Agent（需要在 async 环境中使用）"""
        state = AgentState()
        state.messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_input},
        ]
        
        for iteration in range(state.max_iterations):
            step = AgentStep()
            
            # Step 1: 调用 LLM 决策（这里用模拟代替真实 API）
            decision = await self._simulate_llm_decision(state.messages, iteration)
            
            try:
                action = json.loads(decision)
            except json.JSONDecodeError:
                step.final_answer = decision
                state.steps.append(step)
                break
            
            step.thought = action.get("reasoning", "")
            
            if action.get("action") == "answer":
                step.final_answer = action["content"]
                state.steps.append(step)
                break
            
            elif action.get("action") == "tool_call":
                tool_name = action["tool"]
                tool_args = action.get("args", {})
                
                step.tool_call = ToolCall(
                    id=str(iteration),
                    name=tool_name,
                    arguments=tool_args,
                )
                
                # Step 2: 执行工具
                step.tool_result = self.execute_tool(tool_name, tool_args)
                
                # Step 3: 将工具结果添加到消息历史
                state.messages.append({
                    "role": "assistant",
                    "content": json.dumps(action, ensure_ascii=False),
                })
                state.messages.append({
                    "role": "tool",
                    "content": step.tool_result,
                })
                
                state.steps.append(step)
            else:
                step.final_answer = f"未知 action: {action.get('action')}"
                state.steps.append(step)
                break
        
        return state
    
    async def _simulate_llm_decision(self, messages: list[dict], iteration: int) -> str:
        """模拟 LLM 决策 —— 生产环境替换为真实 API 调用
        
        这个方法的意图是演示 Agent 的决策逻辑，实际应用中：
        response = await openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_schemas,
            tool_choice="auto",
        )
        """
        user_content = messages[1]["content"] if len(messages) > 1 else ""
        
        # 根据用户输入模拟决策
        if iteration == 0:
            if "天气" in user_content:
                # 提取城市名
                cities = ["北京", "上海", "深圳", "东京"]
                found_city = "北京"
                for city in cities:
                    if city in user_content:
                        found_city = city
                        break
                return json.dumps({
                    "action": "tool_call",
                    "tool": "get_current_weather",
                    "args": {"city": found_city},
                }, ensure_ascii=False)
            
            if any(kw in user_content for kw in ["最新", "新技术", "趋势", "搜索"]):
                return json.dumps({
                    "action": "tool_call",
                    "tool": "search_web",
                    "args": {"query": user_content},
                }, ensure_ascii=False)
            
            if any(c in user_content for c in "+-*/") and any(c.isdigit() for c in user_content):
                # 提取表达式
                return json.dumps({
                    "action": "tool_call",
                    "tool": "calculator",
                    "args": {"expression": user_content},
                }, ensure_ascii=False)
            
            if "时间" in user_content or "几点" in user_content:
                return json.dumps({
                    "action": "tool_call",
                    "tool": "get_current_time",
                    "args": {},
                }, ensure_ascii=False)
            
            return json.dumps({
                "action": "answer",
                "content": f"这是一个关于「{user_content}」的模拟回复。",
            }, ensure_ascii=False)
        
        # 后续迭代：基于工具结果回答
        tool_result = messages[-1]["content"] if messages[-1]["role"] == "tool" else ""
        return json.dumps({
            "action": "answer",
            "content": f"根据工具返回的结果：{tool_result[:100]}",
        }, ensure_ascii=False)


# ======================== 4. 工厂函数 ========================

def create_weather_agent() -> Agent:
    """创建一个天气助手 Agent"""
    tools = create_tools()
    return Agent(tools=tools, model="gpt-4o-mini")


# ======================== 5. 运行 Demo ========================

async def main():
    print("=" * 60)
    print("AI Agent Demo")
    print("=" * 60)
    
    agent = create_weather_agent()
    
    # 打印可用工具
    print("\n" + agent.get_tool_help())
    
    # 测试各种查询
    test_queries = [
        "北京今天天气怎么样？",
        "深圳今天热不热？",
        "帮我算一下 (15 + 27) * 3 / 2",
        "现在几点了？",
        "Python 有什么最新进展？",
    ]
    
    for query in test_queries:
        print(f"\n{'='*40}")
        print(f"👤 用户: {query}")
        
        state = await agent.run(query)
        
        for i, step in enumerate(state.steps):
            print(f"\n--- 步骤 {i+1} ---")
            if step.tool_call:
                print(f"🔧 调用工具: {step.tool_call.name}")
                print(f"   参数: {step.tool_call.arguments}")
                print(f"   结果: {step.tool_result[:100]}")
            if step.final_answer:
                print(f"🤖 Agent: {step.final_answer}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
