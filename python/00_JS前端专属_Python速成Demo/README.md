# 🚀 JS/TS 前端开发者专属：Python 速成与 AI 开发衔接指南

欢迎！本目录是专门为你（前端开发者）定制的 Python 语法速成与 AI 应用开发准备包。
每个 `.py` Demo 文件都包含了**大量对标 JavaScript / TypeScript 的精细注释**，可直接独立运行！

---

## 📂 Demo 文件目录与学习路线

| 文件名 | 核心对标 JavaScript / TypeScript 概念 | AI 开发相关应用场景 |
| :--- | :--- | :--- |
| **[`01_变量_作用域与解构_JS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/01_%E5%8F%98%E9%87%8F_%E4%BD%9C%E7%94%A8%E5%9F%9F%E4%B8%8E%E8%A7%A3%E6%9E%84_JS%E5%AF%B9%E6%AF%94.py)** | `let`/`const` vs 无关键字、`Final` 常量、数组解构、对象解构、`...` 展开运算符 vs `*`/`**`、闭包与作用域 (`nonlocal`) | Prompt 变量拼接、Payload 组装 |
| **[`02_高阶函数与列表推导式_JS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/02_%E9%AB%98%E9%98%B6%E5%87%BD%E6%95%B0%E4%B8%8E%E5%88%97%E8%A1%A8%E6%8E%A8%E5%AF%BC%E5%BC%8F_JS%E5%AF%B9%E6%AF%94.py)** | `Array.map`/`filter`/`reduce`/`find`/`some`/`every` vs **列表推导式 (List Comprehension)**、`sorted()`、字典推导式 | Prompt 列表清洗、Token 计数、搜索结果处理 |
| **[`03_对象与字典操作_JSON解析_JS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/03_%E5%AF%B9%E8%B1%A1%E4%B8%8E%E5%AD%97%E5%85%B8%E6%93%8D%E4%BD%9C_JSON%E8%A7%A3%E6%9E%90_JS%E5%AF%B9%E6%AF%94.py)** | `Object.keys/values/entries` vs `dict.items()`、可选链 `?.` vs `.get()`、`JSON.stringify` / `parse` vs `json.dumps()` / `loads()` | **解析大模型返回的 JSON**、容错正则解析 |
| **[`04_TS类型系统与Python_Type_Hints对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/04_TS%E7%B1%BB%E5%9E%8B%E7%B3%BB%E7%BB%9F%E4%B8%8EPython_Type_Hints%E5%AF%B9%E6%AF%94.py)** | TS Types vs Python Type Hints (`Union \|`, `Optional`, `Literal`, `Callable`, `TypedDict`) | 类型安全、Agent 消息格式定义 |
| **[`05_面向对象与TS_Interface对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/05_%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E4%B8%8ETS_Interface%E5%AF%B9%E6%AF%94.py)** | `constructor`/`this` vs `__init__`/`self`、`extends`、`static`、`@property`、`Protocol` (鸭子类型接口)、**`@dataclass`** | 自定义 LLM Agent 类、Tools 工具构建 |
| **[`06_异步编程_Promise与AsyncAwait_JS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/06_%E5%BC%82%E6%AD%A5%E7%BC%96%E7%A8%8B_Promise%E4%B8%8EAsyncAwait_JS%E5%AF%B9%E6%AF%94.py)** | `Promise.all` vs `asyncio.gather()`、`async/await`、事件循环 `asyncio.run()`、**异步生成器 (`async for ... in`)** | **大模型 SSE 流式打字机效果** |
| **[`07_AI开发必备_Pydantic数据校验与TS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/07_AI%E5%BC%80%E5%8F%91%E5%BF%85%E5%A4%87_Pydantic%E6%95%B0%E6%8D%AE%E6%A0%A1%E9%AA%8C%E4%B8%8ETS%E5%AF%B9%E6%AF%94.py)** | TS Interface / Zod Schema vs **Pydantic (`BaseModel`, `Field`, `validator`)** | **FastAPI 接口入参、OpenAI Function Calling / Structured Outputs** |
| **[`08_HTTP请求与API调用_JS对比.py`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/python/00_JS%E5%89%8D%E7%AB%AF%E4%B8%93%E5%B1%9E_Python%E9%80%9F%E6%88%90Demo/08_HTTP%E8%AF%B7%E6%B1%82%E4%B8%8EAPI%E8%B0%83%E7%94%A8_JS%E5%AF%B9%E6%AF%94.py)** | `fetch()` / `axios` vs `requests` (同步) / `httpx` (异步) | 调用 OpenAI / DeepSeek 原生 HTTP API |

---

## 💡 如何高效运行这些 Demo？

在终端直接执行对应文件即可：

```bash
# 必须加上环境变量，确保 Windows 控制台字符正常打印
$env:PYTHONIOENCODING="utf-8"

# 运行某个 Demo
python 01_变量_作用域与解构_JS对比.py
python 02_高阶函数与列表推导式_JS对比.py
python 07_AI开发必备_Pydantic数据校验与TS对比.py
```
