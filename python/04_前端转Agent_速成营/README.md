# 前端转 AI Agent 开发 Python 速成营

这个文件夹中的代码专门为有前端 (JS/TS) 背景的开发者设计，去掉了冗余的 Python 传统教程内容，直奔现代 AI Agent 后端开发所需的核心技能。

## 文件概览

按顺序学习以下四个文件：

1. **[01_基础语法_列表推导式与集合.py](./01_基础语法_列表推导式与集合.py)**
   - 对应前端：`map/filter`、`Set`、`Object`
   - 掌握 RAG 和数据清洗中最常用的原生语法。

2. **[02_类型与Pydantic_结构化输出.py](./02_类型与Pydantic_结构化输出.py)**
   - 对应前端：`TypeScript` + `Zod`
   - 这是 Agent 开发的灵魂。通过 Pydantic 约束大模型输出 JSON 格式。

3. **[03_异步与FastAPI_SSE流式输出.py](./03_异步与FastAPI_SSE流式输出.py)**
   - 对应前端：`Express/NestJS` 中的异步路由
   - 实现大模型“打字机”流式效果的核心服务层。

4. **[04_面向对象_Agent核心类.py](./04_面向对象_Agent核心类.py)**
   - 虽然前端现在流行 Hooks，但各大 AI 框架（LangChain, LlamaIndex）极度依赖面向对象 (OOP) 和魔术方法（如 `__call__`）。

5. **[05_文件操作与JSON_读取写入.py](./05_文件操作与JSON_读取写入.py)**
   - 对应 Node.js 中的 `fs` 模块 和 `JSON.parse`。
   - 读取本地文档构建知识库素材，以及安全解析大模型的输出。

6. **[06_数据库与持久化_SQLite与向量库.py](./06_数据库与持久化_SQLite与向量库.py)**
   - 对应 Node 环境的各种 ORM。
   - 介绍轻量级 SQLite 维持 Agent 会话记忆（Memory）的方法，以及 AI 专用的“向量数据库”概念。

7. **[07_环境变量与错误处理_安全第一.py](./07_环境变量与错误处理_安全第一.py)**
   - 对应 `dotenv` 库 和 `try...catch`。
   - 极其关键的安全基建！讲解如何防止 API Key 泄露、处理长耗时网络请求的报错，以及为什么在后台服务中 `logging` 比 `print` 重要。

## 环境配置与运行指引

建议你使用现代的 Python 环境管理工具 `uv`（极其快，体验类似 `pnpm`）或者传统的 `venv`。

### 方式一：使用 `uv` (推荐)
如果你安装了 `uv`，运行这些脚本非常简单，不需要手动写 `requirements.txt`。

运行 01、02、04、05、06、07 文件（普通脚本）：
```bash
uv run 01_基础语法_列表推导式与集合.py
uv run 02_类型与Pydantic_结构化输出.py
uv run 04_面向对象_Agent核心类.py
uv run 05_文件操作与JSON_读取写入.py
uv run 06_数据库与持久化_SQLite与向量库.py
uv run 07_环境变量与错误处理_安全第一.py
```

运行 03 文件 (FastAPI 服务)：
由于 03 需要依赖包，你可以通过 `uv run` 自动安装依赖并运行：
```bash
uv run --with fastapi --with uvicorn --with pydantic uvicorn 03_异步与FastAPI_SSE流式输出:app --reload --port 8000
```
启动后，可以新建一个终端通过 `curl` 测试流式接口：
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "你好啊", "stream": true}'
```

### 方式二：使用原生 `venv` 与 `pip`

1. 创建虚拟环境：
```bash
python -m venv .venv
```

2. 激活虚拟环境 (Mac/Linux)：
```bash
source .venv/bin/activate
```

3. 安装依赖：
```bash
pip install fastapi uvicorn pydantic
```

4. 运行脚本：
```bash
python 01_基础语法_列表推导式与集合.py
# 启动 Web 服务
uvicorn 03_异步与FastAPI_SSE流式输出:app --reload --port 8000
```

祝你转型顺利！代码里的注释非常详细，可以直接打开文件阅读。
