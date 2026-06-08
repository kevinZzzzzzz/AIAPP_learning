# LLM 原理 & API 使用指南

> 从前端视角，用大白话讲透 LLM 的核心原理和 API 用法。

---

## 一、LLM 到底是什么？

### 专业解释

LLM（Large Language Model，大语言模型）是一个基于 Transformer 架构的神经网络，通过在海量文本上训练"下一个词预测"任务（Next Token Prediction），学到了语言的统计规律、知识和推理能力。

核心流程：**输入文本 → 分词（Tokenize）→ 模型计算 → 输出下一个词的概率分布 → 采样 → 循环直到生成结束**

### 大白话

想象一个超强的"接话机器人"——你给它一段没说完的话，它能根据上下文猜出接下来最可能说什么。它不是真的"理解"，而是学会了"人通常在这种上下文下接什么话"。

比如你输入 `"1+1="`，它看过几十万次 `"1+1=2"`，所以它的回答会是 `"2"`——不是因为真会算，而是频率太高了。

---

## 二、Token（分词）—— LLM 的"基本粒子"

### 专业解释

Token 是 LLM 处理的最小文本单位，不是字符也不是单词。一段文本会先被 Tokenizer 切分成 Token 序列。每个模型有自己的 Tokenizer，同一个词在不同模型中的 Token 数可能不同。

**常见规则**：
- 英文常见词 = 1 token（如 `"hello"` → 1 token）
- 英文罕见词 = 多个 token（如 `"uncharacteristically"` → 6 tokens）
- 中文一个字 = 1~2 tokens
- 标点/空格 = 1 token

### 大白话

你可以把 Token 理解成"AI 的笔画"。就像汉字由笔画组成，AI 读的文字由 Token 组成。`"我热爱编程"` 在 AI 眼里是 `["我", "热爱", "编程"]` 三个"字"。

**为什么重要？** 每个模型有 Token 上限（如 gpt-4o-mini 支持 128K），一旦对话太长超出上限，AI 就开始"遗忘"。API 按 Token 计费，你花的每一分钱就是花的 Token 数。

### Tokenizer 在线体验

打开 [OpenAI Tokenizer](https://platform.openai.com/tokenizer) 自己试试，直观感受 Token 切分。

---

## 三、Temperature —— 控制"胡说八道"的程度

### 专业解释

Temperature（温度）是一个 0~2 之间的参数，控制 LLM 输出概率分布的平滑度：

| 温度 | 行为 | 数学含义 |
|------|------|---------|
| 0 | 总是选概率最高的词（确定性） | argmax |
| 0.1~0.4 | 高概率词占主导（严谨） | 微弱随机 |
| 0.7~1.0 | 平衡创造力和准确性 | 适度随机 |
| 1.5~2.0 | 高随机性（胡说八道风险高） | 近乎均匀分布 |

### 大白话

Temperature = "胡说八道的勇气值"：
- **0**：死板模式，"1+1=?" 每次都答 2，适合代码、翻译、数学
- **0.7**：正常模式，有点创造性但不离谱，适合日常对话
- **1.5**：疯狂模式，"1+1=?" 可能答"是爱情的结晶"，适合写诗

### 规则总结

```
代码生成 / 数学 / 翻译 / 事实性问答 → temperature = 0~0.3
日常对话 / 解释概念 / 写作辅助     → temperature = 0.5~0.8
创意写作 / 头脑风暴 / 起名         → temperature = 0.8~1.5
```

---

## 四、System Prompt vs User Prompt —— 角色扮演

### 专业解释

一次 LLM API 调用的消息列表有三种角色：

| 角色 | 含义 | 位置 |
|------|------|------|
| `system` | 系统级指令，定义 AI 的行为和角色 | 第一条 |
| `user` | 用户的输入 | system 之后 |
| `assistant` | AI 的历史回复 | 交错在 user 之间 |

System Prompt 是"规则设定"，不会被用户看到，但对 AI 行为影响极大。

### 大白话

你 = 餐厅老板，AI = 服务员：
- **System Prompt** = 员工手册："你是一位热情的服务员，用敬语，推荐招牌菜"
- **User Prompt** = 客人说的话："我想吃辣的"
- **Assistant** = 服务员之前说过的话

员工手册决定了服务员的行为基调，但不会给客人看。

### System Prompt 编写技巧

```
✅ 好的 System Prompt:
"你是一位有10年经验的 Python 导师。用通俗易懂的方式解释概念，每次都要给代码示例。用中文回答，回复使用 Markdown 格式。"

❌ 差的 System Prompt:
"你是一个助手。"
```

---

## 五、Top-P 与 Top-K —— 备选词控制

### 专业解释

- **Top-K**：只从概率最高的 K 个候选词中采样
- **Top-P**（Nucleus Sampling）：从累积概率超过 P 的最小候选词集合中采样

一般只调其中一种，不要同时调。OpenAI 推荐只调 temperature 或 top_p 之一。

### 大白话

- Top-K = "海选前 K 名"：100 个候选人，只让前 40 个入围，后面 60 个直接淘汰
- Top-P = "按分数划线"：不固定人数，从高到低排，加起来够 90% 就行

**建议**：先不用管这两个参数，只调 temperature 就够了。

---

## 六、Embedding（向量嵌入）—— AI 的"意义坐标"

### 专业解释

Embedding 是将文本映射到高维向量空间（通常是 768~3072 维）的技术。语义相近的文本，向量距离也近。这是因为模型在训练时学到了"相似上下文中的词有相似的向量表示"。

**计算方式**：`余弦相似度` = 两个向量夹角的余弦值，范围 [-1, 1]，越接近 1 越相似。

### 大白话

想象一个巨大的房间，每样东西都有一个坐标：
- "猫" 在 (3, 8, 2)
- "狗" 在 (3.1, 7.9, 2.2) ← 离"猫"很近！
- "汽车" 在 (15, 2, 10) ← 离"猫"很远

AI 把每个词、每个句子放在这个"意义空间"里。离得近 = 意思相近。这就是 RAG 检索的核心——把用户问题也变成一个坐标，找到最近的文档碎片。

---

## 七、API 调用模式汇总

### 7.1 同步调用（最基本）

```python
from openai import OpenAI
client = OpenAI(api_key="sk-xxx")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "你好"}],
)
print(response.choices[0].message.content)
```

**适用场景**：脚本、CLI 工具、单次请求。

### 7.2 流式调用（打字机效果）

```python
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "讲个故事"}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

**适用场景**：聊天界面、所有需要实时反馈的场景。

### 7.3 异步调用（FastAPI 中必须用）

```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key="sk-xxx")

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "你好"}],
)
```

**适用场景**：Web 后端、高并发场景。

### 7.4 函数调用 / 工具调用

LLM 本身不能"执行"任何操作，但可以通过 Function Calling 要求外部代码执行：

```
用户: "北京天气怎么样？"
   ↓
LLM 输出: { function: "get_weather", arguments: {city: "北京"} }  ← 不是直接回答！
   ↓
你的代码: 调用天气 API，拿到 "25°C 晴天"
   ↓
再次调用 LLM: 把天气数据发给 LLM，生成回答 "北京今天 25°C，晴天"
```

**适用场景**：Agent、让 LLM 查数据库、调外部 API。

---

## 八、成本估算速查

| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|---------|---------|---------|
| gpt-4o-mini | $0.15/1M tokens | $0.60/1M tokens | 日常开发，性价比之王 |
| gpt-4o | $2.50/1M tokens | $10/1M tokens | 复杂推理、生产环境 |
| deepseek-v3 | ¥1/1M tokens | ¥2/1M tokens | 中文场景首选 |

**换算**：1M tokens ≈ 75 万个英文单词 ≈ 10~15 本书。用 gpt-4o-mini 读一本书大约只要 0.1 元人民币。

---

## 九、关键概念速查表

| 概念 | 一句话 | 前端类比 |
|------|--------|---------|
| Token | AI 的最小处理单位 | 编译后的 bytecode 单元 |
| Temperature | 创造力的"温度" | `Math.random()` 的放大倍数 |
| System Prompt | 定义 AI 的人设 | 组件的 `defaultProps` |
| Embedding | 文本的向量坐标 | CSS 中的颜色坐标 (RGB) |
| Function Calling | 让 LLM 能调函数 | 前端调用后端 API |
| Context Window | LLM 的"记忆上限" | 浏览器的 localStorage 容量 |
| Hallucination | AI 一本正经胡说八道 | 无 |

---

## 十、学习路径建议

1. **先用 GPT-4o-mini（便宜）**，调通所有 API 模式
2. **理解 Token 计费**，估算项目成本
3. **写一个好的 System Prompt**，这是 AI 应用的"产品定义"
4. **学会用 Streaming**，用户才觉得"快"
5. **Function Calling 是分水岭**，从"对话机器人"升级到"智能 Agent"

> **一句话收尾**：LLM 是一个超级接话机器人，Token 是它的基本单位，Temperature 控制它的创造力，System Prompt 定义它的人设，Function Calling 让它能干活。理解这五个概念，你就理解了 LLM 开发的 80%。
