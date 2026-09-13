"""CLI 多轮对话机器人 —— 项目 01 主程序。

用法：
    export PYTHONPATH=.                  # 让 import src.xxx 可用
    uv run main.py                       # 启动交互对话
    uv run main.py --once "你好"          # 单次提问
    uv run main.py --model pro           # 用更强的模型
    uv run main.py --plain               # 不用富文本渲染

交互命令：
    /exit      退出
    /clear     清空对话历史
    /stats     查看本次会话用量统计
    /summary   手动触发历史摘要压缩
    /help      显示帮助
"""
import sys
import argparse
import time

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from src.config import config, MODELS
from src.llm import stream_chat
from src.conversation import Conversation, summarize
from src.usage import Usage

console = Console()

BANNER = """[bold cyan]CLI Chatbot[/bold cyan] · 项目 01

模型：[yellow]{model}[/yellow]   温度：{temp}
命令：/exit 退出 · /clear 清空 · /stats 统计 · /summary 压缩历史 · /help 帮助
"""

HELP_TEXT = """
[b]可用命令[/b]
  /exit, /quit    退出程序
  /clear          清空当前对话历史
  /stats          查看本次会话的 token 与成本统计
  /summary        手动把早期对话压缩成摘要
  /model <key>    切换模型（flash / pro / ollama）
  /help           显示此帮助
"""


def run_once(prompt: str, conv: Conversation, usage: Usage, model_hint: str = "") -> str:
    """单次提问，用于脚本化调用。返回完整回复。"""
    conv.add_user(prompt)
    parts = []
    for chunk in stream_chat(conv.build_messages(), usage=usage):
        parts.append(chunk)
    reply = "".join(parts)
    conv.add_assistant(reply)
    return reply


def chat_loop(use_rich: bool = True):
    conv = Conversation(system_prompt=config.system_prompt, max_turns=config.max_turns)
    usage = Usage()

    if use_rich:
        console.print(BANNER.format(model=config.model.name, temp=config.temperature))

    while True:
        # ===== 读取输入 =====
        try:
            user_input = console.input("\n[bold green]你[/bold green] > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]已退出[/dim]")
            break

        if not user_input:
            continue

        # ===== 处理命令 =====
        if user_input.lower() in ("/exit", "/quit"):
            break
        if user_input == "/help":
            console.print(HELP_TEXT)
            continue
        if user_input == "/clear":
            conv.clear()
            usage.reset()
            console.print("[dim]对话历史已清空[/dim]")
            continue
        if user_input == "/stats":
            console.print(Panel(usage.summary(config.usd_to_cny), title="本次会话统计"))
            continue
        if user_input == "/summary":
            if conv.turn_count() < 2:
                console.print("[dim]对话太短，无需压缩[/dim]")
                continue
            with console.status("正在压缩历史..."):
                removed = conv.trim()
                if removed:
                    conv.set_summary(summarize(removed))
            console.print("[dim]历史已压缩为摘要[/dim]")
            continue
        if user_input.startswith("/model"):
            parts = user_input.split()
            if len(parts) == 2 and parts[1] in MODELS:
                config.model_key = parts[1]          # type: ignore
                console.print(f"[dim]已切换到 {config.model.name}[/dim]")
            else:
                console.print(f"[dim]可选模型：{', '.join(MODELS)}[/dim]")
            continue

        # ===== 正常对话 =====
        conv.add_user(user_input)

        # 上下文裁剪（超过上限时自动压缩）
        if conv.needs_trim():
            with console.status("[dim]对话较长，正在压缩历史...[/dim]"):
                removed = conv.trim()
                if removed:
                    new_summary = summarize(removed)
                    conv.set_summary(
                        (conv.summary + "\n" + new_summary).strip() if conv.summary
                        else new_summary
                    )

        start = time.time()
        first_token_at = None
        parts = []

        if use_rich:
            console.print("\n[bold blue]AI[/bold blue] > ", end="")

        try:
            for chunk in stream_chat(conv.build_messages(), usage=usage):
                if first_token_at is None:
                    first_token_at = time.time() - start
                parts.append(chunk)
                if use_rich:
                    console.print(chunk, end="", markup=False, highlight=False)
                else:
                    print(chunk, end="", flush=True)
        except Exception as e:
            console.print(f"\n[red]生成失败：{e}[/red]")
            # 把失败的助手消息也记进去，保持历史结构完整
            conv.add_assistant("[生成失败]")
            continue

        reply = "".join(parts)
        conv.add_assistant(reply)

        elapsed = time.time() - start
        ttft = first_token_at or elapsed

        if use_rich:
            console.print()
            console.print(
                f"[dim]首字 {ttft:.2f}s · 耗时 {elapsed:.2f}s · "
                f"轮次 {conv.turn_count()} · "
                f"累计成本 ¥{usage.cost_usd * config.usd_to_cny:.4f}[/dim]"
            )
        else:
            print(f"\n[首字 {ttft:.2f}s · 耗时 {elapsed:.2f}s]")

    # ===== 退出时打印总结 =====
    if use_rich:
        table = Table(title="本次会话总结")
        table.add_column("项目", style="cyan")
        table.add_column("数值", justify="right")
        table.add_row("模型", config.model.name)
        table.add_row("请求次数", str(usage.requests))
        table.add_row("输入 token", f"{usage.prompt_tokens:,}")
        table.add_row("输出 token", f"{usage.completion_tokens:,}")
        if usage.cache_hit_tokens:
            table.add_row("缓存命中", f"{usage.cache_hit_tokens:,}")
        table.add_row("总成本", f"${usage.cost_usd:.6f}")
        table.add_row("约合人民币", f"¥{usage.cost_usd * config.usd_to_cny:.4f}")
        console.print()
        console.print(table)
    else:
        print(f"\n{usage.summary(config.usd_to_cny)}")


def main():
    ap = argparse.ArgumentParser(description="CLI 多轮对话机器人")
    ap.add_argument("--once", "-o", type=str, help="单次提问后退出")
    ap.add_argument("--model", "-m", choices=list(MODELS.keys()),
                    help="指定模型（flash / pro / ollama）")
    ap.add_argument("--plain", action="store_true", help="不使用富文本输出")
    ap.add_argument("--temperature", "-t", type=float, help="采样温度")
    args = ap.parse_args()

    if args.model:
        config.model_key = args.model          # type: ignore
    if args.temperature is not None:
        config.temperature = args.temperature

    if args.once:
        conv = Conversation(system_prompt=config.system_prompt)
        usage = Usage()
        print(run_once(args.once, conv, usage))
        print(f"\n[{usage.summary(config.usd_to_cny)}]")
        return

    try:
        chat_loop(use_rich=not args.plain)
    except KeyboardInterrupt:
        print("\n已退出")


if __name__ == "__main__":
    main()
