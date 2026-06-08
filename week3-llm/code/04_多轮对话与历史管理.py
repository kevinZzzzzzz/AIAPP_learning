"""
多轮对话与对话历史管理
=========================

演示如何管理 LLM 的对话历史，实现真正的"多轮对话"。

核心知识点：
1. messages 数据结构
2. 对话窗口策略（防 token 爆炸）
3. 对话摘要策略
4. 多用户会话隔离
5. 持久化与恢复
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional


# ====================== 消息数据结构 ======================

@dataclass
class Message:
    """单条消息
    
    对应 OpenAI API 的 messages 格式:
    {"role": "user|assistant|system|tool", "content": "..."}
    """
    role: str       # user / assistant / system / tool
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    def __repr__(self):
        preview = self.content[:40] + "..." if len(self.content) > 40 else self.content
        return f"[{self.role}] {preview}"


# ====================== 会话管理器 ======================

class Conversation:
    """单个对话会话
    
    管理一个会话的完整消息历史，支持：
    - 添加消息
    - 窗口截断（防止超出 token 上限）
    - 摘要压缩
    - 导出/恢复
    """

    def __init__(self, session_id: str, system_prompt: str = ""):
        self.session_id = session_id
        self.messages: list[Message] = []
        self.max_turns = 20  # 默认保留最近 20 轮

        if system_prompt:
            self.add("system", system_prompt)

    def add(self, role: str, content: str):
        """添加一条消息"""
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self._auto_trim()

    def _auto_trim(self):
        """自动裁剪：如果消息太多，只保留 system + 最近 max_turns 条"""
        # 找到 system 消息
        system_msgs = [m for m in self.messages if m.role == "system"]
        non_system = [m for m in self.messages if m.role != "system"]

        if len(non_system) > self.max_turns * 2:
            self.messages = system_msgs + non_system[-(self.max_turns * 2):]

    def to_api_format(self) -> list[dict]:
        """转为 OpenAI API 的 messages 格式"""
        return [m.to_dict() for m in self.messages]

    def get_last_n_turns(self, n: int) -> list[Message]:
        """获取最近 n 轮对话（1轮 = 1 user + 1 assistant）"""
        non_system = [m for m in self.messages if m.role != "system"]
        return non_system[-(n * 2):]

    def summarize_and_compress(self) -> str:
        """生成对话摘要，用于压缩历史
        
        实际项目中，这里会调用 LLM 来生成摘要：
        summary = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "总结以下对话"}, ...],
        )
        """
        turns = len([m for m in self.messages if m.role == "user"])
        total_chars = sum(len(m.content) for m in self.messages)
        return f"[对话摘要] 共 {turns} 轮对话，约 {total_chars} 字符。"

    def stats(self) -> dict:
        """会话统计"""
        roles = {}
        total_chars = 0
        for m in self.messages:
            roles[m.role] = roles.get(m.role, 0) + 1
            total_chars += len(m.content)

        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "by_role": roles,
            "total_chars": total_chars,
            "estimated_tokens": total_chars * 2 // 3,  # 粗略估算
        }

    def reset(self):
        """重置会话（保留 system prompt）"""
        self.messages = [m for m in self.messages if m.role == "system"]

    def export(self) -> str:
        """导出为 JSON"""
        data = {
            "session_id": self.session_id,
            "created_at": self.messages[0].timestamp if self.messages else time.time(),
            "messages": [m.to_dict() for m in self.messages],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def import_from_json(cls, data: dict) -> "Conversation":
        """从 JSON 恢复会话"""
        conv = cls(session_id=data["session_id"])
        for m in data["messages"]:
            conv.add(m["role"], m["content"])
        return conv


# ====================== 多用户会话管理 ======================

class SessionManager:
    """管理多个用户的会话
    
    实际项目中，会话数据应存到 Redis/数据库。
    """

    def __init__(self):
        self._sessions: dict[str, Conversation] = {}

    def get_or_create(self, user_id: str, system_prompt: str = "") -> Conversation:
        """获取或创建用户会话"""
        if user_id not in self._sessions:
            self._sessions[user_id] = Conversation(
                session_id=user_id,
                system_prompt=system_prompt,
            )
        return self._sessions[user_id]

    def delete(self, user_id: str):
        """删除用户会话"""
        self._sessions.pop(user_id, None)

    def list_sessions(self) -> list[dict]:
        """列出所有活跃会话"""
        return [
            {"user_id": uid, "messages": len(conv.messages)}
            for uid, conv in self._sessions.items()
        ]


# ====================== 流式对话模拟 ======================

class StreamingConversation:
    """支持流式输出的对话
    
    演示如何在流式输出中管理对话历史。
    """

    def __init__(self, system_prompt: str = ""):
        self.history: list[dict] = []
        if system_prompt:
            self.history.append({"role": "system", "content": system_prompt})

    def prepare_request(self, user_input: str) -> list[dict]:
        """准备发送给 LLM 的 messages"""
        self.history.append({"role": "user", "content": user_input})
        return self.history.copy()

    def on_stream_chunk(self, chunk: str):
        """处理流式 chunk（在 demo 中直接打印并累积）"""
        self._buffer = getattr(self, "_buffer", "") + chunk

    def on_stream_end(self):
        """流式输出完成后，把完整的回复存入历史"""
        full_reply = getattr(self, "_buffer", "")
        self.history.append({"role": "assistant", "content": full_reply})
        self._buffer = ""


# ====================== 演示 ======================

def demo_multi_turn_basics():
    """演示1：多轮对话基础"""
    print("="*60)
    print("演示1：多轮对话基础")
    print("="*60)

    conv = Conversation(
        session_id="demo-001",
        system_prompt="你是一个前端转 AI 的学习助手。用中文回答，简洁明了。",
    )

    # 模拟对话
    exchanges = [
        ("我叫小明，我是前端工程师", "你好小明！前端转 AI 是个很好的方向。"),
        ("Python 和 JS 有什么区别？", "两者语法相似但运行环境不同。Python 是强类型..."),
        ("我之前问的我叫什么？", "你叫小明，是前端工程师！"),  # AI 需要记住上下文
    ]

    for user_msg, _ in exchanges:
        conv.add("user", user_msg)
        # 在实际代码中，这里会调用 client.chat.completions.create(...)
        # 这里用模拟回复
        reply = f"[模拟回复] 收到: {user_msg[:20]}..."
        conv.add("assistant", reply)

    # 打印对话历史
    print("\n完整对话历史：")
    for msg in conv.messages:
        print(f"  {msg}")

    # 统计
    stats = conv.stats()
    print(f"\n统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    return conv


def demo_window_strategy():
    """演示2：窗口截断策略"""
    print("\n" + "="*60)
    print("演示2：窗口截断策略")
    print("="*60)

    conv = Conversation(session_id="demo-002", system_prompt="你是 AI 助手。")
    
    # 模拟超长对话（30 轮）
    for i in range(30):
        conv.add("user", f"第 {i+1} 个问题")
        conv.add("assistant", f"第 {i+1} 个回答")

    print(f"原始消息数: 30 轮 × 2 + 1 system = 61 条")
    print(f"当前消息数: {conv.stats()['total_messages']}")
    print(f"已自动截断到最多 {conv.max_turns} 轮")
    print()

    # 查看保留了什么
    print("保留的消息（最近5条）:")
    for msg in conv.messages[-5:]:
        print(f"  {msg}")


def demo_summary_strategy():
    """演示3：摘要压缩策略"""
    print("\n" + "="*60)
    print("演示3：摘要压缩策略")
    print("="*60)

    # 场景：用户和 AI 讨论了一个很长的技术方案，但 token 快超了
    conv = Conversation(
        session_id="demo-003",
        system_prompt="你是 AI 助手。",
    )

    # 长对话（模拟）
    conv.add("user", "如何设计一个高并发的 AI 聊天系统？这是需求文档...(此处省略5000字)")
    conv.add("assistant", "建议使用 FastAPI + Redis + 消息队列的架构...(此处省略3000字)")
    conv.add("user", "数据库选型有什么建议？")
    conv.add("assistant", "根据你的场景，建议 PostgreSQL 存结构化数据，MongoDB 存对话历史...")
    conv.add("user", "向量数据库呢？")
    conv.add("assistant", "推荐 Qdrant 或 ChromaDB，适合中小规模...")
    conv.add("user", "好的，那最终方案是什么？")

    print(f"当前对话: {conv.stats()['total_messages']} 条消息")
    print(f"预估 token: {conv.stats()['estimated_tokens']}")

    # 策略：把前几轮总结成摘要，只保留最近一轮
    summary = conv.summarize_and_compress()
    last_turn = conv.get_last_n_turns(1)  # 最近1轮

    print(f"\n摘要: {summary}")
    print(f"保留最近一轮:")
    for msg in last_turn:
        print(f"  {msg}")

    # 构建压缩后的 messages
    compressed = [
        {"role": "system", "content": f"你是 AI 助手。以下是历史对话摘要：{summary}"},
        *[m.to_dict() for m in last_turn],
    ]
    print(f"\n压缩后: {len(compressed)} 条消息 → 可发送给 LLM")


def demo_session_manager():
    """演示4：多用户会话管理"""
    print("\n" + "="*60)
    print("演示4：多用户会话管理")
    print("="*60)

    manager = SessionManager()

    # 模拟多个用户
    users = [
        ("user_a", "你是 Python 导师"),
        ("user_b", "你是面试官，出前端面试题"),
        ("user_a", "你是 Python 导师"),   # 同一用户再访问
    ]

    for user_id, sp in users:
        conv = manager.get_or_create(user_id, sp)
        conv.add("user", f"{user_id} 的问题")
        conv.add("assistant", f"对 {user_id} 的回答")

    # 查看所有会话
    print("当前活跃会话:")
    for s in manager.list_sessions():
        print(f"  {s['user_id']}: {s['messages']} 条消息")

    # 导出 user_a 的会话
    conv_a = manager.get_or_create("user_a")
    print(f"\nuser_a 的会话导出:\n{conv_a.export()[:200]}...")


def demo_export_import():
    """演示5：导出和恢复会话"""
    print("\n" + "="*60)
    print("演示5：会话导出与恢复")
    print("="*60)

    original = Conversation(session_id="export-test", system_prompt="你是助手")
    original.add("user", "问题1")
    original.add("assistant", "回答1")

    # 导出
    json_str = original.export()
    print(f"导出 JSON 长度: {len(json_str)} 字符")

    # 恢复
    restored = Conversation.import_from_json(json.loads(json_str))
    print(f"恢复后消息数: {len(restored.messages)}")
    print(f"恢复后第一条: {restored.messages[0]}")


# ====================== 最佳实践总结 ======================

def print_best_practices():
    """打印最佳实践"""
    print("\n" + "="*60)
    print("多轮对话最佳实践总结")
    print("="*60)

    tips = [
        ("System Prompt", "始终放在 messages[0]，定义 AI 的行为准则"),
        ("历史顺序", "严格按时间顺序: [system, user, asst, user, asst, ...]"),
        ("Token 预算", "给 messages 预留 70% token，给回答留 30%"),
        ("截断策略", "短对话用窗口截断（保留最近N轮），长对话用摘要压缩"),
        ("用户隔离", "每个用户独立会话，用 session_id 区分"),
        ("持久化", "存到数据库/Redis，支持服务重启后恢复"),
        ("输出格式", "不要截断 assistant 的消息，否则 LLM 输出可能损坏"),
        ("最大轮数", "Agent 循环要设置 max_turns 防死循环"),
    ]

    for title, tip in tips:
        print(f"  {title:<16} | {tip}")


# ====================== 主入口 ======================

if __name__ == "__main__":
    demo_multi_turn_basics()
    demo_window_strategy()
    demo_summary_strategy()
    demo_session_manager()
    demo_export_import()
    print_best_practices()

    print('\n\n关键记住: LLM 是无状态的，messages 数组是它唯一的「记忆」。')
    print('管理好 messages = 管理好 LLM 的「大脑」。')
