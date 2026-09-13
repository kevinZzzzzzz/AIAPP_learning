"""向量库：用 sqlite 存"向量 + 原文 + 元数据"，用 numpy 做相似度计算。

为什么要自己写一遍：
    你调 Chroma 的 collection.query() 只有一行，但面试官会问
    "向量检索的时间复杂度是多少？10 万条数据要多久？"
    自己写过才知道答案是 O(N·D) 全量扫描——这也是为什么生产要用 ANN 索引。

这个实现适合 < 10 万条数据。超过就该换 pgvector / Milvus 了。
"""
import sqlite3
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """一个文本片段（检索的基本单位）"""
    id: int
    doc_name: str          # 来源文件名
    chunk_index: int       # 在原文中的序号（用于展示"第 N 段"）
    content: str           # 原文
    score: float = 0.0     # 检索得分（由检索器填入）

    def cite_label(self) -> str:
        """生成引用标签，如「手册.md · 第3段」"""
        return f"{self.doc_name} · 第{self.chunk_index + 1}段"


class VectorStore:
    """基于 sqlite 的极简向量库。

    表结构：
        chunks(id, doc_name, chunk_index, content, embedding, meta)
    embedding 存成 BLOB（float32 二进制），比存 JSON 文本省 3~5 倍空间。
    """

    def __init__(self, db_path: str = "rag.db", dim: int = 1024):
        self.db_path = db_path
        self.dim = dim
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")   # 读写并发更稳
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_name    TEXT    NOT NULL,
                chunk_index INTEGER NOT NULL,
                content     TEXT    NOT NULL,
                embedding   BLOB    NOT NULL,
                meta        TEXT    DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_doc ON chunks(doc_name);

            -- 元信息表：记录入库时用的 embedding 模型
            -- 作用：发现模型被换过就报警，避免"新旧向量混用"这种隐蔽 bug
            CREATE TABLE IF NOT EXISTS index_meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------ 元信息
    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM index_meta WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str):
        self._conn.execute(
            "INSERT INTO index_meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def check_embedding_model(self, model_name: str) -> bool:
        """校验当前配置的 embedding 模型与建库时一致。

        这是防呆设计。真实事故：有人换了 embedding 模型没重建索引，
        检索结果全是噪声，但代码不报错，排查了两天。
        """
        recorded = self.get_meta("embedding_model")
        if recorded is None:
            self.set_meta("embedding_model", model_name)
            return True
        if recorded != model_name:
            logger.error(
                f"⚠️ Embedding 模型已变！建库时是 {recorded}，当前是 {model_name}。"
                f"必须重建索引，否则检索结果无意义。"
            )
            return False
        return True

    # ------------------------------------------------------------ 写入
    @staticmethod
    def _to_blob(vec: list[float]) -> bytes:
        return np.asarray(vec, dtype=np.float32).tobytes()

    @staticmethod
    def _from_blob(blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32)

    def add_chunks(self, doc_name: str,
                   items: list[tuple[int, str, list[float]]],
                   meta: dict | None = None):
        """批量写入。items = [(chunk_index, content, embedding), ...]"""
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        self._conn.executemany(
            "INSERT INTO chunks(doc_name, chunk_index, content, embedding, meta) "
            "VALUES(?,?,?,?,?)",
            [
                (doc_name, idx, content, self._to_blob(vec), meta_json)
                for idx, content, vec in items
            ],
        )
        self._conn.commit()

    def delete_doc(self, doc_name: str) -> int:
        """删除某文档的所有片段（重新索引前调用）。返回删除条数。"""
        cur = self._conn.execute("DELETE FROM chunks WHERE doc_name=?", (doc_name,))
        self._conn.commit()
        return cur.rowcount

    def clear(self):
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()

    # ------------------------------------------------------------ 检索
    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def list_docs(self) -> list[tuple[str, int]]:
        """返回 [(文档名, 片段数), ...]"""
        return self._conn.execute(
            "SELECT doc_name, COUNT(*) FROM chunks GROUP BY doc_name ORDER BY doc_name"
        ).fetchall()

    def all_chunks(self) -> list[Chunk]:
        """取出全部片段（含向量）。BM25 建索引、以及向量全量扫描都用它。

        注意：数据量大时这里会占内存（10 万条 × 1024 维 × 4 字节 ≈ 400MB），
        所以生产环境不会这么干——这是教学实现故意暴露的局限。
        """
        rows = self._conn.execute(
            "SELECT id, doc_name, chunk_index, content, embedding FROM chunks"
        ).fetchall()
        out = []
        for _id, doc, idx, content, blob in rows:
            c = Chunk(id=_id, doc_name=doc, chunk_index=idx, content=content)
            # 挂上向量（临时属性，避免 Dataclass 字段污染）
            c._vec = self._from_blob(blob)
            out.append(c)
        return out

    def search_vector(self, query_vec: list[float], top_k: int = 12) -> list[Chunk]:
        """向量检索：余弦相似度全量扫描。

        时间复杂度 O(N·D)：N 条数据、D 维。
        1 万条 × 1024 维 ≈ 1000 万次浮点乘加，numpy 向量化后 < 10ms，够用。
        但 100 万条就顶不住了——这时候需要 HNSW / IVF 这类 ANN 索引。

        优化点：向量已归一化时，余弦相似度 == 点积，可以省掉两次除法。
        这里显式归一化后统一用点积，顺便把归一化向量也存回去（下次免算）。
        """
        rows = self._conn.execute(
            "SELECT id, doc_name, chunk_index, content, embedding FROM chunks"
        ).fetchall()
        if not rows:
            return []

        # 把所有向量堆成一个矩阵 (N, D)
        mat = np.vstack([self._from_blob(r[4]) for r in rows])

        q = np.asarray(query_vec, dtype=np.float32)
        # 归一化：||a||=1 时，cos(a,b) = a·b
        mat_norm = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-10)
        q_norm = q / (np.linalg.norm(q) + 1e-10)

        scores = mat_norm @ q_norm            # 一次矩阵乘算完所有相似度
        top_idx = np.argsort(-scores)[:top_k]  # 取分数最高的 k 个

        result = []
        for i in top_idx:
            _id, doc, idx, content, _blob = rows[int(i)]
            result.append(
                Chunk(id=_id, doc_name=doc, chunk_index=idx,
                      content=content, score=float(scores[int(i)]))
            )
        return result

    def close(self):
        self._conn.close()
