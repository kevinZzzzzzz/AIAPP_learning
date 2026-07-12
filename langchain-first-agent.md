 # 30 行代码用 LangChain.js 开发第一个 AI Agent — 大白话学习笔记

 > 原文：[30 行代码 langChain.js 开发你的第一个 Agent](https://juejin.cn/post/7524180232024490020) · 作者：双越

 ---

 ## 这篇文章在聊什么？

 双越手把手教你用 LangChain.js 写一个能联网查天气的 AI Agent，核心代码不到 30 行。

 然后更进一步，教你用 LangGraph 自定义 Agent 的行为流程，让 Agent 按你定的逻辑跑，而不是完全交给他"自由发挥"。

 ---

 ## 第一步：搭环境

 ```bash
 npm init
 npm i langchain dotenv
 ```

 装好 langchain 和 dotenv（用来读环境变量）就够了。

 ---

 ## 第二步：给 Agent 配一个"搜索引擎"

 Agent 要能联网查天气，需要给配一个搜索工具。作者用的是 **Tavily**，一个专门给 LLM 用的搜索引擎。

 注册 Tavily 拿到 API key，放 `.env` 文件里：

 ```
 TAVILY_API_KEY=xxx
 ```

 装插件：

 ```bash
 npm i @langchain/tavily
 ```

 代码里定义工具：

 ```javascript
 import { TavilySearch } from '@langchain/tavily'
 const agentTools = [
   new TavilySearch({ maxResults: 3 })
 ]
 ```

 ---

 ## 第三步：选一个大模型

 LangChain 默认推荐 OpenAI，但在国内调不通。作者选的是 **DeepSeek**。

 注册 DeepSeek 拿到 API key，放 `.env`：

 ```
 DEEPSEEK_API_KEY=xxx
 ```

 装插件 + 写代码：

 ```bash
 npm i @langchain/deepseek
 ```

 ```javascript
 import { ChatDeepSeek } from '@langchain/deepseek'
 const agentModel = new ChatDeepSeek({ model: 'deepseek-chat', temperature: 0 })
 ```

 `temperature: 0` 表示每次回答尽可能一致，不要天马行空。

 ---

 ## 第四步：组装一个 ReAct Agent（核心 30 行）

 装 LangGraph：

 ```bash
 npm i @langchain/langgraph @langchain/core
 ```

 写代码：

 ```javascript
 import { MemorySaver } from '@langchain/langgraph'
 import { createReactAgent } from '@langchain/langgraph/prebuilt'

 const agentCheckpoint = new MemorySaver()  // 记忆存储

 const agent = createReactAgent({
   llm: agentModel,       // DeepSeek
   tools: agentTools,      // Tavily 搜索
   checkpointSaver: agentCheckpoint,  // 记忆
 })
 ```

 **ReAct = Reason + Act（推理 + 执行）**。Agent 接到问题后自己决定：需不需要调工具？调哪个工具？拿到结果后怎么回答你？

 `MemorySaver` 的作用：让 Agent 记住对话上下文。否则你刚说"我叫张三"，它转头就忘了。

 ---

 ## 第五步：调用 Agent

 ```javascript
 import { HumanMessage } from '@langchain/core/messages'

 // 查旧金山天气
 const result1 = await agent.invoke(
   { messages: [new HumanMessage('what is the current weather in sf')] },
   { configurable: { thread_id: '1' } }
 )

 // 用同一个 thread_id 查北京天气，Agent 知道"what about Beijing"是在问天气
 const result2 = await agent.invoke(
   { messages: [new HumanMessage('what about Beijing')] },
   { configurable: { thread_id: '1' } }
 )
 ```

 `thread_id` 是记忆的索引。同一个 `thread_id` 的对话才共享上下文。第二次只说了"what about Beijing"，Agent 靠上轮记忆知道你想问天气。

 还可以用 `agent.stream` 流式输出，配合前端实现打字效果。

 ---

 ## 第六步：用 LangGraph 自定义 Agent 流程

 ReAct Agent 虽然能自动推理，但流程是写死的。如果你想自己控制"什么时候调工具、什么时候结束"，就需要 LangGraph 的 `StateGraph`。

 核心思路是定义三个东西：

 ### 1. 工具节点（toolNode）

 ```javascript
 import { ToolNode } from '@langchain/langgraph/prebuilt'
 const tools = [new TavilySearch({ maxResults: 3 })]
 const toolNode = new ToolNode(tools)
 ```

 ### 2. 条件判断函数（shouldContinue）

 ```javascript
 function shouldContinue({ messages }) {
   const lastMessage = messages[messages.length - 1]
   if (lastMessage.tool_calls?.length) {
     return 'tools'   // 如果要调工具，走 tools 节点
   }
   return '__end__'    // 否则结束
 }
 ```

 ### 3. 模型调用函数（callModel）

 ```javascript
 async function callModel(state) {
   const response = await model.invoke(state.messages)
   return { messages: [response] }
 }
 ```

 ### 4. 组装工作流

 ```javascript
 const workflow = new StateGraph(MessagesAnnotation)
   .addNode('agent', callModel)
   .addEdge('__start__', 'agent')
   .addNode('tools', toolNode)
   .addEdge('tools', 'agent')
   .addConditionalEdges('agent', shouldContinue)
   .compile()
 ```

 整个流程长这样：

 ```mermaid
 flowchart TD
     Start[开始] --> Agent[Agent 思考]
     Agent --> Judge{shouldContinue<br/>判断是否需要调工具}
     Judge -->|不需要| End[结束]
     Judge -->|需要| Tools[调工具拿结果]
     Tools --> Agent
 ```

 每一轮：Agent 思考 → 判断要不要调工具 → 如果要，调完再回来让 Agent 继续思考 → 直到不需要调工具为止。

 ---

 ## 三句总结

 1. **一个 Agent 最简模型 = LLM + Tools + Memory**，30 行代码就能跑起来
 2. **用 `createReactAgent` 快速上手，用 `StateGraph` 精确控制**——前者省事但黑盒，后者灵活但要多写几行
 3. **`thread_id` 是记忆的钥匙**，同一个 thread_id 才是同一个会话，共享上下文

 ---

 *笔记基于双越的文章整理，原文链接：https://juejin.cn/post/7524180232024490020*
