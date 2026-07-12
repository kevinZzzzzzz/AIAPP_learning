"""
LangChain Agent Server (Python + FastAPI)
等价于 server/index.js 的 Python 实现。
使用 FastAPI + LangChain + LangGraph + SSE 流式输出。
"""

import os
import json
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# ── 加载环境变量 ──────────────────────────────────────
load_dotenv()

PORT = int(os.getenv("PORT", "3002"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ── 初始化 Agent ──────────────────────────────────────
tools = [TavilySearchResults(max_results=3)]

model = ChatOpenAI(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0,
)

memory = MemorySaver()

agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=memory,
)

# ── FastAPI 应用 ──────────────────────────────────────
app = FastAPI(title="LangChain Agent (Python)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    threadId: str = "default"


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(body: ChatRequest):
    """SSE 流式聊天接口，等价于 Node.js 版的 /api/chat"""

    async def event_stream():
        """用 agent.astream 产生 SSE 事件"""
        config = {"configurable": {"thread_id": body.threadId}}

        try:
            async for event in agent.astream(
                {"messages": [HumanMessage(content=body.message)]},
                config,
                stream_mode="updates",
            ):
                # event 格式: {"agent": {"messages": [...]}} 或 {"tools": {"messages": [...]}}
                for node_name, data in event.items():
                    messages = data.get("messages", [])

                    # 推送 token 内容
                    if messages:
                        last_msg = messages[-1]
                        content = getattr(last_msg, "content", None)
                        if content:
                            chunk = json.dumps(
                                {"type": "token", "content": content},
                                ensure_ascii=False,
                            )
                            yield f"data: {chunk}\n\n"

                    # 推送工具调用通知
                    tool_calls = getattr(last_msg, "tool_calls", None) if messages else None
                    if tool_calls:
                        tool_name = tool_calls[0].get("name", "unknown")
                        chunk = json.dumps(
                            {"type": "tool_call", "toolName": tool_name},
                            ensure_ascii=False,
                        )
                        yield f"data: {chunk}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── 启动入口 ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print(f"Python Agent server running on http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
