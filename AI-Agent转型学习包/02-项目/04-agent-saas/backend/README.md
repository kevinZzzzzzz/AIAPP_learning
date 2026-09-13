# Agent SaaS 后端（FastAPI + SSE）

> 模块 07（后端工程化）的产出项目

## 快速开始

```bash
cd 02-项目/04-agent-saas/backend
cp .env.example .env        # 填入 DEEPSEEK_API_KEY
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000/docs 查看自动生成的 API 文档。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 非流式问答，一次性返回完整答案 |
| POST | `/api/chat/stream` | **SSE 流式问答**（前端主用） |
| GET | `/api/sessions/{sid}` | 查会话历史 |
| DELETE | `/api/sessions/{sid}` | 清空会话 |
| GET | `/api/health` | 健康检查 |

## 不用 curl 也能测

```bash
# 非流式
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"北京天气怎么样？"}'

# 流式（能直接看到 SSE 事件滚动出来）
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"现在几点？算一下到元旦还有几天"}'
```

## SSE 事件协议

后端推送的不是裸文本，而是结构化事件（每行一个 JSON）：

```
event: thinking
data: {"content": "用户想知道天气，我需要调用工具"}

event: tool_call
data: {"tool": "get_weather", "args": {"city": "北京"}}

event: tool_result
data: {"tool": "get_weather", "result": "{...}"}

event: text
data: {"content": "北京今天"}

event: text
data: {"content": "晴，24℃"}

event: done
data: {"tokens": {"input": 850, "output": 42}, "steps": 2}
```

**为什么要设计成多种事件类型**：前端需要据此渲染不同 UI ——
工具调用显示成一张卡片、正文走打字机效果、思考过程折叠起来。
如果只推纯文本，前端就分不清"这句话是模型说的还是工具返回的"。

## 生产化改造清单

| 当前实现 | 生产应改为 | 原因 |
|---|---|---|
| 内存字典存会话 | Redis / Postgres | 多实例部署时内存不共享，且重启丢失 |
| 无鉴权 | JWT / API Key | 任何人都能调你的接口烧你的钱 |
| 无速率限制 | slowapi / 网关限流 | 防滥用 |
| 无超时控制 | 每轮设置总超时 | 防止单请求挂死 |
| print 日志 | structlog + 请求 ID | 便于追踪 |
| 单进程 | uvicorn --workers + Nginx | 并发能力 |
