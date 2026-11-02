# ==============================================================================
# 🐳 双阶段构建 (Multi-Stage Build) Dockerfile
# 特性：
# 1. 第一阶段使用 golang 镜像拉取依赖并编译为纯静态二进制文件
# 2. 第二阶段使用极致小巧的 alpine/scratch 镜像，最终镜像体积仅 ~15MB 左右！
# 3. 对比前端 Node.js 镜像动辄 600MB ~ 1GB，Go 镜像下载拉起速度极快！
# ==============================================================================

# -------------- 构建阶段 (Builder) --------------
FROM golang:1.20-alpine AS builder

# 设置构建工作目录
WORKDIR /app

# 设置国内加速代理与静态编译环境变量
ENV GO111MODULE=on \
    GOPROXY=https://goproxy.cn,direct \
    CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64

# 先单独复制 go.mod 与 go.sum，利用 Docker 缓存层加速构建
COPY go.mod go.sum ./
RUN go mod download

# 复制全量源代码
COPY . .

# 编译生成静态二进制文件（-s -w 去除符号表大幅裁剪体积）
WORKDIR /app/03_gin_gorm_api
RUN go build -ldflags="-s -w" -o /app/server .

# -------------- 运行阶段 (Runner) --------------
FROM alpine:3.19

# 安装时区支持与 SSL 根证书（保证 HTTPS 请求正常）
RUN apk --no-cache add ca-certificates tzdata
ENV TZ=Asia/Shanghai

WORKDIR /app

# 从构建阶段仅仅拷贝编译出的单个二进制文件
COPY --from=builder /app/server /app/server

# 暴露服务端口
EXPOSE 8080

# 启动服务
ENTRYPOINT ["/app/server"]

