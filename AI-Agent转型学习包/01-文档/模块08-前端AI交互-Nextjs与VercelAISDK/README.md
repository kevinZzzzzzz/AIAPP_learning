# 模块 08：前端 AI 交互（Next.js + Vercel AI SDK）

> 对应周次：**W11**｜预计耗时：**15–18 小时**
> 前置要求：完成模块 07
>
> **这是你的主场。** 大多数 AI 开发者的 UI 做得一塌糊涂。你能做出"体验好 + 看得懂 AI 在干什么"的产品，这是转型中最大的差异化优势。

---

## 一、这个模块要解决什么问题

**一句话**：把 Agent 的"黑箱"变成用户能看懂、能控制、能信任的界面。

学完这一模块，你应该能回答：

- AI 对话 UI 和普通聊天 UI 有什么本质不同？
- 模型正在调工具时，用户该看到什么？
- 怎么让用户"看得懂 AI 为什么这么回答"？
- 流式渲染怎么不卡？（每个 token 都 re-render 会炸）
- 用户点了"停止"，后端真的停了吗？

---

## 二、前端在 AI 产品里的四大核心价值

**别说前端在 AI 时代没用了。** 恰恰相反：**模型能力是公共资源，产品体验才是差异化的地方。**

| 价值 | 具体做什么 | 为什么重要 |
|---|---|---|
| **交互体验** | 流式渲染、可中断、可重试、状态可见 | 首字延迟决定用户感觉快不快；不能中途中止会让人焦躁 |
| **可解释性** | 展示引用来源、工具执行轨迹、推理过程 | 用户不信任"黑箱答案"。能看到依据才敢用 |
| **人机协同** | 高风险操作确认、人工接管、下一步建议 | 企业级落地的合规要求 |
| **工程化** | 类型安全、组件复用、自动化测试 | 前端的老本行，直接迁移 |

**关键洞察**：用户对 AI 的信任不是来自"答对了"，而是来自"我能验证它答得对不对"。**把验证能力做出来，是前端的核心贡献。**

---

## 三、Vercel AI SDK v5

### 3.1 ⚠️ 版本提醒（重要）

**v5 相比 v4 有几个破坏性变更**，网上大量旧教程已失效：

| 变化 | 旧写法（v4 及之前） | 新写法（v5） |
|---|---|---|
| `useChat` 导入路径 | `import { useChat } from 'ai/react'` | `import { useChat } from '@ai-sdk/react'` |
| 输入状态 | `useChat` 内部管理 `input`/`handleInputChange` | **不再管理**，自己用 `useState` |
| 发送消息 | `handleSubmit` | `sendMessage({ text })` |
| 传输配置 | 隐式 | **transport 模式**：`new DefaultChatTransport({ api })` |
| 响应创建 | `toDataStreamResponse()` | `toUIMessageStreamResponse()` |
| 消息内容 | `message.content`（字符串） | `message.parts`（数组，含文本/工具调用等类型） |
| 工具调用 | 字符串解析 | **类型化的 parts**，前端能精确识别 |

**看到 `from 'ai/react'` 的文章，说明是旧版，语法已失效。**

### 3.2 架构：服务端 + 客户端分工

```
┌──────────────────────── 服务端 ────────────────────────┐
│  app/api/chat/route.ts                                 │
│    - 持有 API Key（绝不到前端）                          │
│    - 调模型（streamText）                               │
│    - 执行工具（安全边界在这里）                           │
│    - 用 toUIMessageStreamResponse() 把流转成前端能消费的格式│
└───────────────────────┬────────────────────────────────┘
                        │ SSE 流
┌───────────────────────▼────────────────────────────────┐
│  components/chat.tsx (客户端)                           │
│    - useChat 消费流                                     │
│    - 渲染 message.parts（文本 + 工具调用 + 引用）         │
│    - sendMessage 发消息，stop 中断                      │
└─────────────────────────────────────────────────────────┘
```

> **安全铁律**：**API Key 绝不能出现在前端代码里**。如果在浏览器 `useEffect` 里初始化模型客户端，Key 会打包进客户端 bundle，任何人打开开发者工具就能偷走。所有模型调用必须在服务端（Route Handler / Server Action / 独立后端）。

### 3.3 服务端实现

```ts
// app/api/chat/route.ts
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { convertToModelMessages, jsonSchema, streamText, tool, type UIMessage } from 'ai';
import { z } from 'zod';

// 用 OpenAI 兼容接口接 DeepSeek
const deepseek = createOpenAICompatible({
  name: 'deepseek',
  baseURL: 'https://api.deepseek.com/v1',
  apiKey: process.env.DEEPSEEK_API_KEY,      // 服务端环境变量，只在服务端可见
});

export const maxDuration = 60;               // 允许最长 60 秒（部署平台需支持）

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: deepseek('deepseek-v4-flash'),
    system: `你是一个专业的技术助手。
规则：
1. 需要外部信息时调用工具，不要凭空回答
2. 计算必须使用 calculate 工具
3. 不确定的信息要明确说明`,
    messages: convertToModelMessages(messages),   // v5：把 UI 消息格式转成模型格式
    temperature: 0.3,

    // ===== 工具定义（服务端执行，前端能看到执行轨迹）=====
    tools: {
      getWeather: tool({
        description: `查询城市当前天气。
何时使用：用户询问某城市当前天气时。
何时不要使用：查询历史天气或多日预报时。`,
        inputSchema: jsonSchema({
          type: 'object',
          properties: {
            city: { type: 'string', description: '城市中文名，如「北京」' },
          },
          required: ['city'],
          additionalProperties: false,
        }),
        execute: async ({ city }: { city: string }) => {
          // 真实场景调用天气 API
          const fake: Record<string, { condition: string; temp: number }> = {
            '北京': { condition: '晴', temp: 22 },
            '上海': { condition: '多云', temp: 26 },
          };
          const d = fake[city] ?? { condition: '未知', temp: 20 };
          return { city, ...d, unit: 'celsius' };
        },
      }),

      calculate: tool({
        description: '执行数学计算。任何计算都必须用它，不要心算。',
        inputSchema: jsonSchema({
          type: 'object',
          properties: {
            expression: { type: 'string', description: '数学表达式，如 1234*5678' },
          },
          required: ['expression'],
          additionalProperties: false,
        }),
        execute: async ({ expression }: { expression: string }) => {
          // 安全求值：白名单字符
          if (!/^[0-9+\-*/(). ]+$/.test(expression)) {
            return { error: '表达式含非法字符' };
          }
          try {
            // 注意：生产环境应使用专门的表达式解析库，不要用 eval
            const result = Function(`"use strict"; return (${expression})`)();
            return { expression, result };
          } catch (e) {
            return { error: '计算失败', hint: '只支持 + - * / ( ) 和数字' };
          }
        },
      }),
    },
  });

  // v5：改成 toUIMessageStreamResponse
  return result.toUIMessageStreamResponse();
}
```

**服务端要点**：
- `convertToModelMessages()` 是 v5 新增的桥接函数（UI 消息格式 → 模型格式）
- `inputSchema` + `jsonSchema`/`zod` 定义参数（v5 支持 zod，更简洁）
- 工具在这里**执行**，前端只收到执行轨迹，不接触真实逻辑

### 3.4 客户端：基础流式聊天

```tsx
// app/chat/page.tsx
'use client';

import { useChat } from '@ai-sdk/react';           // ⚠️ v5：从 @ai-sdk/react 导入
import { DefaultChatTransport } from 'ai';
import { useState, useRef, useEffect } from 'react';

export default function ChatPage() {
  const [input, setInput] = useState('');           // v5：自己管理输入状态

  const { messages, sendMessage, status, stop, error, regenerate } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),   // v5：transport 模式
  });

  const isLoading = status === 'submitted' || status === 'streaming';
  const bottomRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage({ text: input });                   // v5：sendMessage({ text })
    setInput('');
  };

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* ===== 消息列表 ===== */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id}
               className={message.role === 'user' ? 'text-right' : 'text-left'}>
            <div className={`inline-block max-w-[80%] rounded-lg px-4 py-2 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-900'
            }`}>
              {/* ⚠️ v5 关键变化：message.parts 是数组，不是 message.content */}
              {message.parts.map((part, i) => {
                if (part.type === 'text') {
                  return <span key={i} className="whitespace-pre-wrap">{part.text}</span>;
                }
                if (part.type === 'tool-getWeather') {         // 工具调用（命名规则：tool-<名称>）
                  return <ToolCallCard key={i} part={part} />;
                }
                if (part.type === 'tool-calculate') {
                  return <ToolCallCard key={i} part={part} />;
                }
                return null;
              })}
            </div>
          </div>
        ))}

        {/* 加载状态：让用户知道 AI 在干什么 */}
        {status === 'submitted' && (
          <div className="text-gray-400 text-sm">正在思考...</div>
        )}

        {/* 错误提示 + 重试 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm">
            <p className="text-red-700">生成失败：{error.message}</p>
            <button onClick={() => regenerate()}
                    className="mt-2 text-red-600 underline hover:no-underline">
              重试
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ===== 输入区 ===== */}
      <form onSubmit={handleSubmit} className="border-t p-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题..."
          disabled={isLoading}
          className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
        />
        {isLoading ? (
          // 流式进行中：显示"停止"（用户能中断，这是关键体验）
          <button type="button" onClick={stop}
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg">
            停止
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-300">
            发送
          </button>
        )}
      </form>
    </div>
  );
}
```

### 3.5 工具执行轨迹卡片（差异化关键）

**这是让用户"看懂 AI 在干什么"的核心组件。** 大多数 AI 产品只显示"正在思考…"，你要把执行过程显示出来。

```tsx
// components/tool-call-card.tsx
'use client';

import { useState } from 'react';

type ToolPart = {
  type: string;
  toolCallId: string;
  state: 'input-streaming' | 'input-available' | 'output-available' | 'output-error';
  input?: unknown;
  output?: unknown;
  errorText?: string;
};

const TOOL_LABELS: Record<string, { label: string; icon: string }> = {
  'tool-getWeather':  { label: '查询天气', icon: '🌤' },
  'tool-calculate':   { label: '执行计算', icon: '🧮' },
  'tool-search_web':  { label: '联网搜索', icon: '🔍' },
};

export function ToolCallCard({ part }: { part: ToolPart }) {
  const [expanded, setExpanded] = useState(false);
  const meta = TOOL_LABELS[part.type] ?? { label: part.type, icon: '🔧' };

  const stateText = {
    'input-streaming':   '准备调用...',
    'input-available':   '执行中...',
    'output-available':  '完成',
    'output-error':      '失败',
  }[part.state];

  const isError = part.state === 'output-error';

  return (
    <div className={`my-2 rounded-lg border text-sm ${
      isError ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50'
    }`}>
      {/* 一行摘要：一眼看出在干什么 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-black/5"
      >
        <span>{meta.icon}</span>
        <span className="font-medium">{meta.label}</span>
        <span className={isError ? 'text-red-600' : 'text-gray-500'}>
          {stateText}
        </span>
        {/* 执行中的动画 */}
        {(part.state === 'input-streaming' || part.state === 'input-available') && (
          <span className="ml-auto inline-block w-3 h-3 border-2 border-blue-500
                           border-t-transparent rounded-full animate-spin" />
        )}
        <span className="ml-auto text-gray-400">{expanded ? '收起' : '展开'}</span>
      </button>

      {/* 展开：展示参数和结果（可解释性） */}
      {expanded && (
        <div className="border-t px-3 py-2 space-y-2">
          {part.input != null && (
            <div>
              <div className="text-xs text-gray-500 mb-1">参数</div>
              <pre className="bg-white rounded p-2 text-xs overflow-x-auto">
                {JSON.stringify(part.input, null, 2)}
              </pre>
            </div>
          )}
          {part.output != null && (
            <div>
              <div className="text-xs text-gray-500 mb-1">结果</div>
              <pre className="bg-white rounded p-2 text-xs overflow-x-auto">
                {JSON.stringify(part.output, null, 2)}
              </pre>
            </div>
          )}
          {part.errorText && (
            <div className="text-red-600 text-xs">错误：{part.errorText}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

**为什么这个组件重要**：用户看到"正在调用查询天气…完成"，就知道 AI 在干活、干得怎么样。**这比转圈的 loading 好十倍。** 而且出错时用户能立刻看到失败原因，而不是困惑"为什么它不回答"。

### 3.6 引用来源卡片

```tsx
// components/citation-card.tsx
'use client';

type Citation = {
  index: number;
  source: string;
  title?: string;
  snippet: string;
  url?: string;
};

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-200">
      <div className="text-xs text-gray-500 mb-2">参考来源</div>
      <div className="space-y-1">
        {citations.map((c) => (
          <a
            key={c.index}
            href={c.url ?? '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-2 text-xs text-gray-600 hover:text-blue-600
                       hover:bg-gray-50 rounded p-1.5 transition-colors"
          >
            <span className="inline-flex items-center justify-center w-5 h-5
                             bg-blue-100 text-blue-700 rounded text-[10px] font-medium shrink-0">
              {c.index}
            </span>
            <span className="flex-1">
              <span className="font-medium">{c.source}</span>
              {c.title && <span className="text-gray-400"> · {c.title}</span>}
              <div className="text-gray-500 mt-0.5 line-clamp-2">{c.snippet}</div>
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}
```

### 3.7 性能：流式渲染的优化

**问题**：每个 token 到达都触发 React re-render，长回答时会有几千次渲染，导致卡顿。

**四个优化手段**：

```tsx
// 1. 消息组件用 React.memo 避免无关重渲染
const MessageItem = React.memo(function MessageItem({ message }: { message: Message }) {
  return <div>{/* ... */}</div>;
});

// 2. 长列表虚拟化（消息很多时）
import { useVirtualizer } from '@tanstack/react-virtual';

function MessageList({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-full overflow-y-auto">
      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map((vi) => (
          <div key={vi.key}
               style={{ position: 'absolute', top: 0, left: 0,
                        width: '100%', transform: `translateY(${vi.start}px)` }}>
            <MessageItem message={messages[vi.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}

// 3. 自动滚动用 requestAnimationFrame 节流（避免每次渲染都滚）
const scrollToBottom = useCallback(() => {
  requestAnimationFrame(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'auto' });
  });
}, []);

// 4. 只在用户已经贴底时才自动滚动（用户往上翻阅时别抢滚动条）
const [autoScroll, setAutoScroll] = useState(true);
const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
  const el = e.currentTarget;
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
  setAutoScroll(atBottom);
};
```

### 3.8 首字延迟（TTFT）优化

**这是用户感知"快慢"的唯一指标。** 总耗时 10 秒但首字 0.3 秒，用户觉得"挺快"；总耗时 3 秒但首字 2.5 秒，用户觉得"好慢"。

| 优化手段 | 效果 |
|---|---|
| **服务端流式**（不要等完整响应） | 决定性因素 |
| **减少首 token 前的处理**——不要在流开始前做检索/工具调用 | 有明显效果 |
| **模型选择**——轻量模型首字更快 | 中等 |
| **Prompt 优化**——缩短 system prompt（有缓存更好） | 中等 |
| **Edge Runtime** 部署 | 减少冷启动 |
| **骨架屏 / 状态提示**——让用户知道在处理 | 改变感知，不改变实际 |
| **乐观 UI**——立刻显示用户消息 | 改变感知 |

```tsx
// 乐观 UI：发送后立刻显示用户消息（不等服务端确认）
// useChat 默认已做这件事（messages 里立刻有 user 消息）
// 你要做的是：立刻清空输入框 + 显示"正在思考"

// 带阶段提示的加载状态（比干转圈好得多）
function LoadingIndicator({ status }: { status: string }) {
  const text = {
    submitted: '正在理解你的问题...',
    streaming: '正在生成回答...',
  }[status] ?? '';

  if (!text) return null;
  return (
    <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
      <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
      {text}
    </div>
  );
}
```

### 3.9 用独立后端（Python FastAPI）的方案

如果你的 Agent 逻辑在 Python（推荐，见模块 07），有两种接法：

**方案 A：Next.js 代理转发（推荐，简单）**

```ts
// app/api/chat/route.ts —— Next.js 只做代理，转发给 Python 后端
export async function POST(req: Request) {
  const body = await req.json();
  const upstream = await fetch(`${process.env.PYTHON_BACKEND}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': 'user-from-session',      // 服务端注入，前端伪造不了
    },
    body: JSON.stringify(body),
  });

  // 直接把上游 SSE 流转发给前端（注意：不要 buffer）
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'X-Accel-Buffering': 'no',
      'Cache-Control': 'no-cache',
    },
  });
}
```

**方案 B：前端直连 Python 后端**

```tsx
const { messages, sendMessage, status } = useChat({
  transport: new DefaultChatTransport({
    api: `${process.env.NEXT_PUBLIC_API_BASE}/api/chat`,
  }),
});
```

**注意**：直连时必须让 Python 后端支持 AI SDK 的数据流协议，或者自己解析 SSE（工作量更大）。**推荐方案 A**，用 Next.js 做代理，顺便可以做鉴权和日志。

---

## 四、知识点清单

- [ ] 前端在 AI 产品里的四大价值
- [ ] 用户信任来自"可验证"而非"答得对"
- [ ] AI SDK v5 的 7 个关键变化（对比 v4）
- [ ] 服务端/客户端分工，为什么 API Key 必须在服务端
- [ ] `streamText` + `convertToModelMessages` + `toUIMessageStreamResponse` 的作用
- [ ] `useChat` 的返回值：messages / sendMessage / status / stop / error / regenerate
- [ ] `message.parts` 数组结构（text / tool-xxx 类型）
- [ ] 工具执行轨迹卡片的设计（摘要 + 可展开 + 状态）
- [ ] 引用来源卡片的渲染与可点击
- [ ] 流式渲染的四项性能优化
- [ ] 首字延迟（TTFT）的六项优化手段
- [ ] 可中断（stop）与重试（regenerate）的实现
- [ ] 独立 Python 后端的两种接法及取舍
- [ ] 错误边界与降级提示

---

## 五、常见坑

### 坑 1：API Key 暴露在前端
**后果**：Key 被打包进客户端代码，任何人 F12 就能偷走，然后拿去刷你的额度。**这是最严重的事故。**
**正确做法**：所有模型调用在服务端（Route Handler / Server Action / Python 后端）。

### 坑 2：用 `from 'ai/react'` 导入 useChat
**后果**：v5 已改到 `@ai-sdk/react`，旧导入会报错或行为异常。
**正确做法**：`import { useChat } from '@ai-sdk/react'`。

### 坑 3：访问 `message.content`
**后果**：v5 里消息内容是 `message.parts` 数组，`message.content` 拿不到东西（渲染空白）。
**正确做法**：遍历 `message.parts`，按 `part.type` 分别渲染。

### 坑 4：每个 token 都触发全量 re-render
**后果**：长回答时页面卡顿，输入框输入延迟。
**正确做法**：`React.memo` + 虚拟列表 + 滚动节流。

### 坑 5：不显示工具执行状态
**后果**：用户只看到转圈，不知道 AI 卡住了还是在干活，体验差。
**正确做法**：渲染工具调用卡片，显示"正在查询…/完成"和参数结果。

### 坑 6：自动滚动抢用户滚动条
**后果**：用户往上翻看历史时被强行拽回底部（极其恼人）。
**正确做法**：检测是否在底部，只有当用户在底部时才自动滚动。

### 坑 7：点了"停止"但后端还在跑
**后果**：token 继续消耗，用户下次发消息可能收到上一次的残留。
**正确做法**：`stop()` 会中断 fetch，后端要捕获 `CancelledError` 停止生成（模块 07 讲过）。

### 坑 8：不处理错误状态
**后果**：请求失败后界面卡在"正在思考"或者什么都不显示。
**正确做法**：渲染 `error`，提供 `regenerate()` 重试按钮。

### 坑 9：流式在部署后失效
**后果**：本地流式正常，上线变成一次性返回。
**正确做法**：检查代理层的缓冲设置（`X-Accel-Buffering: no`、Nginx `proxy_buffering off`、Vercel 的 `maxDuration`）。

### 坑 10：只做"好看"不做"可解释"
**后果**：UI 很炫，但用户不知道答案从哪来、AI 干了什么，不敢信任。
**正确做法**：**把可解释性当作核心功能做**——引用来源、工具轨迹、推理过程。这是前端能建立的最大差异化。

---

## 六、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 用 AI SDK v5 搭一个基础流式聊天页 | ⭐⭐ |
| 2 | 实现工具执行轨迹卡片（含展开/收起、状态、错误态） | ⭐⭐⭐⭐ |
| 3 | 实现引用来源卡片，点击能跳转对应内容 | ⭐⭐⭐ |
| 4 | 实现"停止生成"和"重新生成" | ⭐⭐⭐ |
| 5 | 用 500 条消息测试滚动性能，用虚拟列表优化 | ⭐⭐⭐⭐ |
| 6 | 实现阶段提示（"正在检索…/正在生成…"），替代简单转圈 | ⭐⭐⭐ |
| 7 | 测量首字延迟，做优化前后对比 | ⭐⭐⭐⭐ |
| 8 | 实现会话侧边栏（列表 + 切换 + 重命名 + 删除） | ⭐⭐⭐ |
| 9 | 实现移动端适配（响应式布局 + 触摸优化） | ⭐⭐⭐ |
| 10 | **【项目任务】** 完成项目 04 的前端部分 | ⭐⭐⭐⭐⭐ |

**任务 2 和 3 是核心。** 这两个组件做好了，你的项目在面试演示时就能形成明显差异——因为大多数候选人的 AI 应用只有"输入框 + 输出文字"。

---

## 七、自测题

**Q1：为什么 API Key 不能放在前端？**
<details><summary>参考答案</summary>
因为前端代码会完整打包发送到浏览器。任何用户按 F12 打开开发者工具，或者在网络面板看请求，都能拿到 Key。拿到后可以随意调用你的额度。正确做法是所有模型调用在服务端（Route Handler、Server Action、或独立的 Python 后端）执行，前端只跟自己的后端通信。这也是为什么 Vercel AI SDK 的架构是"服务端 streamText + 客户端 useChat"。
</details>

**Q2：AI SDK v5 的 `useChat` 相比 v4 有什么变化？**
<details><summary>参考答案</summary>
① 导入路径从 `ai/react` 改为 `@ai-sdk/react`；② 不再内部管理输入状态（input/handleInputChange），要自己用 `useState`；③ 发送用 `sendMessage({ text })` 而不是 `handleSubmit`；④ 引入 transport 模式，用 `new DefaultChatTransport({ api })` 配置；⑤ 服务端用 `toUIMessageStreamResponse()` 替代 `toDataStreamResponse()`；⑥ 消息内容从 `message.content` 字符串改成 `message.parts` 数组（含 text、tool-xxx 等类型化片段）；⑦ 工具调用变成类型化的 parts，前端能精确识别和渲染。
</details>

**Q3：用户看不到任何反馈，只说"卡住了"。怎么改善？**
<details><summary>参考答案</summary>
要做分层反馈：① **立刻显示用户消息**（乐观 UI），让用户知道消息发出去了；② **阶段提示**——"正在理解问题…/正在检索资料…/正在调用工具…/正在生成回答…"，让用户知道系统在干什么，而不是干转圈；③ **工具执行轨迹卡片**——显示调用了什么工具、参数是什么、执行成功还是失败；④ **流式逐字输出**——首字尽快出现，让用户看到进展；⑤ **首字延迟优化**——减少流开始前的处理，或提前发送一个空 token 作为"心跳"。核心原则：**用户宁可知道"在慢慢处理"，也不愿意面对无反馈的等待。**
</details>

**Q4：为什么要把工具执行轨迹展示给用户？**
<details><summary>参考答案</summary>
三个理由：① **建立信任**——用户看到"查了天气 API，得到 22℃"，就知道答案有依据，不是编的；② **可调试**——出错时用户能看到"工具调用失败：城市名未识别"，而不是困惑"为什么它不回答我"；③ **可控**——用户发现 AI 理解错了（查了错误的城市），可以立即中断纠正。这是前端在 AI 产品里最能创造价值的地方，因为后端无法决定"用户知道多少"。大多数竞品只显示"正在思考"，做了这一步就能形成明显差异。
</details>

**Q5：流式渲染卡顿怎么优化？**
<details><summary>参考答案</summary>
四个方面：① **组件级隔离**——用 `React.memo` 包裹消息组件，避免一条消息更新导致所有消息重渲染；② **虚拟列表**——消息多时用 `@tanstack/react-virtual`，只渲染可视区域；③ **滚动节流**——用 `requestAnimationFrame` 做自动滚动，不要每次渲染都触发；④ **智能自动滚动**——只在用户已贴底时自动滚动，用户往上翻时不要抢滚动条。另外要注意：不要在渲染函数里做重计算（如解析 Markdown），应该用 `useMemo` 缓存。
</details>

**Q6：首字延迟（TTFT）为什么比总耗时更重要？**
<details><summary>参考答案</summary>
因为用户感知的"快慢"主要由等待**第一个字**出现的时间决定。总耗时 10 秒但首字 0.3 秒 → 用户看到内容在流动，感觉"响应很快"；总耗时 3 秒但首字 2.5 秒 → 用户面对 2.5 秒的空白等待，感觉"好慢"。指标上，TTFT 是可优化的（减少流开始前的处理、提前发送状态事件），而总耗时受模型生成速度限制。产品优化的优先级是：先保 TTFT，再优化总时长。
</details>

**Q7：用户点了"停止"，后端怎么知道要停？**
<details><summary>参考答案</summary>
`stop()` 会中断前端的 fetch 请求，HTTP 连接关闭。服务端会收到连接断开的信号——在 FastAPI 里表现为 `asyncio.CancelledError`，在 Node 里表现为请求的 `abort` 事件。后端应该捕获这个信号，停止模型调用（否则还在烧 token），并把已生成的部分内容保存（用户可能想保留）。关键点：**必须显式处理这个信号**，不处理的后果是用户已经离开但服务端还在生成。
</details>

**Q8：你的 Agent 逻辑用 Python，前端用 Next.js，怎么接？**
<details><summary>参考答案</summary>
两种方案。**方案 A（推荐）**：Next.js 做代理——前端请求 Next.js 的 Route Handler，Route Handler 转发给 Python 后端，把上游的 SSE 流直接透传给前端（注意不要 buffer，设置 `X-Accel-Buffering: no`）。好处是可以在代理层统一做鉴权、日志、注入用户身份，前端不用直接接触后端地址。**方案 B**：前端直连 Python 后端，但需要 Python 端实现 AI SDK 的数据流协议，或者前端自己解析 SSE（用 `fetch` + `ReadableStream` 手动处理），工作量更大且容易出错。所以推荐方案 A。
</details>

**Q9：AI 对话 UI 和普通聊天 UI 的本质区别是什么？**
<details><summary>参考答案</summary>
本质区别是**"回答是一个过程"而不是"一个结果"**。普通聊天：消息是原子性的，发出即完整。AI 对话：回答是逐步生成的，中间还有工具调用、检索、推理等阶段。所以 AI 对话 UI 必须处理：① **中间状态**（生成中、调用工具中、检索中）；② **可中断可重试**（生成了一半发现跑偏了怎么办）；③ **可解释性**（答案的来源、依据、推理过程）；④ **非确定性**（同样的输入可能给不同答案，用户需要能重新生成）。这些是普通聊天 UI 完全不需要考虑的。
</details>

---

## 八、延伸阅读

| 主题 | 资源 |
|---|---|
| Vercel AI SDK 官方文档（**必读**） | https://sdk.vercel.ai/docs |
| AI SDK v5 迁移指南 | https://sdk.vercel.ai/docs/migration-guide |
| Next.js 文档 | https://nextjs.org/docs |
| shadcn/ui（现成组件库） | https://ui.shadcn.com/ |
| TanStack Virtual（虚拟列表） | https://tanstack.com/virtual/latest |
| Tailwind CSS | https://tailwindcss.com/docs |

---

## 九、完成标志

- [ ] 一个流式聊天页面（打字机效果、可中断、可重试）
- [ ] 工具执行轨迹卡片（含状态、参数、结果、错误）
- [ ] 引用来源卡片（可点击跳转）
- [ ] 会话侧边栏（列表、切换、删除）
- [ ] 性能优化（虚拟列表 + memo + 滚动节流）
- [ ] **项目 04 前端完成**
- [ ] 能讲清本模块知识点清单的每一条

**下一步**：进入模块 09，学习评测、可观测性与成本控制——证明你的系统真的能用。
