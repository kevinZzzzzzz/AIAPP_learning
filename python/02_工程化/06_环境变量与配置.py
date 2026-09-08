"""
Python 工程化：环境变量与配置管理

在 AI 项目中，绝不要把 API 密钥（如 OPENAI_API_KEY）或数据库密码硬编码在代码里！
最佳实践是：
1. 开发环境：将敏感信息写在项目根目录的 .env 文件中（该文件必须加入 .gitignore 防止提交）
2. 生产环境：通过操作系统的环境变量配置
3. 代码读取：使用 python-dotenv 或者 pydantic-settings 进行读取
"""

import os

# ======================== 1. 基础方式：使用 python-dotenv ========================
# 需要先安装：pip install python-dotenv

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

def demo_dotenv():
    print("--- 使用 python-dotenv ---")
    
    # load_dotenv() 会自动寻找项目根目录下的 .env 文件
    # 并将其中的键值对加载到操作系统的环境变量 (os.environ) 中
    # 例如 .env 内容为： OPENAI_API_KEY=sk-123456
    
    # 模拟创建一个临时的 .env 环境（实际开发中请勿这样写）
    os.environ["MOCK_API_KEY"] = "sk-mock-123"
    
    load_dotenv()
    
    # 读取环境变量，建议提供一个默认值防止报错
    api_key = os.getenv("MOCK_API_KEY", "default_key_if_not_found")
    port = os.getenv("SERVER_PORT", 8080)
    
    print(f"API Key: {api_key}")
    print(f"Server Port: {port} (类型是 {type(port)}，getenv 读出来的都是字符串)")
    print()


# ======================== 2. 进阶方式：使用 pydantic-settings (推荐) ========================
# 需要先安装：pip install pydantic-settings
# 这是 FastAPI 官方强烈推荐的配置管理方式

# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
# pyrefly: ignore [missing-import]
from pydantic import Field

class Settings(BaseSettings):
    """
    Settings 类会自动从环境变量或 .env 文件中读取同名字段。
    最大的好处是：它支持类型转换和校验！
    """
    app_name: str = "My AI App"  # 如果环境变量没提供，就用默认值
    admin_email: str
    server_port: int = Field(default=8000, ge=1024, le=65535) # 可以叠加 Pydantic 的校验
    openai_api_key: str
    
    # 配置从哪个文件读取
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # 忽略多余的环境变量
    )

def demo_pydantic_settings():
    print("--- 使用 pydantic-settings ---")
    
    # 为了演示，我们手动向环境中注入一些变量（模拟 .env 文件的效果）
    os.environ["ADMIN_EMAIL"] = "admin@example.com"
    os.environ["OPENAI_API_KEY"] = "sk-real-secret"
    os.environ["SERVER_PORT"] = "9000" # 虽然传入的是字符串，但 Pydantic 会自动转成 int
    
    try:
        # 实例化时，它会自动去读取环境变量
        config = Settings() 
        print(f"应用名称: {config.app_name}")
        print(f"管理员邮箱: {config.admin_email}")
        print(f"API 密钥: {config.openai_api_key[:5]}***")
        print(f"服务器端口: {config.server_port} (类型自动转为了 {type(config.server_port)})")
    except Exception as e:
        print(f"配置加载失败: {e}")

if __name__ == "__main__":
    demo_dotenv()
    demo_pydantic_settings()
