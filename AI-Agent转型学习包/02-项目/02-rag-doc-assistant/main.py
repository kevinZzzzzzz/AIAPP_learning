#!/usr/bin/env python3
"""RAG 文档助手 CLI —— 模块 03 的产出项目。

用法：
    # 1. 索引文档（首次必须先做，之后新增文档再跑一次即可）
    uv run main.py index ./data

    # 2. 单次提问
    uv run main.py ask "退款需要几天到账？"

    # 3. 交互式问答（连续追问）
    uv run main.py chat

    # 4. 看检索过程（排障用，强烈建议多做）
    uv run main.py debug "退款需要几天到账？"

    # 5. 查看索引状态 / 清空
    uv run main.py stats
    uv run main.py reset
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt

from src.config import config
from src.store import VectorStore
from src.ingest import ingest_dir, ingest_file
from src.rag import RAGAssistant

console = Console()
PROJECT_ROOT = Path(__file__).parent


def _setup_logging(verbose: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s | %(message)s",
    )
    # 压掉第三方库的噪声日志
    for noisy in ("httpx", "openai", "jieba"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_store() -> VectorStore:
    """打开向量库，并校验 embedding 模型一致性。"""
    db_path = PROJECT_ROOT / config.db_path
    store = VectorStore(str(db_path), dim=config.embed.dim)

    if not store.check_embedding_model(config.embed.name):
        console.print(
            Panel(
                f"检测到 embedding 模型已变更！\n"
                f"当前：{config.embed.name}\n"
                f"建库时：{store.get_meta('embedding_model')}\n\n"
                f"向量维度不同，旧向量无法与新查询比较。\n"
                f"请执行 [bold]uv run main.py reset[/bold] 后重新索引。",
                title="⚠️ 模型不一致", border_style="red",
            )
        )
        sys.exit(1)

    return store


# ---------------------------------------------------------------- 子命令
def cmd_index(args):
    """索引文档"""
    store = get_store()
    target = Path(args.path)
    if not target.is_absolute():
        target = PROJECT_ROOT / target

    if not target.exists():
        console.print(f"[red]路径不存在：{target}[/red]")
        sys.exit(1)

    console.print(f"[bold]开始索引：{target}[/bold]  （强制重建={args.force}）")
    if target.is_file():
        n = ingest_file(store, target, force=args.force)
    else:
        n = ingest_dir(store, target, force=args.force)

    console.print(f"\n[green]✓ 本次新增 {n} 个片段[/green]")
    _print_stats(store)


def cmd_stats(args):
    store = get_store()
    _print_stats(store)


def _print_stats(store: VectorStore):
    docs = store.list_docs()
    total = store.count()
    if not docs:
        console.print("[yellow]索引为空。先执行：uv run main.py index ./data[/yellow]")
        return

    table = Table(title=f"索引状态（共 {total} 片段）")
    table.add_column("文档", style="cyan")
    table.add_column("片段数", justify="right", style="green")
    for name, cnt in docs:
        table.add_row(name, str(cnt))
    console.print(table)
    console.print(
        f"[dim]Embedding 模型：{store.get_meta('embedding_model')} | "
        f"库文件：{config.db_path}[/dim]"
    )


def cmd_reset(args):
    store = get_store()
    n = store.count()
    store.clear()
    console.print(f"[yellow]已清空 {n} 个片段。[/yellow]")


def cmd_ask(args):
    """单次提问"""
    store = get_store()
    if store.count() == 0:
        console.print("[yellow]索引为空。先执行：uv run main.py index ./data[/yellow]")
        sys.exit(1)

    assistant = RAGAssistant(store)
    question = " ".join(args.question)

    console.print(f"\n[bold cyan]问题：[/bold cyan]{question}\n")
    console.print("[bold]回答：[/bold]")

    # 流式输出，边生成边显示
    holder = {}

    def on_chunk(text: str):
        console.print(text, end="")

    try:
        ans = assistant.ask(question, stream_callback=on_chunk)
        holder["ans"] = ans
        console.print()
    except Exception as ex:                     # noqa: BLE001
        console.print(f"[red]生成失败：{ex}[/red]")
        sys.exit(1)

    ans = holder["ans"]
    console.print()
    console.print(Panel(ans.format_sources(), title="引用来源", border_style="dim"))
    console.print(
        f"[dim]用量：输入 {ans.prompt_tokens} / 输出 {ans.completion_tokens} token[/dim]"
    )


def cmd_debug(args):
    """展示检索过程"""
    store = get_store()
    assistant = RAGAssistant(store)
    question = " ".join(args.question)

    d = assistant.retriever.retrieve_debug(question, top_k=config.top_k)

    console.print(f"\n[bold cyan]查询：[/bold cyan]{question}\n")

    table = Table(title="融合结果（最终喂给模型）")
    table.add_column("排名", justify="right")
    table.add_column("来源")
    table.add_column("RRF 分", justify="right")

    all_labels = set()
    for label, _ in d["vector"]:
        all_labels.add(label)
    for label, _ in d["bm25"]:
        all_labels.add(label)

    # 标注每条命中来自哪些检索器
    vec_rank = {label: i for i, (label, _) in enumerate(d["vector"], 1)}
    bm_rank = {label: i for i, (label, _) in enumerate(d["bm25"], 1)}

    for i, (label, score) in enumerate(d["fused"], start=1):
        tags = []
        if label in vec_rank:
            tags.append(f"向量#{vec_rank[label]}")
        if label in bm_rank:
            tags.append(f"BM25#{bm_rank[label]}")
        table.add_row(str(i), f"{label}  [dim]({'、'.join(tags)})[/dim]", f"{score:.6f}")
    console.print(table)

    console.print("\n[bold]向量召回 Top：[/bold]")
    for label, score in d["vector"][:5]:
        console.print(f"  {score:>8.4f}  {label}")
    console.print("\n[bold]BM25 召回 Top：[/bold]")
    for label, score in d["bm25"][:5]:
        console.print(f"  {score:>8.4f}  {label}")

    console.print(
        "\n[dim]排查思路：如果正确答案没出现在上面任何一张表里，"
        "说明是[检索]问题（切片/模型/召回数）；\n"
        "如果出现了但排在很后面或没进回答，说明是[排序/生成]问题。[/dim]"
    )


def cmd_chat(args):
    """交互式问答"""
    store = get_store()
    if store.count() == 0:
        console.print("[yellow]索引为空。先执行：uv run main.py index ./data[/yellow]")
        sys.exit(1)

    assistant = RAGAssistant(store)
    console.print(
        Panel(
            "RAG 文档问答（交互模式）\n"
            "直接提问即可。命令：/sources 详细来源  /debug 上次检索过程  /exit 退出",
            title="📚 RAG Assistant", border_style="cyan",
        )
    )
    last = None
    while True:
        try:
            q = Prompt.ask("\n[bold cyan]你[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]再见[/dim]")
            break

        q = q.strip()
        if not q:
            continue
        if q in ("/exit", "/quit", "exit", "quit"):
            break
        if q == "/sources":
            if last:
                console.print(Panel(last.format_sources(), title="引用来源"))
            else:
                console.print("[dim]还没有提问过[/dim]")
            continue
        if q == "/debug":
            if last:
                d = assistant.retriever.retrieve_debug(last.question, top_k=config.top_k)
                for label, score in d["fused"]:
                    console.print(f"  {score:.6f}  {label}")
            else:
                console.print("[dim]还没有提问过[/dim]")
            continue

        console.print("\n[bold]助手[/bold]")
        try:
            ans = assistant.ask(q, stream_callback=lambda t: console.print(t, end=""))
            last = ans
            console.print()
            console.print(
                f"[dim]引用 {len(ans.sources)} 段 | "
                f"token 输入{ans.prompt_tokens} 输出{ans.completion_tokens}[/dim]"
            )
        except Exception as ex:                 # noqa: BLE001
            console.print(f"[red]出错：{ex}[/red]")


# ---------------------------------------------------------------- 入口
def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG 文档问答助手 —— 模块 03 配套项目",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index", help="索引文档（文件或目录）")
    p_idx.add_argument("path", help="文件或目录路径")
    p_idx.add_argument("-f", "--force", action="store_true", help="强制重建已有文档")
    p_idx.set_defaults(func=cmd_index)

    p_ask = sub.add_parser("ask", help="单次提问")
    p_ask.add_argument("question", nargs="+", help="问题内容")
    p_ask.set_defaults(func=cmd_ask)

    p_dbg = sub.add_parser("debug", help="查看检索过程")
    p_dbg.add_argument("question", nargs="+", help="问题内容")
    p_dbg.set_defaults(func=cmd_debug)

    p_chat = sub.add_parser("chat", help="交互式问答")
    p_chat.set_defaults(func=cmd_chat)

    p_stat = sub.add_parser("stats", help="查看索引状态")
    p_stat.set_defaults(func=cmd_stats)

    p_reset = sub.add_parser("reset", help="清空索引")
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    _setup_logging(args.verbose)
    try:
        args.func(args)
    except KeyboardInterrupt:
        console.print("\n[dim]已中断[/dim]")


if __name__ == "__main__":
    main()
