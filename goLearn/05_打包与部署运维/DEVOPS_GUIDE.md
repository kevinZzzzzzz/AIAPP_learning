# 🚢 生产级打包、部署与全栈运维手册

> **写给前端全栈**：在前端世界，我们部署通常是 `npm run build` 生成 `dist` 扔给 Nginx 或 Vercel。而在 Go 后端，你的产物是一个**自包含、静态链接的单个二进制文件**，彻底告别了在服务器上装 Node.js、Python 解释器或 `node_modules` 依赖冲突的噩梦！

---

## 目录索引
- [一、打包与交叉编译核心原理](#一打包与交叉编译核心原理)
- [二、部署方案 A：Linux 裸机 / 云服务器 Systemd 守护进程部署（最常用）](#二部署方案-alinux-裸机--云服务器-systemd-守护进程部署最常用)
- [三、部署方案 B：Docker 与 Docker Compose 容器化编排](#三部署方案-bdocker-与-docker-compose-容器化编排)
- [四、Nginx 反向代理与前后端同域配置](#四nginx-反向代理与前后端同域配置)
- [五、生产性能排查利器：pprof 性能剖析与火焰图](#五生产性能排查利器pprof-性能剖析与火焰图)

---

## 一、打包与交叉编译核心原理

Go 编译器原生支持**交叉编译（Cross-Compilation）**！这意味着你在 Windows 电脑上，只需通过环境变量切换目标操作系统和架构，就能一键打出 Linux 或 macOS 可直接运行的机器码！

### 1. 核心环境变量
- `GOOS`：目标操作系统（`linux`、`windows`、`darwin`）
- `GOARCH`：目标 CPU 架构（`amd64`、`arm64`）
- `CGO_ENABLED=0`：关闭 CGO。生成纯静态二进制文件，不需要目标机器有任何 C 动态链接库（`glibc` 版本不一致也能跑！）
- `-ldflags="-s -w"`：
  - `-s`：去掉符号表（symbol table）
  - `-w`：去掉 DWARF 调试信息
  - 二进制体积可从 25MB 直降到 15MB 左右！

### 2. Windows 终端一键打包 Linux 生产产物
在 PowerShell 中运行：
```powershell
# 切换到后端项目目录
cd "f:\project\AI应用开发\AI appointment develop\goLearn\03_gin_gorm_api"

# 设置交叉编译环境变量并打包
$env:CGO_ENABLED="0"; $env:GOOS="linux"; $env:GOARCH="amd64"
go build -ldflags="-s -w" -o server_linux .
```
打包成功后，你就会得到一个 `server_linux` 文件。这就是你的整个后端程序！

---

## 二、部署方案 A：Linux 裸机 / 云服务器 Systemd 守护进程部署（最常用）

### 步骤 1：上传二进制文件到服务器
使用 `scp` 或任何 SFTP 工具将 `server_linux` 上传到服务器目录，例如 `/data/apps/go-backend/`：
```bash
# 在 Linux 服务器上赋予可执行权限
chmod +x /data/apps/go-backend/server_linux
```

### 步骤 2：创建 Systemd 守护进程配置文件
在 Linux 上创建服务单元文件：
```bash
sudo vim /etc/systemd/system/go-app.service
```
粘贴以下标准配置：
```ini
[Unit]
Description=Go Fullstack Backend Service
After=network.target

[Service]
Type=simple
User=root
# 工作目录
WorkingDirectory=/data/apps/go-backend
# 启动命令
ExecStart=/data/apps/go-backend/server_linux
# 异常退出时自动在 5 秒后重启保活
Restart=always
RestartSec=5
# 环境变量
Environment=GIN_MODE=release

# 标准输出与错误日志输出
StandardOutput=append:/var/log/go-app.log
StandardError=append:/var/log/go-app.error.log

[Install]
WantedBy=multi-user.target
```

### 步骤 3：启动并设置开机自启
```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start go-app

# 检查服务运行状态
sudo systemctl status go-app

# 设置开机自启
sudo systemctl enable go-app
```

---

## 三、部署方案 B：Docker 与 Docker Compose 容器化编排

本项目已在 `05_打包与部署运维/` 目录下准备好极简双阶段构建 `Dockerfile` 和 `docker-compose.yml`。

### 一键拉起完整后端全家桶（App + Redis + MySQL）：
在包含 `docker-compose.yml` 的目录下执行：
```bash
docker compose up -d
```
Docker 会自动按顺序：
1. 先拉起 MySQL 8.0 并等待健康检查通过
2. 拉起 Redis 7 并等待心跳响应
3. 构建并运行 Go 后端应用容器，映射端口 `8080:8080`

### 查看实时容器日志：
```bash
docker compose logs -f app
```

---

## 四、Nginx 反向代理与前后端同域配置

将 `05_打包与部署运维/nginx.conf` 复制或包含到你的 Nginx 配置中：
1. **统一域名**：
   - 前端访问 `https://yourdomain.com/` -> 静态托管 Vue/React 打包后的 `dist/`。
   - API 访问 `https://yourdomain.com/api/` -> 自动反代给 `127.0.0.1:8080`。
2. **零跨域问题**：由于在同一个域名下通过 Nginx 分发，浏览器不会触发跨域预检。

---

## 五、生产性能排查利器：pprof 性能剖析与火焰图

Go 语言自带最强工业级性能剖析工具 `net/http/pprof`。

### 1. 开启性能探针
只需在路由中简单引入：
```go
import _ "net/http/pprof"

// 在单独的管理端口启动 pprof
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

### 2. 导出 CPU / 内存火焰图
当线上遇到 CPU 暴涨或内存泄漏时，无需盲猜：
```bash
# 采样 30 秒的 CPU 性能并用浏览器图形化打开火焰图
go tool pprof -http=:8008 http://localhost:6060/debug/pprof/profile?seconds=30
```
浏览器会自动呈现交互式火焰图，哪一行代码在疯狂消耗 CPU 或内存，毫秒级定位！

