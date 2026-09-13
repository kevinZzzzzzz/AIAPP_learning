# 项目 04：全栈 Agent 应用（SSE 流式）

> 对应模块：**模块 07（后端工程化）+ 模块 08（前端交互）+ 模块 10（部署上线）**
> 建议在第 11–12 周动手｜难度：★★★★☆

把前面三个 CLI 项目变成一个**能给别人用的 Web 服务**：FastAPI 后端 + SSE 流式推送 + 可视化前端。

---

## 这个项目解决了什么前面没解决的问题

前三个项目都是你在终端里自己跑。真实产品必须：

| 问题 | 本项目对应方案 |
|---|---|
| 多个用户同时用 | 会话隔离（session_id） |
| 用户要实时看到输出 | SSE 流式推送 |
| 用户要看见"它在干什么" | 结构化事件（tool_call / tool_result） |
| 前端要能知道后端活着 | 健康检查接口 |
| 用户关掉页面不能白烧钱 | 客户端断开检测 |
| 服务要能部署上线 | uvicorn + Nginx 配置说明 |

---

## 目录结构

```
04-agent-saas/
├── backend/
│   ├── app/
│   │   ├── main.py             # ⭐ FastAPI 应用 + SSE 接口
│   │   ├── agent_service.py    # ⭐ Agent 异步流式改造（核心）
│   │   ├── sessions.py         # 会话管理（含并发保护和过期清理）
│   │   ├── tools.py            # 工具集（Web 版，全非阻塞）
│   │   └── config.py
│   ├── pyproject.toml
│   └── .env.example
└── frontend/
    └── index.html              # 单文件前端（原生 JS 解析 SSE，零依赖）
```

**为什么前端用单文件 HTML 而不是 Next.js**：
本项目的学习重点是 **SSE 协议本身** —— 事件怎么发、怎么收、怎么解析。
Next.js + Vercel AI SDK 会把这一层封装起来（`useChat` 一行搞定），
你就看不到 `reader.read()` 和 `\n\n` 分帧这些细节了。
先把原始 SSE 写一遍，再去看 AI SDK 的封装，你会秒懂它在干什么。

---

## 快速开始

### 1. 启动后端

```bash
cd 02-项目/04-agent-saas/backend
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 2. 打开前端

直接双击 `frontend/index.html`，或用任意静态服务器：

```bash
cd 02-项目/04-agent-saas/frontend
python3 -m http.server 3000
# 然后浏览器打开 http://localhost:3000
```

### 3. 试这些能触发工具调用的提问

```
北京今天天气怎么样？                    → 单工具
现在几点？算一下到 2027 年元旦还有几天   → 多步串联
公司的退款政策是什么？                   → 知识库检索
```

你会看到界面上**实时**出现：思考过程 → 工具调用卡片（带参数）→ 工具返回结果 → 正文打字机效果 → 用量统计。

---

## SSE 事件协议（本项目最重要的设计）

后端推的不是裸文本，而是 7 种结构化事件：

| 事件 | 含义 | 前端渲染 |
|---|---|---|
| `session` | 下发 session_id | 存起来后续用 |
| `thinking` | 模型这步的思考 | 灰色斜体 |
| `tool_call` | 要调工具了（含参数） | 紫色卡片 + loading |
| `tool_result` | 工具返回了 | 卡片里追加结果 |
| `text` | 正文片段 | 打字机效果 |
| `done` | 完成（含用量成本） | 底部统计行 |
| `error` | 出错 | 红色卡片 |

**为什么不用裸文本流**：前端分不清"这句话是模型说的还是工具返回的"，
就没法把工具调用渲染成卡片。事件协议是前后端解耦的关键。

原始 SSE 报文长这样（注意空行分隔）：

```
event: tool_call
data: {"type":"tool_call","tool":"get_weather","args":{"city":"北京"}}

event: text
data: {"type":"text","content":"北京今天"}

```

---

## 四个生产级工程细节（最容易踩坑的地方）

### 1. Nginx 缓冲会毁掉流式效果

这是部署后最常见的"本地好好的，上线就不流式了"问题。

Nginx 默认会缓冲后端响应，攒够一批才发给浏览器 —— 打字机效果就没了。

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;              # 关键 1
    proxy_cache off;
    proxy_read_timeout 300s;          # 关键 2：Agent 可能跑很久，默认 60s 会断
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

代码里也加了响应头 `X-Accel-Buffering: no`（专门给 Nginx 看的），双保险。

### 2. 客户端断开必须停止生成

用户关掉页面后，如果后台还在跑 Agent，就是纯烧钱。

```python
async for ev in run_agent_stream(...):
    if await request.is_disconnected():
        logger.info("客户端断开，停止生成")
        return          # 立刻停止，不再调用模型
```

### 3. 异步：不能用同步 SDK 阻塞事件循环

```python
# ❌ 致命错误：同步调用会阻塞整个事件循环，
#    所有其他用户的请求在这期间全部卡死
resp = client.chat.completions.create(...)

# ✅ 必须用 async 版本
resp = await client.chat.completions.create(...)
```

用 `AsyncOpenAI` 而不是 `OpenAI`。这个错误在低并发时看不出来，
一上量就全站超时。

### 4. 同一会话并发请求要加锁

用户手快连点两次发送，两个协程同时读写 history，会导致消息丢失或乱序。

`Session` 里用了 `asyncio.Lock`。生产环境换 Redis 后要注意用事务保证原子性。

---

## 生产化改造清单（部署前必须做）

| 当前实现 | 生产应改为 | 原因 |
|---|---|---|
| 内存字典存会话 | Redis / Postgres | 多实例不共享，重启就丢 |
| 无鉴权 | JWT / API Key | 否则任何人都能烧你的额度 |
| 无速率限制 | slowapi / 网关限流 | 防滥用 |
| 无总超时 | 每轮请求设 timeout | 防单请求挂死 |
| `print`/`logging` | structlog + trace_id | 便于追踪一次请求的全链路 |
| 单进程 uvicorn | `--workers 4` + Nginx | 并发能力 |
| 无信号处理 | 优雅关闭（等请求跑完） | 部署时不丢请求 |

---

## 进阶练习

1. **加"停止生成"按钮（⭐️⭐️）**：前端 abort 请求，后端靠 `is_disconnected` 感知。体会流式场景下"取消"怎么实现。
2. **加工具确认（⭐️⭐️⭐️）**：加一个 `write_file` 工具，触发时推 `requires_confirm` 事件并暂停，前端弹窗确认后调 `/api/confirm` 恢复执行。这就是 LangGraph `interrupt()` 做的事。
3. **会话持久化到 Redis（⭐️⭐️⭐️）**：加 redis 依赖，启动两个 worker 实例，验证会话能跨实例共享。
4. **接真实 RAG（⭐️⭐️⭐️）**：把 `search_knowledge_base` 换成项目 02 的 RAG，观察 Agent 自主决定检索次数。
5. **换成 Next.js + AI SDK（⭐️⭐️⭐️）**：用 `useChat` 重写前端，对比"手写 SSE 解析"和"框架封装"的差异。**这时候你才真正理解 AI SDK 帮你省了什么。**

---

## 常见坑

| 现象 | 原因 | 解决 |
|---|---|---|
| 本地流式正常，上线变一次性输出 | Nginx 缓冲 | `proxy_buffering off` |
| 请求 60 秒后断开 | Nginx 默认 `proxy_read_timeout 60s` | 调到 300s |
| 浏览器 CORS 报错 | 后端没配 `CORS_ORIGINS` | `.env` 里加上前端地址 |
| 高并发时全站卡顿 | 用了同步 SDK 阻塞事件循环 | 换成 `AsyncOpenAI` |
| 会话历史串了 | 前端没传 `session_id` | 从 `session` 事件里取并存下来 |
| 页面关了还在烧钱 | 没做断开检测 | `await request.is_disconnected()` |
| SSE 事件前端的 `data` 解析不到 | JSON 里有未转义的换行 | 后端用 `json.dumps`（自动转义 `\n`） |
