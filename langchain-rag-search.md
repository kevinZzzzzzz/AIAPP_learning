 # 用 LangChain.js 实现 RAG 知识库语义搜索 — 大白话学习笔记

 > 原文：[使用 langChain.js 实现 RAG 知识库语义搜索](https://juejin.cn/post/7526914707665829923) · 作者：双越

 ---

 ## 这篇文章在聊什么？

 双越教你怎么用 LangChain.js 搭一个 RAG 系统——就是让 AI 先去你的知识库里查资料，再根据查到的内容回答你的问题。

 说白了：**不让 AI 凭记忆瞎编，先查资料再回答。**

 ---

 ## RAG 是什么？一句话说清楚

 RAG = Retrieval-Augmented Generation（检索增强生成）。

 三步走：

 ```mermaid
 flowchart LR
     A[① 把资料拆碎 -&gt; 转成向量 -&gt; 存起来] --> B[② 用户提问 -&gt; 去库里搜最相关的内容]
     B --> C[③ 把搜到的内容 + 问题一起扔给 LLM -&gt; 生成答案]
 ```

 核心价值：**答案有据可查，不是 AI 凭空瞎编的。**

 ---

 ## 第一步：搭环境

 ```bash
 npm init
 npm i langchain @langchain/community @langchain/core dotenv
 ```

 建一个 `rag.js` 文件，后面的代码都写在这。

 ---

 ## 第二步：加载文档并存入向量数据库

 ### 加载 PDF

 准备一个 PDF 文件，用 `PDFLoader` 加载：

 ```javascript
 import { PDFLoader } from '@langchain/community/document_loaders/fs/pdf'
 const loader = new PDFLoader('data/nke-10k-2023.pdf')
 const docs = await loader.load()
 ```

 ### 拆成小块（Chunk）

 一整份 PDF 太大了，直接扔给 LLM 可能超 Token 限制，先切成小段：

 ```javascript
 import { RecursiveCharacterTextSplitter } from '@langchain/textsplitters'
 const textSplitter = new RecursiveCharacterTextSplitter({
   chunkSize: 1000,       // 每段大约 1000 字符
   chunkOverlap: 200,     // 相邻段落重叠 200 字符，避免切断了关键句子
 })
 const allSplits = await textSplitter.splitDocuments(docs)
 ```

 切完后 `allSplits.length` 会比原来大很多，一份长文档可能变成几十个小块。

 ### 转成向量并存储

 LangChain 默认的 `OpenAIEmbeddings` 在国内用不了。作者用的是 **阿里通义千问（Alibaba Tongyi）** 的 embeddings 模型。

 去阿里云百炼平台申请 API key，放 `.env`：

 ```
 ALIBABA_API_KEY=xxxx
 ```

 装插件 + 写代码：

 ```bash
 npm i @langchain/community
 ```

 ```javascript
 import { AlibabaTongyiEmbeddings } from '@langchain/community/embeddings/alibaba_tongyi'
 import { MemoryVectorStore } from 'langchain/vectorstores/memory'

 const embeddings = new AlibabaTongyiEmbeddings({})
 const vectorStore = new MemoryVectorStore(embeddings)
 await vectorStore.addDocuments(allSplits)
 ```

 **解释一下什么是向量**：你可以把一段文本想象成一个几百维的"坐标"。两个坐标之间的距离越近，两段文本的意思就越接近。这就是语义搜索的原理——搜的不是关键词，是"意思相近的内容"。

 ### 测试一下搜索

 ```javascript
 const results = await vectorStore.similaritySearch('When was Nike incorporated?')
 console.log(results[0])
 ```

 它会从向量库里找出跟问题最相关的那段 PDF 内容返回给你。

 ---

 ## 第三步：换成网页内容

 换一个场景——不加载 PDF，改成抓网页内容来建知识库：

 ```javascript
 import { CheerioWebBaseLoader } from '@langchain/community/document_loaders/web/cheerio'

 const cheerioLoader = new CheerioWebBaseLoader(
   'https://www.wangeditor.com/v5/development.html',
   { selector: 'p' }  // 只抓 <p> 标签的内容
 )
 const docs = await cheerioLoader.load()
 ```

 后面的切分、转向量、存库，跟 PDF 流程一模一样。

 ---

 ## 第四步：定义 RAG 工作流（检索 → 生成）

 装 LangGraph：

 ```bash
 npm i @langchain/langgraph
 ```

 ### 定义数据结构

 工作流各节点之间传什么数据：

 ```javascript
 const StateAnnotation = Annotation.Root({
   question: Annotation,  // 用户输入的问题
   context: Annotation,   // 从向量库搜出来的资料
   answer: Annotation,    // 最终答案
 })
 ```

 ### 定义"检索"节点

 ```javascript
 const retrieve = async (state) => {
   const retrievedDocs = await vectorStore.similaritySearch(state.question)
   return { context: retrievedDocs }
 }
 ```

 拿着用户问题去向量库里搜最相关的段落。

 ### 定义"生成"节点

 ```javascript
 const generate = async (state) => {
   const docsContent = state.context.map(doc => doc.pageContent).join('\n')
   const messages = await promptTemplate.invoke({
     question: state.question,
     context: docsContent,
   })
   const response = await llm.invoke(messages)
   return { answer: response.content }
 }
 ```

 把搜到的资料 + 用户问题组装成 Prompt 发给 LLM，LLM 基于资料回答问题。

 ### 组装工作流

 ```javascript
 const graph = new StateGraph(StateAnnotation)
   .addNode('retrieve', retrieve)
   .addNode('generate', generate)
   .addEdge('__start__', 'retrieve')
   .addEdge('retrieve', 'generate')
   .addEdge('generate', '__end__')
   .compile()
 ```

 流程太直观了：

 ```mermaid
 flowchart LR
     Start[开始] --> Retrieve[检索：去向量库搜相关段落]
     Retrieve --> Generate[生成：LLM 基于搜到的内容回答]
     Generate --> End[结束：返回答案]
 ```

 ### 调用

 ```javascript
 const result = await graph.invoke({ question: '什么是 ModalMenu?' })
 console.log(result.answer)
 ```

 还能用 `graph.stream` 流式输出，配合前端实现打字效果。

 ---

 ## 生产环境怎么搞？

 开发阶段用的 `MemoryVectorStore` 是存在内存里的，重启就没了。生产环境要用真正的向量数据库：

 - **Pinecone** — 推荐，有免费额度
 - 其他选项：Weaviate、Qdrant、Milvus

 ---

 ## 三句总结

 1. **RAG 的核心就三步**：切碎资料 → 转成向量存起来 → 用户提问时去搜最相关的，让 LLM 基于搜到的内容回答
 2. **向量不是什么高深概念**，就是"文本的坐标"，坐标距离近 = 意思相近
 3. **国内开发注意选替代品**：OpenAI 的 embeddings 用不了就用阿里通义千问，LLM 用 DeepSeek

 ---

 *笔记基于双越的文章整理，原文链接：https://juejin.cn/post/7526914707665829923*
