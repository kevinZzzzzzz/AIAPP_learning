# 🚀 Go (Gin + GORM) 后端从零搭建、本地运行与服务器部署全流程指南

本文档专门为你（前端开发者）编写，配套目录下的 Go 全栈后端示例项目 [**`go-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/go-backend-demo)。

---

## 🛠️ 一、 需要什么环境与安装步骤

### 1. Go 语言环境 (Go 1.18+)
*   **版本要求**：Go 1.18 或更高版本（系统经检测已安装 `go1.18.3 windows/amd64`）。
*   **如何检查**：打开终端运行 `go version`，看到 `go1.x.x` 即正常。

### 2. 配置国内 GOPROXY 代理 (极速下载依赖包)
由于网络原因，国内拉取 Go 依赖库推荐配置七牛云/阿里代理：

```bash
# 配置国内 Go 代理镜像源
go env -w GOPROXY=https://goproxy.cn,direct
```

### 3. VS Code 插件
在 VS Code 扩展商店搜索并安装 **`Go`** (官方插件)，支持代码跳转与自动 import 保存。

---

## 📁 二、 项目目录结构与模块拆解

```
go-backend-demo/
├── go.mod                      # 1. 项目模块与依赖说明书 (对标 package.json)
├── gorm_demo.db                # 2. SQLite 本地磁盘数据库文件 (自动生成)
├── main.go                     # 3. Gin 主程序入口 (CORS, DB 迁移, 路由注册)
├── common/
│   └── result.go               # 4. 统一 JSON 响应封装 { code, message, data }
├── models/
│   ├── user.go                 # 5. GORM 用户数据库结构体
│   └── appointment.go          # 6. GORM 预约业务数据库结构体
└── controllers/
    ├── user_controller.go      # 7. 用户 API 请求处理层
    └── appointment_controller.go# 8. 预约 API 请求处理层
```

---

## 💻 三、 本地如何运行与测试

### 1. 整理与拉取依赖包

```bash
# 切换到 go-backend-demo 目录
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\go-backend-demo"

# 自动下载依赖 (相当于 npm install)
go mod tidy
```

### 2. 本地直接运行启动

```bash
go run main.go
```

控制台打印如下信息说明启动成功：
```
==================================================
🚀 Go Gin 全栈后端服务已成功启动！
端口: 8081
基础 API: http://localhost:8081/api/users
==================================================
```

### 3. 前端联调范例 (Axios)
```javascript
// 前端请求 Go 后端 8081 端口范例
import axios from 'axios';

const goApi = axios.create({ baseURL: 'http://localhost:8081' });

async function getGoUsers() {
  const res = await goApi.get('/api/users');
  console.log('Go 服务返回用户列表:', res.data.data);
}
```

---

## 🚢 四、 服务器打包与部署上线（Go 的绝对王牌优势！）

Go 语言最大的优势之一就是：**静态编译为单个二进制可执行文件**！
**在服务器上不需要安装 Go、不需要 Python、也不需要 JRE，直接把生成的一个二进制文件上传就能立马跑起来！**

### 1. 交叉编译生成 Linux 云服务器二进制包
在 Windows 本地终端中，直接编译出适合 Linux 服务器运行的无依赖程序：

```bash
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\go-backend-demo"

# 设置环境变量进行交叉编译 (目标平台 Linux x86_64)
$env:CGO_ENABLED="0"
$env:GOOS="linux"
$env:GOARCH="amd64"

# 编译为单个文件 app_server
go build -o app_server main.go
```

### 2. 服务器运行 (零依赖运行)
1. 使用 SCP 将编译好的 `app_server` 上传到 Linux 服务器。
2. 添加执行权限并后台运行：
   ```bash
   chmod +x app_server
   nohup ./app_server > server.log 2>&1 &
   ```

### 3. 使用 Docker 部署 (体积仅十几 MB！)
创建 `Dockerfile`：

```dockerfile
# 编译阶段
FROM golang:1.18-alpine AS builder
WORKDIR /app
COPY . .
RUN go env -w GOPROXY=https://goproxy.cn,direct && go build -o main main.go

# 运行阶段 (仅使用极其轻量的 alpine 镜像，构建出来的镜像只有约 15MB！)
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/main .
EXPOSE 8081
CMD ["./main"]
```

运行 Docker 指令：
```bash
docker build -t go-gin-demo .
docker run -d -p 8081:8081 --name go-server go-gin-demo
```
