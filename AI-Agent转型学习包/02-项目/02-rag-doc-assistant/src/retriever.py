"""检索器：向量检索 + BM25 关键词检索，用 RRF 融合。

## 为什么要融合，而不能直接把分数相加？

因为两个分数量纲不同。向量余弦相似度在 [-1, 1]，BM25 分数可以到几十。
直接相加，BM25 会碾压向量分。归一化又很麻烦（BM25 分数没有上界）。

## RRF（Reciprocal Rank Fusion，倒数排名融合）

思路极其简单粗暴，但效果出奇地好：

    每个文档的最终分 = Σ 1 / (k + rank_i)
                        i 为各检索器

其中 rank 是文档在该检索器里的排名（从 1 开始），k 通常取 60。

**精髓在于：它只用排名，不用原始分数。** 所以不需要归一化，
不怕分数量纲不同。这是工程上非常聪明的做法。

举个例子（k=60）：
    文档 A：向量排名 1，BM25 排名 5 → 1/61 + 1/65 ≈ 0.0318
    文档 B：向量排名 3，BM25 排名 2 → 1/63 + 1/62 ≈ 0.0320
    → B 略胜，因为它在两个检索器里都排得靠前

"两个都认可"的文档会浮上来，"只有一个认可"的会被压下去——这正是我们要的。
"""
import logging

from src.config import config
from src.store import VectorStore, Chunk
from src.bm25 import BM25
from src.embedder import embed_query

logger = logging.getLogger(__name__)


class Retriever:
    """统一的检索入口。

    初始化时会加载全部片段建 BM25 索引。数据量大时这一步会慢，
    生产环境应该把 BM25 索引持久化（比如存到磁盘），而不是每次重建。
    """

    def __init__(self, store: VectorStore, use_hybrid: bool | None = None):
        self.store = store
        self.use_hybrid = config.use_hybrid if use_hybrid is None else use_hybrid

        # BM25 需要一个全量片段快照
        self._all_chunks = store.all_chunks()
        self._bm25 = BM25(self._all_chunks) if self._all_chunks else None
        # id → chunk 的映射，融合时用来还原片段
        self._by_id = {c.id: c for c in self._all_chunks}

        logger.info(
            f"检索器就绪：{len(self._all_chunks)} 个片段，"
            f"混合检索={'开' if self.use_hybrid else '关'}"
        )

    # ------------------------------------------------------------ 公开接口
    def retrieve(self, query: str, top_k: int | None = None) -> list[Chunk]:
        """检索入口。返回融合排序后的片段列表。"""
        top_k = top_k or config.top_k

        # 1) 向量检索
        q_vec = embed_query(query)
        vec_hits = self.store.search_vector(q_vec, top_k=config.vector_top_k)

        if not self.use_hybrid or self._bm25 is None:
            return vec_hits[:top_k]

        # 2) 关键词检索
        bm25_hits = self._bm25.search(query, top_k=config.bm25_top_k)

        # 3) RRF 融合
        fused = self._rrf_fuse([vec_hits, bm25_hits], top_k=top_k)
        logger.debug(
            f"召回：向量 {len(vec_hits)} 条 / BM25 {len(bm25_hits)} 条 "
            f"→ 融合后 {len(fused)} 条"
        )
        return fused

    def retrieve_debug(self, query: str, top_k: int = 5) -> dict:
        """调试用：返回各检索器的原始结果，用于对比"谁召回了什么"。

        排障必备。当答案不对时，你要能一眼看出：
            是压根没召回（检索问题）？还是召回了但排在后面（排序问题）？
        """
        q_vec = embed_query(query)
        vec_hits = self.store.search_vector(q_vec, top_k=config.vector_top_k)
        bm25_hits = self._bm25.search(query, top_k=config.bm25_top_k) if self._bm25 else []
        fused = self._rrf_fuse([vec_hits, bm25_hits], top_k=top_k)

        return {
            "query": query,
            "vector": [(c.cite_label(), round(c.score, 4)) for c in vec_hits],
            "bm25": [(c.cite_label(), round(c.score, 4)) for c in bm25_hits],
            "fused": [(c.cite_label(), round(c.score, 6)) for c in fused],
        }

    # ------------------------------------------------------------ 融合
    def _rrf_fuse(self, result_lists: list[list[Chunk]], top_k: int) -> list[Chunk]:
        """RRF 融合。只用排名，不用分数。"""
        k = config.rrf_k
        fused_score: dict[int, float] = {}
        chunk_map: dict[int, Chunk] = {}

        for results in result_lists:
            for rank, chunk in enumerate(results, start=1):
                fused_score[chunk.id] = fused_score.get(chunk.id, 0.0) + 1.0 / (k + rank)
                # 保留第一次出现的副本（内容是同一份，无所谓用哪个）
                chunk_map.setdefault(chunk.id, chunk)

        ranked = sorted(fused_score.items(), key=lambda kv: -kv[1])[:top_k]

        out: list[Chunk] = []
        for cid, score in ranked:
            src = chunk_map[cid]
            out.append(Chunk(
                id=src.id, doc_name=src.doc_name, chunk_index=src.chunk_index,
                content=src.content, score=score,
            ))
        return out

    def rebuild(self):
        """重新加载索引（新增文档后调用）。"""
        self._all_chunks = self.store.all_chunks()
        self._bm25 = BM25(self._all_chunks) if self._all_chunks else None
        self._by_id = {c.id: c for c in self._all_chunks}

    def stats(self) -> str:
        docs = self.store.list_docs()
        lines = [f"索引文档 {len(docs)} 份，片段 {self.store.count()} 条："]
        for name, cnt in docs:
            lines.append(f"  - {name}  ({cnt} 片)")
        return "\n".join(lines)
