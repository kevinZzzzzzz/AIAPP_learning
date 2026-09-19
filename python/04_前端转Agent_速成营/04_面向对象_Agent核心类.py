# 04_面向对象_Agent核心类.py

"""
进阶：面向对象编程 (OOP) 与 Agent 类的封装
前端写 React / Vue 习惯了函数式 (Hooks, Composables)。
但在 Python AI 开发中 (比如 LangChain), OOP 面向对象非常普遍。
你需要熟悉 class、__init__、__call__ 以及继承的概念。
"""

class BaseAgent:
    """
    Agent 基类。定义了所有 Agent 都会有的通用属性和方法。
    """
    # __init__ 相当于 JS Class 的 constructor()
    def __init__(self, name: str, system_prompt: str):
        self.name = name  # self 相当于 JS 的 this
        self.system_prompt = system_prompt
        self.memory = []  # 保存对话历史
        
    def add_memory(self, role: str, content: str):
        """向记忆中添加一条消息"""
        self.memory.append({"role": role, "content": content})
        
    def _prepare_messages(self, user_msg: str) -> list:
        """
        内部方法 (Python 里习惯用单下划线开头表示 protected 方法，虽然只是约定)
        组装发给大模型的消息数组
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.memory)
        messages.append({"role": "user", "content": user_msg})
        return messages


# 继承 (Inheritance)
class ChatAgent(BaseAgent):
    """
    具体的对话 Agent，继承自 BaseAgent。
    """
    def __init__(self, name: str, system_prompt: str, temperature: float = 0.7):
        # super() 相当于 JS 的 super()，调用父类构造函数
        super().__init__(name, system_prompt)
        self.temperature = temperature
        
    # __call__ 是一种特殊的“魔术方法”。
    # 它允许你像调用函数一样调用一个类的实例对象！(JS中极少见这种操作)
    def __call__(self, user_input: str) -> str:
        """
        当执行 agent("你好") 时，实际上是在调用这个方法。
        """
        print(f"\n[{self.name}] 思考中... (温度: {self.temperature})")
        
        # 1. 组装上下文
        msgs = self._prepare_messages(user_input)
        
        # 2. 记录用户输入
        self.add_memory("user", user_input)
        
        # 3. 模拟调用 LLM (这里直接 mock 返回)
        mock_response = f"我是 {self.name}，我已经明白了你的意思。这是根据规则生成的回复。"
        
        # 4. 记录 AI 回复
        self.add_memory("assistant", mock_response)
        
        return mock_response


def oop_demo():
    print("--- 面向对象封装 Agent 演示 ---")
    
    # 实例化对象
    assistant = ChatAgent(
        name="客服小助手",
        system_prompt="你是一个礼貌的客服，用简短的话回答问题。",
        temperature=0.3
    )
    
    # 注意这里！因为类实现了 __call__ 方法，所以实例 assistant 可以被当做函数调用
    # 这种写法在 Python 的 AI 框架 (PyTorch, LangChain 等) 中极其常见！
    reply1 = assistant("我的快递到哪了？")
    print(f"AI: {reply1}")
    
    reply2 = assistant("帮我催一下")
    print(f"AI: {reply2}")
    
    print("\nAgent 当前记忆:")
    for m in assistant.memory:
        print(f"[{m['role']}]: {m['content']}")


if __name__ == "__main__":
    oop_demo()
