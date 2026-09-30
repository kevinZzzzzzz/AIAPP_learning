# 🚢 前端转全栈：Python 全栈应用部署上线与 Docker / Nginx 运维指南

恭喜你！当你学完前面的 API 路由、数据库 ORM、SSE 打字机与 JWT 鉴权后，**最后一步就是把你的应用部署上线，让全球用户都能通过域名访问你的全栈产品！**

---

## 🏗️ 架构全景：生产环境全栈部署架构

```
[用户浏览器]
     │
     ▼ (HTTPS 端口 443 / 80)
┌────────────────────────────────────────────────────────┐
│ Nginx 网关服务器 (反向代理 / SSL 证书 / 静态资源宿主)       │
└────────────┬──────────────────────────────┬────────────┘
             │ (路由代理 /api/*)             │ (静态资源 /)
             ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│ Python FastAPI 后端服务   │    │ 前端静态构建包 (HTML/JS)  │
│ (Uvicorn 进程池 8000 端口) │    │ (dist / build 目录)       │
└────────────┬─────────────┘    └──────────────────────────┘
             │ (读写落盘)
             ▼
┌──────────────────────────┐
│ 数据库 (SQLite / Postgres)│
└──────────────────────────┘
```

---

## 🐳 方案一：使用 Docker 容器化一键部署 (推荐 🔥)

Docker 是现代化部署的标准。它可以保证“在你的电脑上能跑，在云服务器上也 100% 能跑”。

### 1. 编写 FastAPI 专属 `Dockerfile`
在你的后端根目录下新建 `Dockerfile`：

```dockerfile
# 1. 使用轻量级 Python 3.11 镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制项目代码
COPY . .

# 5. 暴露出 8000 端口
EXPOSE 8000

# 6. 使用 uvicorn 多进程模式启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. 编写 `docker-compose.yml` 编排整套全栈服务
在根目录下新建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # Python 后端服务
  backend:
    build: .
    container_name: python_ai_backend
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./app_database.db:/app/app_database.db # 挂载数据库文件防丢失
      - ./uploaded_files:/app/uploaded_files   # 挂载上传的文件
    environment:
      - APP_ENV=production
      - DEEPSEEK_API_KEY=sk-your-real-key
```

### 一键部署启动指令：
```bash
docker-compose up -d --build
```

---

## 🌐 方案二：云服务器 Nginx 反向代理配置

当你在阿里云/腾讯云注册域名并开启 HTTPS 后，用 Nginx 转发 API 请求（**注意对 SSE 流式和 WebSocket 的配置支持**）：

编辑 `/etc/nginx/sites-available/default`：

```nginx
server {
    listen 80;
    server_name your-domain.com; # 你的域名

    # 1. 托管前端打包资源 (React / Vue build 目录)
    location / {
        root /var/www/my-fullstack-app/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 2. 反向代理 Python FastAPI API 接口
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 💥 关键配置: 开启 SSE 流式打字机支持 (防缓存/防分块缓冲)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    # 3. 反向代理 WebSocket 协议
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## ⚡ 方案三：免费 Serverless 托管 (Vercel / Railway)

如果你不想购买阿里云服务器，可以使用全免费的现代化 Serverless 托管服务：

1. **前端**：一键部署在 **Vercel** / Netlify。
2. **FastAPI 后端**：一键部署在 **Railway** / Render / Zeabur（连接 GitHub 仓库，自动检测 Python 启动）。
3. **数据库**：使用免费的 **Supabase** / Neon (PostgreSQL 托管) 或 PlanetScale。

---

## 🎯 全栈上线检查清单 (Checklist)

- [ ] `.env` 文件已加入 `.gitignore`（严禁将 API Key 提交到 GitHub 仓库）。
- [ ] 后端 `CORSMiddleware` 的 `allow_origins` 在生产环境从 `["*"]` 改为你的前端真实域名。
- [ ] 数据库 `sqlite` 挂载磁盘或切换为生产级 `PostgreSQL`。
- [ ] 全局异常捕获中间件已生效，不泄露后台敏感报错信息。
