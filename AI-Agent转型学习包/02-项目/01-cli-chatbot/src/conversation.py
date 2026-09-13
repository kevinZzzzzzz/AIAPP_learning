"""对话历史管理：上下文裁剪 + 摘要压缩。

核心问题：messages 由你自己维护，但无限增长会超限且成本线性上升。
"""
from dataclasses import dataclass, field


@dataclass
class Conversation:
    """对话历史。

    两种裁剪策略：
    - 滑动窗口：只保留最近 N 轮，简单但会丢失早期信息
    - 摘要压缩：把超出的部分总结成一段，保留要点（需要额外一次模型调用）
    """
    system_prompt: str
    max_turns: int = 10
    messages: list[dict] = field(default_factory=list)
    summary: str = ""                       # 被压缩掉的早期内容摘要

    def __post_init__(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def build_messages(self) -> list[dict]:
        """构造发给模型的完整消息数组。

        如果有摘要，把它作为额外的 system 消息插在开头，
        这样模型既知道早期的关键信息，又不用带完整历史。
        """
        msgs = [self.messages[0]]                # system prompt（固定，利于缓存命中）
        if self.summary:
            msgs.append({"role": "system", "content": f"【此前对话摘要】\n{self.summary}"})
        msgs.extend(self.messages[1:])
        return msgs

    def needs_trim(self) -> bool:
        """是否需要裁剪（system 之外的轮数 = (len-1)/2）"""
        return (len(self.messages) - 1) // 2 > self.max_turns

    def trim(self) -> list[dict]:
        """滑动窗口裁剪。返回被裁掉的消息（可用于生成摘要）。

        注意：裁剪时不能把 tool 消息和它对应的 assistant 消息拆开，
        否则模型会报错。这里简化处理，只裁普通的 user/assistant 对。
        """
        if not self.needs_trim():
            return []

        keep = self.max_turns * 2               # 保留最近 N 轮（一轮 = user + assistant）
        removed = self.messages[1:-(keep)]
        self.messages = [self.messages[0]] + self.messages[-keep:]
        return removed

    def set_summary(self, summary: str):
        self.summary = summary

    def turn_count(self) -> int:
        return (len(self.messages) - 1) // 2

    def clear(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.summary = ""


SUMMARIZE_PROMPT = """请把下面这段对话压缩成要点摘要。

要求：
- 保留：用户透露的关键信息（身份、偏好、约束）、已达成的结论、未解决的问题
- 丢弃：寒暄、重复内容、已经讨论完的细节
- 用条目式列出，不要超过 200 字

对话内容：
{conversation}

只输出摘要内容，不要其他说明。"""


def summarize(messages: list[dict]) -> str:
    """把被裁掉的消息压成摘要。需要一次模型调用，所以只在必要时做。"""
    from src.llm import simple_chat

    text = "\n".join(
        f"{m['role']}: {m.get('content') or '[工具调用]'}"
        for m in messages if m.get("content")
    )
    if not text.strip():
        return ""

    return simple_chat(
        [{"role": "user", "content": SUMMARIZE_PROMPT.format(conversation=text)}],
        temperature=0,
    )
