# AI 应用与全栈开发：现场高频手撕代码题（Live Coding）精粹与通关源码

> **写在前面**：大模型开发岗位面试（无论是一面、二面还是机考）越来越倾向于**脱离 LangChain / LlamaIndex / CrewAI 等封装库**，考察候选人**脱手写原生代码**的能力。以下 6 道手撕代码题均为一线大厂和顶尖 AI 初创公司最高频的真题，代码均采用生产级规范编写（含类型注解、异常处理与最佳工程实践）。

---

## 目录
- [题目 1：脱离框架，手写原生 Function Calling 闭环状态机（含参数校验与错误反思循环）](#题目-1脱离框架手写原生-function-calling-闭环状态机含参数校验与错误反思循环)
- [题目 2：纯 NumPy 手写向量余弦相似度计算与 Top-K 近邻检索器](#题目-2纯-numpy-手写向量余弦相似度计算与-top-k-近邻检索器)
- [题目 3：手写生产级自适应指数退避重试装饰器（Exponential Backoff with Full Jitter）](#题目-3手写生产级自适应指数退避重试装饰器exponential-backoff-with-full-jitter)
- [题目 4：手写基于 Token 动态配额的上下文滑动截断与摘要归并器](#题目-4手写基于-token-动态配额的上下文滑动截断与摘要归并器)
- [题目 5：前端/全栈手撕：流式 Markdown 未闭合代码块启发式自动补全器](#题目-5前端全栈手撕流式-markdown-未闭合代码块启发式自动补全器)
- [题目 6：手写异步高并发 LLM 调用限流池（Async Semaphore + Token Bucket 速率控制）](#题目-6手写异步高并发-llm-调用限流池async-semaphore--token-bucket-速率控制)

---

## 题目 1：脱离框架，手写原生 Function Calling 闭环状态机（含参数校验与错误反思循环）

### 【题目要求】
不使用 LangChain，基于 OpenAI 官方 SDK（或标准 API 格式），实现一个能够自主判断是否调用工具、执行本地真实 Python 函数、捕获执行异常并自动反馈给大模型纠偏的闭环 Agent。要求具备最大步数限制（防止死循环）。

### 【标准实现源码】

```python
import json
from typing import Callable, Dict, Any, List
from openai import OpenAI

# 1. 模拟两个真实外部工具
def get_current_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """查询指定城市的天气"""
    # 模拟真实业务数据
    if "beijing" in location.lower() or "北京" in location:
        return {"temperature": 22, "unit": unit, "condition": "Sunny"}
    elif "shanghai" in location.lower() or "上海" in location:
        return {"temperature": 26, "unit": unit, "condition": "Cloudy"}
    return {"error": f"City '{location}' not found."}

def calculate_ticket_price(distance_km: int, discount_rate: float = 1.0) -> Dict[str, Any]:
    """根据距离和折扣率计算票价"""
    if distance_km <= 0:
        raise ValueError("distance_km must be greater than 0")
    base_price = distance_km * 0.45
    final_price = round(base_price * discount_rate, 2)
    return {"distance_km": distance_km, "final_price": final_price, "currency": "CNY"}

# 2. 工具注册中心 (Tool Registry)
TOOL_REGISTRY: Dict[str, Callable] = {
    "get_current_weather": get_current_weather,
    "calculate_ticket_price": calculate_ticket_price
}

# 3. 符合 JSON Schema 规范的工具描述
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "获取指定城市的实时天气数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称，如 '北京' 或 'Shanghai'"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_ticket_price",
            "description": "计算高铁/车票的估算价格",
            "parameters": {
                "type": "object",
                "properties": {
                    "distance_km": {"type": "integer", "description": "距离（公里）"},
                    "discount_rate": {"type": "number", "description": "折扣比例，0.1 到 1.0 之间"}
                },
                "required": ["distance_km"]
            }
        }
    }
]

# 4. 核心 Agent 执行引擎
def run_agent_loop(
    user_query: str, 
    client: OpenAI, 
    model: str = "gpt-4o", 
    max_steps: int = 5
) -> str:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "你是一个高效务实的助理。善于根据用户意图调用工具，并结合工具输出给出最终结论。"},
        {"role": "user", "content": user_query}
    ]

    for step in range(1, max_steps + 1):
        print(f"\n--- [Step {step}] 思考与决策中 ---")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        
        response_msg = response.choices[0].message
        messages.append(response_msg)  # 关键：必须把 assistant 的历史决策加入上下文

        # 判断是否需要调用工具
        if not response_msg.tool_calls:
            print("[Agent] 决策完成，输出最终答案。")
            return response_msg.content or "无返回内容"

        # 执行工具调用列表 (支持单轮多工具并发调用)
        for tool_call in response_msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args_str = tool_call.function.arguments
            call_id = tool_call.id
            
            print(f"[Agent] 计划调用工具: {fn_name}, 参数: {fn_args_str}")
            
            # 安全执行与异常捕获
            tool_fn = TOOL_REGISTRY.get(fn_name)
            if not tool_fn:
                tool_output = json.dumps({"error": f"Tool '{fn_name}' does not exist."}, ensure_ascii=False)
            else:
                try:
                    args = json.loads(fn_args_str)
                    exec_res = tool_fn(**args)
                    tool_output = json.dumps(exec_res, ensure_ascii=False)
                except json.JSONDecodeError as err:
                    # 提示大模型修正 JSON 格式
                    tool_output = json.dumps({"error": f"Invalid JSON arguments: {str(err)}. Please fix format."}, ensure_ascii=False)
                except Exception as err:
                    # 提示大模型参数错误并重试
                    tool_output = json.dumps({"error": f"Execution error: {str(err)}. Please adjust arguments."}, ensure_ascii=False)

            # 回填 tool 结果（标准 protocol 格式）
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_output
            })
            print(f"[Tool Return] {tool_output}")

    return "【熔断警告】已达到最大执行步数，任务被迫中止。"
```

---

## 题目 2：纯 NumPy 手写向量余弦相似度计算与 Top-K 近邻检索器

### 【题目要求】
很多初学者只知道 `vector_store.similarity_search()`。面试官要求：**不使用任何向量库与高阶机器学习库，仅用 Python 与 NumPy，手写批处理余弦相似度（Cosine Similarity）矩阵运算，并返回得分最高的前 K 个文档索引和分数。**

### 【核心数学原理】
$$\text{Cosine Similarity}(u, v) = \frac{u \cdot v}{\|u\|_2 \times \|v\|_2}$$
矩阵化加速：若 Query 向量 $Q \in \mathbb{R}^{1 \times D}$，知识库矩阵 $V \in \mathbb{R}^{N \times D}$。先对每行进行 L2 归一化（Normalize），直接做矩阵点积 $Q \cdot V^T$ 即可一次性得到所有相似度。

### 【标准实现源码】

```python
import numpy as np
from typing import List, Tuple, Dict, Any

class InMemoryVectorSearch:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.docs: List[Dict[str, Any]] = []
        # 初始化空矩阵 (0, dimension)
        self.vectors: np.ndarray = np.empty((0, dimension), dtype=np.float32)

    def add_documents(self, docs: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        """添加文档及其对应的 Embedding 向量"""
        emb_matrix = np.array(embeddings, dtype=np.float32)
        if emb_matrix.shape[1] != self.dimension:
            raise ValueError(f"Embedding 维度不匹配! 期望: {self.dimension}, 实际: {emb_matrix.shape[1]}")
        
        # 1. 关键优化：写入时直接进行 L2 归一化，检索时省去重复归一化开销
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        # 防止除以 0 导致 NaN
        norms = np.where(norms == 0, 1e-12, norms)
        normalized_emb = emb_matrix / norms
        
        # 2. 追加到全局矩阵
        self.vectors = np.vstack([self.vectors, normalized_emb])
        self.docs.extend(docs)

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """
        基于余弦相似度的 Top-K 检索
        """
        if len(self.docs) == 0:
            return []

        # 1. 转换并归一化 Query 向量
        q = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q_normalized = q / q_norm  # Shape: (D,)

        # 2. 核心：向量矩阵乘法 (N, D) @ (D,) -> (N,) 所有文档的分数瞬间算出
        scores = np.dot(self.vectors, q_normalized)

        # 3. 性能关键：使用 np.argpartition 替代全量 np.argsort
        # 全量排序复杂度 O(N log N)，argpartition 寻找前 K 个仅需 O(N)
        k = min(top_k, len(scores))
        top_indices = np.argpartition(scores, -k)[-k:]
        # 对这 K 个元素单独进行降序排列
        top_indices_sorted = top_indices[np.argsort(-scores[top_indices])]

        results = []
        for idx in top_indices_sorted:
            results.append((self.docs[idx], float(scores[idx])))
            
        return results

# 测试验证代码
if __name__ == "__main__":
    searcher = InMemoryVectorSearch(dimension=4)
    corpus = [
        {"id": 1, "text": "Python 编程与大模型"},
        {"id": 2, "text": "Vue 与 React 前端框架对比"},
        {"id": 3, "text": "FastAPI 高性能微服务"}
    ]
    # 模拟 Embedding (4 维)
    corpus_vectors = [
        [0.8, 0.2, 0.1, 0.0],
        [0.1, 0.9, 0.3, 0.0],
        [0.7, 0.1, 0.8, 0.1]
    ]
    searcher.add_documents(corpus, corpus_vectors)
    
    # 查询 "后端接口" 模拟向量
    q_vec = [0.75, 0.15, 0.6, 0.05]
    hits = searcher.search(q_vec, top_k=2)
    for doc, score in hits:
        print(f"得分: {score:.4f} | 内容: {doc['text']}")
```

---

## 题目 3：手写生产级自适应指数退避重试装饰器（Exponential Backoff with Full Jitter）

### 【题目要求】
在生产环境中，调用 OpenAI、Anthropic 或自建 vLLM 服务极易遇到网络抖动或 `429 (Rate Limit)`。请手写一个 Python 装饰器：
1. 支持配置最大重试次数、基础等待时间与最大等待时间。
2. 采用业内 AWS/Google 推荐的 **Full Jitter（全随机抖动）算法**，避免“惊群效应（Thundering Herd）”。
3. 自动识别异常类型，仅针对网络超时和 429 进行重试，认证失败（401）或参数非法（400）立即抛出中断。

### 【标准实现源码】

```python
import time
import random
import functools
import logging
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger(__name__)

class RateLimitException(Exception): pass
class NetworkTimeoutException(Exception): pass
class AuthenticationException(Exception): pass  # 不可重试的异常

def retry_with_exponential_backoff(
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RateLimitException, NetworkTimeoutException)
):
    """
    自适应指数退避 + 全抖动重试装饰器
    公式: sleep_time = random(0, min(max_delay, base_delay * 2^attempt))
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(f"函数 {func.__name__} 重试 {max_retries} 次后最终失败. 错误: {str(e)}")
                        raise
                    
                    # 1. 计算指数上限: min(max_delay, base_delay * 2^(attempt-1))
                    exp_cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    # 2. 全抖动 (Full Jitter): 避免数百个请求同时在同一时间重发
                    sleep_time = random.uniform(0, exp_cap)
                    
                    logger.warning(
                        f"调用 {func.__name__} 捕获异常 [{e.__class__.__name__}: {str(e)}]. "
                        f"将在 {sleep_time:.2f} 秒后发起第 {attempt}/{max_retries} 次重试..."
                    )
                    time.sleep(sleep_time)
                except Exception as unhandled_err:
                    # 不可重试的异常（如 401 密钥失效）立即向上抛出
                    logger.error(f"遭遇不可恢复异常: {str(unhandled_err)}")
                    raise
        return wrapper
    return decorator

# 实战演示
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mock_call_count = 0

    @retry_with_exponential_backoff(max_retries=3, base_delay=0.5, max_delay=4.0)
    def fetch_llm_response(prompt: str):
        global mock_call_count
        mock_call_count += 1
        if mock_call_count < 3:
            raise RateLimitException("429 Too Many Requests: TPM limit exceeded")
        return f"成功生成: {prompt}"

    res = fetch_llm_response("写一首关于秋天的诗")
    print(f"最终结果: {res}")
```

---

## 题目 4：手写基于 Token 动态配额的上下文滑动截断与摘要归并器

### 【题目要求】
多轮 Agent 对话中，必须维持核心 `System Prompt` 永久生效，但当历史多轮消息的总 Token 数超过预设上限（例如 3000 tokens）时：
1. 保证 System Prompt 绝不被删除。
2. 保持最新的 $K$ 条消息完整（维持最近的会话语境）。
3. 将中间溢出的较早会话进行滑动裁剪（或合并为摘要槽位），精准控制总 Token 预算。

### 【标准实现源码】

```python
from typing import List, Dict, Any

# 简易 Token 估算器 (无依赖快速版本: 中文约 1.2 token/字，英文约 0.25 token/词)
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # 工业界可用 tiktoken.get_encoding("cl100k_base").encode(text) 替代
    return max(1, int(len(text) * 0.8))

class ContextBudgetManager:
    def __init__(self, max_token_budget: int = 3000, keep_recent_turns: int = 4):
        self.max_budget = max_token_budget
        self.keep_recent_turns = keep_recent_turns

    def trim_context(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        messages 结构:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
        """
        if not messages:
            return []

        # 1. 拆分 System Prompt 与普通对话列表
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conversation_msgs = [m for m in messages if m.get("role") != "system"]

        # 计算 System Prompt 基础开销
        system_tokens = sum(estimate_tokens(m.get("content", "")) for m in system_msgs)
        remaining_budget = self.max_budget - system_tokens

        if remaining_budget <= 0:
            raise ValueError("System Prompt 长度已超过总 Token 预算!")

        # 2. 如果对话消息总消耗在剩余预算内，原样返回
        conv_total_tokens = sum(estimate_tokens(m.get("content", "")) for m in conversation_msgs)
        if conv_total_tokens <= remaining_budget:
            return system_msgs + conversation_msgs

        # 3. 必须截断：优先保留最近的 keep_recent_turns 条消息
        recent_msgs = conversation_msgs[-self.keep_recent_turns:]
        older_msgs = conversation_msgs[:-self.keep_recent_turns]

        recent_tokens = sum(estimate_tokens(m.get("content", "")) for m in recent_msgs)
        budget_for_older = remaining_budget - recent_tokens

        # 4. 从较早消息中逆向（从近到远）能塞进多少就塞多少
        selected_older: List[Dict[str, str]] = []
        if budget_for_older > 0:
            for msg in reversed(older_msgs):
                msg_token = estimate_tokens(msg.get("content", ""))
                if budget_for_older - msg_token >= 0:
                    selected_older.insert(0, msg)
                    budget_for_older -= msg_token
                else:
                    break

        # 5. 如果发生裁剪，插入一条系统提示告知已被截断
        if len(selected_older) < len(older_msgs):
            summary_notice = {
                "role": "system", 
                "content": f"[系统提示: 此处已自动压缩并省略了 {len(older_msgs) - len(selected_older)} 条更早的历史对话]"
            }
            return system_msgs + [summary_notice] + selected_older + recent_msgs

        return system_msgs + selected_older + recent_msgs
```

---

## 题目 5：前端/全栈手撕：流式 Markdown 未闭合代码块启发式自动补全器

### 【题目要求】
前端在流式（Streaming）接收 LLM 下发的内容时，经常遇到代码块生成了一半（如 ````typescript\nconst a = 1;`），此时直接送给 Markdown 解析器会造成页面布局闪烁、代码高亮丢失。
请写一个轻量高效的自动补全函数：
- 识别未闭合的代码块反引号（```` ``` ````），在流式渲染中间态自动补齐 `\n``` `。
- 支持识别未闭合的内联行内代码（`` `code ``）。
- 绝不破坏合法已闭合的内容。

### 【标准实现源码（TypeScript / JavaScript）】

```typescript
/**
 * 流式 Markdown 启发式增量补全器
 * 用于在前端实时渲染中间态 Token 时，避免代码块未闭合引发的闪烁
 */
export function autoCloseStreamingMarkdown(content: string): string {
  if (!content) return "";

  let result = content;

  // 1. 检查三反引号代码块 (```) 的出现频次
  // 匹配行首或行内独立的 ``` (可以带语言名，如 ```ts)
  const codeBlockRegex = /```/g;
  let blockMatches = 0;
  while (codeBlockRegex.exec(content) !== null) {
    blockMatches++;
  }

  // 如果包含奇数个 ```，说明当前正处于代码块内部未闭合状态
  if (blockMatches % 2 !== 0) {
    // 补全一个换行和结束标记
    result += "\n```";
    return result;
  }

  // 2. 如果多行代码块已闭合，再检查单行内联反引号 (`code)
  // 排除掉已经成对的 ``` 之后，计算单个 ` 的奇偶性
  // 简单安全方案：统计所有反引号总数
  const allBackticks = (content.match(/`/g) || []).length;
  // 如果剩余总反引号数是奇数，在末尾补齐单个 `
  if (allBackticks % 2 !== 0) {
    result += "`";
  }

  return result;
}

// === 测试用例演示 ===
// 用例 1: 正在输出代码片段
const streamingChunk1 = "下面是一个函数：\n```typescript\nfunction sum(a: number, b: number) {\n  return a + b;";
console.log(autoCloseStreamingMarkdown(streamingChunk1));
// 输出末尾会自动带上 \n``` ，Markdown 渲染器即可正确将其识别为高亮代码块！

// 用例 2: 已经正常闭合
const streamingChunk2 = "```bash\npnpm install\n```\n安装完毕。";
console.log(autoCloseStreamingMarkdown(streamingChunk2) === streamingChunk2); // true (原样返回)
```

---

## 题目 6：手写异步高并发 LLM 调用限流池（Async Semaphore + Token Bucket 速率控制）

### 【题目要求】
在生产后端（如 FastAPI）中，可能有 50 个并发用户同时请求大模型，但上游 API 限制了最大并发请求数为 5，且每秒最多放行 3 次调用。
请使用 Python `asyncio` 手写一个请求限流器：
1. 限制最大并发并发度（Concurrent Workers）。
2. 平滑控制每秒最大请求数（QPS / Leaky Bucket）。
3. 支持超时取消（Timeout）。

### 【标准实现源码】

```python
import asyncio
import time
from typing import Callable, Any

class AsyncLLMRateLimiter:
    def __init__(self, max_concurrent: int = 5, max_qps: float = 3.0):
        # 1. 信号量：控制最大在途并发度
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.interval = 1.0 / max_qps  # 每个请求之间的最小时间间隔
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()      # 保护时间戳竞争

    async def execute(self, async_fn: Callable[..., Any], *args, **kwargs) -> Any:
        # 进入并发槽位
        async with self.semaphore:
            # 进入速率平滑控制
            async with self.lock:
                now = time.monotonic()
                time_since_last = now - self.last_request_time
                if time_since_last < self.interval:
                    sleep_needed = self.interval - time_since_last
                    await asyncio.sleep(sleep_needed)
                self.last_request_time = time.monotonic()

            # 执行真正的底层异步调用
            return await async_fn(*args, **kwargs)

# 测试代码
async def mock_llm_request(user_id: int):
    print(f"[{time.strftime('%X')}] 用户 {user_id} 开始调用模型...")
    await asyncio.sleep(1.0)  # 模拟网络与推理耗时 1s
    print(f"[{time.strftime('%X')}] 用户 {user_id} 获得响应 ✅")
    return f"Response for {user_id}"

async def main():
    limiter = AsyncLLMRateLimiter(max_concurrent=2, max_qps=2.0)
    
    # 模拟 6 个并发请求同时涌入
    tasks = [
        limiter.execute(mock_llm_request, i)
        for i in range(1, 7)
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

