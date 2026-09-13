"""Agent 服务层：把 ReAct 循环改造成可以"边跑边推"的异步生成器。

## 与项目 03 的关键区别

项目 03 是同步阻塞的：`result = agent.run(question)` 跑完才返回。
Web 服务不能这样 —— 用户要实时看到进度，不能等 10 秒才出第一个字。

所以这里改成 **async generator**：每发生一件事就 yield 一个事件，
上层（FastAPI）把它们变成 SSE 推给前端。

## 事件类型设计

    {"type": "thinking",    "content": "..."}     模型这步的思考
    {"type": "tool_call",   "tool": "...", "args": {...}}   要调工具了
    {"type": "tool_result", "tool": "...", "result": "..."} 工具返回了
    {"type": "text",        "content": "..."}     正文片段（打字机）
    {"type": "done",        "usage": {...}}       全部完成
    {"type": "error",       "message": "..."}     出错

前端按 type 分发渲染。这个协议设计得越清楚，前端越好写。
"""
import json
import time
import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings, get_client
from app.tools import TOOL_SCHEMAS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个可以调用工具的助手，服务于企业员工。\n"
    "工作方式：\n"
    "1. 先判断是否需要工具。常识问题直接回答，不要为了调工具而调工具。\n"
    "2. 需要外部信息（时间、天气、计算、公司政策）时调用工具，一次调一个。\n"
    "3. 拿到结果后用中文简洁回答，不要复述工具的原始 JSON。\n"
    "4. 工具报错时看懂原因再决定是否重试，不要盲目重复同样的调用。\n"
    "5. 无法完成时如实说明卡在哪里，不要假装成功。"
)


async def run_agent_stream(
    question: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """运行 Agent，逐步 yield 事件。

    这是整个后端的核心。注意几个工程细节：
    - 用 AsyncOpenAI 而非同步客户端（否则阻塞事件循环）
    - 每个事件都要是可以 JSON 序列化的简单结构
    - 出错要 yield error 事件而不是抛异常（SSE 连接已经建立了）
    """
    client = AsyncOpenAI(
        api_key=__import__("os").getenv(settings.model.api_key_env),
        base_url=settings.model.base_url,
    )

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    total_in = 0
    total_out = 0
    steps = 0

    for step_idx in range(settings.max_steps):
        steps = step_idx + 1

        # ---------- 请求模型 ----------
        try:
            resp = await client.chat.completions.create(
                model=settings.model.name,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=settings.temperature,
            )
        except Exception as ex:                 # noqa: BLE001
            logger.exception("模型调用失败")
            yield {"type": "error", "message": f"模型调用失败：{ex}"}
            return

        if getattr(resp, "usage", None):
            total_in += getattr(resp.usage, "prompt_tokens", 0) or 0
            total_out += getattr(resp.usage, "completion_tokens", 0) or 0

        msg = resp.choices[0].message

        # ---------- 情况 A：直接回答 ----------
        if not msg.tool_calls:
            content = msg.content or ""
            # 逐字符推送（模拟打字机）。真实项目可以直接整段推，
            # 让前端用 CSS 动画做打字效果 —— 那样更省事。
            yield {"type": "text", "content": content}
            yield {
                "type": "done",
                "usage": {
                    "input_tokens": total_in,
                    "output_tokens": total_out,
                    "steps": steps,
                    "cost_usd": round(
                        total_in / 1e6 * settings.model.price_input
                        + total_out / 1e6 * settings.model.price_output, 8
                    ),
                },
            }
            return

        # ---------- 情况 B：调用工具 ----------
        if msg.content and msg.content.strip():
            yield {"type": "thinking", "content": msg.content.strip()}

        # 必须先把 assistant 消息（含 tool_calls）加进历史
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name,
                                 "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                if not isinstance(args, dict):
                    args = {}
            except json.JSONDecodeError as ex:
                err = (f"参数解析失败：不是合法 JSON（{ex}）。"
                       f"原始内容：{tc.function.arguments[:200]}")
                yield {"type": "tool_result", "tool": name, "result": err, "error": True}
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": err})
                continue

            # 推给前端：要调工具了（前端可显示 loading 卡片）
            yield {"type": "tool_call", "tool": name, "args": args}

            result = execute_tool(name, args)

            # 推给前端：工具返回了
            yield {"type": "tool_result", "tool": name, "result": result}

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    # ---------- 达到步数上限 ----------
    yield {
        "type": "error",
        "message": (
            f"已尝试 {settings.max_steps} 步仍未完成，已停止以避免继续消耗。"
            f"请换个说法或缩小任务范围。"
        ),
    }


async def run_agent_once(question: str, history: list[dict] | None = None) -> dict:
    """非流式版本：跑完一次性返回。适合简单调用和测试。

    实现方式：复用流式版本，把事件收集起来再拼装。
    为什么不重写一遍：避免两套逻辑不一致（这是很常见的坑）。
    """
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    usage: dict = {}
    error: str | None = None

    async for ev in run_agent_stream(question, history):
        t = ev.get("type")
        if t == "text":
            text_parts.append(ev["content"])
        elif t == "tool_call":
            tool_calls.append({"tool": ev["tool"], "args": ev["args"]})
        elif t == "done":
            usage = ev.get("usage", {})
        elif t == "error":
            error = ev.get("message")

    return {
        "answer": "".join(text_parts),
        "tool_calls": tool_calls,
        "usage": usage,
        "error": error,
    }
