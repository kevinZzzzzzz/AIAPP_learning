"""健壮的模型调用封装：流式 + 重试 + 用量统计。

生产代码必须这么写。Agent 一次任务可能调 20 次模型，
任何一次网络抖动都会中断整个流程，所以重试是刚需。
"""
import time
import logging
from typing import Iterator, Generator

from openai import OpenAI, APIError, RateLimitError, APITimeoutError, APIConnectionError

from src.config import config, get_client
from src.usage import Usage, extract_usage

logger = logging.getLogger(__name__)


def _price_dict() -> dict:
    m = config.model
    return {
        "input": m.price_input,
        "cache_hit": m.price_input_cache_hit,
        "output": m.price_output,
    }


def stream_chat(
    messages: list[dict],
    usage: Usage | None = None,
    max_retries: int = 3,
    temperature: float | None = None,
) -> Generator[str, None, None]:
    """流式对话。逐 token 产出文本。

    使用方式：
        for chunk in stream_chat(messages, usage):
            print(chunk, end="", flush=True)
    """
    client = get_client()
    temp = config.temperature if temperature is None else temperature
    emitted = False                      # 是否已经输出过内容（决定能否安全重试）

    for attempt in range(max_retries):
        try:
            stream = client.chat.completions.create(
                model=config.model.name,
                messages=messages,
                temperature=temp,
                stream=True,
                stream_options={"include_usage": True},
            )

            final_usage = None
            for chunk in stream:
                # 部分提供方的最后一个 chunk 携带用量
                if getattr(chunk, "usage", None):
                    final_usage = chunk.usage
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    emitted = True
                    yield content

            # 记录用量
            if usage is not None and final_usage is not None:
                p = getattr(final_usage, "prompt_tokens", 0) or 0
                c = getattr(final_usage, "completion_tokens", 0) or 0
                hit = getattr(final_usage, "prompt_cache_hit_tokens", 0) or 0
                usage.add(p, c, hit, _price_dict())

            return                       # 正常结束

        except (RateLimitError,) as e:
            if emitted:
                # ⚠️ 已经输出过内容，重试会导致前端看到重复内容
                raise RuntimeError(f"限流，但已输出部分内容，无法安全重试：{e}") from e
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(f"触发限流，{wait}s 后重试（{attempt + 1}/{max_retries}）")
            time.sleep(wait)

        except (APITimeoutError, APIConnectionError) as e:
            if emitted:
                raise RuntimeError(f"连接异常，但已输出部分内容：{e}") from e
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(f"连接异常，{wait}s 后重试：{e}")
            time.sleep(wait)

        except APIError as e:
            status = getattr(e, "status_code", None)
            # 4xx 通常是请求本身有问题，重试无用
            if status and 400 <= status < 500:
                logger.error(f"客户端错误 {status}，不重试：{e}")
                raise
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(f"服务端错误 {status}，{wait}s 后重试")
            time.sleep(wait)


def simple_chat(messages: list[dict], usage: Usage | None = None,
                temperature: float | None = None) -> str:
    """非流式对话，返回完整文本。适合脚本化调用。"""
    client = get_client()
    temp = config.temperature if temperature is None else temperature

    resp = client.chat.completions.create(
        model=config.model.name,
        messages=messages,
        temperature=temp,
    )
    p, c, hit = extract_usage(resp)
    if usage is not None:
        usage.add(p, c, hit, _price_dict())
    return resp.choices[0].message.content


def call_with_usage(messages: list[dict], **kwargs):
    """需要原始响应对象时用这个（比如要 tool_calls）。"""
    client = get_client()
    return client.chat.completions.create(
        model=config.model.name,
        messages=messages,
        temperature=kwargs.pop("temperature", config.temperature),
        **kwargs,
    )
