"""
LLM API 调用模式大全
=====================

演示 OpenAI 兼容 SDK 的 6 种调用方式：

1. 同步单次调用    — client.chat.completions.create()
2. 流式输出        — stream=True，逐 Token 接收
3. 异步调用        — AsyncOpenAI，FastAPI 场景
4. 异步流式         — 异步 + 流式，生产环境主流
5. 批量并发         — asyncio.gather，多个请求同时发出
6. 多轮对话         — messages 历史管理

运行前安装：pip install openai python-dotenv

环境变量（不设置则使用内置演示模式）：
  OPENAI_API_KEY   — OpenAI API 密钥
  OPENAI_BASE_URL  — API 地址（默认为 OpenAI 官方）
"""

import asyncio
import os
import time
from typing import Optional

# ========== 演示模式：无需 API Key 也能跑 ==========

class DemoClient:
    """演示客户端 —— 模拟 OpenAI 行为，无需 API Key"""

    class chat:
        class completions:
            @staticmethod
            def create(*, model, messages, temperature=0.7, stream=False, **kwargs):
                if stream:
                    return _DemoStream(model, messages)
                return _DemoResponse(model, messages)

            @staticmethod
            async def acreate(*, model, messages, temperature=0.7, stream=False, **kwargs):
                if stream:
                    return _DemoAsyncStream(model, messages)
                return _DemoResponse(model, messages)

    class embeddings:
        @staticmethod
        def create(*, model, input, **kwargs):
            import hashlib
            texts = input if isinstance(input, list) else [input]
            data = []
            for t in texts:
                # 用 hash 模拟固定维度的向量
                h = hashlib.sha256(t.encode()).digest()[:64]
                vec = [float(b) / 255.0 for b in h] + [0.0] * (1536 - 64)
                data.append({"embedding": vec[:1536], "index": len(data)})
            return type("obj", (), {"data": data})()


class _DemoResponse:
    def __init__(self, model, messages):
        user_msg = messages[-1]["content"] if messages else "你好"
        system_msg = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""

        reply = _generate_demo_reply(user_msg, system_msg, model)

        self.choices = [
            type("c", (), {
                "message": type("m", (), {"role": "assistant", "content": reply})(),
                "index": 0,
            })()
        ]
        self.model = model
        self.usage = type("u", (), {
            "prompt_tokens": len(user_msg),
            "completion_tokens": len(reply),
            "total_tokens": len(user_msg) + len(reply),
        })()


class _DemoStream:
    def __init__(self, model, messages):
        self._reply = _generate_demo_reply(
            messages[-1]["content"] if messages else "你好",
            messages[0]["content"] if messages and messages[0]["role"] == "system" else "",
            model,
        )
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._reply):
            raise StopIteration
        char = self._reply[self._index]
        self._index += 1
        return type("c", (), {
            "choices": [type("ch", (), {"delta": type("d", (), {"content": char})(), "index": 0})()]
        })()


class _DemoAsyncStream:
    def __init__(self, model, messages):
        self._reply = _generate_demo_reply(
            messages[-1]["content"] if messages else "你好",
            messages[0]["content"] if messages and messages[0]["role"] == "system" else "",
            model,
        )
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._reply):
            raise StopAsyncIteration
        char = self._reply[self._index]
        self._index += 1
        await asyncio.sleep(0.01)  # 模拟网络延迟
        return type("c", (), {
            "choices": [type("ch", (), {"delta": type("d", (), {"content": char})(), "index": 0})()]
        })()


def _generate_demo_reply(user_msg: str, system_msg: str, model: str) -> str:
    """根据用户输入生成演示回复"""
    msg_lower = user_msg.lower()
    
    if "流式" in msg_lower or "stream" in msg_lower:
        return "流式输出是一种让 LLM 逐 Token 返回结果的技术，用户可以看到文字像打字一样一个个出现，体验更好。在 OpenAI SDK 中设置 stream=True 即可启用。"
    elif "token" in msg_lower:
        return "Token 是 LLM 处理文本的最小单位。中文字通常 1-2 个 Token，英文单词通常 1 个 Token。Token 数量影响成本和上下文长度上限。"
    elif "温度" in msg_lower or "temperature" in msg_lower:
        return "Temperature 控制输出的随机性。0 是确定性（总选最可能的词），1 是正常随机，2 是高度随机（可能胡说）。代码和翻译建议 0~0.3，写作建议 0.7~1.0。"
    elif "你好" in msg_lower or "hello" in msg_lower:
        return f"你好！我是演示客户端（模型：{model}）。当前未配置 OpenAI API Key，展示的是离线模拟回复。设置 OPENAI_API_KEY 环境变量后可获得真实 AI 回复。"
    else:
        return f"关于「{user_msg[:30]}」——这是演示回复。本代码展示了 6 种 LLM API 调用模式：同步、流式、异步、异步流式、批量并发、多轮对话。运行代码查看完整演示！"


# ========== 真实客户端 ==========

def get_client():
    """获取客户端（有 API Key 用真实，没有用演示）"""
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        except ImportError:
            print("[提示] 未安装 openai 库，使用演示模式。安装: pip install openai")
    return DemoClient()


def get_async_client():
    """获取异步客户端"""
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import AsyncOpenAI
            return AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        except ImportError:
            pass
    return DemoClient()


MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ====================== 模式 1：同步单次调用 ======================

def demo_sync_call():
    """最基本的调用方式 —— 发请求，等结果"""
    client = get_client()

    print("--- 模式1：同步单次调用 ---")
    start = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话解释什么是 Token"}],
        temperature=0.3,
    )

    elapsed = time.time() - start
    print(f"耗时: {elapsed:.2f}s")
    print(f"回复: {response.choices[0].message.content}")
    print(f"Token: 输入={response.usage.prompt_tokens}, 输出={response.usage.completion_tokens}\n")


# ====================== 模式 2：流式输出 ======================

def demo_stream_call():
    """打字机效果的流式输出"""
    client = get_client()

    print("--- 模式2：流式输出 ---")
    print("AI: ", end="", flush=True)

    start = time.time()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用3句话解释流式输出"}],
        stream=True,
    )

    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)

    elapsed = time.time() - start
    print(f"\n耗时: {elapsed:.2f}s\n")

    """
    流式输出代码模式（供复制到你的项目）：
    
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="")
    """


# ====================== 模式 3：异步调用 ======================

async def demo_async_call():
    """异步调用 —— FastAPI 等 Web 框架的标准写法
    
    对比 JS:
    - JS:  await openai.chat.completions.create({...})
    - Python: await client.chat.completions.create(...)
    
    语法几乎一样，但注意 Python 需要 import asyncio
    """
    client = get_async_client()

    print("--- 模式3：异步调用 ---")
    start = time.time()

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话解释什么是 Temperature"}],
        temperature=0.3,
    )

    elapsed = time.time() - start
    print(f"耗时: {elapsed:.2f}s")
    print(f"回复: {response.choices[0].message.content}\n")


# ====================== 模式 4：异步流式 ======================

async def demo_async_stream():
    """异步流式 —— 生产环境的主流选择
    
    同时享受异步并发 + 流式体验。
    FastAPI 中即使用这个模式实现 SSE。
    """
    client = get_async_client()

    print("--- 模式4：异步流式 ---")
    print("AI: ", end="", flush=True)

    start = time.time()
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用2句话解释 System Prompt"}],
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)

    elapsed = time.time() - start
    print(f"\n耗时: {elapsed:.2f}s\n")


# ====================== 模式 5：批量并发 ======================

async def demo_batch_concurrent():
    """批量并发 —— 多个问题同时发送，总耗时 = 最慢的那一个
    
    关键：asyncio.gather() 同时发起多个异步请求。
    如果顺序调用 5 个请求各 1 秒，总耗时 5 秒。
    如果并发调用，总耗时约 1 秒。
    """
    client = get_async_client()

    questions = [
        "什么是 Token？一句话回答",
        "什么是 Temperature？一句话回答",
        "什么是 Embedding？一句话回答",
        "什么是 System Prompt？一句话回答",
        "什么是 Function Calling？一句话回答",
    ]

    print(f"--- 模式5：批量并发（{len(questions)} 个问题同时发出）---")
    start = time.time()

    async def ask_one(question: str) -> str:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # asyncio.gather = JS 的 Promise.all()
    answers = await asyncio.gather(*[ask_one(q) for q in questions])

    for q, a in zip(questions, answers):
        print(f"  Q: {q}")
        print(f"  A: {a}\n")

    elapsed = time.time() - start
    print(f"总耗时: {elapsed:.2f}s (如果串行则约 {elapsed * len(questions):.0f}s)\n")


# ====================== 模式 6：多轮对话 ======================

def demo_multi_turn():
    """多轮对话 —— 把历史 messages 一直往后传
    
    关键数据结构：
    messages = [
        {"role": "system", "content": "你是..."},         # 人设
        {"role": "user",   "content": "我叫小明"},        # 第1轮
        {"role": "assistant", "content": "你好小明！"},    # 第1轮
        {"role": "user",   "content": "我叫什么？"},       # 第2轮 ← 当前问题
    ]
    
    最后一轮 LLM 能看到前面所有历史，所以能回答 "你叫小明"。
    
    注意 token 爆炸问题：
    如果消息列表过长，可以：
    1. 只保留最近 N 轮（窗口策略）
    2. 把旧消息总结成一段（摘要策略）
    """
    client = get_client()

    print("--- 模式6：多轮对话 ---")

    messages = [
        {
            "role": "system",
            "content": "你是一个友好的助手。回答问题要简洁。记住对话中的信息。",
        },
        {"role": "user", "content": "我叫小明，我是一名前端工程师，在学习 AI。"},
    ]

    def chat(user_input: str):
        messages.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.5,
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply

    # 第1轮
    reply1 = chat("你好")
    print(f"你: 你好")
    print(f"AI: {reply1}\n")

    # 第2轮 —— AI 应该能记住上下文
    reply2 = chat("我叫什么名字？做什么工作？")
    print(f"你: 我叫什么名字？做什么工作？")
    print(f"AI: {reply2}\n")

    # 第3轮
    reply3 = chat("我适合转行做什么？")
    print(f"你: 我适合转行做什么？")
    print(f"AI: {reply3}\n")

    print(f"消息历史共 {len(messages)} 条")


# ====================== 演示历史压缩策略 ======================

def demo_context_compression():
    """演示：如何防止对话历史超出 Token 上限
    
    三种策略：
    1. 窗口截断 —— 只保留最近 K 轮
    2. 摘要压缩 —— 把历史对话总结成一段
    3. 智能截断 —— 保留 system + 最近的消息
    """
    print("--- 附加演示：上下文压缩策略 ---")
    
    messages = [
        {"role": "system", "content": "你是 AI 助手。"},
        {"role": "user", "content": "问题1"},
        {"role": "assistant", "content": "回答1"},
        {"role": "user", "content": "问题2"},
        {"role": "assistant", "content": "回答2"},
        {"role": "user", "content": "问题3"},
        {"role": "assistant", "content": "回答3"},
        {"role": "user", "content": "问题4"},
        {"role": "assistant", "content": "回答4"},
        {"role": "user", "content": "新问题"},
    ]
    
    print(f"原始消息数: {len(messages)}")
    
    # 策略1: 窗口截断（保留 system + 最后6条）
    K = 6
    truncated = [messages[0]] + messages[-(K):]
    print(f"窗口截断(最后{K}条): 从 {len(messages)} → {len(truncated)} 条")
    
    # 策略2: 摘要压缩（把中间的消息"压缩"成一条 system 消息）
    summary = "[历史摘要] 前几轮谈到了问题1~4，用户逐渐深入..."
    compressed = [
        {"role": "system", "content": f"你是 AI 助手。以下是之前对话的摘要：{summary}"},
        messages[-1],  # 只保留最后一轮
    ]
    print(f"摘要压缩: 从 {len(messages)} → {len(compressed)} 条")
    
    # 策略3: 混合（保留 system + 最近2轮 + 摘要前面的）
    hybrid = [
        {"role": "system", "content": f"你是 AI 助手。历史摘要：{summary}"},
        *messages[-3:],  # 最近1.5轮
    ]
    print(f"混合策略: 从 {len(messages)} → {len(hybrid)} 条\n")


# ====================== 主入口 ======================

async def main():
    mode = "真实 API" if os.getenv("OPENAI_API_KEY") else "演示模式"
    print(f"""
╔══════════════════════════════════════════════╗
║  LLM API 调用模式大全 — {mode}
╚══════════════════════════════════════════════╝
""")

    # 同步
    demo_sync_call()
    demo_stream_call()
    
    # 异步（需要事件循环）
    await demo_async_call()
    await demo_async_stream()
    await demo_batch_concurrent()
    
    # 多轮对话 & 上下文压缩
    demo_multi_turn()
    demo_context_compression()

    print("所有模式演示完毕！")


if __name__ == "__main__":
    asyncio.run(main())
