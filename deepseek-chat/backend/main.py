"""
DeepSeek Chat —— 后端服务
==========================
基于 FastAPI + LangChain + DeepSeek 的聊天机器人后端。

核心功能：
- SSE 流式聊天
- LangChain LCEL 管道（Prompt | ChatModel | StrOutputParser）
- 对话历史管理
- CORS 跨域

启动：
  cd deepseek-chat/backend
  pip install -r requirements.txt
  python main.py

注意：请先在 config.py 中设置 DEEPSEEK_API_KEY
"""

import json
import asyncio
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 本地配置
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    HOST,
    PORT,
    ALLOWED_ORIGINS,
    SYSTEM_PROMPT,
)

# ====================== 日志 ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deepseek-chat")


# ====================== FastAPI 应用 ======================

app = FastAPI(
    title="DeepSeek Chat API",
    description="基于 LangChain + DeepSeek 的聊天机器人 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================== LangChain 核心 ======================

def create_chat_model() -> ChatOpenAI:
    """创建 DeepSeek 聊天模型
    
    DeepSeek 兼容 OpenAI SDK，通过 ChatOpenAI 指定 base_url 即可。
    """
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.7,
        streaming=True,
    )


def create_chain():
    """创建 LangChain 对话链
    
    LCEL 管道：
    Prompt Template → Chat Model → String Parser
    
    其中 Prompt Template 包含：
    - System Prompt（固定的人设）
    - MessagesPlaceholder（动态插入对话历史）
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    model = create_chat_model()
    parser = StrOutputParser()

    # LCEL 管道
    chain = prompt | model | parser
    return chain


# ====================== 对话历史管理 ======================

class ConversationMemory:
    """简单的对话记忆管理
    
    策略：保留最近 20 轮对话（40 条消息），超出自动截断。
    """

    MAX_MESSAGES = 40

    def __init__(self):
        self.history: list = []  # LangChain 消息对象列表

    def add_user_message(self, content: str):
        self.history.append(HumanMessage(content=content))
        self._trim()

    def add_ai_message(self, content: str):
        self.history.append(AIMessage(content=content))
        self._trim()

    def _trim(self):
        """超出上限时截断"""
        if len(self.history) > self.MAX_MESSAGES:
            self.history = self.history[-self.MAX_MESSAGES:]

    def get_history(self) -> list:
        return self.history.copy()

    def clear(self):
        self.history.clear()

    @property
    def message_count(self) -> int:
        return len(self.history)


# 全局会话存储（生产环境应使用 Redis）
sessions: dict[str, ConversationMemory] = {}


def get_or_create_session(session_id: str) -> ConversationMemory:
    """获取或创建会话"""
    if session_id not in sessions:
        sessions[session_id] = ConversationMemory()
        logger.info(f"新会话: {session_id}")
    return sessions[session_id]


# ====================== Pydantic 模型 ======================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="用户消息")
    session_id: str = Field(default="default", description="会话 ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    history_length: int


# ====================== API 路由 ======================

@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "DeepSeek Chat API",
        "model": DEEPSEEK_MODEL,
        "base_url": DEEPSEEK_BASE_URL,
        "status": "running",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """非流式聊天"""
    reply = await _chat_non_stream(request)
    session = get_or_create_session(request.session_id)
    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        history_length=session.message_count,
    )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天 —— SSE 协议"""
    return StreamingResponse(
        _stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """清空会话历史"""
    if session_id in sessions:
        sessions[session_id].clear()
        return {"message": f"会话 {session_id} 已清空", "session_id": session_id}
    return {"message": f"会话 {session_id} 不存在"}


@app.get("/api/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    return {
        "sessions": [
            {
                "session_id": sid,
                "messages": mem.message_count,
            }
            for sid, mem in sessions.items()
        ]
    }


# ====================== 核心逻辑 ======================

async def _chat_non_stream(request: ChatRequest) -> str:
    """非流式聊天"""
    session = get_or_create_session(request.session_id)
    session.add_user_message(request.message)

    chain = create_chain()

    # LangChain invoke
    response = await chain.ainvoke({
        "input": request.message,
        "history": session.get_history()[:-1],  # 不包含刚加的最新一条
    })

    session.add_ai_message(response)
    return response


async def _stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """SSE 流式聊天"""
    session = get_or_create_session(request.session_id)
    session.add_user_message(request.message)

    try:
        chain = create_chain()

        # 发送开始信号
        yield _sse({"status": "started"})

        full_reply = ""

        # LangChain astream —— 异步流式
        async for chunk in chain.astream({
            "input": request.message,
            "history": session.get_history()[:-1],
        }):
            full_reply += chunk
            yield _sse({"token": chunk})

        # 保存完整回复到历史
        session.add_ai_message(full_reply)

        # 发送结束信号
        yield _sse({
            "done": True,
            "session_id": request.session_id,
            "history_length": session.message_count,
        })

    except Exception as e:
        logger.error(f"流式聊天错误: {e}")
        yield _sse({"error": True, "message": str(e)})


# ====================== 工具函数 ======================

def _sse(data: dict) -> str:
    """构造 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ====================== 中间件 ======================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未捕获异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},
    )


# ====================== 启动入口 ======================

if __name__ == "__main__":
    import uvicorn

    print(f"""
╔══════════════════════════════════════════════╗
║       DeepSeek Chat API                      ║
║                                              ║
║  Model:   {DEEPSEEK_MODEL:<36}║
║  API:     http://localhost:{PORT:<21}║
║  Docs:    http://localhost:{PORT}/docs{'':<17}║
║                                              ║
║  前端运行在 http://localhost:5173             ║
╚══════════════════════════════════════════════╝
""")
    uvicorn.run(app, host=HOST, port=PORT)
