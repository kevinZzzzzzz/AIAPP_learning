"""BM25 关键词检索：向量检索的补充手段。

为什么需要它：
    向量检索擅长"意思相近"，但会漏掉**精确字符串**。
    用户问"ERR_502_TIMEOUT 怎么处理"，向量检索可能召回一堆"错误处理"的段落，
    却漏掉真正写了这个错误码的那一段。BM25 能精确命中。

什么时候 BM25 会赢：型号、错误码、人名、SKU、专有名词、数字。
什么时候向量会赢：口语化提问、同义改写、跨语言。

所以成熟的 RAG 系统两个都要 —— 这叫**混合检索（Hybrid Search）**。

BM25 是什么（白话版）：
    它给每个词打分，分三步——
    1. 这个词在这段里出现几次？（TF，但不是线性加分，出现 5 次不等于 5 倍）
    2. 这个词在全库里稀有吗？（IDF，越稀有越值钱，"的"这种词几乎没分）
    3. 这段比平均长度长吗？（长文档天然包含更多词，要按长度惩罚）
    三项一乘，就是 BM25 分数。
"""
import math
import logging
from collections import Counter

from src.store import Chunk

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    """中文分词。

    中文不能按空格切（"今天天气"是一个词还是四个字？）。
    这里用 jieba 做分词。如果没装 jieba，退回字符 bigram——
    比单字好（"天气"能匹配上），比 jieba 差（"今天天气"切不出准确词边界）。
    """
    try:
        import jieba
        # 静默模式，避免每次启动打印一堆加载日志
        jieba.setLogLevel(logging.WARNING)
        tokens = list(jieba.cut(text))
    except ImportError:
        # 退化方案：中文取 2-gram，英文数字按词
        tokens = _bigram_fallback(text)

    # 过掉纯标点和空白，统一小写
    return [t.strip().lower() for t in tokens
            if t.strip() and not _is_punct(t)]


def _is_punct(s: str) -> bool:
    return all(not c.isalnum() for c in s)


def _bigram_fallback(text: str) -> list[str]:
    """没装 jieba 时的兜底：英文按词、中文按 2-gram"""
    import re as _re
    tokens: list[str] = []
    for seg in _re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+", text):
        if _re.match(r"[a-zA-Z0-9_]+", seg):
            tokens.append(seg)
        else:
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    return tokens


class BM25:
    """Okapi BM25 实现。参数 k1=1.5, b=0.75 是行业默认值。

    k1：词频饱和速度。调大 → 出现次数多更占优；1.2~2.0 常见。
    b：长度归一化强度。0=不归一化，1=完全归一化；0.75 是默认。
    """

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self.doc_tokens: list[list[str]] = [tokenize(c.content) for c in chunks]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0

        # 文档频率 df[term] = 包含该词的文档数
        self.df: Counter = Counter()
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] += 1

        self.n = len(chunks)
        # 预计算 TF 表，避免每次查询重新数
        self.tf: list[Counter] = [Counter(t) for t in self.doc_tokens]

    def _idf(self, term: str) -> float:
        """IDF：词越稀有分越高。

        用带 +0.5 平滑的标准形式，避免除零和负值（老式 log(N/df)
        在词出现在超过半数文档时会变负数，那是错的）。
        """
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 12) -> list[Chunk]:
        """检索。返回带 BM25 分数的片段，按分降序。"""
        if not self.chunks:
            return []

        q_terms = tokenize(query)
        if not q_terms:
            return []

        scores = [0.0] * self.n
        for term in q_terms:
            if term not in self.df:
                continue                      # 全库都没这个词，跳过
            idf = self._idf(term)
            for i in range(self.n):
                f = self.tf[i].get(term, 0)
                if f == 0:
                    continue
                # BM25 核心公式
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / (self.avgdl or 1))
                scores[i] += idf * (f * (self.k1 + 1)) / denom

        ranked = sorted(range(self.n), key=lambda i: -scores[i])[:top_k]
        out: list[Chunk] = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            c = self.chunks[i]
            out.append(Chunk(
                id=c.id, doc_name=c.doc_name, chunk_index=c.chunk_index,
                content=c.content, score=scores[i],
            ))
        return out
