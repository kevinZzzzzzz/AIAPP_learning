 # 用 LangChain.js 实现智能总结（大文档 + Token 限制）— 大白话学习笔记

 > 原文：[使用 langChain.js 实现智能总结（考虑大文档和 token 限制）](https://juejin.cn/post/7539932143431352335) · 作者：双越

 ---

 ## 这篇文章在聊什么？

 很多内容平台都有"智能总结"功能——把一篇文章丢给 AI，让它自动生成几百字的摘要。

 小文章好办，直接发给 LLM 就行。但碰上几万字的巨长文档，LLM 有 Token 上限，装不下。怎么办呢？

 双越教了你两种方案，核心是第二种 **Map-Reduce**——把大文章拆成小块，分别总结，最后拼起来。

 ---

 ## 方式一：小文档直接"塞"（Stuff）

 如果你的文档很短，不超过 LLM 的 Token 上限，简单粗暴就行：

 ### 加载文档

 ```javascript
 import { TextLoader } from 'langchain/document_loaders/fs/text'
 const loader = new TextLoader('data/blog1.md')
 const doc = await loader.load()
 ```

 ### 定义 LLM（同样用 DeepSeek）

 ```javascript
 import { ChatDeepSeek } from '@langchain/deepseek'
 import 'dotenv/config'
 const llm = new ChatDeepSeek({ model: 'deepseek-chat', temperature: 0 })
 ```

 ### 定义 Prompt + Chain + 调用

 ```javascript
 import { createStuffDocumentsChain } from 'langchain/chains/combine_documents'
 import { StringOutputParser } from '@langchain/core/output_parsers'
 import { PromptTemplate } from '@langchain/core/prompts'

 const prompt = PromptTemplate.fromTemplate(
   `简单总结这篇文章，200 字以内。
   <article>
   {context}
   </article>`
 )

 const chain = await createStuffDocumentsChain({
   llm,
   outputParser: new StringOutputParser(),
   prompt,
 })

 const result = await chain.invoke({ context: doc })
 console.log(result)
 ```

 还能用 `chain.stream` 流式输出，前端展示打字效果。

 **适用场景：** 几千字以内的短文。一旦文档太长，LLM 可能直接报 Token 超限错误。

 ---

 ## 方式二：大文档用 Map-Reduce

 如果你的文章有上万字，就不能一次性塞给 LLM 了。**Map-Reduce** 的思路：

 > 把大文章切成小段 → 每段分别让 LLM 写摘要（Map） → 把所有摘要合并成一份总摘要（Reduce） → 如果合并后还太长，继续压缩（递归Reduce）

 ```mermaid
 flowchart TD
     Raw[原始大文档] --> Split[切成N个小块]
     Split --> Map1[块1 → 摘要1]
     Split --> Map2[块2 → 摘要2]
     Split --> Map3[块N → 摘要N]
     Map1 --> Collect[收集所有摘要]
     Map2 --> Collect
     Map3 --> Collect
     Collect --> Check{总摘要是否<br/>超出 Token 限制？}
     Check -->|没超| Final[生成最终总结]
     Check -->|超了| Collapse[继续压缩合并]
     Collapse --> Check
 ```

 ### 第一步：加载大文档并切分

 准备一份上万字的 Markdown 文档，加载后切块：

 ```javascript
 import { RecursiveCharacterTextSplitter } from '@langchain/textsplitters'

 const textSplitter = new RecursiveCharacterTextSplitter({
   chunkSize: 1000,
   chunkOverlap: 100,
 })
 const splitDocs = await textSplitter.splitDocuments(doc)
 // 比如切出 30 个小块
 ```

 ### 第二步：Map — 每块分别总结

 用 `Send` 把每个小块分发给 `generateSummary` 节点：

 ```javascript
 import { Send } from '@langchain/langgraph'

 const mapSummaries = (state) => {
   return state.contents.map(
     (content) => new Send('generateSummary', { content })
   )
 }

 const generateSummary = async (state) => {
   const prompt = await mapPrompt.invoke({ context: state.content })
   const response = await llm.invoke(prompt)
   return { summaries: [String(response.content)] }
 }
 ```

 结果：原来是 `['内容1', '内容2', '内容3']`，变成了 `['摘要1', '摘要2', '摘要3']`。

 ### 第三步：Reduce — 合并摘要

 把所有摘要收集起来，判断是否超出 Token 限制：

 ```javascript
 const collectSummaries = async (state) => {
   return {
     collapsedSummaries: state.summaries.map(
       (summary) => new Document({ pageContent: summary })
     ),
   }
 }

 const shouldCollapse = async (state) => {
   let numTokens = await lengthFunction(state.collapsedSummaries)
   if (numTokens > tokenMax) {
     return 'collapseSummaries'  // 超了，继续压缩
   } else {
     return 'generateFinalSummary'  // 没超，生成最终总结
   }
 }

 const generateFinalSummary = async (state) => {
   const response = await _reduce(state.collapsedSummaries)
   return { finalSummary: response }
 }
 ```

 如果还超 Token，就继续递归压缩，直到能在限制内生成最终总结。

 ### 第四步：用 StateGraph 搭工作流

 ```javascript
 const graph = new StateGraph(OverallState)
   .addNode('generateSummary', generateSummary)     // Map
   .addNode('collectSummaries', collectSummaries)     // 收集
   .addNode('collapseSummaries', collapseSummaries)   // 压缩
   .addNode('generateFinalSummary', generateFinalSummary) // 最终
   .addConditionalEdges('__start__', mapSummaries, ['generateSummary'])
   .addEdge('generateSummary', 'collectSummaries')
   .addConditionalEdges('collectSummaries', shouldCollapse, [
     'collapseSummaries',
     'generateFinalSummary',
   ])
   .addConditionalEdges('collapseSummaries', shouldCollapse, [
     'collapseSummaries',
     'generateFinalSummary',
   ])
   .addEdge('generateFinalSummary', '__end__')
   .compile()
 ```

 用 `stream` 调用，拿到最终总结：

 ```javascript
 for await (const step of await app.stream(
   { contents: splitDocs.map(doc => doc.pageContent) },
   { recursionLimit: 10 }
 )) {
   if (step.hasOwnProperty('generateFinalSummary')) {
     console.log(step.generateFinalSummary)
   }
 }
 ```

 ---

 ## 踩坑提醒

 作者在计算 Token 数量时遇到一个报错 `Failed to calculate number of tokens, falling back to approximate count`。解决方案是直接用字符串的 `length` 代替：

 ```javascript
 async function lengthFunction(documents) {
   return documents.reduce((sum, doc) => sum + doc.pageContent.length, 0)
 }
 ```

 虽然不是精确的 Token 数，但作为粗略判断够用了。

 ---

 ## 三句总结

 1. **小文档用 Stuff**，直接整个丢给 LLM 总结，简单粗暴
 2. **大文档用 Map-Reduce**：切块 → 分别总结（Map） → 合并摘要（Reduce） → 太长就递归压缩
 3. **LangGraph 的工作流是核心**，`StateGraph` + `Send` + 条件判断，搭出可控制的多步 AI 流程

 ---

 *笔记基于双越的文章整理，原文链接：https://juejin.cn/post/7539932143431352335*
