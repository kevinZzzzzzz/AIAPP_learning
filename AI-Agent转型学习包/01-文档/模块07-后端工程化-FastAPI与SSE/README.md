# 模块 07：后端工程化（FastAPI + SSE）

> 对应周次：**W10**｜预计耗时：**15–18 小时**
> 前置要求：完成模块 01–06
>
> **本模块的目标**：把前面所有 Demo 从"能跑"变成"能上线"。

---

## 一、这个模块要解决什么问题

**一句话**：让 Agent 服务在真实流量、真实故障下还能正常工作。

学完这一模块，你应该能回答：

- 流式接口报错了怎么告诉前端？（HTTP 状态码已经发出去了）
- 一个用户的长请求会不会拖垮所有人？
- 会话状态存哪？多个实例怎么共享？
- 怎么防止有人狂刷接口把额度用完？
- 一个 Agent 任务跑到一半服务重启了，怎么办？

---

## 二、核心概念：AI 后端和普通后端的差异

### 2.1 五个关键差异

| 差异点 | 普通 CRUD 接口 | AI 接口 | 影响 |
|---|---|---|---|
| **耗时** | 几十毫秒 | 几秒到几分钟 | 连接要保持很久，容易超时 |
| **响应方式** | 一次性返回 | 流式（SSE）或长轮询 | 传统请求-响应模型不够用 |
| **失败模式** | 明确的错误码 | 部分成功/降级/幻觉 | 错误处理更复杂 |
| **成本** | 几乎免费 | 按 token 计费 | 必须做配额和限流 |
| **非确定性** | 同样输入同样输出 | 同样输入可能不同输出 | 缓存策略要更谨慎 |

### 2.2 SSE：AI 流式输出的标准方案

**是什么**：Server-Sent Events，HTTP 协议上的服务端单向持续推送机制。

**协议格式**（很简单）：

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type":"token","content":"你"}

data: {"type":"token","content":"好"}

data: {"type":"done","usage":{"prompt":20,"completion":5}}

```

每个事件以 `data: ` 开头，以**两个换行**结束。

**SSE vs WebSocket 怎么选**：

| 对比 | SSE | WebSocket |
|---|---|---|
| 方向 | 服务端 → 客户端（单向） | 双向 |
| 协议 | 纯 HTTP | 独立协议（ws://） |
| 自动重连 | 浏览器原生支持 | 需自己实现 |
| 代理/防火墙兼容 | 好（就是 HTTP） | 有时被拦截 |
| 实现复杂度 | 低 | 中 |
| 适用 | **AI 对话（绝大多数场景）** ✅ | 需要双向实时（协作编辑、游戏） |

**结论**：**AI 对话用 SSE 就够了。** 只有需要客户端持续高频发消息给服务端的场景才用 WebSocket。这是面试常问点。

### 2.3 流式接口的错误处理（核心难点）

**问题**：流已经开始输出了，HTTP 状态码已经发送（200），此时报错怎么办？

```
时间线：
  t0  服务端返回 200 + 开始推送 token
  t1  模型 API 超时/报错
  t2  ← 此时无法改状态码了！前端的 fetch 已经拿到 200
```

**解决方案：定义"流内错误事件"协议**。

```python
# 统一的事件协议（前后端约好的契约）
{"type": "start",    "data": {"conversation_id": "..."}}
{"type": "token",    "data": {"content": "文"}}
{"type": "tool_call","data": {"name": "search", "args": {...}}}
{"type": "tool_result", "data": {"name": "search", "result": "..."}}
{"type": "citation", "data": {"index": 1, "source": "...", "snippet": "..."}}
{"type": "error",    "data": {"code": "MODEL_TIMEOUT", "message": "模型响应超时", "retryable": true}}
{"type": "done",     "data": {"usage": {...}, "cost": 0.0012}}
```

**前端识别 `type: "error"` 后展示错误提示 + 重试按钮。** 这是流式接口设计的标准做法。

---

## 三、代码示例：生产级 Agent 后端

### 3.1 项目结构

```
agent-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（Pydantic Settings）
│   ├── models.py            # 请求/响应模型
│   ├── sse.py               # SSE 事件协议
│   ├── llm.py               # 模型调用封装（含重试）
│   ├── agent.py             # Agent 逻辑
│   ├── session.py           # 会话持久化
│   ├── ratelimit.py         # 限流
│   └── routers/
│       ├── chat.py          # 聊天接口
│       └── health.py        # 健康检查
├── tests/
├── .env
├── .env.example
├── pyproject.toml
└── Dockerfile
```

### 3.2 配置管理

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """集中配置。所有魔法数字都在这里，不散落在代码各处。"""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 模型
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-v4-flash"
    model_temperature: float = 0.3
    model_timeout: int = 120              # AI 接口很慢，超时要给足

    # 限额
    max_context_tokens: int = 30000
    max_output_tokens: int = 4096
    max_agent_iterations: int = 8
    rate_limit_per_minute: int = 20       # 每用户每分钟请求数
    daily_token_quota: int = 200_000      # 每用户每日 token 配额

    # 存储
    database_url: str = "sqlite:///./agent.db"

    # 服务
    cors_origins: list[str] = ["http://localhost:3000"]

settings = Settings()
```

> **为什么用 Pydantic Settings**：① 类型安全，配置错了启动就报错（而不是运行时才发现）；② 自动从环境变量/.env 读取；③ 集中管理，便于审查有哪些配置项。

### 3.3 SSE 事件协议

```python
# app/sse.py
"""统一 SSE 事件协议。前后端契约，改动要同步。"""
import json
from typing import Any, AsyncGenerator
from enum import Enum

class EventType(str, Enum):
    START       = "start"
    TOKEN       = "token"
    TOOL_CALL   = "tool_call"
    TOOL_RESULT = "tool_result"
    CITATION    = "citation"
    ERROR       = "error"
    DONE        = "done"

def sse_event(event_type: EventType | str, data: Any) -> str:
    """构造一个 SSE 事件。注意结尾必须是两个换行。"""
    et = event_type.value if isinstance(event_type, EventType) else event_type
    payload = json.dumps({"type": et, "data": data}, ensure_ascii=False)
    return f"data: {payload}\n\n"

def sse_error(code: str, message: str, retryable: bool = False) -> str:
    return sse_event(EventType.ERROR, {
        "code": code, "message": message, "retryable": retryable,
    })

class SSEResponse:
    """SSE 响应头。这几个头缺一不可。"""
    @staticmethod
    def headers() -> dict:
        return {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",     # ⚠️ 关键：禁用 Nginx 缓冲，否则流式失效
        }
```

> ⚠️ **`X-Accel-Buffering: no` 非常重要**。部署在 Nginx 后面时，Nginx 默认会缓冲响应，导致流式输出变成"一次性返回"。这是前端同学最容易踩的坑（本地正常，上线就不流式了）。

### 3.4 模型调用封装（含重试和用量统计）

```python
# app/llm.py
import asyncio, logging, time
from dataclasses import dataclass
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=settings.model_timeout,
)

@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0

    def add(self, p: int, c: int):
        self.prompt_tokens += p
        self.completion_tokens += c
        # DeepSeek flash 价格（2026-09，单位：美元/百万 token）
        self.cost += p / 1e6 * 0.14 + c / 1e6 * 0.28


async def stream_completion(messages: list[dict], tools: list[dict] | None = None,
                            usage: Usage | None = None, max_retries: int = 3):
    """流式调用模型，带重试和用量统计。

    yield: (delta_content, tool_calls, chunk)
    """
    usage = usage or Usage()

    for attempt in range(max_retries):
        try:
            stream = await client.chat.completions.create(
                model=settings.model_name,
                messages=messages,
                tools=tools,
                temperature=settings.model_temperature,
                stream=True,
                stream_options={"include_usage": True},   # 关键：让流式也返回用量
            )

            async for chunk in stream:
                if chunk.usage:                            # 最后一个 chunk 带用量
                    usage.add(chunk.usage.prompt_tokens, chunk.usage.completion_tokens)

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                yield delta.content, delta.tool_calls, chunk

            return          # 正常结束

        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(f"限流，{wait}s 后重试")
            await asyncio.sleep(wait)

        except (APITimeoutError, APIError) as e:
            # 已经输出了一部分内容，不能重试（会导致重复内容）
            # 这个判断必须做，否则前端会看到内容重复
            if attempt == max_retries - 1:
                raise
            status = getattr(e, "status_code", None)
            if status and 400 <= status < 500:
                raise                    # 客户端错误不重试
            wait = 2 ** attempt
            logger.warning(f"模型错误 {e}，{wait}s 后重试")
            await asyncio.sleep(wait)


async def non_stream_completion(messages: list[dict], tools: list[dict] | None = None,
                                usage: Usage | None = None, max_retries: int = 3):
    """非流式调用（用于 Agent 的中间决策步骤，不需要流式）。"""
    usage = usage or Usage()
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model=settings.model_name, messages=messages,
                tools=tools, temperature=settings.model_temperature,
            )
            if resp.usage:
                usage.add(resp.usage.prompt_tokens, resp.usage.completion_tokens)
            return resp
        except (RateLimitError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("重试耗尽")
```

### 3.5 会话持久化

```python
# app/session.py
"""会话持久化。生产环境用 Postgres，这里演示 SQLite。
关键：会话数据必须持久化，否则多实例部署或重启就丢数据。
"""
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from app.config import settings

def _conn():
    c = sqlite3.connect(settings.database_url.replace("sqlite:///", ""))
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            title       TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT,
            tool_calls      TEXT,          -- JSON 字符串
            tool_call_id    TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, id);
        CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);

        -- 用量统计表（成本监控用，模块 09 会用）
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cost REAL,
            created_at TEXT NOT NULL
        );
        """)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_conversation(conv_id: str, user_id: str, title: str = "新对话"):
    with _conn() as c:
        c.execute("INSERT INTO conversations VALUES (?,?,?,?,?)",
                  (conv_id, user_id, title, now(), now()))

def get_conversation(conv_id: str, user_id: str) -> Optional[dict]:
    """⚠️ 必须校验归属：不同用户不能访问彼此的会话。"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM conversations WHERE id=? AND user_id=?",
            (conv_id, user_id)).fetchone()
        return dict(row) if row else None

def add_message(conv_id: str, role: str, content: str | None,
                tool_calls: list | None = None, tool_call_id: str | None = None):
    with _conn() as c:
        c.execute("""INSERT INTO messages
                     (conversation_id, role, content, tool_calls, tool_call_id, created_at)
                     VALUES (?,?,?,?,?,?)""",
                  (conv_id, role, content,
                   json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
                   tool_call_id, now()))
        c.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now(), conv_id))

def get_messages(conv_id: str, limit: int = 50) -> list[dict]:
    """取最近 N 条消息，按时间正序。"""
    with _conn() as c:
        rows = c.execute(
            """SELECT role, content, tool_calls, tool_call_id FROM messages
               WHERE conversation_id=? ORDER BY id DESC LIMIT ?""",
            (conv_id, limit)).fetchall()
    msgs = []
    for r in reversed(rows):
        m = {"role": r["role"], "content": r["content"]}
        if r["tool_calls"]:
            m["tool_calls"] = json.loads(r["tool_calls"])
        if r["tool_call_id"]:
            m["tool_call_id"] = r["tool_call_id"]
        msgs.append(m)
    return msgs

def log_usage(user_id: str, conv_id: str, prompt_tokens: int,
              completion_tokens: int, cost: float):
    with _conn() as c:
        c.execute("""INSERT INTO usage_log
                     (user_id, conversation_id, prompt_tokens, completion_tokens, cost, created_at)
                     VALUES (?,?,?,?,?,?)""",
                  (user_id, conv_id, prompt_tokens, completion_tokens, cost, now()))

def get_daily_usage(user_id: str) -> int:
    """当日已用 token 总量（配额检查用）。"""
    today = datetime.now(timezone.utc).date().isoformat()
    with _conn() as c:
        row = c.execute(
            """SELECT COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS t
               FROM usage_log WHERE user_id=? AND created_at LIKE ?""",
            (user_id, f"{today}%")).fetchone()
    return row["t"]
```

### 3.6 限流与配额

```python
# app/ratelimit.py
"""限流与配额。
学习实现用内存，生产环境要换成 Redis（多实例共享）。
"""
import time
from collections import defaultdict
from fastapi import HTTPException

# 生产环境必须用 Redis：内存版在多实例部署时限流会失效
_buckets: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(user_id: str, limit_per_minute: int):
    """滑动窗口限流：每分钟最多 N 次请求。"""
    now = time.time()
    window = now - 60
    _buckets[user_id] = [t for t in _buckets[user_id] if t > window]

    if len(_buckets[user_id]) >= limit_per_minute:
        retry_after = int(60 - (now - _buckets[user_id][0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请 {retry_after} 秒后重试",
            headers={"Retry-After": str(retry_after)},
        )
    _buckets[user_id].append(now)

def check_token_quota(user_id: str, used: int, quota: int):
    if used >= quota:
        raise HTTPException(
            status_code=429,
            detail=f"今日 token 配额已用完（{used}/{quota}），请明日再试",
        )
```

> **为什么必须有配额**：AI 接口按 token 计费。一个恶意用户写个脚本狂刷，一天能烧掉你几千块。**配额不是优化项，是风控底线。**

### 3.7 完整的流式聊天接口

```python
# app/routers/chat.py
import json, uuid, logging, asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.sse import sse_event, sse_error, EventType, SSEResponse
from app.llm import stream_completion, non_stream_completion, Usage
from app import session
from app.ratelimit import check_rate_limit, check_token_quota

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


# ============ 请求/响应模型 ============
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None

class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=100)


# ============ 简化的鉴权（生产用真实的 JWT/OAuth）============
async def get_current_user(request: Request) -> str:
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return user_id


# ============ 会话管理接口 ============
@router.post("/conversations")
async def create_conversation(body: ConversationCreate, user_id: str = Depends(get_current_user)):
    conv_id = str(uuid.uuid4())
    session.create_conversation(conv_id, user_id, body.title)
    return {"conversation_id": conv_id}


@router.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, user_id: str = Depends(get_current_user)):
    if not session.get_conversation(conv_id, user_id):
        # 注意：不区分"不存在"和"无权限"，避免泄露信息
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"messages": session.get_messages(conv_id)}


# ============ 核心：流式聊天 ============
@router.post("/chat")
async def chat(body: ChatRequest, user_id: str = Depends(get_current_user)):
    # 1. 限流 + 配额检查（快速失败，不要等到调模型时才发现）
    check_rate_limit(user_id, settings.rate_limit_per_minute)
    used = session.get_daily_usage(user_id)
    check_token_quota(user_id, used, settings.daily_token_quota)

    # 2. 会话校验与创建
    conv_id = body.conversation_id
    if conv_id:
        if not session.get_conversation(conv_id, user_id):
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conv_id = str(uuid.uuid4())
        session.create_conversation(conv_id, user_id, body.message[:30])

    session.add_message(conv_id, "user", body.message)

    # 3. 返回流式响应
    return StreamingResponse(
        _chat_stream(conv_id, user_id),
        media_type="text/event-stream",
        headers=SSEResponse.headers(),
    )


async def _chat_stream(conv_id: str, user_id: str):
    """SSE 事件生成器。所有异常都必须在这里捕获并转成 error 事件。"""
    usage = Usage()
    full_reply = ""

    try:
        # 发送 start 事件（前端据此初始化 UI）
        yield sse_event(EventType.START, {"conversation_id": conv_id})

        history = session.get_messages(conv_id, limit=30)
        messages = [{"role": "system", "content": "你是专业的技术助手，回答简洁准确。"}] + history

        async for content, tool_calls, _ in stream_completion(messages, usage=usage):
            if content:
                full_reply += content
                yield sse_event(EventType.TOKEN, {"content": content})
            # 说明：这里演示纯文本流。带工具调用的完整 Agent 流程见项目 04

        # 保存回复
        session.add_message(conv_id, "assistant", full_reply)

        # 记录用量
        session.log_usage(user_id, conv_id, usage.prompt_tokens,
                          usage.completion_tokens, usage.cost)

        # 发送结束事件（含用量，前端可展示）
        yield sse_event(EventType.DONE, {
            "conversation_id": conv_id,
            "usage": {"prompt_tokens": usage.prompt_tokens,
                      "completion_tokens": usage.completion_tokens},
            "cost": round(usage.cost, 6),
        })

    except asyncio.CancelledError:
        # 客户端主动断开（用户点了"停止"）。这是正常情况，不是错误。
        logger.info(f"客户端断开连接 conv={conv_id}")
        if full_reply:
            session.add_message(conv_id, "assistant", full_reply + " [已中断]")
        raise

    except Exception as e:
        # ⚠️ 关键：流已开始，不能改状态码，只能发 error 事件
        logger.exception(f"流式响应异常 conv={conv_id}")
        session.add_message(conv_id, "assistant", full_reply or "[生成失败]")
        retryable = not isinstance(e, (ValueError,))
        yield sse_error("STREAM_ERROR", f"生成失败：{str(e)[:200]}", retryable=retryable)
```

### 3.8 主入口（含健康检查、日志、CORS）

```python
# app/main.py
import logging, time, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app import session
from app.routers import chat

# ---- 结构化日志（生产必备，方便检索）----
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    session.init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("服务关闭")


app = FastAPI(title="Agent Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """请求日志 + 耗时统计 + 请求 ID 追踪。"""
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())[:8]
    start = time.time()
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
        elapsed = (time.time() - start) * 1000
        logger.info(f"method={request.method} path={request.url.path} "
                    f"status={response.status_code} ms={elapsed:.0f} req_id={req_id}")
        return response
    except Exception:
        elapsed = (time.time() - start) * 1000
        logger.exception(f"未处理异常 path={request.url.path} ms={elapsed:.0f} req_id={req_id}")
        return JSONResponse(status_code=500,
                            content={"error": "服务内部错误", "req_id": req_id})


@app.get("/health")
async def health():
    """健康检查。K8s / 负载均衡器靠它判断实例是否可用。"""
    return {"status": "ok", "model": settings.model_name}


@app.get("/health/ready")
async def readiness():
    """就绪检查：依赖（数据库、外部 API）是否可用。"""
    try:
        session.get_daily_usage("__probe__")
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(e)})


app.include_router(chat.router)
```

### 3.9 运行

```bash
# 安装
uv add fastapi "uvicorn[standard]" openai pydantic-settings python-dotenv

# 启动（开发，热重载）
uv run uvicorn app.main:app --reload --port 8000

# 测试流式接口
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -d '{"message":"用三句话解释什么是 SSE"}'
# -N 关闭 curl 缓冲，才能看到流式效果
```

---

## 四、并发与性能

### 4.1 异步的常见错误

```python
# ❌ 错误：同步阻塞调用卡住事件循环
import requests
@app.get("/bad")
async def bad():
    r = requests.get("https://api.example.com")   # 阻塞！整个服务卡住
    return r.json()

# ❌ 错误：同步的 OpenAI 客户端
from openai import OpenAI                     # 不是 AsyncOpenAI
@app.post("/bad2")
async def bad2():
    resp = client.chat.completions.create(...)  # 阻塞事件循环
    return resp

# ✅ 正确：全链路异步
from openai import AsyncOpenAI
import httpx
@app.post("/good")
async def good():
    async with httpx.AsyncClient() as c:
        r = await c.get("https://api.example.com")
    return r.json()
```

**为什么严重**：FastAPI 是单线程事件循环。一个同步阻塞调用会**卡住所有并发请求**。10 个用户同时请求，全部排队等待。

**如果必须用同步库**：用 `run_in_threadpool` 包装。

```python
from fastapi.concurrency import run_in_threadpool

@app.get("/ok")
async def ok():
    result = await run_in_threadpool(sync_blocking_function)
    return result
```

### 4.2 并发控制

```python
# app/concurrency.py
"""并发控制：防止模型 API 被自己打爆（触发限流）或被恶意刷爆。"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import HTTPException

class Semaphore:
    """全局并发闸门。限制同时进行的模型调用数量。"""
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def acquire(self, timeout: float = 5.0):
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=503, detail="服务繁忙，请稍后重试")
        try:
            yield
        finally:
            self._sem.release()

# 全局实例：同时最多 20 个模型调用
model_gate = Semaphore(max_concurrent=20)

# 使用
# async with model_gate.acquire():
#     async for ... in stream_completion(...):
#         yield ...
```

### 4.3 超时控制（必须做）

| 层级 | 超时设置 | 说明 |
|---|---|---|
| 模型 API 调用 | 60–120s | AI 生成慢，但要有上限 |
| Agent 单轮 | 180s | 含多次模型 + 工具调用 |
| 整个 SSE 流 | 600s | 防止连接永久占用 |
| 前端 fetch | 比后端略长 | 留缓冲 |

```python
# 整个流的超时保护
async def _chat_stream_with_timeout(conv_id: str, user_id: str, timeout: float = 600):
    try:
        async with asyncio.timeout(timeout):
            async for event in _chat_stream(conv_id, user_id):
                yield event
    except asyncio.TimeoutError:
        yield sse_error("TIMEOUT", "任务超时，请简化问题后重试", retryable=True)
```

### 4.4 优雅关闭

```python
# 长任务在服务重启时应保存进度，而不是丢失
@asynccontextmanager
async def lifespan(app: FastAPI):
    session.init_db()
    yield
    # 关闭前：等待进行中的请求完成（给 30s 缓冲），或保存状态
    logger.info("等待进行中的请求完成...")
    await asyncio.sleep(1)
    logger.info("服务已关闭")
```

---

## 五、知识点清单

- [ ] AI 后端与普通后端的五个关键差异
- [ ] SSE 协议格式与实现方式
- [ ] SSE vs WebSocket 的对比与选型
- [ ] 流式接口的错误处理（流内错误事件协议）
- [ ] `X-Accel-Buffering: no` 的作用（Nginx 缓冲问题）
- [ ] 统一 SSE 事件协议的设计（start/token/tool_call/citation/error/done）
- [ ] Pydantic Settings 做集中配置
- [ ] 会话持久化的表设计与归属校验
- [ ] 限流（滑动窗口）与 token 配额
- [ ] 为什么要做配额（风控底线）
- [ ] 异步编程的陷阱（同步阻塞卡事件循环）与 `run_in_threadpool`
- [ ] 并发闸门控制模型调用数量
- [ ] 多层超时设置
- [ ] 结构化日志与请求 ID 追踪
- [ ] 健康检查 vs 就绪检查
- [ ] 客户端断开的处理（CancelledError 是正常情况）

---

## 六、常见坑

### 坑 1：用同步 OpenAI 客户端
**后果**：事件循环被阻塞，并发能力退化成串行。
**正确做法**：`AsyncOpenAI` + 全链路 async。

### 坑 2：流式接口报错时想改状态码
**后果**：报错 `RuntimeError: Response headers already sent`，或者前端拿到 200 但内容是空的。
**正确做法**：定义流内错误事件协议，前端识别 `type: error`。

### 坑 3：忘了 `X-Accel-Buffering: no`
**后果**：本地流式正常，部署到 Nginx 后面变成一次性返回（这是经典坑）。
**正确做法**：加响应头禁用缓冲。

### 坑 4：AI 接口设了 5 秒超时
**后果**：正常请求频繁超时。
**正确做法**：AI 接口超时设 60–120s，前端设更长。

### 坑 5：没有限流和配额
**后果**：被恶意刷接口，一天烧掉几千块。
**正确做法**：限流 + token 配额，两层都要有。

### 坑 6：内存版限流用于多实例
**后果**：3 个实例各自的计数器独立，限流形同虚设（实际能刷 3 倍）。
**正确做法**：生产环境用 Redis 做共享计数。

### 坑 7：不校验会话归属
**后果**：改一下 `conversation_id` 就能看别人的对话（严重数据泄露）。
**正确做法**：查询时必须带 `user_id` 条件。返回 404 而不是 403（不泄露"存在与否"信息）。

### 坑 8：流式重试导致内容重复
**后果**：已经推了 100 个字，重试后重新生成，前端看到内容接了两遍。
**正确做法**：流式调用时，已经输出过内容就不再重试（只能报错给前端让用户手动重试）。

### 坑 9：客户端断开后继续跑
**后果**：用户关掉页面，服务端还在生成、还在烧 token。
**正确做法**：捕获 `CancelledError`，停止生成并保存已有内容。

### 坑 10：日志里打印完整 Prompt
**后果**：日志文件里堆满用户隐私数据，还有合规风险。
**正确做法**：日志只记录长度、token 数、ID 等元信息，敏感内容要脱敏。

---

## 七、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 用 FastAPI 写一个最小 SSE 接口，用 curl -N 验证流式效果 | ⭐⭐ |
| 2 | 实现完整 SSE 事件协议（含 error 事件），前端模拟一个错误场景 | ⭐⭐⭐ |
| 3 | 实现会话持久化，验证服务重启后历史还在 | ⭐⭐⭐ |
| 4 | 实现滑动窗口限流 + token 配额，用脚本测试触发 429 | ⭐⭐⭐ |
| 5 | 故意用同步阻塞调用，用并发压测观察性能塌陷，再改成异步对比 | ⭐⭐⭐⭐ |
| 6 | 实现并发闸门，压测出服务能承载的并发上限 | ⭐⭐⭐⭐ |
| 7 | 实现会话归属校验，验证用别人的 conversation_id 访问被拒 | ⭐⭐⭐ |
| 8 | 写一份压测报告：QPS、P95 延迟、并发上限、瓶颈在哪 | ⭐⭐⭐⭐ |
| 9 | **【项目任务】** 把项目 04 的后端部分完成 | ⭐⭐⭐⭐⭐ |

---

## 八、自测题

**Q1：SSE 和 WebSocket 怎么选？为什么 AI 对话用 SSE？**
<details><summary>参考答案</summary>
AI 对话是**单向推送**（服务端持续推 token 给客户端，客户端只需发请求），SSE 正好匹配。选 SSE 的理由：① 纯 HTTP 协议，代理/防火墙兼容性好；② 浏览器原生支持自动重连；③ 实现简单（就是 `text/event-stream`）。WebSocket 是双向的，适合需要客户端高频发消息的场景（协作编辑、游戏、实时语音）。用 WebSocket 做 AI 对话是过度设计，还要自己处理重连。
</details>

**Q2：流式接口中途报错了，怎么通知前端？**
<details><summary>参考答案</summary>
不能改 HTTP 状态码（响应头已经发出，状态码是 200）。解决方案是定义**流内错误事件协议**：在 SSE 流里发送一个特殊事件 `{"type":"error","data":{"code":"...","message":"...","retryable":true}}`。前端监听事件类型，遇到 `error` 就展示错误提示和重试按钮。`retryable` 字段告诉前端这个错误重试是否有意义（如超时=true，参数错误=false）。
</details>

**Q3：什么是 `X-Accel-Buffering: no`？为什么需要它？**
<details><summary>参考答案</summary>
这是给 Nginx 的响应头，用来禁用 Nginx 的响应缓冲。Nginx 默认会缓冲上游响应，等积累到一定大小才转发给客户端——这会导致流式输出变成"攒一批发一批"甚至"一次性返回"，流式效果完全失效。这是典型的"本地正常、上线不流式"问题的根因。除了这个头，还要检查 Nginx 配置里的 `proxy_buffering`。
</details>

**Q4：为什么 AI 服务必须做限流和配额？**
<details><summary>参考答案</summary>
因为 AI 接口按 token 计费，成本与调用量直接挂钩。没有限制的话：① 恶意用户可以写脚本狂刷，一天烧掉几千块；② 单个用户的复杂任务可能占用大量并发，影响其他用户；③ 代码 bug（如无限循环 Agent）会自己打爆自己的账单。所以限流（控频率）+ 配额（控总量）是风控底线，不是可选的性能优化。生产环境的配额数据和限流计数器必须放 Redis，内存版在多实例部署时会失效。
</details>

**Q5：在 FastAPI 里调用同步阻塞函数会怎样？**
<details><summary>参考答案</summary>
会**阻塞整个事件循环**。FastAPI 用单线程事件循环处理并发，一个同步阻塞调用（如 `requests.get` 或同步版 OpenAI SDK）会让所有其他请求排队等待，服务并发能力退化为串行。解决方案：① 优先使用异步库（`httpx`、`AsyncOpenAI`）；② 如果必须用同步库，用 `await run_in_threadpool(fn)` 把它丢到线程池执行，避免阻塞事件循环。
</details>

**Q6：为什么跨会话查询必须带 user_id 条件？**
<details><summary>参考答案</summary>
防止越权访问（IDOR 漏洞）。如果只用 `conversation_id` 查询，攻击者只要猜到或枚举到别人的会话 ID 就能读取他人对话内容。正确做法是查询条件同时带 `user_id`。另外，返回时应该用 404 而不是 403——如果返回 403 表示"存在但无权限"，攻击者就能通过状态码差异判断哪些 ID 是有效的，属于信息泄露。
</details>

**Q7：客户端点"停止生成"后，服务端应该怎么做？**
<details><summary>参考答案</summary>
应该捕获 `asyncio.CancelledError`（客户端断开时 FastAPI 会抛出），然后：① 立即停止模型调用（否则还在烧 token）；② 把已经生成的部分内容保存到数据库（用户可能想留着）；③ 记录日志（这是正常行为，不是错误，日志级别用 info）。关键认知：**不处理的后果是用户已经离开，服务端还在白烧钱生成内容。**
</details>

**Q8：你的流式接口部署后不流式了，本地却正常，排查思路？**
<details><summary>参考答案</summary>
按这个顺序查：① **响应头**是否包含 `X-Accel-Buffering: no`；② **Nginx** 的 `proxy_buffering` 是否为 off、`proxy_cache` 是否开启；③ **中间层**（CDN、API 网关、Serverless 平台）是否缓冲响应——有些云平台（如某些 Serverless）对响应有缓冲行为；④ 代码里是否有地方读取了整个流再返回（如误用了 `await resp.text()` 而不是迭代）；⑤ 客户端是否用了缓冲（curl 要加 `-N`）。最常见的根因是 Nginx 缓冲。
</details>

**Q9：健康检查和就绪检查有什么区别？**
<details><summary>参考答案</summary>
**健康检查（liveness）**：进程是否活着。失败时编排系统（K8s）会**重启**该实例。所以健康检查不能依赖外部服务（如果数据库挂了就重启服务是错的，重启解决不了问题）。**就绪检查（readiness）**：实例是否能正常处理请求（依赖是否可用）。失败时编排系统会**把流量摘除**，不重启。所以就绪检查应该探测数据库、外部 API 等依赖。混淆两者会导致"依赖故障 → 服务被反复重启 → 雪崩"。
</details>

**Q10：流式调用的重试有什么特殊限制？**
<details><summary>参考答案</summary>
**如果已经向客户端输出了内容，就不能重试**。因为重试会让模型重新生成，前端会看到内容接了两遍（重复）。所以流式场景的重试策略是：① 在**开始输出前**的错误（如连接失败、限流）可以安全重试；② **已经开始输出**后的错误，只能发 error 事件让前端决定是否手动重试（此时需要清空已显示的内容重新开始）。实现上要记录"是否已输出过内容"这个状态。
</details>

---

## 九、延伸阅读

| 主题 | 资源 |
|---|---|
| FastAPI 官方文档 | https://fastapi.tiangolo.com/ |
| MDN Server-Sent Events | https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events |
| FastAPI 并发与 async | https://fastapi.tiangolo.com/async/ |
| Pydantic Settings | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| OpenAI Python SDK（AsyncOpenAI） | https://github.com/openai/openai-python |

---

## 十、完成标志

- [ ] 一个完整的 FastAPI 流式聊天服务，含 SSE 事件协议
- [ ] 会话持久化 + 归属校验
- [ ] 限流 + token 配额
- [ ] 并发闸门 + 多层超时
- [ ] 结构化日志 + 健康检查
- [ ] 一份压测报告（QPS / P95 / 并发上限）
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 08，学习前端 AI 交互——这是你的主场。
