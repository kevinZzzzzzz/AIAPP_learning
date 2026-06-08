"""
DeepSeek Chat —— 配置常量
==========================
API Key 通过常量设置。
"""

# DeepSeek API Key（替换为你的 Key）
DEEPSEEK_API_KEY = "sk-your-deepseek-api-key-here"

# DeepSeek API 地址
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 模型名称
DEEPSEEK_MODEL = "deepseek-chat"

# 服务配置
HOST = "0.0.0.0"
PORT = 8000
ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

# 系统提示词
SYSTEM_PROMPT = (
    "你是 DeepSeek 智能助手，一个由深度求索公司创造的 AI 助手。"
    "你乐于帮助用户解决问题，回答准确、简洁、友好。"
    "用中文回答，使用 Markdown 格式使回复更易读。"
)
