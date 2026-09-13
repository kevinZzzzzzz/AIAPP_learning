"""配置与模型客户端。"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    name: str
    base_url: str
    api_key_env: str
    price_input_cache_hit: float
    price_input: float
    price_output: float


# 价格来源：DeepSeek 官方价格页（核实于 2026-09-13）
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
}


@dataclass
class AppConfig:
    model_key: str = field(default_factory=lambda: os.getenv("MODEL_KEY", "flash"))
    max_steps: int = field(default_factory=lambda: int(os.getenv("MAX_STEPS", "8")))
    verbose: bool = field(default_factory=lambda: os.getenv("VERBOSE", "true").lower() == "true")
    temperature: float = 0.1
    usd_to_cny: float = 7.2

    system_prompt: str = (
        "你是一个可以调用工具的助手。\n"
        "工作方式：\n"
        "1. 先判断是否需要工具。如果问题你已知道答案，或不需要外部信息，直接回答。\n"
        "2. 需要工具时，一次调用一个，等结果回来再决定下一步。\n"
        "3. 拿到工具结果后，用中文简洁地回答用户，不要复述工具的原始输出。\n"
        "4. 如果工具报错，看懂错误原因后再决定是否换参数重试，不要盲目重试。\n"
        "5. 如果连续几步都无法完成，直接告诉用户你卡在哪里，不要假装成功。"
    )

    @property
    def model(self) -> ModelConfig:
        return MODELS[self.model_key]


config = AppConfig()


def get_client():
    from openai import OpenAI

    m = config.model
    api_key = os.getenv(m.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"缺少环境变量 {m.api_key_env}。请复制 .env.example 为 .env 并填入 Key。"
        )
    return OpenAI(api_key=api_key, base_url=m.base_url)
