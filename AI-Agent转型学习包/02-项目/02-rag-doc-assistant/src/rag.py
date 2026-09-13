"""RAG 问答主流程：检索 → 组装 Prompt → 生成 → 带引用回答。

这个文件是整个项目的"大脑"，其他文件都是它的零件。
读懂 ask() 函数，你就读懂了 RAG 的全貌。
"""
import logging
from dataclasses import dataclass, field

from src.config import config, get_gen_client
from src.retriever import Retriever
from src.store import Chunk

logger = logging.getLogger(__name__)


@dataclass
class Answer:
    """一次问答的完整结果。把中间产物都留下来，便于调试和前端展示。"""
    question: str
    text: str                              # 模型生成的答案
    sources: list[Chunk] = field(default_factory=list)   # 引用的片段
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def format_sources(self) -> str:
        """把引用来源格式化成可读文本。"""
        if not self.sources:
            return "（无引用）"
        lines = []
        for i, c in enumerate(self.sources, start=1):
            preview = c.content.replace("\n", " ")[:80]
            lines.append(f"[{i}] {c.cite_label()}：{preview}…")
        return "\n".join(lines)


def build_context(chunks: list[Chunk]) -> str:
    """把检索到的片段拼成【参考资料】块，带编号。

    编号是给模型看的，让它能写 [1] [2] 这种引用。
    最后做一次长度裁剪：宁可少放几段，也不要因为超长导致请求失败。
    """
    parts: list[str] = []
    used = 0
    for i, c in enumerate(chunks, start=1):
        block = f"[{i}] 来源：{c.cite_label()}\n{c.content}"
        if used + len(block) > config.max_context_chars:
            logger.warning(f"上下文达到上限，丢弃剩余 {len(chunks) - i + 1} 段")
            break
        parts.append(block)
        used += len(block)
    return "\n\n---\n\n".join(parts)


class RAGAssistant:
    """RAG 文档问答助手。"""

    def __init__(self, store, use_hybrid: bool | None = None):
        from src.store import VectorStore
        if isinstance(store, VectorStore):
            self.store = store
        else:
            self.store = VectorStore(store, dim=config.embed.dim)

        self.retriever = Retriever(self.store, use_hybrid=use_hybrid)
        self._history: list[dict] = []

    # ------------------------------------------------------------ 主流程
    def ask(self, question: str, top_k: int | None = None,
            stream_callback=None) -> Answer:
        """完整 RAG 流程。

        Args:
            question: 用户问题
            top_k: 覆盖默认召回数
            stream_callback: 传入则走流式，逐段回调文本
        """
        top_k = top_k or config.top_k

        # ---- 1. 检索 ----
        chunks = self.retriever.retrieve(question, top_k=top_k)
        if not chunks:
            return Answer(
                question=question,
                text="知识库为空或没有检索到相关内容。请先索引文档。",
                sources=[],
            )

        # ---- 2. 组装 Prompt ----
        context = build_context(chunks)
        user_msg = (
            f"【参考资料】\n{context}\n\n"
            f"【问题】\n{question}\n\n"
            f"请依据上述资料回答，并用 [1][2] 标注引用来源。"
        )

        messages = [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": user_msg},
        ]

        # ---- 3. 生成 ----
        client = get_gen_client()
        m = config.gen_model

        if stream_callback:
            resp_text, p_tok, c_tok = self._generate_stream(client, messages, stream_callback)
        else:
            resp = client.chat.completions.create(
                model=m.name, messages=messages, temperature=config.temperature,
            )
            resp_text = resp.choices[0].message.content or ""
            p_tok = getattr(resp.usage, "prompt_tokens", 0) or 0
            c_tok = getattr(resp.usage, "completion_tokens", 0) or 0

        # ---- 4. 记录历史（多轮追问时，把上一轮的问题也带上）----
        self._history.append({"q": question, "a": resp_text})

        return Answer(
            question=question, text=resp_text, sources=chunks,
            prompt_tokens=p_tok, completion_tokens=c_tok,
        )

    def _generate_stream(self, client, messages, callback):
        """流式生成，边收边回调。"""
        stream = client.chat.completions.create(
            model=config.gen_model.name,
            messages=messages,
            temperature=config.temperature,
            stream=True,
            stream_options={"include_usage": True},
        )
        buf: list[str] = []
        usage = None
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if not chunk.choices:
                continue
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                buf.append(content)
                callback(content)

        p_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        c_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        return "".join(buf), p_tok, c_tok

    # ------------------------------------------------------------ 辅助
    def multi_query_rewrite(self, question: str, n: int = 3) -> list[str]:
        """多查询改写（进阶技巧）。

        用户的问题往往不好检索（"那个怎么弄？"）。
        先让模型把问题改写成 N 个不同角度的检索式，分别检索再合并，
        能显著提升召回率。代价是多花一次模型调用。

        这是"查询扩展"最简单有效的实现，值得在生产里用。
        """
        client = get_gen_client()
        prompt = (
            f"请把下面的问题改写成 {n} 个不同角度的检索查询，"
            f"每行一个，不要编号，不要解释。\n\n问题：{question}"
        )
        resp = client.chat.completions.create(
            model=config.gen_model.name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,     # 改写要发散，温度高一点
        )
        text = resp.choices[0].message.content or ""
        queries = [line.strip() for line in text.split("\n") if line.strip()]
        # 去重，并始终保留原问题
        seen = {question}
        out = [question]
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return out[:n + 1]

    def ask_with_rewrite(self, question: str, top_k: int | None = None) -> Answer:
        """带查询改写的问答：先扩展问题 → 多路检索 → RRF 合并 → 生成。"""
        queries = self.multi_query_rewrite(question)
        logger.info(f"查询改写：{queries}")

        # 每一路都检索，然后一起融合
        all_hits: list[list[Chunk]] = []
        for q in queries:
            hits = self.retriever.retrieve(q, top_k=config.vector_top_k)
            all_hits.append(hits)

        fused = self.retriever._rrf_fuse(all_hits, top_k=top_k or config.top_k)

        context = build_context(fused)
        user_msg = (
            f"【参考资料】\n{context}\n\n【问题】\n{question}\n\n"
            f"请依据上述资料回答，并用 [1][2] 标注引用来源。"
        )
        client = get_gen_client()
        resp = client.chat.completions.create(
            model=config.gen_model.name,
            messages=[
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=config.temperature,
        )
        return Answer(
            question=question,
            text=resp.choices[0].message.content or "",
            sources=fused,
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
        )
