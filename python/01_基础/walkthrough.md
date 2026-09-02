# 前端视角 Python 学习内容补充总结

我已经根据计划，为您在项目中补充了针对前端开发者痛点的 4 个关键概念教学文件。这些文件不仅包含了理论解释，还配备了可执行的代码片段，通过对比 JavaScript 语法，帮助您快速理解和上手。

## 补充文件概览

### 1. 模块与包机制
#### [NEW] [01_基础/06_模块与包机制.py](file:///f:/project/AI应用开发/AI appointment develop/python/01_基础/06_模块与包机制.py)
**解决的痛点**：前端开发者通常习惯了 `import {} from 'x'` 和从当前目录向上查找依赖的机制，对 Python 的导入常常感到困惑。
- 详细对比了 ES Modules 语法与 Python 导入语法。
- 解释了 `__init__.py` 在包（Package）中的作用。
- 解释了 `sys.path` 模块搜索路径的机制。
- **高频避坑**：如何避免 Python 中最让人头疼的**循环导入 (Circular Import)**。
- 解释了 `if __name__ == "__main__":` 这个魔法写法的真正用途。

### 2. 数据结构高级操作
#### [NEW] [01_基础/07_数据结构与推导式.py](file:///f:/project/AI应用开发/AI appointment develop/python/01_基础/07_数据结构与推导式.py)
**解决的痛点**：前端高度依赖 `map`、`filter` 操作数组，习惯用 `...` 扩展运算符合并对象和数组。
- 讲解了非常 Pythonic 的**列表推导式**和**字典推导式**，作为 JS 中 `map` 和 `filter` 的完美替代方案。
- 演示了如何使用 `*` 和 `**` 进行解包，完美对标 JS 中的展开运算符（Spread Operator）。
- 介绍了实用的 `zip` 函数，简化多列表遍历。

### 3. 单元测试
#### [NEW] [02_工程化/04_单元测试pytest.py](file:///f:/project/AI应用开发/AI appointment develop/python/02_工程化/04_单元测试pytest.py)
**解决的痛点**：为了工程代码质量，需要了解前端 `Jest/Vitest` 在 Python 中的对标工具。
- 引入了社区绝对主流的 `pytest` 测试框架。
- 介绍了原生的 `assert` 用法，告别长串的 `expect().toBe()`。
- 重点讲解了超越 `beforeEach` 的高级测试依赖注入机制 —— **`Fixture`**。
- 演示了如何对异常捕获以及参数化数据进行测试。

### 4. 跨域与中间件
#### [NEW] [03_网络与API/FastAPI入门/02_跨域与中间件.py](file:///f:/project/AI应用开发/AI appointment develop/python/03_网络与API/FastAPI入门/02_跨域与中间件.py)
**解决的痛点**：全栈开发中前端经常卡在 CORS 报错，以及不知道如何在后端统一处理请求状态。
- 演示了如何使用 FastAPI 的 `CORSMiddleware` 配置跨域，解决与前端 (如 React/Vue 本地服务器) 的联调问题。
- 对比 Express 中间件，演示了在 FastAPI 中如何编写拦截请求、计算耗时的自定义中间件。

---

> [!TIP]
> 建议您打开这些文件并直接运行它们。在大部分文件底部，我都提供了可以直接 `python xxx.py` 执行的演示代码。对于 FastAPI 和 pytest，文件中也包含了具体的终端启动命令。
