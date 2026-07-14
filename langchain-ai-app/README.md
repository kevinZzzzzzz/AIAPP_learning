# LangChain AI 应用（前端开发程序员版）

基于掘金文章《手把手教你使用LangChain（前端开发程序员版）》构建的全栈 AI 应用项目。

**前端:** React + TypeScript + Vite
**后端:** Python + FastAPI + LangChain

## 项目结构

```
langchain-ai-app/
├── frontend/             # React 前端项目
│   ├── src/
│   │   ├── components/   # 核心功能组件
│   │   │   ├── Chat.tsx          # 基础对话
│   │   │   ├── PromptTemplate.tsx # Prompt 模板
│   │   │   ├── ChainDemo.tsx     # 链式调用
│   │   │   └── RAGQA.tsx         # RAG 文档问答
│   │   ├── hooks/
│   │   │   └── useApi.ts         # API 请求封装
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/              # Python 后端项目
│   ├── main.py           # FastAPI 路由入口
│   ├── chat.py           # 基础对话模块
│   ├── prompts.py        # Prompt 模板模块
│   ├── chains.py         # 链式调用模块
│   ├── rag.py            # RAG 文档问答模块
│   ├── config.py         # 配置管理
│   ├── requirements.txt  # Python 依赖
│   ├── .env.example      # 环境变量示例
│   └── knowledge_base/   # 知识库文档目录
└── README.md
```

## 快速开始

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY

# 启动服务
python main.py
# 服务运行在 http://localhost:8000
# API 文档在 http://localhost:8000/docs
```

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 服务运行在 http://localhost:5173
```

## 功能说明

| 功能 | 对应文章 | 说明 |
|------|---------|------|
| 基础对话 | 2.1 | 类似前端调用 API 的方式调用 LLM |
| Prompt 模板 | 2.2 | 前端模板化思维，复用 Prompt |
| 链式调用 | 2.3 | 流水线式的多步 LLM 调用 |
| RAG 文档问答 | 2.4 | 上传文档，基于文档内容问答 |

## 注意事项

- 生产环境中不要在浏览器端直接暴露 API Key，本项目中 API Key 仅在后端配置
- 上传文档支持格式: .txt, .md, .pdf, .py, .js, .ts, .jsx, .tsx
- 首次使用知识库问答时，需先上传文档到知识库
- 前端通过 Vite proxy 代理请求到后端，避免跨域问题

## 进阶方向（文章第五步）

- 实现流式输出：类似 ChatGPT 实时打字效果
- 自定义组件：封装可复用的 AI 组件
- 结合 Agent 智能体：自动排查问题、优化代码
- 集成 LangSmith：调试 LangChain 调用链
