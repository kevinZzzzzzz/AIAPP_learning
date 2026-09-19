# 模块 01：LLM 基础与 API 调用

> 对应周次：**W1**｜预计耗时：**12–15 小时**
> 前置要求：能跑通 `环境搭建与工具链指南.md` 里的章节 1–2

---

## 一、这个模块要解决什么问题

**一句话**：让你能稳定地调用大模型，并且知道每一次调用花了多少钱、为什么有时候它会"胡说"。

学完这一模块，你应该能回答：

- 大模型到底在做什么？（为什么它会一个字一个字往外蹦字）
- `messages` 数组里放什么、顺序有什么讲究？
- 为什么对话产品必须用流式输出？
- Token 是什么？我的程序一次对话花多少钱？
- 为什么模型会"幻觉"？这是 bug 还是特性？

---

## 二、核心概念

### 2.1 大模型在做什么：下一 token 预测

**一句话解释**：大模型做的事情只有一件——**根据前面所有的文字，预测下一个最可能出现的字（token）**。然后把这个字加回去，再预测下一个，循环往复。

举例，输入"今天天气真"，模型计算下一个 token 的概率分布可能是：

```
"好"  → 62%
"不"  → 15%
"热"  → 8%
"冷"  → 4%
...其他
```

它选一个（通常是概率最高的，或按概率采样），输出"好"。然后变成"今天天气真好"，再预测下一个。

**这个认知极其重要**，因为它解释了后面几乎所有现象：

| 现象 | 为什么 |
|---|---|
| 模型会"编造"事实 | 它在预测"什么字看起来最合理"，不是在查数据库。假话说得通顺就会被说出来 |
| 同样的输入输出不一样 | 采样有随机性（除非把温度设成 0） |
| 模型不能"真的计算" | 计算不是预测下一个字的子任务，它只是见过很多算式，模仿着算。所以数学要用工具算 |
| 输出越长越可能跑偏 | 每一步都有小概率选错，错误会累积 |
| 流式输出为什么字字显示 | 因为本来就是一个个生成的，不是生成完再切开发 |

> ⚠️ **注意区分**：这是对模型**行为**的解释，不是对模型**内部**的解释。关于"大模型是否真的理解"，学界没有定论。做工程你不必纠结这个，但要记住：**它的输出是概率结果，不是真理**。

### 2.2 Token：模型眼里的文字单位

Token 是模型处理文字的最小单位，**不等于字，也不等于单词**。

| 语言 | 大致换算 |
|---|---|
| 英文 | 1 token ≈ 0.75 个单词（1000 token ≈ 750 词） |
| 中文 | 1 个汉字 ≈ 0.6–1.5 token（取决于词表和分词方式） |
| 代码 | 波动大，缩进和符号也占 token |

**为什么你必须关心 Token**：

1. **计费按 token 算**，输入输出单价不同（通常输出更贵）
2. **上下文窗口按 token 算**，超了直接报错
3. **延迟与 token 数正相关**，输出 500 token 和 5000 token 的等待时间差很多

**算钱的公式**：

```
单次成本 = 输入token数 × 输入单价 + 输出token数 × 输出单价
```

以 DeepSeek 为例（2026-09-13 官方价格，每百万 token）：

| 模型 | 输入（缓存命中） | 输入（缓存未命中） | 输出 |
|---|---|---|---|
| `deepseek-v4-flash` | $0.0028 | $0.14 | $0.28 |
| `deepseek-v4-pro` | $0.003625 | $0.435 | $0.87 |

**实际感受一下**：一次典型对话，输入 2000 token（含历史）、输出 500 token。

用 flash：`2000/1e6 × 0.14 + 500/1e6 × 0.28 ≈ $0.00042`，约 **¥0.003**。

也就是说，**学习阶段跑几百次对话，成本不到 1 块钱**。但如果你在写循环 Agent，一次任务跑 50 步、每步上下文累积到 20K token，单次任务成本就会到 ¥0.5 量级——这就是为什么第 7 周要学上下文管理和成本控制。

### 2.3 一次调用的完整结构

```python
messages = [
    {"role": "system",    "content": "你是一个专业的...（设定身份、规则、输出格式）"},
    {"role": "user",      "content": "用户说的话"},
    {"role": "assistant", "content": "模型上次的回复"},
    {"role": "user",      "content": "用户这次说的话"},
]
```

| 角色 | 作用 | 前端类比 |
|---|---|---|
| `system` | 全局设定：身份、规则、约束、输出格式。模型最"听话"的位置 | 类似全局配置 / 中间件 |
| `user` | 用户输入 | 用户事件 |
| `assistant` | 模型上一次的输出 | 服务端响应 |

**关于 `system` 的三个要点**：

1. **模型对 system 的服从度最高。** 关键约束（如"只输出 JSON"）要放这里，不要放在 user 里
2. **system 通常要放长且固定**，正好能命中 prompt cache（前面价格表里"缓存命中"那列），省钱关键。**⚠️避坑**：不要把频繁变化的动态变量（如当前时间戳）放在 system prompt 的开头，否则会导致 Cache 前缀匹配失败，失去降本提速效果。动态变量应尽量往后放，或放在 user 消息里。
3. **顺序有意义**：一般 system 在最前，然后是历史对话按时间排序，最后是当前 user 消息

### 2.4 上下文窗口（Context Window）

**定义**：模型一次能"看到"的 token 总量上限（输入 + 输出）。

**为什么重要**：这是 Agent 开发最核心的工程约束之一。

| 问题 | 后果 |
|---|---|
| 上下文太长 | 报错（直接失败）或成本飙升 |
| 上下文太长但没超限 | **"中间遗忘"**：模型对长上下文中间部分的注意力会下降，早期的关键信息可能被忽略 |
| 上下文太短 | 模型不知道前情，回答不连贯 |

**应对策略**（模块 05 会详细讲）：

| 策略 | 适用场景 |
|---|---|
| 滑动窗口（只保留最近 N 轮） | 简单对话 |
| 摘要压缩（把旧对话总结成一段） | 长对话 |
| 按需检索（只把相关的历史拿出来） | 复杂 Agent |
| 关键信息重注入（每轮重复重要的约束） | 长任务，防"中间遗忘" |

### 2.5 流式输出（Streaming）

**不流式**：等模型全部生成完，一次性返回。用户看着转圈等 5 秒。

**流式**：模型每生成一个 token 就立刻推给前端。用户 0.3 秒就看到第一个字。

**对于对话类产品，流式不是优化项，是必需品。** 原因：

- 首字延迟（TTFT, Time To First Token）直接决定用户感觉"快还是慢"
- 总耗时其实一样，但感知差异巨大
- 用户能提前判断"它是不是理解错了"，可以立刻中断，省时间省 token

**技术实现**：HTTP 的 **SSE（Server-Sent Events）**，一种服务端单向持续推送的机制。

前端你其实已经熟悉这种模式了——它就是 `EventSource` / 逐块读取响应体。SSE 在模块 07 会详细讲。

### 2.6 采样参数：怎么控制输出的"随机程度"

| 参数 | 作用 | 怎么调 |
|---|---|---|
| `temperature` | 随机性。0 = 几乎确定，2 = 很随机 | 事实问答/工具调用调 **0–0.3**；创意写作调 **0.7–1.0** |
| `top_p` | 只从累积概率前 p 的候选里采样 | 一般和 temperature 二选一调。调它就设 temperature=1 |
| `max_tokens` | 输出上限 | 按需设置，防止模型啰嗦烧钱（但不是所有接口都支持） |
| `stop` | 遇到指定字符串就停止 | 需要严格控制输出边界时用 |
| `frequency_penalty` | 惩罚重复用词 | 输出重复时调高 |
| `presence_penalty` | 鼓励谈论新话题 | 让回答更发散时调高 |

> **新手最容易犯的错**：所有场景都用默认 temperature。**工具调用、结构化输出、分类任务必须用低温（0–0.3）**，否则格式会出错。

**关于"思考模式"**：现在的模型（如 `deepseek-v4-flash` 默认支持）有思考/非思考两种模式。思考模式会先输出一段推理过程再给答案，**推理能力更强但更慢更贵**。复杂任务（多步推理、数学、规划）开思考模式，简单任务关掉。DeepSeek 通过 `reasoning_effort` 参数和 `thinking` 字段控制，具体写法见官方文档。

### 2.7 幻觉（Hallucination）：不是 bug，是机制

**定义**：模型生成了看起来合理、但事实错误或不存在的内容。

**为什么会发生**（回到 2.1）：

模型的目标是"生成最像样的下一个字"，**不是"说真话"**。当它不知道答案时，它不会说"我不知道"，而是会生成一个**在语言上最合理**的答案——包括编造人名、编造论文标题、编造 API 方法名。

**四类典型幻觉**：

| 类型 | 例子 | 应对 |
|---|---|---|
| 事实型幻觉 | 编造不存在的历史事件 | RAG + 要求给引用 |
| 引用型幻觉 | 编造论文名、链接 | 强制引用必须来自检索结果，且校验链接 |
| 代码型幻觉 | 编造不存在的库方法 | 用文档做 RAG；代码要真的运行验证 |
| 过度自信 | 对模糊问题给出确定答案 | 提示词要求"不确定时明确说不确定" |

**治理手段（按性价比排序）**：

1. **给它资料**（RAG）——最有效。有依据就少编
2. **要求说"不知道"**——提示词里明确给"逃逸出口"
3. **降低温度**——减少随机发挥
4. **要求引用来源**——让它必须指出依据，并**在代码里校验**引用是否真的存在
5. **外部校验**——关键事实用工具查证（搜索、数据库）

> **关键认知**：**幻觉无法根除，只能降低。** 任何声称 100% 准确的 AI 系统都在吹牛。所以产品设计上要有"人可核对"机制——显示引用来源，让用户自己判断。这也正是前端在 AI 产品里的核心价值所在。

---

## 三、知识点清单

学完本模块，下面每一条你都要能用自己的话讲出来：

- [ ] 下一 token 预测：模型的基本工作机制
- [ ] Token 的概念、中英文换算比例、为什么影响成本和延迟
- [ ] 输入/输出 token 分别计费，缓存命中的原理和价格差
- [ ] `messages` 数组结构与三种角色（system/user/assistant）的作用和顺序
- [ ] 上下文窗口限制，以及超限的两种后果（报错 / 中间遗忘）
- [ ] 流式输出的价值和 SSE 的基本原理
- [ ] 采样参数：temperature / top_p / max_tokens / stop 的作用与典型取值
- [ ] 思考模式（reasoning）与普通模式的区别、成本差异
- [ ] 幻觉的成因、四种类型、五层治理手段
- [ ] 多轮对话的上下文组装逻辑
- [ ] API 调用的错误类型（401/429/超时/超限）及处理方式

---

## 四、代码示例

完整可运行版本见 `02-项目/01-cli-chatbot/`。以下为核心片段。

### 4.1 最小调用（非流式）

```python
# src/basic_call.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# DeepSeek 完全兼容 OpenAI SDK，只需改 base_url
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个简洁的技术助手，回答问题不超过 3 句话。"},
        {"role": "user", "content": "什么是 RAG？"},
    ],
    temperature=0.3,
)

print(resp.choices[0].message.content)

# 关键：把用量打印出来，养成本能
u = resp.usage
print(f"\n[用量] 输入 {u.prompt_tokens} / 输出 {u.completion_tokens} / 合计 {u.total_tokens} token")
```

**这段代码你必须理解的三点**：
1. 为什么改 `base_url` 就能用 DeepSeek（因为 API 协议兼容）
2. `temperature=0.3` 为什么适合事实问答
3. 为什么要立刻看 `usage`（不看就永远对成本没感觉）

### 4.2 流式输出（对话产品的核心）

```python
# src/stream_call.py
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

start = time.time()
first_token_at = None

stream = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "用三句话解释什么是向量数据库"}],
    stream=True,          # 关键开关
    temperature=0.3,
)

for chunk in stream:
    # 注意：流式下每个 chunk 可能没有 content（比如第一个 chunk 只带 role）
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta.content:
        if first_token_at is None:
            first_token_at = time.time() - start     # 记录首字延迟
        print(delta.content, end="", flush=True)     # flush 才能逐字显示

print(f"\n\n[首字延迟] {first_token_at:.2f}s  [总耗时] {time.time() - start:.2f}s")
```

**核心理解点**：
- `stream=True` 返回的是**迭代器**，不是完整结果
- 每个 `chunk` 只包含**一小部分**内容，要自己拼接
- 有些 chunk 的 `delta.content` 是 `None`（心跳、结束标记、仅角色信息），**必须判空**，否则报错
- `flush=True` 不加的话，输出会攒在缓冲区，看起来像"一次性蹦出来"
- **首字延迟（TTFT）** 是对话产品的核心指标，从这周开始就要养成测量的习惯

### 4.3 多轮对话 + 上下文管理

```python
# src/chat_loop.py —— 完整版见项目 01
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

SYSTEM_PROMPT = "你是一个专业的技术助手，回答简洁准确，不确定时明确说不确定。"

MAX_TURNS = 10          # 最多保留最近 10 轮，防止上下文无限增长

def chat():
    # 关键：messages 是你自己维护的列表，模型本身没有记忆
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    total_cost = 0.0

    while True:
        user_input = input("\n你: ").strip()
        if not user_input:
            continue
        if user_input in ("/exit", "/quit"):
            print(f"\n本次会话累计成本约 ¥{total_cost:.4f}")
            break

        history.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=history,
            stream=True,
            stream_options={"include_usage": True}, # 关键：流式必须加这个参数，否则拿不到用量
            temperature=0.3,
        )

        print("AI: ", end="")
        reply = ""
        usage = None
        for chunk in stream:
            if getattr(chunk, "usage", None):      # 最后一个 chunk 会携带完整的用量信息
                usage = chunk.usage
            if not chunk.choices:                  # 携带 usage 的 chunk choices 可能为空，需判空
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                reply += delta.content
                print(delta.content, end="", flush=True)
        print()

        history.append({"role": "assistant", "content": reply})

        # 上下文裁剪：只保留 system + 最近 MAX_TURNS 轮对话
        if len(history) > 1 + MAX_TURNS * 2:
            history = [history[0]] + history[-(MAX_TURNS * 2):]
            print("  [提示] 上下文已裁剪，遗忘早期对话")

        # 成本统计（DeepSeek flash 价格，每百万 token）
        if usage:
            cost = usage.prompt_tokens / 1e6 * 0.14 + usage.completion_tokens / 1e6 * 0.28
            total_cost += cost
            print(f"  [本轮] {usage.prompt_tokens}+{usage.completion_tokens} token ≈ ¥{cost:.4f}")
        else:
            print("  [警告] 未获取到 token 用量")

if __name__ == "__main__":
    chat()
```

**这段代码要理解的核心**：
1. **模型没有记忆，`messages` 由你自己维护并每次全量发送** —— 这是最常见的认知误区，必须掰正
2. 上下文裁剪为什么必要（不加的话第 30 轮就报错）
3. 裁剪的代价：模型会"忘记"早期内容。这就是后面要学记忆管理的原因

### 4.4 健壮的调用封装（错误处理）

```python
# src/llm_client.py
import os
import time
import logging
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

def call_llm(messages, model="deepseek-v4-flash", temperature=0.3,
             max_retries=3, timeout=60):
    """带重试和错误处理的模型调用封装。生产代码必须这么写。"""
    last_error = None

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
            )
            return resp

        except RateLimitError as e:
            # 429：限流。必须退避等待，不能立刻重试（会加重限流）
            wait = 2 ** attempt          # 指数退避：1s, 2s, 4s
            logger.warning(f"触发限流，{wait}s 后重试（第 {attempt+1} 次）")
            time.sleep(wait)
            last_error = e

        except APITimeoutError as e:
            # 超时：网络或服务端慢，重试可能有效
            logger.warning(f"请求超时，重试中（第 {attempt+1} 次）")
            last_error = e

        except APIError as e:
            # 其他 API 错误：4xx 通常是请求本身有问题，重试没用
            if e.status_code and 400 <= e.status_code < 500:
                logger.error(f"客户端错误 {e.status_code}，不重试：{e}")
                raise
            logger.warning(f"服务端错误 {e.status_code}，重试中")
            last_error = e

    raise RuntimeError(f"重试 {max_retries} 次后仍失败") from last_error
```

**为什么这段代码很重要**：你的第一个 Demo 可以不管错误处理，但**从第 6 周做 Agent 开始，重试和超时是刚需**。Agent 一次任务可能调 20 次模型，任何一次抖动都会中断整个流程。现在养成好习惯。

**错误类型速查**：

| 错误 | 含义 | 该不该重试 |
|---|---|---|
| 401 | Key 无效/未授权 | ❌ 不重试，改配置 |
| 402/403 | 欠费/无权限 | ❌ 不重试 |
| 404 | 模型名错误 | ❌ 不重试，改模型名 |
| 429 | 限流 | ✅ 重试 + 指数退避 |
| 5xx | 服务端故障 | ✅ 重试 + 退避 |
| 超时 | 网络/服务慢 | ✅ 重试（但注意幂等性） |
| 上下文超限 | 输入太长 | ❌ 不重试，先裁剪上下文 |

---

## 五、常见坑（提前避开）

### 坑 1：Key 写死在代码里
**后果**：推到 GitHub 后几小时内被盗刷，损失真金白银。
**正确做法**：`.env` + `.gitignore`，第 1 天就配好。

### 坑 2：以为模型有记忆
**后果**：不做多轮对话，或者困惑"为什么它忘了刚才说的话"。
**正确做法**：记住 `messages` 是你自己维护的数组，每次全量传给模型。

### 坑 3：流式输出时没判空 `chunk.choices`
**后果**：`IndexError: list index out of range` 或 `AttributeError: 'NoneType'`。
**正确做法**：`if not chunk.choices: continue`，并且 `delta.content` 也要判空。

### 坑 4：不统计 token，对成本没概念
**后果**：写了循环 Agent 跑了 100 次任务，账单几十块，还不知道钱花在哪。
**正确做法**：从第一个 Demo 就打印 usage。

### 坑 5：所有场景都用默认 temperature
**后果**：要做格式输出时，模型随机发挥导致解析失败。
**正确做法**：结构化输出/工具调用 temperature ≤ 0.3。

### 坑 6：不检查 `finish_reason`
**后果**：有时候模型输出的 JSON 格式残缺，导致后续解析直接报错崩溃。其实是因为文本过长触发了限制被截断了。
**正确做法**：习惯检查流式返回的最后一次 `finish_reason`，如果等于 `"length"`，说明内容被截断，需要在产品层面做容错或重试。

### 坑 7：上下文无限增长
**后果**：跑到第 20 轮突然报错，或者成本线性上升、回答质量还变差。
**正确做法**：明确设定上下文上限并做裁剪或摘要。

### 坑 8：以为模型会算数
**后果**：让它算财务数据，结果算错还理直气壮。
**正确做法**：计算交给代码/工具（这是模块 04 的重点）。

### 坑 9：用 `print` 调试大对象
**后果**：输出一大坨看不出重点。
**正确做法**：只打关键字段，或用 `rich` 库美化输出。

---

## 六、练习任务

按顺序完成，**不许跳步**。

| # | 任务 | 目的 | 难度 |
|---|---|---|---|
| 1 | 写一个脚本，分别调 flash 和 pro，问同一个问题，对比输出质量、耗时、成本 | 建立"模型能力 vs 成本"的直观感受 | ⭐ |
| 2 | 把同一个问题用 temperature=0 和 1.2 各问 5 次，观察差异 | 理解采样参数的实际影响 | ⭐ |
| 3 | 实现一个 token 计数器，在对话中实时显示本轮和累计成本 | 建立成本意识 | ⭐⭐ |
| 4 | 故意触发 429（快速连续调用 100 次），观察报错并实现退避重试 | 理解限流和重试机制 | ⭐⭐ |
| 5 | 做一个"上下文爆炸"实验：不断追问，直到报上下文超限错误，记录在第几轮失败 | 亲身体会上下文限制 | ⭐⭐ |
| 6 | 让模型答一个它肯定不知道的问题（比如某个不存在的人物），观察它是否编造 | 亲眼看到幻觉 | ⭐⭐ |
| 7 | 用同一批 10 个问题，测试"不提供资料"vs"提示词要求不确定就说不确定"两种方式，统计编造率 | 量化幻觉治理效果 | ⭐⭐⭐ |
| 8 | 把模型调用封装成一个类，支持切换提供方（DeepSeek/OpenAI/Ollama），配置从环境变量读 | 为后面项目打基础 | ⭐⭐⭐ |

**任务 6、7 是本周最重要的练习。** 亲手看到模型自信地编造事实，你才会真正理解为什么后面要学 RAG、为什么产品必须显示引用来源。

---

## 七、自测题

先自己回答，再看答案。答不出 6 题以上，回去重读。

**Q1：为什么大模型会"胡说八道"？**
<details><summary>参考答案</summary>
因为它的工作机制是预测"下一个最可能出现的 token"，目标是生成语言上合理的内容，而不是输出真理。当它不知道答案时，会生成一个语言上通顺但事实错误的答案，而不是承认不知道。
</details>

**Q2：模型有记忆吗？多轮对话是怎么实现的？**
<details><summary>参考答案</summary>
模型本身没有记忆（单次请求无状态）。多轮对话是把历史消息拼成 messages 数组，每次请求全量发送。所以"历史管理"完全是你（应用层）的责任。
</details>

**Q3：为什么对话产品必须用流式输出？总耗时不是一样吗？**
<details><summary>参考答案</summary>
总耗时确实差不多，但首字延迟（TTFT）差异巨大：非流式要等全部生成完（可能 5–10 秒），流式 0.3 秒就能看到第一个字。用户感知的"快慢"取决于首字时间，而不是总时长。另外流式让用户可以提前判断回答是否跑偏并中断，节省时间和 token。
</details>

**Q4：什么情况下必须把 temperature 设成 0 或接近 0？**
<details><summary>参考答案</summary>
需要确定性输出的场景：结构化输出（JSON）、工具调用（Function Calling）、分类/抽取任务、代码生成、需要事实准确性的问答。这些场景要的是"稳定复现"，不是"创意发挥"。
</details>

**Q5：`deepseek-v4-flash` 和 `deepseek-v4-pro` 该怎么选？**
<details><summary>参考答案</summary>
按任务复杂度选。简单任务（分类、抽取、格式转换、简单问答）用 flash，便宜 3 倍且更快。复杂推理（多步规划、复杂代码、需要深度分析）用 pro。注意：不要因为"pro 看起来更强"就全部用 pro，那是 3 倍成本换来的边际提升。（另：老的 `deepseek-chat`/`deepseek-reasoner` 已于 2026-07-24 下线，不要再用）
</details>

**Q6：上下文超限会怎样？有哪两种后果？**
<details><summary>参考答案</summary>
两种：一是直接报错（超过硬限制，请求失败）；二是虽然没超限但出现"中间遗忘"——模型对长上下文中间部分的注意力下降，早期关键信息被忽略。所以不是"没报错就没问题"。
</details>

**Q7：什么是 prompt caching？能省多少钱？**
<details><summary>参考答案</summary>
服务端把重复出现的提示词前缀缓存起来，后续请求命中缓存时按更低价格计费。DeepSeek 的缓存命中输入价是未命中的 1/50（$0.0028 vs $0.14）。所以要把长而固定的内容（system prompt、工具定义、示例）放在消息前面，提高命中率。这是长对话/Agent 场景的核心省钱手段。
</details>

**Q8：为什么说"幻觉无法根除"？产品上该怎么应对？**
<details><summary>参考答案</summary>
因为幻觉源于模型的生成机制本身（预测最像样的下一个 token），不是某个可以修掉的 bug。只能通过 RAG、提示词约束、降低温度、外部校验等手段降低概率。产品层面必须提供"人可核对"的机制：显示引用来源、标注不确定性、对高风险答案给出人工复核入口。
</details>

**Q9：遇到过 429 错误该怎么处理？为什么不能立刻重试？**
<details><summary>参考答案</summary>
429 是限流，表示请求频率超过配额。不能立刻重试，因为立即重试会继续增加请求压力，可能加重限流甚至被临时封禁。应该用指数退避：等 1s、2s、4s、8s……逐步加大等待时间，并设置最大重试次数上限。同时应该做请求节流（本地限速）。
</details>

**Q10：让模型算 "12345 × 67890"，它算错了。这是模型坏了还是正常？**
<details><summary>参考答案</summary>
正常。大模型不做精确计算，只是"见过很多算式，模仿着算"。多位乘法超出它的可靠范围。正确做法是用工具（代码执行器 / 计算器）来算，让模型负责理解问题、决定调用工具、解释结果——这就是模块 04 要学的 Tool Calling 的核心动机。
</details>

---

## 八、延伸阅读

| 主题 | 资源 |
|---|---|
| DeepSeek API 文档（**必读**） | https://api-docs.deepseek.com/ |
| DeepSeek 价格页（**必读**） | https://api-docs.deepseek.com/quick_start/pricing |
| OpenAI 文档 | https://platform.openai.com/docs |
| Token 可视化工具（试试中文分词） | https://platform.openai.com/tokenizer |
| Anthropic 关于幻觉的工程文章 | https://docs.anthropic.com |

> 更完整的资源清单见 `03-资源/学习资源清单.md`

---

## 九、完成标志

本模块结束时，你应该有：

- [ ] 一个能跑的多轮对话 CLI 程序，显示实时 token 和成本
- [ ] 一个带重试和错误处理的模型调用封装类
- [ ] 一份"幻觉实验"记录：不提供资料时模型编造率是多少
- [ ] 能不看资料讲清本模块「知识点清单」里的每一条

**下一步**：进入模块 02，学习怎么让模型稳定按你要的格式输出。
