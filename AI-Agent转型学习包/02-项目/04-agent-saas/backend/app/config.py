"""配置。"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    name: str
    base_url: str
    api_key_env: str
    price_input: float
    price_output: float


MODELS: dict[str, ModelConfig] = {
    "flash": ModelConfig(
        name="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input=0.14,
        price_output=0.28,
    ),
    "pro": ModelConfig(
        name="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input=0.435,
        price_output=0.87,
    ),
}


@dataclass
class Settings:
    model_key: str = field(default_factory=lambda: os.getenv("MODEL_KEY", "flash"))
    max_history_turns: int = field(default_factory=lambda: int(os.getenv("MAX_HISTORY_TURNS", "20")))
    max_steps: int = 6
    temperature: float = 0.1
    usd_to_cny: float = 7.2

    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]
    )

    @property
    def model(self) -> ModelConfig:
        return MODELS[self.model_key]


settings = Settings()


def get_client():
    from openai import OpenAI

    m = settings.model
    api_key = os.getenv(m.api_key_env)
    if not api_key:
        raise RuntimeError(f"缺少环境变量 {m.api_key_env}")
    return OpenAI(api_key=api_key, base_url=m.base_url)
