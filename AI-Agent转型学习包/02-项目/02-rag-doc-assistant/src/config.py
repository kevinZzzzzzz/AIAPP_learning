"""集中配置：模型、切片参数、检索参数、价格。

所有"可调旋钮"都放在这里。RAG 调优的本质就是调这几个数：
    chunk_size / chunk_overlap / top_k / 是否混合检索 / 是否重排
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------- 生成模型
@dataclass
class GenModelConfig:
    name: str
    base_url: str
    api_key_env: str
    price_input_cache_hit: float   # 美元 / 百万 token
    price_input: float
    price_output: float


# 价格来源：DeepSeek 官方价格页（核实于 2026-09-13）
GEN_MODELS: dict[str, GenModelConfig] = {
    "flash": GenModelConfig(
        name="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input_cache_hit=0.0028,
        price_input=0.14,
        price_output=0.28,
    ),
    "pro": GenModelConfig(
        name="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        price_input_cache_hit=0.003625,
        price_input=0.435,
        price_output=0.87,
    ),
}


# ---------------------------------------------------------------- 向量模型
@dataclass
class EmbedConfig:
    name: str
    base_url: str
    api_key_env: str
    dim: int              # 向量维度（务必与库里已有向量一致）
    batch_size: int       # 单次请求最多传几条文本
    price_per_million: float   # 人民币 / 百万 token


# 选型说明见《模块03-RAG与向量检索》。
# ⚠️ 铁律：入库与查询必须用同一个模型。换模型 = 全库重新索引。
EMBED_PROVIDERS: dict[str, EmbedConfig] = {
    "dashscope": EmbedConfig(
        name="text-embedding-v4",
        # 百炼的 OpenAI 兼容端点，可以继续用 openai SDK，不用换库
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        dim=1024,
        # text-embedding-v4 单次最多 10 条。超了会报 400，这是最常见的坑。
        batch_size=10,
        price_per_million=0.5,
    ),
    "openai": EmbedConfig(
        name="text-embedding-3-small",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        dim=1536,
        batch_size=100,
        price_per_million=1.4,   # 约 $0.02 * 7.2
    ),
}


# ---------------------------------------------------------------- 应用配置
@dataclass
class AppConfig:
    # 切片
    chunk_size: int = 400          # 每片目标字符数
    chunk_overlap: int = 80        # 相邻片重叠字符数（防止答案被切断）
    min_chunk_size: int = 80       # 太短的片丢弃，通常是噪声

    # 检索
    top_k: int = 5                 # 最终喂给模型的片段数
    vector_top_k: int = 12         # 向量检索召回数（先多召回再融合）
    bm25_top_k: int = 12           # 关键词检索召回数
    use_hybrid: bool = True        # 是否启用混合检索
    rrf_k: int = 60                # RRF 融合常数，一般取 60

    # 生成
    temperature: float = 0.1       # RAG 要的是忠实，不是创意
    max_context_chars: int = 6000  # 上下文硬上限，防止爆 token

    # 存储
    db_path: str = "rag.db"
    usd_to_cny: float = 7.2

    gen_model_key: str = field(default_factory=lambda: os.getenv("GEN_MODEL_KEY", "flash"))
    embed_provider: str = field(default_factory=lambda: os.getenv("EMBED_PROVIDER", "dashscope"))

    system_prompt: str = (
        "你是一个严谨的文档问答助手。请严格依据【参考资料】回答问题。\n"
        "规则：\n"
        "1. 只能使用参考资料中的信息，不要引入外部知识。\n"
        "2. 每个结论后面用 [1]、[2] 标注它来自第几段资料。\n"
        "3. 如果参考资料不足以回答问题，直接说"
        "「根据现有资料无法回答」，不要猜测。\n"
        "4. 用中文回答，简洁准确。"
    )

    @property
    def gen_model(self) -> GenModelConfig:
        return GEN_MODELS[self.gen_model_key]

    @property
    def embed(self) -> EmbedConfig:
        return EMBED_PROVIDERS[self.embed_provider]


config = AppConfig()


def get_gen_client():
    """生成模型客户端（DeepSeek）。"""
    from openai import OpenAI

    m = config.gen_model
    api_key = os.getenv(m.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"缺少环境变量 {m.api_key_env}。\n"
            f"请复制 .env.example 为 .env 并填入 API Key。"
        )
    return OpenAI(api_key=api_key, base_url=m.base_url)


def get_embed_client():
    """向量模型客户端（百炼 / OpenAI 均可，都是 OpenAI 兼容协议）。"""
    from openai import OpenAI

    e = config.embed
    api_key = os.getenv(e.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"缺少环境变量 {e.api_key_env}（当前 provider={config.embed_provider}）。\n"
            f"请复制 .env.example 为 .env 并填入 API Key。"
        )
    return OpenAI(api_key=api_key, base_url=e.base_url)
