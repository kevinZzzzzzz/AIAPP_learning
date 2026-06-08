"""
ReAct 模式（Reasoning + Acting）详解
=================================================================

ReAct（Reasoning + Acting）是构建 AI Agent 最经典的模式。

核心循环：
  Thought → Action → Observation → Thought → Action → ... → Final Answer

对比其他模式：
- ReAct: 推理和行动交替进行
- Plan-and-Execute: 先做完整计划，再逐步执行
- ReWOO: 先规划所有工具调用，然后批量执行
"""

import json
from typing import Any
from dataclasses import dataclass, field


# ======================== 1. ReAct 模式的形式化定义 ========================

"""
ReAct 循环的每一步都是以下格式：

Thought: 分析当前状态，决定下一步做什么
Action: 要执行的动作（调用工具）
Action Input: 工具的输入参数
Observation: 工具返回的结果
... (重复)
Thought: 我现在有足够的信息来回答
Final Answer: 最终答案

OpenAI 的 Function Calling 已经把 Action 和 Action Input 标准化了，
但理解 ReAct 模式有助于设计和调试复杂的 Agent 行为。
"""


# ======================== 2. ReAct 循环实现 ========================

@dataclass
class ReActStep:
    """ReAct 循环的一步"""
    thought: str        # 思考：分析当前状态
    action: str         # 行动：工具名称
    action_input: dict  # 行动输入：工具参数
    observation: str    # 观察：工具返回结果

@dataclass
class ReActResult:
    """ReAct 循环的最终结果"""
    question: str
    steps: list[ReActStep] = field(default_factory=list)
    final_answer: str = ""
    total_tokens: int = 0


class ReActAgent:
    """ReAct 模式的 Agent 实现
    
    这是 Agent 最经典的模式，LangChain 的 AgentExecutor 就是这个思路。
    """
    
    def __init__(self, tools: dict):
        self.tools = tools
    
    def build_prompt(self, question: str, previous_steps: list[ReActStep] = None) -> str:
        """构建 ReAct Prompt"""
        tool_descriptions = "\n".join([
            f"- {name}: {tool['description']}"
            for name, tool in self.tools.items()
        ])
        
        # 构建历史步骤
        history = ""
        if previous_steps:
            for step in previous_steps:
                history += f"""
Thought: {step.thought}
Action: {step.action}
Action Input: {json.dumps(step.action_input, ensure_ascii=False)}
Observation: {step.observation}
"""
        
        prompt = f"""你是一个智能助手，可以使用以下工具：

{tool_descriptions}

请使用以下格式回答问题：

Question: 用户的问题
Thought: 分析问题，决定下一步
Action: 工具名称（必须是上面列出的之一）
Action Input: 工具的 JSON 格式参数
Observation: 工具返回的结果（由系统填入）
...（这个 Thought/Action/Action Input/Observation 可以重复）
Thought: 我现在知道最终答案了
Final Answer: 最终答案

注意：
- 每次只执行一个 Action
- 工具之间可以组合使用
- 如果不需要工具，直接给出 Final Answer

{history}
Question: {question}
"""
        return prompt
    
    def run_sync(self, question: str, max_steps: int = 5) -> ReActResult:
        """同步运行 ReAct Agent（演示用，用规则匹配模拟 LLM 决策）"""
        result = ReActResult(question=question)
        
        for _ in range(max_steps):
            # 模拟 LLM 推理（实际应调用 API）
            decision = self._simulate_decision(question, result.steps)
            
            if decision["type"] == "final_answer":
                result.final_answer = decision["content"]
                break
            
            if decision["type"] == "action":
                tool_name = decision["action"]
                tool_input = decision["action_input"]
                
                # 执行工具
                if tool_name in self.tools:
                    observation = self.tools[tool_name]["handler"](**tool_input)
                else:
                    observation = f"错误：未知工具 {tool_name}"
                
                step = ReActStep(
                    thought=decision.get("thought", ""),
                    action=tool_name,
                    action_input=tool_input,
                    observation=str(observation),
                )
                result.steps.append(step)
        
        if not result.final_answer:
            result.final_answer = "无法在限制步骤内回答问题"
        
        return result
    
    def _simulate_decision(
        self, question: str, steps: list[ReActStep]
    ) -> dict:
        """模拟 LLM 决策 —— 用规则模拟 ReAct 推理过程"""
        
        # 第一步：分析问题，决定是否使用工具
        if not steps:
            if "天气" in question:
                return {
                    "type": "action",
                    "thought": "用户想查询天气，我需要调用天气工具",
                    "action": "get_weather",
                    "action_input": {"city": self._extract_city(question)},
                }
            elif "计算" in question or any(c in question for c in "+-*/"):
                return {
                    "type": "action",
                    "thought": "用户需要数学计算，我应该使用计算器工具",
                    "action": "calculator",
                    "action_input": self._extract_expression(question),
                }
            elif "搜索" in question or "什么是" in question:
                return {
                    "type": "action",
                    "thought": "用户想了解某个知识，我需要搜索",
                    "action": "search",
                    "action_input": {"query": question},
                }
            else:
                return {
                    "type": "final_answer",
                    "content": f"我理解了你的问题：{question}。这是一个模拟回答。",
                }
        
        # 有工具结果后：综合信息给出答案
        last_obs = steps[-1].observation
        return {
            "type": "final_answer",
            "content": f"根据工具返回的结果，我的回答是：{last_obs}",
        }
    
    def _extract_city(self, text: str) -> str:
        """简单城市名提取"""
        for city in ["北京", "上海", "深圳", "杭州", "广州"]:
            if city in text:
                return city
        return "北京"
    
    def _extract_expression(self, text: str) -> dict:
        """提取数学表达式"""
        # 简单取出算式部分
        for c in "+-*/":
            if c in text:
                # 找到包含算式的部分
                parts = text.split()
                for part in parts:
                    if any(op in part for op in "+-*/"):
                        return {"expression": part}
        return {"expression": text}


# ======================== 3. 多工具协作示例 ========================

def demo_react_in_action():
    """演示 ReAct Agent 处理复杂查询"""
    
    # 定义工具
    def get_weather(city: str) -> str:
        weather = {"北京": "25°C 晴天", "上海": "30°C 多云", "深圳": "28°C 阵雨"}
        return weather.get(city, "数据不可用")
    
    def calculator(expression: str) -> str:
        import math
        try:
            result = eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt})
            return str(result)
        except Exception as e:
            return str(e)
    
    def search(query: str) -> str:
        return f"关于'{query}'，这是模拟的搜索结果：内容非常丰富..."
    
    tools = {
        "get_weather": {"description": "获取城市天气", "handler": get_weather},
        "calculator": {"description": "数学计算", "handler": calculator},
        "search": {"description": "搜索信息", "handler": search},
    }
    
    agent = ReActAgent(tools)
    
    # 测试需要多工具协作的问题
    complex_queries = [
        "北京和上海今天哪个城市更热？",
        "帮我算一下 156 * 23 + 789",
        "搜索一下 Python 的最新动态",
        "直接打招呼：你好！",
    ]
    
    for query in complex_queries:
        print(f"\n{'='*50}")
        print(f"👤 用户: {query}")
        print(f"生成的 Prompt（前 300 字符）:")
        prompt = agent.build_prompt(query)
        print(prompt[:300] + "...")
        
        result = agent.run_sync(query)
        
        for i, step in enumerate(result.steps):
            print(f"\n--- ReAct 步骤 {i+1} ---")
            print(f"💭 Thought: {step.thought}")
            print(f"🔧 Action: {step.action}({step.action_input})")
            print(f"👁️ Observation: {step.observation}")
        
        print(f"\n🎯 Final Answer: {result.final_answer}")


# ======================== 4. 使用 LangChain 的 Agent（代码参考） ========================

"""
真实生产环境中，推荐使用 LangChain 的 AgentExecutor：

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    '''获取城市天气'''
    return f"{city}今天25°C，晴天"

@tool
def calculator(expression: str) -> str:
    '''执行数学计算'''
    return str(eval(expression))

# 创建 Agent
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [get_weather, calculator]

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,           # 打印推理过程
    max_iterations=5,       # 最大循环次数
    handle_parsing_errors=True,
)

# 运行
result = agent_executor.invoke({"input": "北京天气怎么样？"})
print(result["output"])
"""


# ======================== 5. Agent 模式对比 ========================

"""
ReAct（Reasoning + Acting）          ← 本章重点
  优点：灵活，适合复杂场景
  缺点：每步都需要 LLM 调用，token 消耗大
  场景：多步推理、需要动态决策的任务

Plan-and-Execute（计划+执行）
  优点：一次规划多次执行，效率高
  缺点：计划可能不准确，需要重规划
  场景：任务明确、步骤可预见的场景

ReWOO（Reason without Observation）
  优点：减少中间 Observation 的 token 消耗
  缺点：需要 LLM 能力较强
  场景：工具调用之间不相互依赖的场景

AutoGPT / BabyAGI
  优点：全自动，可自主分解子任务
  缺点：不可控，成本高，容易跑偏
  场景：探索性任务（不推荐生产环境）
"""


if __name__ == "__main__":
    demo_react_in_action()
