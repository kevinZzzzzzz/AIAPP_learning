import os
import json 
from typing import Optional, Literal
from dotenv import load_dotenv, find_dotenv
from openai import AsyncOpenAI

load_dotenv(find_dotenv())

ai_api_key = os.getenv("AI_API_KEY")
ai_base_url = os.getenv("AI_BASE_URL")
api_model_name = os.getenv("AI_MODEL_NAME")


# ======================== 1. 初始化客户端（同步 vs 异步） ========================
def create_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> AsyncOpenAI:
    """创建 AsyncOpenAI 客户端
    
    通过 base_url 参数可以切换到国产模型：
    - DeepSeek: https://api.deepseek.com
    - Qwen（阿里云）: https://dashscope.aliyuncs.com/compatible-mode/v1
    - GLM（智谱）: https://open.bigmodel.cn/api/paas/v4
    - Moonshot（月之暗面）: https://api.moonshot.cn/v1
    """
    return AsyncOpenAI(
        api_key = api_key or ai_api_key,
        base_url = base_url or ai_base_url
    )


# ======================== 2. 基本对话 ========================
async def basic_chat():
    client = create_client()

    response = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {"role": "system", "content": "你是一个python编程助手"},
            {"role": "user", "content": "用一句话解释什么是装饰器"},
        ],
        temperature=0.7,
        max_tokens=100,
    )
    content = response.choices[0].message.content
    
    usage = response.usage
    print(f"回复: {coqwntent}")
    print(f"Token 用量： prompt={usage.prompt_tokens},"
        f"completion={usage.completion_tokens}",
        f"total={usage.total_tokens}"
    )

    return content

    

# ======================== 3. 多轮对话 ========================
async def mutil_turn_chat():
    client = create_client()
    messages = [
        {"role": "system", "content": "你是一个友好的助手"},
    ]
    # 第一轮
    messages.append({"role": "user", "content": "我叫小胡。"})
    response = await client.chat.completions.create(
        model=api_model_name,
        messages=messages,
    )
    reply1 = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply1})
    print(f"第一轮: {reply1}")


    
    # 第二轮（包含第一轮的上下文）
    messages.append({"role": "user", "content": "我叫什么名字？"})
    response = await client.chat.completions.create(
        model=api_model_name,
        messages=messages,
    )
    reply2 = response.choices[0].message.content

    print(f"第二轮: {reply2}")
    return messages

# ======================== 4. System Prompt 设计 ========================

SYSTEM_PROMPTS = {
    "translator": "你是一个专业翻译。请把用户输入翻译成英文。只输出译文，不要解释。",
    
    "code_reviewer": """
你是一个资深代码审查员。审查用户的代码时，请从以下角度分析：
1. 代码正确性
2. 性能优化
3. 安全隐患
4. 可维护性
用中文回复，给出具体建议。
""",
    
    "data_analyst": """
你是一个数据分析师。请用以下格式回复：
1. 一句话总结
2. 关键发现（bullet points）
3. 行动建议
""",
}
async def demo_system_prompt():
    """测试不同的 System Prompt 效果"""
    client = create_client()

    user_input = "hello world"

    for role_name, system_prompt in SYSTEM_PROMPTS.items():
        print(f"\n=== {role_name} ====")
        response = await client.chat.completions.create(
            model=api_model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        print(response.choices[0].message.content)


# ======================== 5. 控制输出格式（Temperature / Top-P） ========================
async def demo_sampling_params():
    """理解 Temperature 和 Top-P 的作用"""
    client = create_client()

    prompt = input("请输入你想查询到的：")
    
    # Temperature=0 → 确定性输出，每次结果一样
    response_cold = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
    )
    response_hot = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=1.5,
    )
    print(f"Temperature=0 (确定性):\n{response_cold.choices[0].message.content}")
    print(f"Temperature=0 (创造性):\n{response_hot.choices[0].message.content}")


# ======================== 6. 流式输出（SSE） ========================
async def streaming_chat():
    """流式输出 —— 逐 token 返回，实时展示"""
    client = create_client()
    stream = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {"role": "user", "content": "用五言夸我帅"},
        ],
        stream=True
    )

    print("ChatGpt 正在答复: ", end="", flush=True)

    full_content = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            full_content += delta.content
        
    print("\n")
    return full_content


# ======================== 7. 结构化输出（JSON Mode） ========================
async def structured_output():
    """让 LLM 返回结构化 JSON
    
    需要 System Prompt 中明确要求 JSON 格式输出
    """
    client = create_client()
    response = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {
                "role": "system",
                "content": "你是一个数据分析师。请始终用以下 JSON 格式回复："
                           '{"summary": "总结", "sentiment": "positive/negative/neutral", '
                           '"keywords": ["关键词1", "关键词2"], "score": 0.0-1.0}'
            },
            {
                "role": "user",
                "content": "分析这段文本：Python 是一门优雅高效的编程语言，"
                           "在 AI 领域广泛应用，社区生态非常丰富。"
            },
        ],
        temperature=0
    )
    content = response.choices[0].message.content

    try:
        data = json.loads(content)
        print(f"总结: {data['summary']}")
        print(f"情感: {data['sentiment']}")
        print(f"关键词: {data['keywords']}")
        print(f"得分: {data['score']}")
    except json.JSONDecodeError:
        print(f"JSON 解析失败，原始输出: {content}")




async def main():
    print("=" * 60)
    print("LLM API 调用Demo")
    print("=" * 60)

    try:
        print("\n1.基本会话")
        # await basic_chat()
        # await mutil_turn_chat()
        # await demo_system_prompt()
        # await demo_sampling_params()
        # await streaming_chat()
        await structured_output()
    except Exception as e:
        print(f"跳过（需要API KEY）: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

