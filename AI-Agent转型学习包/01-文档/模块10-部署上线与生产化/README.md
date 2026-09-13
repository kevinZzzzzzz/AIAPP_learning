# 模块 10：部署上线与生产化

> 对应周次：**W12（后半）**｜预计耗时：**8–10 小时**
> 前置要求：完成模块 07、08、09
>
> **本模块目标**：把你的项目真正跑在线上，拿到一个可以放进简历和面试演示的可访问链接。

---

## 一、这个模块要解决什么问题

**一句话**：从"能在我的电脑上跑"到"别人能通过一个链接访问并使用"。

学完这一模块，你应该能回答：

- 前后端怎么部署？各选什么平台？
- 环境变量怎么管理？密钥怎么安全地传上去？
- 数据库在云上放哪？
- 怎么知道线上服务挂了？
- 域名和 HTTPS 怎么配？

---

## 二、部署架构选择

### 2.1 三种架构

**架构 A：全栈 Next.js（最简单，推荐起步）**

```
用户 → Vercel（Next.js 前端 + API Routes）
              ├→ 模型 API（DeepSeek）
              └→ 向量库（云服务如 Pinecone，或 Vercel Postgres + pgvector）
```

**优点**：一个平台搞定，部署零配置，自动 HTTPS + CDN。
**缺点**：Serverless 有执行时长限制（免费版通常 10–60s），长任务 Agent 可能超时。

**架构 B：前后端分离（推荐，生产级）**

```
用户 → Vercel（Next.js 前端）
              ↓
        Railway / Render（Python FastAPI 后端）
              ├→ 模型 API
              └→ PostgreSQL（含 pgvector）
```

**优点**：后端能跑长时间任务；Python 生态最全（LangGraph 等）；前后端独立扩容。
**缺点**：两套部署，需要配 CORS 和 API 地址。

**架构 C：容器化 + VPS（成本可控，适合长期）**

```
用户 → Nginx（HTTPS + 反代）
              ├→ Next.js（Docker 容器）
              └→ FastAPI（Docker 容器）
                    └→ PostgreSQL（Docker 或托管）
```

**优点**：完全可控，成本最低（一台 2C4G 服务器约 ¥60/月）。
**缺点**：运维工作自己做（备份、监控、安全更新）。

**选择建议**：

| 你的情况 | 推荐 |
|---|---|
| 学习 + 面试演示 | **架构 A**（最快见效） |
| 项目有长任务 / 复杂 Agent | **架构 B** |
| 想练运维 / 长期运营 | 架构 C |

**先选 A 跑通，需要时再升级到 B。不要一开始就搞 K8s。**

---

## 三、环境变量与密钥管理

### 3.1 铁律

| 规则 | 说明 |
|---|---|
| **密钥绝不进 Git** | `.env` 必须在 `.gitignore` 里。已提交的要立刻轮换密钥 |
| **前端变量会公开** | `NEXT_PUBLIC_*` 前缀的变量会打包进客户端，**绝不能放密钥** |
| **平台变量优先** | 生产环境用平台的环境变量面板，不用 `.env` 文件 |
| **最小权限** | 给部署用的密钥只开必要的权限，能只读就不给写 |
| **定期轮换** | 怀疑泄露立即轮换，不必纠结原因 |

### 3.2 Git 安全检查（提交前必做）

```bash
# 检查是否有 .env 被提交
git ls-files | grep -E "\.env"

# 如果已经在历史提交里了，要清除历史（不只是删除当前文件）
# 用 git-filter-repo（推荐）或 BFG
brew install git-filter-repo
git filter-repo --path .env --invert-paths

# 检查代码里是否有硬编码的密钥
rg -i "sk-[a-zA-Z0-9]{20,}" --glob '!node_modules'
rg -i "api[_-]?key\s*=\s*['\"]" --glob '!node_modules'
```

> ⚠️ **重要**：如果密钥已经推到 GitHub，**必须立即去平台撤销并重新生成**。删除文件或改历史都不够——爬虫可能已经抓到了（公开仓库的密钥通常在几分钟内被发现）。**撤销比隐藏重要。**

### 3.3 `.gitignore` 模板

```gitignore
# 环境变量
.env
.env.local
.env.*.local

# Python
.venv/
__pycache__/
*.pyc
uv.lock.bak

# Node
node_modules/
.next/
out/
dist/

# 数据
*.db
*.sqlite
chroma_db/
data/
traces.db
cache.db

# 系统
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

---

## 四、部署实战

### 4.1 后端部署到 Railway

**Railway 适合**：Python/FastAPI 服务，支持长任务，配置简单，有免费额度。

```dockerfile
# Dockerfile（后端）
FROM python:3.12-slim

WORKDIR /app

# 安装 uv（快速依赖管理）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 先复制依赖文件（利用 Docker 层缓存）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

# 非 root 用户运行（安全实践）
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# 生产用多 worker（注意：SSE 长连接下 worker 数要合理）
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

```bash
# 部署步骤
# 1. 推送到 GitHub
git add . && git commit -m "deploy" && git push

# 2. Railway 上 New Project → Deploy from GitHub
# 3. 添加环境变量（在 Settings → Variables）
#    DEEPSEEK_API_KEY=sk-xxx
#    DATABASE_URL=postgresql://...
#    CORS_ORIGINS=["https://your-app.vercel.app"]
# 4. 添加 PostgreSQL 插件（一键，自动注入 DATABASE_URL）
```

**关键配置**：

| 配置项 | 值 | 说明 |
|---|---|---|
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | **必须用平台注入的 $PORT** |
| Healthcheck Path | `/health` | 平台靠它判断服务是否健康 |
| Restart Policy | On Failure | 崩溃自动重启 |

> ⚠️ **最常见的部署错误：端口写死**。云平台会注入 `$PORT` 环境变量，你必须监听它，而不是固定 8000。否则容器起来了但健康检查失败。

### 4.2 前端部署到 Vercel

```bash
# 方式一：命令行
npm i -g vercel
vercel            # 首次会引导登录和项目配置
vercel --prod     # 部署到生产环境

# 方式二：GitHub 集成（推荐）
# vercel.com → New Project → 导入仓库 → 自动部署
# 之后每次 push 自动部署
```

**环境变量**（Vercel Dashboard → Settings → Environment Variables）：

```bash
# 服务端变量（不暴露给浏览器）
DEEPSEEK_API_KEY=sk-xxx
PYTHON_BACKEND_URL=https://your-backend.up.railway.app

# 客户端变量（会暴露！只能放非敏感信息）
NEXT_PUBLIC_APP_NAME=My Agent App
```

**Serverless 时长限制处理**：

```ts
// app/api/chat/route.ts
export const maxDuration = 60;        // 秒。免费版通常上限 10-60s，Pro 版更长
export const runtime = 'nodejs';      // 不要用 edge（部分 SDK 不兼容）

export async function POST(req: Request) {
  // 如果任务可能超过时长限制，改成：
  // 1. 立即返回一个 task_id
  // 2. 后台异步处理（用队列）
  // 3. 前端轮询或订阅进度
}
```

> **超过时长限制怎么办**：不要硬扛。改成"异步任务 + 轮询"模式：接口立刻返回 `task_id`，任务丢到队列（或后端的后台任务），前端定时查询进度。这是处理长任务的标准做法。

### 4.3 数据库

| 方案 | 成本 | 适用 |
|---|---|---|
| **Railway PostgreSQL** | 有免费额度 | 起步推荐（和后端同平台，一键配） |
| **Supabase** | 免费额度较大 | 需要 Postgres + 自带 Auth/Storage |
| **Neon** | 免费额度 | Serverless Postgres，冷启动慢 |
| **Vercel Postgres** | 按量 | 前端 Vercel 项目方便 |

**pgvector 启用**：

```sql
-- 在 Postgres 里启用向量扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 建向量表
CREATE TABLE documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1024),          -- 维度要和你的 Embedding 模型一致
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 建索引（HNSW 比 IVFFlat 更适合动态数据）
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- 相似度查询
SELECT content, metadata,
       1 - (embedding <=> $1::vector) AS similarity
FROM documents
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

> **注意**：`<=>` 是余弦距离操作符（越小越相似）。`1 - 距离 = 相似度`。建好索引后要 `ANALYZE documents` 让查询规划器知道统计信息。

### 4.4 生产环境配置清单

```python
# app/config.py —— 生产环境必须调整的配置
class Settings(BaseSettings):
    debug: bool = False                      # 生产必须关掉
    cors_origins: list[str] = ["https://your-app.vercel.app"]   # 不要用 ["*"]

    # 安全
    require_auth: bool = True                # 必须开启鉴权
    max_request_size: int = 100_000          # 限制请求体大小

    # 性能
    model_timeout: int = 120
    max_concurrent_requests: int = 20

    # 限额（防刷）
    rate_limit_per_minute: int = 20
    daily_token_quota: int = 200_000
```

**CORS 不要用 `*`**：

```python
# ❌ 危险：任何网站都能调你的接口（配合 Cookie 会有 CSRF 风险）
allow_origins=["*"]

# ✅ 生产：明确列出允许的来源
allow_origins=["https://your-app.vercel.app"]
```

---

## 五、监控与告警

### 5.1 三层监控

| 层级 | 监控什么 | 工具 |
|---|---|---|
| **存活** | 服务是否在跑 | 平台自带的健康检查 | 
| **性能** | 延迟、错误率、吞吐 | 平台面板 / Sentry |
| **业务** | 任务成功率、成本、异常输出 | 自建（模块 09 的追踪） |

### 5.2 最简告警方案

```python
# monitoring/alert.py
"""最简告警：成本超阈值 / 错误率超阈值 时推送到飞书/企业微信。
学习阶段用定时任务检查即可，不需要上 Prometheus。
"""
import os, time, sqlite3
import httpx
from dotenv import load_dotenv

load_dotenv()

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")          # 飞书群机器人 webhook

def send_alert(title: str, content: str, level: str = "warning"):
    """发送告警到飞书"""
    if not FEISHU_WEBHOOK:
        print(f"[告警-未配置webhook] {title}: {content}")
        return

    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "ℹ️")
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{emoji} {title}"},
                "template": {"info": "blue", "warning": "orange", "critical": "red"}[level],
            },
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}],
        },
    }
    try:
        httpx.post(FEISHU_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"告警发送失败：{e}")


def check_health(usage_db: str = "agent.db",
                 cost_threshold: float = 1.0,        # 单日成本上限（USD 等值）
                 error_rate_threshold: float = 0.1):
    """检查指标，超阈值就告警。建议做成每小时运行的定时任务。"""
    import datetime
    today = datetime.date.today().isoformat()

    with sqlite3.connect(usage_db) as c:
        # 当日成本
        row = c.execute("""SELECT COUNT(*), COALESCE(SUM(cost), 0)
                           FROM usage_log WHERE created_at LIKE ?""",
                        (f"{today}%",)).fetchone()
        requests, cost = row

        if cost > cost_threshold:
            send_alert("成本告警",
                       f"今日成本 ${cost:.4f}，已超过阈值 ${cost_threshold}\n请求数：{requests}",
                       "critical")

        if requests == 0:
            send_alert("服务无流量", "今日暂无任何请求，请确认服务是否正常", "warning")

    print(f"[检查完成] 请求 {requests} 次，成本 ${cost:.4f}")


if __name__ == "__main__":
    check_health()
```

### 5.3 错误追踪（Sentry）

```bash
# 后端
uv add sentry-sdk
# 前端
npm i @sentry/nextjs
```

```python
# app/main.py
import os, sentry_sdk
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=0.1,          # 采样 10% 的请求做性能追踪（省钱）
        environment=os.getenv("ENV", "production"),
    )
```

**有了 Sentry，线上报错会自动聚合、通知，并带上调用栈和上下文。** 免费额度对个人项目够用。

---

## 六、域名与 HTTPS

```bash
# Vercel 绑定自定义域名
# Dashboard → Settings → Domains → 添加域名 → 按提示配 DNS
# Vercel 自动签发和续期 HTTPS 证书

# 如果用自己的 VPS + Nginx
```

```nginx
# /etc/nginx/sites-available/your-app
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ===== 前端 =====
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ===== 后端 API（SSE 必须特殊配置）=====
    location /api/ {
        proxy_pass http://127.0.0.1:8000;

        # ⚠️ SSE 关键配置：这三行不加，流式就失效
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header X-Accel-Buffering no;

        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # AI 接口耗时长，超时要给足
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

```bash
# HTTPS 证书（Let's Encrypt，免费）
brew install certbot
sudo certbot --nginx -d your-domain.com
# 自动续期：certbot 会装好 systemd timer / cron
```

> **SSE 部署到 Nginx 后面必查**：`proxy_buffering off`。这是"本地流式、线上不流式"最常见的原因。

---

## 七、上线前检查清单

**逐项确认，缺一项都不要上线。**

### 7.1 安全

- [ ] `.env` 不在 Git 历史里（`git ls-files | grep .env` 无输出）
- [ ] 代码里没有硬编码密钥（`rg "sk-" ` 无结果）
- [ ] CORS 不是 `*`
- [ ] 所有接口都有鉴权
- [ ] 会话查询带 user_id 校验（防越权）
- [ ] 限流 + token 配额已开启
- [ ] 危险工具标记了需要人工确认
- [ ] 日志不包含完整 Prompt 和用户隐私

### 7.2 稳定

- [ ] 健康检查接口可用（`/health`）
- [ ] 所有模型调用有超时设置
- [ ] 有重试机制（含指数退避）
- [ ] 有并发闸门（防自己打爆模型 API）
- [ ] 服务崩溃能自动重启
- [ ] 客户端断开能正确停止生成

### 7.3 监控

- [ ] 错误追踪已接入（Sentry 或等价）
- [ ] 成本统计可用
- [ ] 有成本/错误率告警
- [ ] 关键指标（延迟、成功率）可查

### 7.4 体验

- [ ] 流式输出正常（线上环境验证，不只看本地）
- [ ] 首字延迟可接受（< 1s 最好）
- [ ] 有加载状态和错误提示
- [ ] 可中断、可重试
- [ ] 移动端基本可用
- [ ] 引用来源可点击

---

## 八、知识点清单

- [ ] 三种部署架构的取舍（全栈 / 分离 / 容器）
- [ ] Serverless 时长限制及"异步任务 + 轮询"的应对
- [ ] 密钥管理的五条铁律
- [ ] `NEXT_PUBLIC_*` 会暴露给客户端（不能放密钥）
- [ ] Git 密钥泄露的应急处理（撤销比隐藏重要）
- [ ] Dockerfile 最佳实践（层缓存、非 root 用户）
- [ ] 云平台端口注入（必须用 `$PORT`）
- [ ] pgvector 的启用、索引选择和查询语法
- [ ] 生产环境 CORS 配置（不要用 `*`）
- [ ] 三层监控（存活 / 性能 / 业务）
- [ ] 告警实现（阈值检查 + 飞书推送）
- [ ] Nginx 的 SSE 配置（`proxy_buffering off`）
- [ ] 上线前检查清单的四类检查

---

## 九、常见坑

### 坑 1：端口写死
**后果**：云平台注入 `$PORT`，你的服务监听 8000，健康检查失败，判定部署失败。
**正确做法**：`--port $PORT`（或代码里读 `os.getenv("PORT", 8000)`）。

### 坑 2：`.env` 被提交
**后果**：密钥泄露，可能几分钟内被盗刷。
**正确做法**：第 1 天就配 `.gitignore`。已泄露的立即去平台撤销密钥（**撤销比清理 Git 历史重要**）。

### 坑 3：把密钥放进 `NEXT_PUBLIC_*`
**后果**：密钥打包进客户端 bundle，任何用户 F12 就能看到。
**正确做法**：`NEXT_PUBLIC_*` 只放非敏感信息（如应用名、公开 API 地址）。

### 坑 4：CORS 设为 `*`
**后果**：任何网站都能调你的接口（配合凭据还有 CSRF 风险），也可能被抓取滥用。
**正确做法**：明确列出允许的前端域名。

### 坑 5：线上流式失效
**后果**：本地正常，部署后变成一次性返回。
**正确做法**：检查 `X-Accel-Buffering: no`、Nginx `proxy_buffering off`、中间层（CDN/网关）的缓冲。

### 坑 6：Serverless 超时
**后果**：长任务跑到一半被平台杀掉，前端收到不完整响应。
**正确做法**：缩短单次调用时长；或改成"异步任务 + 进度轮询"模式。

### 坑 7：数据库连接池耗尽
**后果**：并发上来后数据库连接用完，请求全部失败。
**正确做法**：用连接池并设合理上限；Serverless 场景用连接池代理（如 PgBouncer 或 Neon 的内置池）。

### 坑 8：只在本地测过就上线
**后果**：线上环境差异导致各种奇怪问题（时区、编码、环境变量、依赖版本）。
**正确做法**：部署到预发环境跑一遍完整流程，尤其是**流式输出、鉴权、超时**这三个环节。

### 坑 9：不做备份
**后果**：数据库出问题，用户数据全丢。
**正确做法**：托管数据库一般有自动备份，要确认开启并知道怎么恢复。自己搭的必须配定时备份。

### 坑 10：日志全是 print
**后果**：线上出问题完全无法排查（看不到请求 ID、时间、上下文）。
**正确做法**：结构化日志（JSON 格式）+ 请求 ID 贯穿全链路。

---

## 十、练习任务

| # | 任务 | 难度 |
|---|---|---|
| 1 | 给项目写 Dockerfile，本地构建并运行 | ⭐⭐⭐ |
| 2 | 部署后端到 Railway（或 Render），验证健康检查通过 | ⭐⭐⭐ |
| 3 | 部署前端到 Vercel，配置环境变量 | ⭐⭐⭐ |
| 4 | 配好 CORS，验证前端能正常访问后端 | ⭐⭐⭐ |
| 5 | 用某个云 Postgres（含 pgvector），把向量数据迁上去 | ⭐⭐⭐⭐ |
| 6 | 接入 Sentry，故意触发一个错误验证能收到通知 | ⭐⭐⭐ |
| 7 | 实现成本告警，推送到飞书/企业微信 | ⭐⭐⭐ |
| 8 | 走一遍上线前检查清单（四类共 20+ 项） | ⭐⭐⭐⭐ |
| 9 | 配一个自定义域名（可选，用便宜的 .xyz 域名试） | ⭐⭐⭐ |
| 10 | **【项目任务】** 拿到一个可公开访问的项目链接 | ⭐⭐⭐⭐⭐ |

---

## 十一、自测题

**Q1：部署后服务起不来，第一步查什么？**
<details><summary>参考答案</summary>
按顺序查：① **环境变量**——是否都在平台上配好了（尤其 API Key、数据库 URL）；② **端口**——是否用了平台注入的 `$PORT`（最常见问题，写死端口会导致健康检查失败）；③ **启动命令**——是否和本地一致（注意平台的工作目录可能不同）；④ **日志**——看具体报错信息（模块导入错误、依赖缺失、数据库连不上）；⑤ **依赖锁定**——`uv.lock` / `package-lock.json` 是否提交了，平台装依赖的版本是否和本地一致；⑥ **健康检查路径**——配置的路径是否和代码里的路由一致。
</details>

**Q2：为什么 `NEXT_PUBLIC_` 开头的变量不能放密钥？**
<details><summary>参考答案</summary>
因为 Next.js 在构建时会把所有 `NEXT_PUBLIC_*` 前缀的环境变量**内联到客户端 JavaScript bundle** 里——这是设计上的约定，用于让前端代码访问公开配置。任何用户打开开发者工具查看 JS 源码，或直接搜 bundle 文件，都能看到这些值。所以只能用它们存非敏感信息（应用名、公开 API 地址、埋点 ID）。密钥必须通过服务端变量（无前缀）访问，且只在服务端代码（Route Handler / Server Action）里使用。
</details>

**Q3：Serverless 平台有 60 秒时长限制，你的 Agent 任务要跑 3 分钟，怎么办？**
<details><summary>参考答案</summary>
改成"异步任务 + 进度查询"模式：① 接口立刻返回 `task_id`（200 响应，1 秒内）；② 把任务放到队列、后台任务或独立的长时运行服务（如 Railway 上的 FastAPI）执行；③ 前端用 task_id 轮询进度接口，或通过 SSE 订阅进度；④ 任务完成后前端拉取结果。这个模式的额外好处是用户体验更好（能看到进度，不用干等），且不受 Serverless 限制。如果任务必须在服务端同步完成，就应该把后端部署到非 Serverless 平台（Railway / Render / VPS）。
</details>

**Q4：部署到 Nginx 后面流式输出失效了，怎么排查和解决？**
<details><summary>参考答案</summary>
原因：Nginx 默认会**缓冲**上游响应，等积累到一定量才发给客户端，导致流式变成一次性返回。解决：① 在 location 配置里加 `proxy_buffering off;` 和 `proxy_cache off;`；② 在应用的响应头里加 `X-Accel-Buffering: no`（这个头会被 Nginx 读取并禁用缓冲）；③ 确认 `Connection` 头没有被错误处理（`proxy_set_header Connection "";` 配合 `proxy_http_version 1.1`）；④ 检查是否还有 CDN 或 API 网关在中间做缓冲。排查方法：用 `curl -N` 直连后端确认有流式，再直连 Nginx 确认有没有——能定位到是哪一层的问题。
</details>

**Q5：密钥已经推到 GitHub 了，怎么处理？**
<details><summary>参考答案</summary>
**第一优先级是撤销密钥**，不是清理 Git 历史。因为公开仓库的密钥通常几分钟内就被爬虫抓走了，无论你怎么清理历史，泄露的密钥都已经被记录。步骤：① 立即到平台（DeepSeek/OpenAI 等）**删除该密钥并生成新的**；② 检查账单是否有异常使用；③ 配好 `.gitignore` 防止再次发生；④ 再考虑清理 Git 历史（`git filter-repo` 或 BFG）；⑤ 如果是私有仓库且确认无人访问，风险较低但仍建议轮换。关键认知：**密钥安全的重心在"可撤销"而不是"藏得深"。**
</details>

**Q6：上线前必须检查哪几类事项？**
<details><summary>参考答案</summary>
四类：① **安全**——密钥不在 Git、无硬编码密钥、CORS 不是 `*`、有鉴权、会话校验归属、有限流配额、危险操作需确认、日志脱敏；② **稳定**——健康检查可用、有超时、有重试退避、有并发闸门、崩溃能重启、断连能停止生成；③ **监控**——错误追踪接入、成本统计可用、有告警、关键指标可查；④ **体验**——**线上环境**验证流式正常、首字延迟可接受、有加载和错误提示、可中断可重试、移动端可用。最容易漏的是第 ④ 类的"线上验证流式"——很多人只在本地测过就上线。
</details>

**Q7：为什么 CORS 不能用 `*`？**
<details><summary>参考答案</summary>
两个风险：① **接口被滥用**——任何网站都能在你的用户浏览器里调用你的接口，如果接口没有独立的鉴权，就等于公开的服务（别人可以拿你的额度做他们的产品）；② **配合凭据的 CSRF 风险**——虽然浏览器规范禁止 `credentials: include` 与 `Access-Control-Allow-Origin: *` 同时生效，但配置不当时可能产生安全缺口。正确做法是明确列出允许的来源（如 `["https://your-app.vercel.app"]`）。另外注意：CORS 是浏览器端的保护，不能替代服务端鉴权——即使配了 CORS，也必须做鉴权。
</details>

---

## 十二、延伸阅读

| 主题 | 资源 |
|---|---|
| Railway 文档 | https://docs.railway.com/ |
| Vercel 部署文档 | https://vercel.com/docs/deployments |
| pgvector | https://github.com/pgvector/pgvector |
| Sentry 文档 | https://docs.sentry.io/ |
| Nginx SSE 配置 | 搜 "nginx proxy_buffering server-sent events" |
| Let's Encrypt / certbot | https://certbot.eff.org/ |

---

## 十三、完成标志

- [ ] 后端部署成功，健康检查可通过
- [ ] 前端部署成功，能正常访问
- [ ] 自定义域名 + HTTPS（可选）
- [ ] 数据库在云上（含 pgvector）
- [ ] Sentry 接入并能收到错误通知
- [ ] 成本告警可用
- [ ] 上线前检查清单全部通过
- [ ] **拿到一个可公开访问的项目链接**
- [ ] 能讲清本模块知识点清单的每一条

---

## 🎉 恭喜完成 12 周学习

到这里，你手里应该有：

| 交付物 | 说明 |
|---|---|
| 4 个可运行项目 | CLI 聊天、RAG 助手、工具 Agent、全栈应用 |
| 1 个线上可访问的应用 | 可以写进简历、面试演示 |
| 一份评测报告 | 质量 + 成本 + 延迟的量化数据 |
| 一套方法论 | 建评测、做优化、控成本的工程习惯 |

**接下来做什么**：

1. **整理作品集**——把 4 个项目推到 GitHub，每个都写清楚 README（问题、方案、数据）。面试官通常只看 README 决定要不要细看代码
2. **写技术笔记**——把踩过的坑写出来发到公开平台（掘金、知乎）。这是最有效的个人品牌建设
3. **深挖一个方向**——RAG 检索质量 / Agent 稳定性 / 多模态 / 成本优化，选一个持续深入。**不要全都浅尝**
4. **结合你的前端优势**——做"AI + 垂直场景"的小产品。一个能跑通的小产品比大厂实习经历更能证明能力

**最后一句话**：12 周不够让你成为专家，但足够让你从"只会写页面"变成"能独立交付 AI 应用"。决定成败的不是这 12 周学了多少，而是第 13 周你还在不在写。
