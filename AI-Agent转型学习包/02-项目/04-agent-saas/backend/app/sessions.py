"""会话管理：每个 session_id 独立维护对话历史。

## 当前实现：内存字典

优点：简单，零依赖。
缺点（生产必须改）：
    1. 多进程部署时不共享 —— 用户请求打到实例 A 存的会话，下次打到 B 就读不到
    2. 进程重启全部丢失
    3. 内存无限增长 → OOM

## 生产改造路径

```python
# 换成 Redis（推荐，天然支持过期）
import redis, json
r = redis.Redis(...)
r.setex(f"session:{sid}", 3600, json.dumps(history))   # 1 小时过期

# 或者 Postgres（需要审计/长期留存时）
# 表：sessions(id, user_id, created_at) + messages(id, session_id, role, content)
```

## 一个容易忽略的点：并发写

同一个 session 同时收到两个请求，两个协程可能同时读写 history，
导致消息丢失或顺序错乱。这里用 asyncio.Lock 做了简单保护。
生产环境用 Redis 的话要注意用事务或 Lua 脚本保证原子性。
"""
import asyncio
import time
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """一个会话。"""
    id: str
    created_at: float = field(default_factory=time.time)
    history: list[dict] = field(default_factory=list)   # [{role, content}, ...]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def add_turn(self, question: str, answer: str, max_turns: int):
        """记录一轮问答。超出上限时丢弃最早的。"""
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})

        # 滑动窗口：保留最近 max_turns 轮（每轮 2 条消息）
        max_msgs = max_turns * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def to_messages(self) -> list[dict]:
        """转成发给模型的消息格式。"""
        return list(self.history)


class SessionStore:
    """会话存储（内存版）。"""

    def __init__(self, max_history_turns: int = 20):
        self._sessions: dict[str, Session] = {}
        self.max_history_turns = max_history_turns

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        sid = session_id or uuid.uuid4().hex[:12]
        session = Session(id=sid)
        self._sessions[sid] = session
        logger.info(f"新建会话 {sid}（当前共 {len(self._sessions)} 个）")
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def count(self) -> int:
        return len(self._sessions)

    def cleanup_expired(self, ttl_seconds: float = 7200) -> int:
        """清理过期会话。生产环境应该由定时任务调用。

        为什么要做：内存版的会话永远不会自己消失，
        线上跑一周就是几万个废弃会话占着内存。
        """
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(f"清理了 {len(expired)} 个过期会话")
        return len(expired)


# 全局单例
store = SessionStore()
