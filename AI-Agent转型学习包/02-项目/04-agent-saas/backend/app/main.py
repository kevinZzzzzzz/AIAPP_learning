"""FastAPI 应用：SSE 流式接口 + 会话管理。

## SSE 实现要点（很多人会踩的坑）

1. **必须禁用中间件缓冲**
   Nginx 默认会缓冲响应，导致 SSE 事件被攒着一起发，
   前端的"打字机效果"就变成了"半天不出字，然后一次性全出来"。
   Nginx 配置要加：`proxy_buffering off;`

2. **响应头必须正确**
   Content-Type: text/event-stream
   Cache-Control: no-cache
   X-Accel-Buffering: no    ← 专门给 Nginx 看的，告诉它别缓冲

3. **客户端断开要检测**
   用户关掉页面后，后台如果还在跑 Agent，就是白烧 token。
   用 `await request.is_disconnected()` 检测。
"""
import json
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.sessions import store
from app.agent_service import run_agent_stream, run_agent_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent SaaS API",
    description="模块 07 产出项目：带 SSE 流式的 Agent 服务",
    version="0.1.0",
)

# CORS：前后端分离时必须配置，否则浏览器会拦请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- 请求模型
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000,
                         description="用户消息")
    session_id: str | None = Field(None, description="会话 ID，不传则新建")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[dict] = []
    usage: dict = {}
    error: str | None = None


# ---------------------------------------------------------------- 接口
@app.get("/api/health")
async def health():
    """健康检查。部署时负载均衡器会轮询这个接口。"""
    return {
        "status": "ok",
        "model": settings.model.name,
        "sessions": store.count(),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式问答。一次性返回完整结果。"""
    session = store.get_or_create(req.session_id)

    async with session.lock:            # 防止同一会话并发写乱序
        result = await run_agent_once(req.message, session.to_messages())
        if result["answer"]:
            session.add_turn(req.message, result["answer"], settings.max_history_turns)

    return ChatResponse(
        session_id=session.id,
        answer=result["answer"],
        tool_calls=result["tool_calls"],
        usage=result["usage"],
        error=result["error"],
    )


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """SSE 流式问答。前端主用这个。

    SSE 格式说明：
        event: <事件名>\n
        data: <JSON>\n
        \n                        ← 空行表示一个事件结束
    """
    session = store.get_or_create(req.session_id)
    logger.info(f"[{session.id}] 收到消息：{req.message[:50]}")

    async def event_generator():
        # 先把 session_id 推给前端，方便它保存用于后续请求
        yield _sse("session", {"session_id": session.id})

        answer_parts: list[str] = []

        try:
            async for ev in run_agent_stream(req.message, session.to_messages()):
                # ⚠️ 检测客户端是否已断开
                if await request.is_disconnected():
                    logger.info(f"[{session.id}] 客户端断开，停止生成")
                    return

                # 收集正文用于写入历史
                if ev.get("type") == "text":
                    answer_parts.append(ev["content"])

                yield _sse(ev["type"], ev)

        except Exception as ex:                 # noqa: BLE001
            logger.exception(f"[{session.id}] 流式生成异常")
            yield _sse("error", {"type": "error", "message": f"服务异常：{ex}"})
            return

        # 流结束，把这一轮存进历史
        answer = "".join(answer_parts)
        if answer:
            session.add_turn(req.message, answer, settings.max_history_turns)
        logger.info(f"[{session.id}] 完成，回答 {len(answer)} 字符")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",      # 关键：告诉 Nginx 别缓冲
        },
    )


def _sse(event: str, data: dict) -> str:
    """格式化一个 SSE 事件。

    注意 data 必须是一行 —— 换行会破坏 SSE 协议。
    所以 JSON 里的换行要转义（json.dumps 默认就会转义为 \\n）。
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# ---------------------------------------------------------------- 会话管理
@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """查看会话历史。"""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "session_id": session.id,
        "turns": len(session.history) // 2,
        "history": session.history,
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """清空会话。"""
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True, "message": "会话已清空"}


@app.post("/api/sessions/cleanup")
async def cleanup_sessions(ttl_seconds: float = 7200):
    """清理过期会话。生产环境应该由定时任务自动调用。"""
    n = store.cleanup_expired(ttl_seconds)
    return {"cleaned": n, "remaining": store.count()}
