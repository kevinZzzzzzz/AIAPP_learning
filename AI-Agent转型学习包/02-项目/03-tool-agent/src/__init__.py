"""工具调用 Agent —— 模块 04/05 配套项目。

模块划分：
    config.py    配置与模型客户端
    tools.py     工具定义 + 工具注册表（含参数校验、超时、错误处理）
    safety.py    危险操作的确认机制（人在环）
    agent.py     手写 ReAct 循环（本项目的心脏）
    main.py      CLI 入口
"""
