# 📚 第三阶段：Gin + GORM + Redis 生产级后端实战

> 本目录是一个符合真实企业级规范的 **完整 RESTful API 后端微服务**。

---

## 🏗️ 架构分层解析（对比前端 MVC / NestJS）

| 目录模块 | 作用与职责 | 前端概念映射 (NestJS / Express) |
| :--- | :--- | :--- |
| `models/` | 数据库表结构定义与 GORM 关联映射 | Prisma Schema / TypeORM Entity |
| `database/` | 数据库连接与连接池参数调优 | TypeORM DataSource / Database Client |
| `cache/` | Redis 客户端连接与高可用容灾判定 | RedisService / IoRedis |
| `middlewares/` | 跨域 CORS、JWT 拦截器、请求延迟链路监控 | Express Middleware / Nest Guards & Interceptors |
| `controllers/` | 请求参数绑定校验、业务逻辑处理、响应包装 | Controller + Service |
| `routes/` | API 路由注册与版本分组 (`/api/v1`) | Router (`app.use('/api', router)`) |
| `main.go` | 程序唯一入口、服务启动与操作系统优雅停机 | `main.ts` (`bootstrap()`) |

---

## 🚀 如何在本地跑起来？

### 步骤 1：启动服务
在终端进入本目录或项目根目录，运行：
```powershell
cd f:\project\AI应用开发\goLearn\03_后端实战项目_Gin_GORM_Redis
go run main.go
```
终端将输出：
```text
✅ 数据库表结构自动迁移成功！
⚠️ [Redis 提示]: 本地 127.0.0.1:6379 未开启或连接超时... (已自动开启降级模式)
⚡ API 服务已就绪，正在监听端口 http://127.0.0.1:8080
```
*(本项目已集成纯 Go 嵌入式 SQLite `app.db`，即使你本地没装 MySQL / Redis 也可 100% 顺畅启动并执行完整的增删改查！)*

---

## 📡 接口联调实战（前端可直接测试）

### 1. 注册新账号
- **请求方式**: `POST http://127.0.0.1:8080/api/v1/auth/register`
- **请求体**:
```json
{
  "username": "alex",
  "password": "mypassword123",
  "email": "alex@example.com"
}
```

### 2. 登录并换取 JWT Token
- **请求方式**: `POST http://127.0.0.1:8080/api/v1/auth/login`
- **请求体**:
```json
{
  "username": "alex",
  "password": "mypassword123"
}
```
- **响应示例**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_id": 1,
    "username": "alex"
  }
}
```

### 3. 创建文章（携带 JWT）
- **请求方式**: `POST http://127.0.0.1:8080/api/v1/articles`
- **请求头**: `Authorization: Bearer <上一步返回的token>`
- **请求体**:
```json
{
  "title": "从前端到 Go 全栈的心路历程",
  "content": "Go 的协程并发模型和编译单二进制交付体验真是太棒了！"
}
```

### 4. 获取文章列表（公开接口，体验缓存）
- **请求方式**: `GET http://127.0.0.1:8080/api/v1/articles?page=1&pageSize=10`
- 观察响应头中的 `X-Cache-Status`:
  - 第一次访问：`MISS`（查库并回写缓存）
  - 第二次访问：`HIT`（直接从 Redis 极速响应，延迟小于 1ms）

### 5. 优雅关机测试
在运行中的终端按下 `Ctrl + C`，观察终端输出：
```text
收到操作系统终止信号 [interrupt]，准备启动优雅停机流程...
🎉 HTTP 服务已平稳安全关闭，零丢单、零脏数据！
```
