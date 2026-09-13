"""文档切片与入库（Ingestion Pipeline）。

流程：读文件 → 清洗 → 切片 → 向量化 → 入库

切片是 RAG 里最影响效果、也最容易被忽视的一步。
切大了：一片里混了多个主题，向量语义被"平均"掉，检索不准。
切小了：语义不完整，模型拼不出答案。
"""
import re
import logging
from pathlib import Path

from src.config import config
from src.embedder import embed_texts
from src.store import VectorStore

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIX = {".md", ".txt", ".markdown"}


# ---------------------------------------------------------------- 读取
def read_file(path: Path) -> str:
    """读文本文件。优先 UTF-8，失败退回 GBK（中文 Windows 文件常见）。"""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk", errors="ignore")


def clean_text(text: str) -> str:
    """清洗：去掉噪声，但不要破坏语义。

    保守原则：只做无损操作。不要在这里"聪明地"删段落——
    你以为在去噪，可能把答案删掉了。
    """
    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去掉 markdown 图片语法里的路径（保留 alt 文字，它有信息量）
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 连续 3 个以上空行压成 2 个（保留段落结构，不要全删）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------- 切片
def split_text(text: str,
               chunk_size: int | None = None,
               chunk_overlap: int | None = None) -> list[str]:
    """按结构优先、长度兜底的方式切片。

    策略（按优先级）：
    1) 优先在 Markdown 标题处切 —— 天然是语义边界，切出来的片最干净
    2) 合并过短的相邻小节 —— 标题切分会产出大量碎片，碎片检索不准
    3) 段落仍然过长，按句子切（句号/问号/感叹号/换行）
    4) 加 overlap：相邻片重叠若干字符，避免答案正好卡在边界上

    这是"递归字符切片"的手写版，也是 LangChain RecursiveCharacterTextSplitter
    的核心思路。手写一遍你就明白它做了什么，也知道它做错了什么。
    """
    chunk_size = chunk_size or config.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else config.chunk_overlap

    # 第一层：按 markdown 标题切大块
    sections = _split_by_headings(text)

    chunks: list[str] = []
    for sec in sections:
        if len(sec) <= chunk_size:
            chunks.append(sec)
        else:
            chunks.extend(_split_long_section(sec, chunk_size, overlap))

    # 第二层：合并过短的碎片。
    # 为什么必须做：按标题切分时，"### 2.1 注册方式"这种小节可能只有 100 字，
    # 单独成片会导致语义信息量不足、检索时谁都匹配不上。这是切片最常见的坑。
    chunks = _merge_short_chunks(chunks, chunk_size)

    # 过滤过短的碎片（合并后仍太短，通常是孤立标题、目录残留）
    chunks = [c.strip() for c in chunks if len(c.strip()) >= config.min_chunk_size]

    # 给每个 chunk 加 overlap 前缀（从上一片尾部借 characters）
    return _apply_overlap(chunks, overlap)


def _merge_short_chunks(chunks: list[str], chunk_size: int) -> list[str]:
    """合并过短的相邻片段。

    规则：如果【当前片】与【下一片】拼起来不超过 chunk_size，
    且当前片不足 chunk_size 的一半，就合并。

    合并上限也是 chunk_size —— 不能为了消除碎片把片切得过大，
    那样又回到了"一片混多主题"的老问题。
    """
    if len(chunks) <= 1:
        return chunks

    half = chunk_size // 2
    out: list[str] = []
    buf = chunks[0]

    for nxt in chunks[1:]:
        # 拼起来不超限 且 当前缓冲区偏短 → 合并
        if buf and len(buf) < half and len(buf) + len(nxt) + 1 <= chunk_size:
            buf = buf + "\n" + nxt
        else:
            out.append(buf)
            buf = nxt
    if buf:
        out.append(buf)
    return out


def _split_by_headings(text: str) -> list[str]:
    """按 markdown 标题（# ~ ######）切分。没有标题就整篇当一块。"""
    lines = text.split("\n")
    sections: list[str] = []
    buf: list[str] = []

    for line in lines:
        if re.match(r"^#{1,6}\s+\S", line):
            # 遇到新标题，先把缓冲区收起来
            if buf:
                block = "\n".join(buf).strip()
                if block:
                    sections.append(block)
                buf = []
        buf.append(line)

    if buf:
        block = "\n".join(buf).strip()
        if block:
            sections.append(block)

    return sections or [text]


def _split_long_section(section: str, chunk_size: int, overlap: int) -> list[str]:
    """超长段落 → 先按空行切段 → 还长就按句子切 → 再按长度硬切兜底。"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]

    pieces: list[str] = []
    for p in paragraphs:
        if len(p) <= chunk_size:
            pieces.append(p)
        else:
            pieces.extend(_split_by_sentence(p, chunk_size))

    # 合并相邻小片段，凑到接近 chunk_size（避免产生大量碎片）
    merged: list[str] = []
    buf = ""
    for piece in pieces:
        if not buf:
            buf = piece
        elif len(buf) + len(piece) + 1 <= chunk_size:
            buf += "\n" + piece
        else:
            merged.append(buf)
            buf = piece
    if buf:
        merged.append(buf)

    # 兜底：单个句子仍超长（比如没有标点的长表格），按字符硬切
    final: list[str] = []
    for m in merged:
        if len(m) <= chunk_size:
            final.append(m)
        else:
            for i in range(0, len(m), chunk_size):
                final.append(m[i:i + chunk_size])
    return final


def _split_by_sentence(text: str, chunk_size: int) -> list[str]:
    """按中英文句末标点切句，再按长度合并成不超过 chunk_size 的块。"""
    sentences = re.split(r"(?<=[。！？!?；;])\s*", text)
    sentences = [s for s in sentences if s.strip()]

    out: list[str] = []
    buf = ""
    for s in sentences:
        if len(buf) + len(s) <= chunk_size:
            buf += s
        else:
            if buf:
                out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    """给每片加上前一片的尾部若干字符，缓解"答案卡在边界"的问题。

    注意：overlap 不是免费的——它会让索引体积和 embedding 成本增加
    overlap/chunk_size 的比例。一般 10%~20% 比较合适。
    """
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        out.append(prev_tail + "\n" + chunks[i])
    return out


# ---------------------------------------------------------------- 入库
def ingest_file(store: VectorStore, path: Path, force: bool = False) -> int:
    """把单个文件灌进向量库。返回写入的片段数。

    force=False 时若该文档已存在则跳过（避免重复索引、重复花钱）。
    """
    doc_name = path.name

    existing = dict(store.list_docs())
    if doc_name in existing and not force:
        logger.info(f"跳过（已索引 {existing[doc_name]} 片）：{doc_name}")
        return 0
    if doc_name in existing and force:
        store.delete_doc(doc_name)

    text = clean_text(read_file(path))
    if len(text) < config.min_chunk_size:
        logger.warning(f"内容太短，跳过：{doc_name}")
        return 0

    chunks = split_text(text)
    if not chunks:
        logger.warning(f"切片后为空，跳过：{doc_name}")
        return 0

    logger.info(f"切片完成：{doc_name} → {len(chunks)} 片，开始向量化…")
    vectors = embed_texts(chunks)

    items = [(i, c, v) for i, (c, v) in enumerate(zip(chunks, vectors))]
    store.add_chunks(doc_name, items, meta={"source": str(path)})
    logger.info(f"入库完成：{doc_name}（{len(chunks)} 片）")
    return len(chunks)


def ingest_dir(store: VectorStore, dir_path: Path,
               force: bool = False, recursive: bool = True) -> int:
    """批量索引一个目录下的所有 .md / .txt 文件。"""
    pattern = "**/*" if recursive else "*"
    files = sorted(
        p for p in dir_path.glob(pattern)
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIX
    )
    if not files:
        logger.warning(f"目录下没有可索引的文本文件：{dir_path}")
        return 0

    total = 0
    for p in files:
        try:
            total += ingest_file(store, p, force=force)
        except Exception as ex:                      # noqa: BLE001
            # 单个文件失败不应该中断整批任务
            logger.error(f"索引失败 {p.name}：{ex}")
    return total
