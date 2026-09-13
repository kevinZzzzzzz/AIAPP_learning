"""用量统计与成本计算。

为什么必须做：不看 token 就永远对成本没感觉。
Agent 场景下成本会随轮数近似平方增长，没数据就无法优化。
"""
from dataclasses import dataclass


@dataclass
class Usage:
    """累计用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit_tokens: int = 0
    cost_usd: float = 0.0
    requests: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int,
            cache_hit_tokens: int = 0, price: dict | None = None):
        """累加一次调用的用量并计算成本。"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.cache_hit_tokens += cache_hit_tokens
        self.requests += 1

        if price:
            # 缓存命中的那部分输入按低价算，其余按标准输入价
            miss = max(prompt_tokens - cache_hit_tokens, 0)
            self.cost_usd += (
                miss / 1e6 * price["input"]
                + cache_hit_tokens / 1e6 * price["cache_hit"]
                + completion_tokens / 1e6 * price["output"]
            )

    def reset(self):
        self.prompt_tokens = self.completion_tokens = 0
        self.cache_hit_tokens = 0
        self.cost_usd = 0.0
        self.requests = 0

    def summary(self, usd_to_cny: float = 7.2) -> str:
        return (
            f"请求 {self.requests} 次 | "
            f"输入 {self.prompt_tokens:,} token | "
            f"输出 {self.completion_tokens:,} token | "
            f"成本 ${self.cost_usd:.6f} (约 ¥{self.cost_usd * usd_to_cny:.4f})"
        )


def extract_usage(resp) -> tuple[int, int, int]:
    """从响应里提取 token 用量。不同提供方字段名可能不同，做容错处理。"""
    u = getattr(resp, "usage", None)
    if not u:
        return 0, 0, 0

    prompt = getattr(u, "prompt_tokens", 0) or 0
    completion = getattr(u, "completion_tokens", 0) or 0

    # 缓存命中字段：DeepSeek 在 prompt_cache_hit_tokens / prompt_tokens_details 里
    cache_hit = getattr(u, "prompt_cache_hit_tokens", 0) or 0
    if not cache_hit:
        details = getattr(u, "prompt_tokens_details", None)
        if details:
            cache_hit = getattr(details, "cached_tokens", 0) or 0

    return prompt, completion, cache_hit
