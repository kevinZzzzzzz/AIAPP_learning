"""
Python 面向对象 (OOP) 与 TS Interface / Class 对比指南
======================================================
在 AI 框架（如 LangChain, LlamaIndex, OpenAI SDK）中，面向对象和类 (Class) 被大量使用。
本 Demo 帮你将 JS/TS Class 概念快速映射到 Python Class。

运行方法：python 05_面向对象与TS_Interface对比.py
"""

from dataclasses import dataclass, field
from typing import Protocol, List
from abc import ABC, abstractmethod


# === 1. Class 基础定义 (constructor, this vs __init__, self) ===
"""
JS/TS 写法:
class BaseAgent {
  private apiKey: string;
  public modelName: string;

  constructor(modelName: string, apiKey: string) {
    this.modelName = modelName;
    this.apiKey = apiKey;
  }

  public chat(prompt: string): string {
    return `[${this.modelName}] Response to: ${prompt}`;
  }
}
"""

class BaseAgent:
    def __init__(self, model_name: str, api_key: str):
        # Python 中没有 this，全部显式传入 `self` 作为第一个参数
        self.model_name = model_name
        
        # 私有属性习惯用法：
        # 单下划线 `_api_key` 表示约定私有 (受保护)
        # 双下划线 `__api_key` 会触发名称修饰 (Name Mangling)，相当于 JS 的 #apiKey 真正私有
        self._api_key = api_key

    def chat(self, prompt: str) -> str:
        return f"[{self.model_name}] 响应: '{prompt}' (Key: {self._api_key[:4]}***)"

    # === Getter / Setter (TS 中的 get/set 属性访问器) ===
    @property
    def info(self) -> str:
        # JS: get info() { return ... }
        return f"Agent Model: {self.model_name}"

    # === Static Method 静态方法 ===
    @staticmethod
    def get_supported_models() -> list[str]:
        # JS: static getSupportedModels() { ... }
        return ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet"]


# === 2. 类的继承 (Extends vs Python 继承) ===
"""
JS/TS:
class CustomAgent extends BaseAgent {
  private temperature: number;
  constructor(modelName: string, apiKey: string, temperature = 0.7) {
    super(modelName, apiKey);
    this.temperature = temperature;
  }
}
"""

class CustomAgent(BaseAgent):  # 括号里写父类名称
    def __init__(self, model_name: str, api_key: str, temperature: float = 0.7):
        super().__init__(model_name, api_key)  # 调用父类构造函数
        self.temperature = temperature

    # 方法重写 (Override)
    def chat(self, prompt: str) -> str:
        base_res = super().chat(prompt)
        return f"{base_res} [Temp: {self.temperature}]"


# === 3. TS Interface 接口定义 (Python 中的 Protocol - 鸭子类型) ===
"""
TS Interface 定义行为契约:
interface Tool {
  name: string;
  execute(args: string): string;
}
"""

class ToolProtocol(Protocol):
    """Python Protocol: 只要实现了 name 和 execute 方法，就被认为是 Tool，无需显式继承！(Duck Typing)"""
    name: str
    def execute(self, args: str) -> str: ...


class CalculatorTool:
    name: str = "calculator"
    def execute(self, args: str) -> str:
        return f"计算结果({args}) = 42"


def run_tool(tool: ToolProtocol, input_str: str):
    print(f"运行工具 [{tool.name}]: {tool.execute(input_str)}")


# === 4. Dataclass (🔥前端开发者最爱：自动生成构造函数的简洁 Class) ===
"""
TS 写法:
interface UserProfile {
  id: string;
  name: string;
  tags: string[];
}
"""

@dataclass
class UserProfile:
    # 不需要写 __init__！dataclass 会自动帮你生成 __init__、__repr__ (toString)、__eq__ 等方法！
    id: str
    name: str
    role: str = "user"
    tags: list[str] = field(default_factory=list)  # 列表等可变默认值需要用 field(default_factory=list)

    def add_tag(self, tag: str):
        self.tags.append(tag)


def demo_oop_in_action():
    print("\n--- 1. 基础类与继承测试 ---")
    agent = CustomAgent("deepseek-chat", "sk-1234567890", temperature=0.2)
    print(agent.info)
    print(agent.chat("什么是 AI Agent？"))
    print("支持的模型列表:", CustomAgent.get_supported_models())

    print("\n--- 2. Protocol (鸭子类型接口) 测试 ---")
    calc = CalculatorTool()
    run_tool(calc, "21 * 2")

    print("\n--- 3. Dataclass 测试 ---")
    user = UserProfile(id="u_001", name="Kevin")
    user.add_tag("Python速成")
    user.add_tag("AI开发")
    # print(user) 会自动打出漂亮的对象结构，相当于 JS 的 JSON.stringify(user)
    print("Dataclass 打印效果:", user)


if __name__ == "__main__":
    print("==================================================")
    print("  Python 面向对象与 TS Class/Interface 对比 Demo")
    print("==================================================")
    demo_oop_in_action()
