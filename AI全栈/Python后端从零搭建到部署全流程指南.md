# 🚀 Python FastAPI 后端从零搭建、本地运行与服务器部署全流程指南

本文档专门为你（前端开发者）编写，配套目录下的 Python 全栈后端示例项目 [**`python-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/python-backend-demo)。

---

## 🛠️ 一、 需要什么环境与安装步骤

### 1. Python 环境 (Python 3.10+)
*   **版本要求**：Python 3.10 或更高版本（当前系统经检测已安装 `Python 3.10.10`）。
*   **如何检查**：打开终端运行 `python --version`，显示 `Python 3.10.x` 即正常。

### 2. 虚拟环境 (Virtualenv) 与依赖安装
推荐在虚拟环境中隔离安装第三方包（相当于前端的本地 `node_modules` 隔离）：

```bash
# 1. 切换到 python-backend-demo 目录
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\python-backend-demo"

# 2. 创建虚拟环境 venv
python -m venv venv

# 3. 激活虚拟环境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 4. 安装依赖包 (利用国内清华/阿里镜像极速安装)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 📁 二、 项目目录结构与模块拆解

```
python-backend-demo/
├── requirements.txt            # 1. 依赖包清单 (对标 package.json 中的 dependencies)
├── database.py                 # 2. 数据库连接配置 (SQLite 零配置磁盘文件 ./sql_app.db)
├── models.py                   # 3. SQLAlchemy ORM 数据库实体表 (Users, Appointments)
├── schemas.py                  # 4. Pydantic DTO 数据校验模型 (声明入参出参格式)
├── crud.py                     # 5. 数据库 CRUD 增删改查方法层
└── main.py                     # 6. FastAPI 主程序入口 (CORS, 路由声明, 种子数据初始化)
```

---

## 💻 三、 本地如何运行与测试

### 1. 启动服务命令

```bash
# 方式 A：直接运行主入口脚本
python main.py

# 方式 B：使用 uvicorn 命令行启动 (带热重载 --reload)
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

终端控制台打出以下内容即代表启动成功：
```
🚀 启动 Python FastAPI 服务器: http://127.0.0.1:8000
📚 API 可视化交互文档: http://127.0.0.1:8000/docs
```

### 2. 在线交互测试 (Swagger UI)
在浏览器打开：`http://127.0.0.1:8000/docs`
FastAPI 会自动为你生成可视化的交互式 API 测试页面，点击 **Try it out** 即可在线调用 `GET /api/users` 或 `POST /api/appointments`。

### 3. 前端代码联调范例 (Axios)
```javascript
// 前端请求范例
import axios from 'axios';

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' });

// 获取用户列表
async function getUsers() {
  const res = await api.get('/api/users');
  console.log('用户列表:', res.data.data);
}
```

---

## 🚢 四、 服务器打包与部署上线

### 1. 后台不间断运行 (Nohup / Gunicorn)
将代码上传到 Linux 云服务器后：

```bash
# 1. 在服务器安装依赖
pip install -r requirements.txt

# 2. 使用 nohup 后台不间断运行
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > app.log 2>&1 &
```

### 2. 使用 Docker 容器化部署 (推荐 🔥)
在项目根目录新建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

运行 Docker 指令：
```bash
docker build -t python-fastapi-demo .
docker run -d -p 8000:8000 --name fastapi-app python-fastapi-demo
```

### 3. Nginx 反向代理与 SSE 打字机流式支持
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        
        # 支持 SSE 打字机流式传输防缓存
        proxy_buffering off;
        proxy_cache off;
    }
}
```
