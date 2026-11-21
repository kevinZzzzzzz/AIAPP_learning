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
    print(f"回复: {content}")
    print(f"Token 用量： prompt={usage.prompt_tokens},\n"
        f"completion={usage.completion_tokens}\n",
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
        content = response.choices[0].message.content
        print(content)


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
        stream=True # 流式关键参数
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


# ======================== 8. Function Calling 基础 ========================
async def function_calling_basic():
    """Function Calling —— 让 LLM 调用外部工具
    
    这是 Agent 的核心机制！后面 07_Agent 章节会详讲
    """
    client = create_client()
    
    # 定义工具（函数）
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "descrption": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，例如：上海、北京、深圳、广州、汕头",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "温度单位"
                        },
                    },
                    "required": ["city"]
                }
            }
        }
    ]

    response = await client.chat.completions.create(
        model=api_model_name,
        messages=[
            {
                "role": "user", "content": "深圳今天天气怎么样"
            }
        ],
        tools=tools,
        tool_choice="auto"  # LLM 自动决定是否调用工具
    )

    message = response.choices[0].message
    print(f"tool_calls{message.tool_calls}\n")

    if message.tool_calls:
        for tool_call in message.tool_calls:
            print(f"tool_call----{tool_call}\n")
            func_name = tool_call.function.name
            print(f"func_name----{func_name}\n")
            func_args = json.loads(tool_call.function.arguments)
            print(f"LLM 想调用: {func_name}({func_args})\n")

            # 模拟工具执行
            if func_name == "get_weather":
                result = f"{func_args['city']}今天晴天，25℃"
                print(f"LLM 想调用: {message.model_dump()}\n")
                # 把工具结果返回给 LLM
                messages = [
                    {"role": "user", "content": "北京今天天气怎么样？"},
                    message.model_dump(),  # 包含 tool_calls 的消息
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    }
                ]
                response2 = await client.chat.completions.create(
                    model=api_model_name,
                    messages=messages
                )
                print(f"最终回复: {response2.choices[0].message.content}\n")
    else:
        print(f"LLM 直接回复: {message.content}\n")


# ======================== 9. Token 计算（tiktoken） ========================
import tiktoken
def count_tokens(text: str, model: str = api_model_name):
    # encoding = tiktoken.encoding_for_model(model)
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

text = "Hello World! 你好世界！"
print(f"Token 数: {count_tokens(text)}")


# ======================== 10. 错误处理最佳实践 ========================
import asyncio
async def safe_chat(prompt: str, max_retries: int = 3) -> Optional[str]:
    client = create_client()
    for attemp in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=api_model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )
            return response.choices[0].message.content
        
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                wait = 2 ** attemp
                print(f"频率限制，等待{wait}秒。。。")
                await asyncio.sleep(wait)
            elif attemp == max_retries - 1:
                print(f"重试{max_retries}次后仍然失败： {e}")
                return None
            else:
                await asyncio.sleep(1)
    return  None

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
        # await structured_output()
        # await function_calling_basic()
        result = await safe_chat("五言绝句夸我帅")
        print(f"{result}")
    except Exception as e:
        print(f"跳过（需要API KEY）: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

