"""手写 ReAct Agent 循环 —— 本项目的心脏。

## ReAct 是什么

ReAct = Reasoning + Acting。核心循环极其简单：

    想 → 做 → 看 → 想 → 做 → 看 → … → 给出最终答案
    (Thought) (Action) (Observation)

用 API 的语言翻译一遍，就是下面这个 while 循环：

    while 还没结束:
        把「历史消息」发给模型
        模型返回：
            情况 A：直接给文字答案  → 结束，输出答案
            情况 B：给出 tool_calls → 我执行工具，把结果加进历史消息，继续循环

**理解了这 30 行，你就理解了所有 Agent 框架的本质。**
LangGraph、AutoGPT、CrewAI 都只是在这个骨架上加东西：
加状态管理、加持久化、加分支、加多 Agent 协作。

## 为什么必须先手写

因为框架会把这些细节藏起来，而恰恰是这些细节决定了 Agent 靠不靠谱：

- 消息历史怎么维护？（漏一条消息模型就"失忆"）
- 死循环怎么防？（模型可能反复调同一个工具）
- 工具报错怎么处理？（崩溃还是让模型自我修复）
- 步数上限设多少？（设小了任务做不完，设大了烧钱）
- 每次循环都发全部历史，token 成本怎么涨？（平方级增长）

这些坑，手写过一遍你就永远记住了。
"""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Any

from src.config import config, get_client
from src.tools import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- 结果结构
@dataclass
class Step:
    """Agent 的一步。把中间过程完整记录下来。

    为什么要记录：Agent 出错时你必须能看清它每一步在想什么、
    调了什么、拿到了什么。没有这个，调试 Agent 就是盲人摸象。
    """
    index: int
    thought: str = ""              # 模型这步的文字说明（如果有）
    tool_name: str = ""            # 调用的工具
    tool_args: dict = field(default_factory=dict)
    observation: str = ""          # 工具返回结果
    is_final: bool = False         # 是否是最后一步（直接给答案）


@dataclass
class AgentResult:
    """一次 Agent 运行的完整结果。"""
    question: str
    answer: str
    steps: list[Step] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    stopped_reason: str = "completed"   # completed / max_steps / error

    @property
    def tool_calls(self) -> int:
        return sum(1 for s in self.steps if s.tool_name)

    def cost_usd(self) -> float:
        m = config.model
        # 简化计算：不区分缓存命中（Agent 场景上下文变化大，缓存命中率低）
        return (self.prompt_tokens / 1e6 * m.price_input
                + self.completion_tokens / 1e6 * m.price_output)


# ---------------------------------------------------------------- Agent
class ReActAgent:
    """手写 ReAct Agent。

    用法：
        agent = ReActAgent(registry)
        result = agent.run("北京今天天气怎么样？")
        print(result.answer)
    """

    def __init__(self, registry: ToolRegistry,
                 system_prompt: str | None = None,
                 max_steps: int | None = None,
                 on_confirm: Callable[[Any, dict], bool] | None = None,
                 on_step: Callable[[Step], None] | None = None):
        """
        Args:
            registry: 工具注册表
            system_prompt: 覆盖默认系统提示
            max_steps: 最大迭代步数（防死循环）
            on_confirm: 敏感操作的确认回调
            on_step: 每步完成的回调（用于 CLI 实时打印、前端推送进度）
        """
        self.registry = registry
        self.system_prompt = system_prompt or config.system_prompt
        self.max_steps = max_steps or config.max_steps
        self.on_confirm = on_confirm
        self.on_step = on_step

    # ------------------------------------------------------------ 主循环
    def run(self, question: str, history: list[dict] | None = None) -> AgentResult:
        """执行一个任务。

        Args:
            question: 用户问题
            history: 之前的对话历史（多轮对话时传入）
        """
        client = get_client()
        m = config.model

        # 消息历史：整个 ReAct 循环的"记忆"。
        # 每一步都要往这个列表里追加消息，下次请求整个列表都发过去。
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        result = AgentResult(question=question, answer="")
        tool_schemas = self.registry.schemas()

        for step_idx in range(self.max_steps):
            step = Step(index=step_idx)

            # ---------- 1. 请求模型 ----------
            try:
                resp = self._call_model(client, messages, tool_schemas)
            except Exception as ex:                 # noqa: BLE001
                logger.error(f"模型调用失败：{ex}")
                result.answer = f"模型调用失败：{ex}"
                result.stopped_reason = "error"
                return result

            # 累计用量
            if getattr(resp, "usage", None):
                result.prompt_tokens += getattr(resp.usage, "prompt_tokens", 0) or 0
                result.completion_tokens += getattr(resp.usage, "completion_tokens", 0) or 0

            msg = resp.choices[0].message
            step.thought = msg.content or ""

            # ---------- 2. 判断：给答案 还是 调工具 ----------
            if not msg.tool_calls:
                # 情况 A：模型直接回答了 → 结束
                step.is_final = True
                result.answer = msg.content or ""
                result.steps.append(step)
                self._emit(step)
                return result

            # 情况 B：模型要调工具
            # ⚠️ 关键：必须先把 assistant 这条消息（含 tool_calls）加进历史。
            # 后面 tool 角色的消息必须"回应"这些 tool_call_id，
            # 少一条或 id 对不上，API 会直接报 400。
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # ---------- 3. 执行工具（可能多个并行调用）----------
            for tc in msg.tool_calls:
                name = tc.function.name
                args_raw = tc.function.arguments

                # 解析参数。模型偶尔会返回非法 JSON（尤其是长参数或含引号时）
                try:
                    args = json.loads(args_raw) if args_raw else {}
                    if not isinstance(args, dict):
                        args = {}
                except json.JSONDecodeError as ex:
                    # 不崩溃，把解析错误告诉模型，它能自我修复
                    observation = (
                        f"参数解析失败：你返回的 arguments 不是合法 JSON（{ex}）。"
                        f"原始内容：{args_raw[:200]}。请检查引号和转义后重试。"
                    )
                    # ⚠️ 必须记录到 step，否则调试时看不到这一步发生了什么
                    step.tool_name = name
                    step.observation = observation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": observation,
                    })
                    continue

                # 记录这一步（取第一个工具调用用于展示）
                if not step.tool_name:
                    step.tool_name = name
                    step.tool_args = args

                # 执行 —— 所有安全检查和错误处理都在 registry.execute 里
                observation = self.registry.execute(
                    name, args, on_confirm=self.on_confirm
                )
                step.observation = observation

                # 把结果作为 tool 消息塞回历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": observation,
                })

            result.steps.append(step)
            self._emit(step)

        # ---------- 4. 达到步数上限 ----------
        # 这不是正常结束。必须明确告知，不能让用户以为任务完成了。
        result.stopped_reason = "max_steps"
        result.answer = (
            f"已尝试 {self.max_steps} 步仍未完成任务，已停止以避免继续消耗。\n"
            f"最后一步的执行结果是：\n{result.steps[-1].observation if result.steps else '（无）'}\n\n"
            f"你可以换个说法重新提问，或者缩小任务范围。"
        )
        return result

    # ------------------------------------------------------------ 内部方法
    def _call_model(self, client, messages: list[dict], tool_schemas: list[dict]):
        """调用模型。带重试。

        为什么要重试：Agent 一次任务可能调 10+ 次模型，
        每次失败都会中断整个流程。不重试的话成功率会低得无法接受。
        （假设单次成功率 99%，10 次串起来只有 90%。）
        """
        last_err = None
        for attempt in range(3):
            try:
                return client.chat.completions.create(
                    model=config.model.name,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    temperature=config.temperature,
                )
            except Exception as ex:                 # noqa: BLE001
                last_err = ex
                msg = str(ex)
                # 4xx 是请求本身有问题，重试无用
                if "400" in msg or "invalid_request" in msg.lower():
                    raise
                if attempt == 2:
                    break
                wait = 2 ** attempt
                logger.warning(f"模型调用失败，{wait}s 后重试：{ex}")
                time.sleep(wait)
        raise last_err

    def _emit(self, step: Step):
        if self.on_step:
            try:
                self.on_step(step)
            except Exception as ex:                 # noqa: BLE001
                logger.debug(f"步骤回调失败：{ex}")


# ---------------------------------------------------------------- 多轮对话封装
class ConversationAgent:
    """带多轮记忆的 Agent。

    注意：这里用最简单的"全量历史"策略 —— 每轮把之前所有对话都带上。
    问题：token 随轮数线性增长，几轮之后就很贵。
    优化：见 src/context_management.py 里的滑动窗口和摘要压缩。
    """

    def __init__(self, registry: ToolRegistry, **kwargs):
        self.agent = ReActAgent(registry, **kwargs)
        self.history: list[dict] = []

    def chat(self, question: str) -> AgentResult:
        result = self.agent.run(question, history=self.history)

        # 把这一轮的问和答记入历史（工具调用过程不记，否则历史会爆炸）
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": result.answer})

        # 简单保护：历史超过 N 轮就丢弃最早的（滑动窗口）
        max_messages = 20
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
        return result

    def reset(self):
        self.history.clear()
