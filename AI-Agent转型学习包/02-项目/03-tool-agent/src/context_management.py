"""上下文管理：Agent 的"记忆"到底该怎么维护。

## 核心矛盾

Agent 的每一轮都要把「全部历史」发给模型（模型本身无状态）。
所以 token 消耗随轮数**近似平方增长**：

    第 1 轮发 1 份内容，第 2 轮发 2 份，第 3 轮发 3 份…
    累计 token = 1+2+3+…+n = n(n+1)/2

10 轮对话，累计发送量是单轮的 55 倍。这就是 Agent 烧钱的根源。

## 四种策略（由简到繁）

| 策略 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| 全量保留 | 什么都不删 | 信息无损 | 又贵又慢，最终超上下文 |
| 滑动窗口 | 只留最近 N 轮 | 简单有效 | 丢失早期信息 |
| 摘要压缩 | 老对话用 LLM 压成摘要 | 省钱且不丢要点 | 多一次调用，摘要会失真 |
| 选择性保留 | 工具结果按需裁剪 | 精准 | 实现复杂 |

生产环境的做法通常是：**滑动窗口 + 摘要压缩**组合。
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContextManager:
    """上下文管理器。

    用法：
        cm = ContextManager(max_messages=20, max_chars=20000)
        cm.add({"role": "user", "content": "..."})
        msgs = cm.build()
    """
    max_messages: int = 20             # 最多保留多少条消息
    max_chars: int = 20000             # 消息总字符上限（粗略对应 token）
    keep_system: bool = True           # system 消息永不丢弃
    summarize_threshold: int = 30      # 超过这么多条触发摘要压缩

    messages: list[dict] = field(default_factory=list)
    _summary: str = ""                 # 被压缩掉的历史摘要

    def add(self, message: dict):
        """添加一条消息。超限时自动裁剪。"""
        self.messages.append(message)
        self._trim()

    def add_many(self, messages: list[dict]):
        self.messages.extend(messages)
        self._trim()

    def _trim(self):
        """裁剪策略：先按条数裁剪，再按字符数裁剪。

        注意裁剪顺序：**从最老的开始删**，但保留 system 消息和摘要。
        """
        if len(self.messages) <= self.max_messages:
            return

        # 分离 system 消息（永不删）
        system_msgs = [m for m in self.messages if m.get("role") == "system"]
        other_msgs = [m for m in self.messages if m.get("role") != "system"]

        # 保留最近的 N 条
        keep_n = self.max_messages - len(system_msgs)
        dropped = other_msgs[:-keep_n] if keep_n > 0 else other_msgs
        kept = other_msgs[-keep_n:] if keep_n > 0 else []

        if dropped:
            logger.info(f"上下文裁剪：丢弃 {len(dropped)} 条早期消息")

        self.messages = system_msgs + kept
        self._trim_by_chars()

    def _trim_by_chars(self):
        """按总字符数裁剪。保留 system，从最老的开始丢。"""
        system_msgs = [m for m in self.messages if m.get("role") == "system"]
        other_msgs = [m for m in self.messages if m.get("role") != "system"]

        while other_msgs and self._total_chars(system_msgs + other_msgs) > self.max_chars:
            other_msgs.pop(0)          # 丢最老的一条

        self.messages = system_msgs + other_msgs

    @staticmethod
    def _total_chars(messages: list[dict]) -> int:
        total = 0
        for m in messages:
            c = m.get("content")
            if isinstance(c, str):
                total += len(c)
            # tool_calls 也占 token，要算进去
            if m.get("tool_calls"):
                total += len(str(m["tool_calls"]))
        return total

    def build(self) -> list[dict]:
        """产出要发给模型的消息列表。

        如果之前做过摘要压缩，把摘要作为一个 system 消息插在最前面，
        这样模型既知道"之前聊过什么"，又不用承担全部 token 成本。
        """
        out = []
        system_msgs = [m for m in self.messages if m.get("role") == "system"]
        other = [m for m in self.messages if m.get("role") != "system"]

        out.extend(system_msgs)
        if self._summary:
            out.append({
                "role": "system",
                "content": f"【之前的对话摘要】\n{self._summary}",
            })
        out.extend(other)
        return out

    def clear(self):
        self.messages.clear()
        self._summary = ""


# ---------------------------------------------------------------- 工具结果裁剪
def truncate_tool_result(content: str, max_chars: int = 2000) -> str:
    """裁剪过长的工具返回结果。

    为什么需要：一个工具可能返回 5 万字符（比如读了个大文件、或者 API 返回了
    JSON 大数组）。这个结果会一直留在消息历史里，之后每一轮都要重发一次。
    一次大结果 = 后面每轮都贵。

    做法：保留头尾，中间省略。头尾通常是模型最需要的（开头有结构，结尾有汇总）。
    """
    if len(content) <= max_chars:
        return content

    head = max_chars // 2
    tail = max_chars - head - 100
    return (
        content[:head]
        + f"\n\n…（中间省略 {len(content) - head - tail} 字符）…\n\n"
        + content[-tail:]
    )
