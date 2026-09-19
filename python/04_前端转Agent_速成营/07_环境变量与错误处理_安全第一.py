# 07_环境变量与错误处理_安全第一.py

"""
第 7 课：环境变量 (API Keys) 与 错误处理
对应 Node.js 中的：process.env / dotenv, try...catch
重要性：⭐⭐⭐⭐⭐ (极高，关乎账号安全和代码健壮性)
在 AI Agent 开发中，你每天都要和各种大模型 API Key 打交道。
绝对、永远、不要把 API Key 直接写死在代码里提交到 Git！
"""

import os
# 如果报错说找不到 dotenv，需要通过 `uv pip install python-dotenv` 安装
try:
    from dotenv import load_dotenv
except ImportError:
    print("提示: 实际项目中请先安装 python-dotenv。你可以通过 `uv pip install python-dotenv` 来安装。")
    load_dotenv = lambda: None  # mock function

def env_demo():
    print("--- 1. 环境变量与 API Key 管理 ---")
    
    # 在 Node 中你习惯在根目录建一个 .env 文件，然后 require('dotenv').config()
    # 在 Python 中一模一样！
    load_dotenv() 
    
    # Node 中获取变量：process.env.OPENAI_API_KEY
    # Python 中获取变量：os.getenv("KEY_NAME")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        # 出于安全考虑，只打印前4位和后4位
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        print(f"✅ 成功从环境变量读取 API Key: {masked_key}")
    else:
        print("⚠️ 未找到 OPENAI_API_KEY。")
        print("   解决办法：在当前目录新建一个 .env 文件，写入 OPENAI_API_KEY=sk-xxxxxx")
        
    # 如果某个配置是系统强依赖的（比如连数据库），缺失就没法运行，建议用 os.environ[]
    # 它和 getenv 的区别是：getenv 找不到会返回 None，environ 找不到会直接抛出报错。
    try:
        db_pwd = os.environ["DB_PASSWORD"]
    except KeyError:
        print("💡 [正确抛错] 强依赖配置 DB_PASSWORD 缺失，程序主动拦截。")


def try_except_demo():
    print("\n--- 2. 错误处理 (try...except 对应 try...catch) ---")
    
    # 场景：调用大模型 API 时，网络经常超时，你需要捕获它并重试
    
    def call_llm():
        # 模拟一个会报错的网络请求
        raise ConnectionError("连接大模型服务器超时，请检查网络！")
        # 在 JS 中抛出错误是: throw new Error("...")
        # Python 中是: raise Exception("...")
        
    try:
        print("正在调用 LLM...")
        call_llm()
    except ConnectionError as e:
        # 针对特定类型的错误进行捕获处理 (推荐)
        print(f"❌ 捕获到网络错误: {e}")
        print("   >>> 可以在这里写重试(Retry)逻辑")
    except Exception as e:
        # 对应 catch (e)，捕获所有其他意外报错
        print(f"❌ 捕获到未知错误: {e}")
    finally:
        # 对应 JS 的 finally，不管报没报错都会执行。通常用来关闭文件或数据库连接。
        print("🧹 清理资源 (finally)...")

def logging_concept():
    print("\n--- 3. 为什么 AI 后端更喜欢 logging 而不是 print ---")
    print("""
作为前端，你可能习惯了疯狂 console.log()。
但在 Python 的 AI 后端开发中，Agent 可能在后台默默执行 5 分钟的复杂任务（比如爬网、查资料）。
如果全用 print()，一旦部署到服务器，你很难区分哪些是报错，哪些是普通提示。

因此，强烈建议习惯使用 logging 模块：
```python
import logging
logging.basicConfig(level=logging.INFO)

logging.info("Agent 正在规划任务...") 
logging.warning("API Token 余额不足，请注意！")
logging.error("连接向量数据库失败！")
```
它能自动帮你打上时间戳、日志级别，并能轻松写入日志文件中。
    """)


if __name__ == "__main__":
    env_demo()
    try_except_demo()
    logging_concept()
