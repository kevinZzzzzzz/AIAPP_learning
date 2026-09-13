#!/usr/bin/env python3
"""工具调用 Agent CLI。

用法：
    # 单次任务
    uv run main.py "北京今天天气怎么样？"

    # 需要多步工具调用的任务
    uv run main.py "现在几点？帮我算一下从今天到 2027 年元旦还有多少天"

    # 会触发敏感操作确认的任务
    uv run main.py "帮我写一个文件叫 todo.md，内容是：明天要做的事"

    # 交互式多轮对话
    uv run main.py --chat

    # 查看所有可用工具
    uv run main.py --tools

    # 不显示中间步骤（只看最终答案）
    uv run main.py -q "成都天气如何"
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import config
from src.toolkit import build_registry
from src.agent import ReActAgent, ConversationAgent, Step
from src.safety import cli_confirm

console = Console()


def setup_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s | %(message)s",
    )
    for noisy in ("httpx", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------- 步骤展示
def print_step(step: Step):
    """把 Agent 的一步可视化成人类能看懂的样子。

    这是调试 Agent 最重要的工具。看不清它每一步做什么，就没法优化。
    """
    if step.is_final:
        return

    # 模型这步的思考（有时有，有时是纯工具调用）
    if step.thought and step.thought.strip():
        console.print(f"  [dim italic]💭 {step.thought.strip()[:150]}[/dim italic]")

    if not step.tool_name:
        return

    # 工具调用 + 参数
    args_str = ", ".join(f"{k}={_short(v)}" for k, v in step.tool_args.items())
    console.print(f"  [cyan]🔧 {step.tool_name}[/cyan]([yellow]{args_str}[/yellow])")

    # 观察结果
    obs = step.observation.replace("\n", " ")
    console.print(f"  [dim]👁  {_short(obs, 160)}[/dim]")


def _short(v, limit: int = 60) -> str:
    s = str(v)
    return s if len(s) <= limit else s[:limit] + "…"


# ---------------------------------------------------------------- 结果展示
def print_result(result, show_steps: bool = True):
    """打印最终结果。"""
    console.print()

    if show_steps and result.steps:
        console.print("[bold]执行过程：[/bold]")
        for step in result.steps:
            print_step(step)
        console.print()

    # 最终答案
    border = "yellow" if result.stopped_reason != "completed" else "green"
    console.print(Panel(
        result.answer or "（无输出）",
        title=f"最终答案 · {result.stopped_reason}",
        border_style=border,
    ))

    # 统计信息 —— 让成本可见
    m = config.model
    console.print(
        f"[dim]步数 {len(result.steps)} | 工具调用 {result.tool_calls} 次 | "
        f"token 输入 {result.prompt_tokens:,} / 输出 {result.completion_tokens:,} | "
        f"成本 ${result.cost_usd():.6f} (约 ¥{result.cost_usd() * config.usd_to_cny:.4f})[/dim]"
    )


def cmd_tools():
    """列出所有工具及其 Schema。"""
    reg = build_registry()
    table = Table(title=f"可用工具（{len(reg.names())} 个）")
    table.add_column("名称", style="cyan")
    table.add_column("敏感", justify="center")
    table.add_column("描述", style="dim", max_width=60)

    for name in reg.names():
        t = reg.get(name)
        table.add_row(
            name,
            "[yellow]需确认[/yellow]" if t.requires_confirm else "-",
            (t.description or "").replace("\n", " ")[:80],
        )
    console.print(table)
    console.print(
        "\n[dim]提示：工具的 description 是模型选择工具的唯一依据。"
        "写不好描述，模型就会调错工具或该调不调。[/dim]"
    )


def cmd_once(question: str, quiet: bool):
    reg = build_registry()
    agent = ReActAgent(reg, on_confirm=cli_confirm)

    console.print(f"\n[bold cyan]任务：[/bold cyan]{question}\n")
    if not quiet:
        console.print("[bold]执行过程：[/bold]")

    steps_buf = []

    def on_step(step):
        steps_buf.append(step)
        if not quiet:
            print_step(step)

    agent.on_step = on_step
    result = agent.run(question)

    if quiet:
        print_result(result, show_steps=False)
    else:
        console.print()
        border = "yellow" if result.stopped_reason != "completed" else "green"
        console.print(Panel(
            result.answer or "（无输出）",
            title=f"最终答案 · {result.stopped_reason}",
            border_style=border,
        ))
        console.print(
            f"[dim]步数 {len(result.steps)} | 工具调用 {result.tool_calls} 次 | "
            f"token 输入 {result.prompt_tokens:,} / 输出 {result.completion_tokens:,} | "
            f"成本 ${result.cost_usd():.6f} (约 ¥{result.cost_usd() * config.usd_to_cny:.4f})[/dim]"
        )


def cmd_chat():
    """交互式多轮对话。"""
    reg = build_registry()
    agent = ConversationAgent(reg, on_confirm=cli_confirm)

    console.print(Panel(
        "工具调用 Agent（多轮对话）\n"
        "命令：/tools 查看工具  /reset 清空对话记忆  /exit 退出",
        title="🤖 ReAct Agent", border_style="cyan",
    ))

    while True:
        try:
            q = console.input("\n[bold cyan]你[/bold cyan] > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]再见[/dim]")
            break

        if not q:
            continue
        if q in ("/exit", "/quit", "exit", "quit"):
            break
        if q == "/tools":
            cmd_tools()
            continue
        if q == "/reset":
            agent.reset()
            console.print("[dim]对话记忆已清空[/dim]")
            continue

        console.print("\n[bold]执行过程：[/bold]")
        result = agent.chat(q)
        console.print()
        border = "yellow" if result.stopped_reason != "completed" else "green"
        console.print(Panel(result.answer or "（无输出）", border_style=border))
        console.print(
            f"[dim]工具调用 {result.tool_calls} 次 | "
            f"成本 ${result.cost_usd():.6f}[/dim]"
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="agent", description="工具调用 Agent —— 模块 04/05 配套项目"
    )
    parser.add_argument("question", nargs="*", help="任务描述")
    parser.add_argument("-c", "--chat", action="store_true", help="交互式对话模式")
    parser.add_argument("-t", "--tools", action="store_true", help="列出所有工具")
    parser.add_argument("-q", "--quiet", action="store_true", help="不显示中间步骤")
    parser.add_argument("-v", "--verbose", action="store_true", help="调试日志")

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        if args.tools:
            cmd_tools()
        elif args.chat:
            cmd_chat()
        elif args.question:
            cmd_once(" ".join(args.question), args.quiet)
        else:
            parser.print_help()
            console.print("\n[dim]示例：uv run main.py \"北京今天天气怎么样？\"[/dim]")
    except KeyboardInterrupt:
        console.print("\n[dim]已中断[/dim]")


if __name__ == "__main__":
    main()
