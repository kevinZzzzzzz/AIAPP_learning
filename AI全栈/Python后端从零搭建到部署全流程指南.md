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

# 3. 激活虚拟环境
#    Windows (PowerShell):
.\venv\Scripts\Activate.ps1
#    macOS / Linux (终端、zsh、bash 通用):
source venv/bin/activate
# 说明：激活成功后，命令行提示符前面会出现 (venv) 字样，表示已处于隔离环境；
#       退出虚拟环境（回到系统全局 Python）执行：deactivate

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


将本地代码上传到 Linux 云服务器，通常有以下 **4 种主流方式**。推荐**方式一（Git）**或**方式二（rsync/scp 命令行）**。

---

### ⚠️ 上传前的关键注意点（必看）
> **切勿把本地的 `venv` 文件夹上传到服务器！**
> `venv` 是 Mac 本地的 Python 环境，Linux 系统无法直接运行。上传到服务器后，需要在服务器上重新执行 `pip install -r requirements.txt`。

---

### 方式 1：通过 Git 仓库拉取（⭐⭐⭐⭐⭐ 行业最标准做法）

这是正规项目开发与部署的最优解，后续更新代码只需要一条 `git pull`。

1. **本地推送代码到 GitHub / Gitee**：
   在本地项目目录下：
   ```bash
   cd /Users/kevinzzzzzzz/Documents/Code/AIAPP_learning/AI全栈/python-backend-demo
   git init
   git add .
   git commit -m "feat: init fastApi backend"
   # 推送到你的 GitHub / Gitee 远程仓库
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```

2. **在云服务器上克隆拉取**：
   通过 SSH 登录云服务器后：
   ```bash
   ssh root@<你的服务器公网IP>
   
   # 在服务器上拉取代码
   git clone https://github.com/你的用户名/你的仓库名.git
   cd 你的仓库名
   ```

---

### 方式 2：使用 `rsync` 或 `scp` 命令行直传（⭐⭐⭐⭐ 快速、无需建 Git 仓库）

Mac 自带这两个命令，一条命令就能把本地代码同步到服务器，并自动**排除** `venv` 和缓存文件。

在 **Mac 本地终端** 运行：

```bash
# 进入 demo 所在的上级目录
cd /Users/kevinzzzzzzz/Documents/Code/AIAPP_learning/AI全栈

# 使用 rsync 传输（排除 venv 虚拟环境和 Python 缓存）
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  python-backend-demo/ root@<你的服务器IP>:/var/www/python-backend-demo/
```
*(输入服务器密码即可完成传输，传输速度极快且自带压缩)*

---

### 方式 3：使用图形化 SFTP 工具（⭐⭐⭐⭐ 新手最直观）

如果你习惯鼠标拖拽操作：

1. 下载免费的 SFTP 工具，如：
   * **[Cyberduck](https://cyberduck.io/)**（Mac 上经典开源）
   * **[FileZilla](https://filezilla-project.org/)**
   * **[Termius](https://termius.com/)**（好看好用的 SSH + SFTP 终端）
2. 新建连接：
   * 协议：`SFTP`
   * 主机/IP：你的服务器公网 IP
   * 用户名：`root`（或你的服务器用户）
   * 端口：`22`
   * 密码：你的服务器密码
3. 连接成功后，左边是 Mac 本地文件，右边是服务器目录，直接**全选文件（不选 venv）拖到右边**即可。

---

### 方式 4：使用 VS Code 的 Remote - SSH 插件

1. 在 VS Code 安装官方插件 **`Remote - SSH`**。
2. 按 `Cmd + Shift + P`，输入 `Remote-SSH: Connect to Host...`，输入 `root@<你的服务器IP>` 连接。
3. 连接后，VS Code 左侧会变成服务器的目录，你可以直接把本地文件拖入左侧文件树，也可以直接在服务器上写代码、开终端。

---

### 代码上传后的第一步：
代码传到服务器后，在服务器终端执行：
```bash
cd python-backend-demo
# 1. 推荐在服务器也创建独立的虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装项目依赖
pip install -r requirements.txt

# 3. 运行服务
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```