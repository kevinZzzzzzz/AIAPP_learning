"""Embedding 封装：批量调用 + 重试 + 自动分批 + 成本统计。

三个必须处理的现实问题：
1. 服务商有单次条数上限（百炼 v4 是 10 条），必须自动分批
2. 网络会抖，必须重试
3. 调用要花钱，必须统计
"""
import time
import logging

from src.config import config, get_embed_client

logger = logging.getLogger(__name__)


class EmbedError(Exception):
    """向量化失败"""


def embed_texts(texts: list[str], max_retries: int = 3) -> list[list[float]]:
    """把一批文本转成向量，自动按服务商限制分批。

    返回顺序与输入严格一一对应（这一点很重要，
    顺序错了会导致"问题配错答案"，且不报错，极难排查）。
    """
    if not texts:
        return []

    client = get_embed_client()
    e = config.embed
    out: list[list[float]] = []

    for i in range(0, len(texts), e.batch_size):
        batch = texts[i:i + e.batch_size]
        out.extend(_embed_batch(client, batch, e, max_retries))

    return out


def _embed_batch(client, batch: list[str], e, max_retries: int) -> list[list[float]]:
    """单批调用，带指数退避重试。"""
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(
                model=e.name,
                input=batch,
                # 百炼要求显式指定维度；OpenAI 用 dimensions 参数
                dimensions=e.dim,
                encoding_format="float",
            )
            # 按 index 排序！API 不保证返回顺序，虽然实际上通常有序，
            # 但显式排序是零成本的保险。
            items = sorted(resp.data, key=lambda d: d.index)
            return [d.embedding for d in items]

        except Exception as ex:                     # noqa: BLE001
            last_err = ex
            msg = str(ex)
            # 参数错误重试无用，直接抛出
            if "400" in msg or "invalid" in msg.lower():
                raise EmbedError(
                    f"Embedding 请求被拒绝（通常是超批次上限或维度不对）：{msg}"
                ) from ex
            if attempt == max_retries - 1:
                break
            wait = 2 ** attempt
            logger.warning(f"Embedding 失败，{wait}s 后重试（{attempt + 1}/{max_retries}）：{ex}")
            time.sleep(wait)

    raise EmbedError(f"Embedding 连续 {max_retries} 次失败：{last_err}")


def embed_query(text: str) -> list[float]:
    """单条查询向量化。

    注意：查询和入库用的是同一个方法、同一个模型。
    如果这里换了模型，检索结果会静默变差——查不出错但答非所问。
    """
    return embed_texts([text])[0]
