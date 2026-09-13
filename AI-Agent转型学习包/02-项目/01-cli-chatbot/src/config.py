"""集中配置。所有模型参数、价格、路径都在这里，不散落到代码各处。

为什么要集中：改模型名、调价格、换提供方只需要动这一个文件。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    base_url: str
    api_key_env: str
    # 价格（美元/百万 token），用于成本计算。以你注册时的官方价格为准
    price_input_cache_hit: float
    price_input: float
    price_output: float


# 价格来源：DeepSeek 官方价格页（核实于 2026-09-13）
# https://api-docs.deepseek.com/quick_start/pricing
MODELS: dict[str, ModelConfig] = {
    "flash": ModelConfig(
        name="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input_cache_hit=0.0028,
        price_input=0.14,
        price_output=0.28,
    ),
    "pro": ModelConfig(
        name="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input_cache_hit=0.003625,
        price_input=0.435,
        price_output=0.87,
    ),
    # 本地 Ollama（OpenAI 兼容接口），零成本调试用
    "ollama": ModelConfig(
        name="qwen3:8b",
        base_url="http://localhost:11434/v1",
        api_key_env="OLLAMA_API_KEY",       # Ollama 不校验 key，填任意值即可
        price_input_cache_hit=0.0,
        price_input=0.0,
        price_output=0.0,
    ),
}


@dataclass
class AppConfig:
    """应用配置"""
    model_key: str = field(default_factory=lambda: os.getenv("MODEL_KEY", "flash"))
    temperature: float = 0.3
    max_turns: int = 10                      # 上下文最多保留的对话轮数
    system_prompt: str = (
        "你是一个专业的技术助手，回答简洁准确。"
        "不确定的信息要明确说明不确定，不要编造。"
    )

    # 汇率仅用于展示（成本计算用美元，展示换算成人民币）
    usd_to_cny: float = 7.2

    @property
    def model(self) -> ModelConfig:
        return MODELS[self.model_key]


config = AppConfig()


def get_client():
    """创建模型客户端。支持 DeepSeek / Ollama 切换。"""
    from openai import OpenAI

    m = config.model
    api_key = os.getenv(m.api_key_env)

    if m.api_key_env == "OLLAMA_API_KEY":
        api_key = "ollama"                   # 本地 Ollama 不需要真实 key

    if not api_key:
        raise RuntimeError(
            f"缺少环境变量 {m.api_key_env}。\n"
            f"请复制 .env.example 为 .env 并填入你的 API Key。"
        )

    return OpenAI(api_key=api_key, base_url=m.base_url)
