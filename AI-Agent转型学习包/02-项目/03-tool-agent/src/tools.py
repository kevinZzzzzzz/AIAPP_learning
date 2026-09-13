"""工具定义与注册表。

## 这个文件要解决的核心问题

模型只会"提出"调用意图，执行永远由你的代码完成。
所以工具的 4 件事必须由这里负责：

1. **定义 Schema** —— 告诉模型这个工具叫什么、干什么、要什么参数
2. **参数校验** —— 模型给的参数可能缺失、类型错误、甚至是幻觉出来的字段
3. **错误兜底** —— 工具会抛异常（网络、文件不存在、除零），不能让 Agent 直接崩
4. **权限拦截** —— 危险操作要在这里拦下来，而不是指望模型"自觉"

第 3 点和第 4 点是最容易被忽略、但生产环境最要命的。
"""
import json
import time
import inspect
import logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- 工具定义
@dataclass
class Tool:
    """一个可被模型调用的工具。

    Attributes:
        name: 工具名。模型靠它选择工具，用英文小写下划线，别用中文。
        description: 工具描述。**最重要的字段** —— 模型靠它判断该不该调。
                     写清楚"什么时候用"，比写清楚"它做了什么"更关键。
        parameters: JSON Schema 格式的参数定义。
        func: 实际执行的函数。
        requires_confirm: 是否需要人工确认（危险操作）。
        timeout: 执行超时秒数（None 表示不限制）。
    """
    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]
    requires_confirm: bool = False
    timeout: float | None = 30.0

    def to_openai_schema(self) -> dict:
        """转成 OpenAI tools 参数格式。

        注意这个格式每次请求都要重新发一遍 —— 模型不记得上次的工具清单。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ---------------------------------------------------------------- 注册表
class ToolRegistry:
    """工具注册表：集中管理所有可用工具。

    为什么要注册表而不是一个 list：
    - 可以按名字查（调试、日志、权限检查都需要）
    - 可以动态开关工具（不同用户/场景给不同工具集，这是权限控制的关键）
    - 可以统一做参数校验和执行包装
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        if tool.name in self._tools:
            raise ValueError(f"工具名重复：{tool.name}")
        # 校验 Schema 至少是个 object
        if tool.parameters.get("type") != "object":
            raise ValueError(f"工具 {tool.name} 的 parameters 必须是 object 类型")
        self._tools[tool.name] = tool
        return self

    def tool(self, name: str, description: str, parameters: dict,
             requires_confirm: bool = False, timeout: float | None = 30.0):
        """装饰器写法。让工具定义靠近实现，可读性更好。"""
        def decorator(func: Callable) -> Callable:
            self.register(Tool(
                name=name, description=description, parameters=parameters,
                func=func, requires_confirm=requires_confirm, timeout=timeout,
            ))
            return func
        return decorator

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def subset(self, names: list[str]) -> "ToolRegistry":
        """取子集。用于按角色/场景授予不同工具权限。

        例：只读用户只给查询类工具，不给 write_file / run_sql。
        这是最小权限原则在 Agent 里的落地方式。
        """
        sub = ToolRegistry()
        for n in names:
            if n in self._tools:
                sub._tools[n] = self._tools[n]
            else:
                logger.warning(f"子集中忽略未注册工具：{n}")
        return sub

    def schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    # ------------------------------------------------------------ 执行
    def execute(self, name: str, arguments: dict,
                on_confirm: Callable[[Tool, dict], bool] | None = None) -> str:
        """执行工具。**这是整个 Agent 的安全咽喉**。

        所有工具调用都必须经过这里。任何绕过这个函数的执行路径
        都意味着绕过了确认机制和错误处理。

        Returns:
            工具执行结果的字符串表示。永远不会抛异常 —— 
            错误会变成一段描述文本返回给模型，让它自己决定怎么办。
        """
        tool = self.get(name)
        if tool is None:
            available = ", ".join(self.names())
            # 把可用工具告诉模型，它能据此自我修正
            return f"错误：不存在名为 {name} 的工具。可用工具：{available}"

        # ---- 1. 危险操作需人工确认 ----
        if tool.requires_confirm:
            if on_confirm is None:
                return (
                    f"错误：工具 {name} 是敏感操作，需要人工确认，"
                    f"但当前没有配置确认回调。已拒绝执行。"
                )
            if not on_confirm(tool, arguments):
                return "用户拒绝了这个操作的执行。请告知用户操作已取消，不要重试。"

        # ---- 2. 参数校验 ----
        err = _validate_params(tool, arguments)
        if err:
            return f"参数错误：{err}"

        # ---- 2.5 过滤幻觉参数 ----
        # 模型经常会"发明"schema 里没有的字段（比如给 calculator 传个 unit）。
        # 如果直接 **arguments 透传给函数，会抛 TypeError: unexpected keyword argument。
        # 这里主动剔除，只保留 schema 定义的参数。
        clean_args = _filter_params(tool, arguments)

        # ---- 3. 执行（含超时保护）----
        try:
            return _call_with_timeout(tool, clean_args)
        except Exception as ex:                     # noqa: BLE001
            # 关键：错误不抛出，而是作为"观察结果"返回给模型。
            # 模型看到错误信息后往往能自己调整参数重试 —— 这是 Agent 的自我修复能力。
            logger.warning(f"工具 {name} 执行失败：{ex}")
            return f"工具执行失败：{type(ex).__name__}: {ex}"


def _validate_params(tool: Tool, arguments: dict) -> str | None:
    """按 JSON Schema 校验参数。返回错误信息，None 表示通过。

    只做必要校验（必填项、类型），不引入 jsonschema 依赖。
    生产环境建议直接用 pydantic 或 jsonschema 做完整校验。
    """
    schema = tool.parameters
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # 必填检查
    missing = [r for r in required if r not in arguments or arguments[r] is None]
    if missing:
        return f"缺少必填参数：{', '.join(missing)}"

    # 类型检查（模型偶尔会传错类型，比如把数字传成字符串）
    type_map = {
        "string": str, "integer": int, "number": (int, float),
        "boolean": bool, "array": list, "object": dict,
    }
    for key, value in arguments.items():
        if key not in props:
            # 不认识的字段：警告但不报错（模型可能幻觉出多余字段）
            logger.debug(f"工具 {tool.name} 收到未定义参数：{key}")
            continue
        expected = props[key].get("type")
        py_type = type_map.get(expected)
        if py_type is None or value is None:
            continue
        if expected == "integer" and isinstance(value, bool):
            return f"参数 {key} 应为整数，收到布尔值"
        if not isinstance(value, py_type):
            return f"参数 {key} 类型错误：期望 {expected}，收到 {type(value).__name__}"

    return None


def _filter_params(tool: Tool, arguments: dict) -> dict:
    """剔除 schema 里没定义的参数，只保留合法参数。

    为什么必须做：模型会"发明"参数。比如你定义 get_weather(city)，
    模型可能传 {"city": "北京", "unit": "celsius"}，
    直接透传会抛 TypeError: unexpected keyword argument 'unit'。

    这种错误在真实使用中很常见（尤其是工具描述写得不够精确时），
    过滤掉比报错好 —— 多一个无关参数不影响功能。
    """
    props = tool.parameters.get("properties", {})
    if not props:
        # 无参数工具：不允许任何参数
        if arguments:
            logger.debug(f"工具 {tool.name} 不接受参数，已忽略：{list(arguments)}")
        return {}

    clean = {k: v for k, v in arguments.items() if k in props}
    dropped = [k for k in arguments if k not in props]
    if dropped:
        logger.debug(f"工具 {tool.name} 忽略未定义参数：{dropped}")
    return clean


def _call_with_timeout(tool: Tool, arguments: dict) -> str:
    """执行工具函数并把结果转成字符串。

    关于超时：Python 没有干净的方式给任意函数加超时（signal 只能在主线程用，
    线程无法被强制终止）。这里用线程池 + timeout 做**结果层面**的超时保护：
    超时后不再等待，返回超时错误。注意底层函数仍在后台跑，这是已知妥协。

    生产环境更稳的做法：用 subprocess 隔离，或者工具本身设置好网络超时。
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FTimeout

    if tool.timeout is None:
        result = tool.func(**arguments)
    else:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(tool.func, **arguments)
            try:
                result = future.result(timeout=tool.timeout)
            except FTimeout:
                return f"工具执行超时（超过 {tool.timeout}s）。请考虑换个方式，或缩小处理范围。"

    return _stringify(result)


def _stringify(result: Any) -> str:
    """把工具返回值转成字符串给模型看。

    这一步有讲究：模型只能读文本。所以返回值要
    - 信息完整（别丢关键字段）
    - 不要太啰嗦（浪费 token）
    - 结构化优先（JSON 优于自然语言拼接）
    """
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)
    return str(result)
