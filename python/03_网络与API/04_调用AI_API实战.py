"""
网络与 API：调用主流 AI 模型 API

在开发 AI 应用时，除了手写 httpx/requests 发送请求，
通常最省事的方法是直接使用官方提供的 SDK 包。

目前整个行业（包括通义千问、DeepSeek、百川、月之暗面 Kimi 等）
都广泛兼容或直接采用了 OpenAI 的 API 格式规范。
因此，学会使用 `openai` 这个 Python 包，就能对接市面上 90% 的大模型。
"""

# 需要安装：pip install openai
# pyrefly: ignore [missing-import]
from openai import OpenAI
import os

# ======================== 1. 初始化客户端 ========================
# 假设我们要调用国内某个兼容 OpenAI 格式的 API（例如 DeepSeek 或 Kimi）
# 你需要在环境变量中设置 API KEY
# 这里作为演示，如果不填将无法真正运行

api_key = os.getenv("MY_AI_API_KEY", "your-api-key-here")
base_url = "https://api.deepseek.com/v1" # 替换为你使用的供应商 Base URL

# 初始化同步客户端 (也有 AsyncOpenAI 异步客户端用于 FastAPI)
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# ======================== 2. 基础对话请求 (阻塞式) ========================

def chat_basic():
    print("--- 发送基础对话请求 ---")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 模型名称
            messages=[
                {"role": "system", "content": "你是一个幽默的 AI 助手。"},
                {"role": "user", "content": "请用一句话解释什么是量子力学。"}
            ],
            temperature=0.7, # 创意度 (0.0 到 2.0)
            max_tokens=100   # 最大输出长度
        )
        
        # 解析返回结果
        answer = response.choices[0].message.content
        print(f"AI 的回答：\\n{answer}")
        
    except Exception as e:
        print(f"请求失败（可能是 API Key 未配置）: {e}")


# ======================== 3. 流式对话请求 (Streaming) ========================
# 配合 02_SSE流式输出.py 学习效果更佳

def chat_stream():
    print("\\n--- 发送流式对话请求 (打字机效果) ---")
    try:
        # 加上 stream=True 即可
        response_stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "写一首描写赛博朋克城市的短诗。"}
            ],
            stream=True
        )
        
        print("AI 的回答：", end="")
        
        # 遍历生成的数据块
        for chunk in response_stream:
            # 每次拿到一个很小的文本切片（几个字甚至一个字）
            content = chunk.choices[0].delta.content
            if content is not None:
                # 打印到控制台，且不换行，实现打字效果
                print(content, end="", flush=True)
                
        print() # 最后换行
        
    except Exception as e:
         print(f"\\n请求失败: {e}")

if __name__ == "__main__":
    print("注意：要运行此脚本，请先设置好真实的 API_KEY")
    chat_basic()
    # chat_stream()
