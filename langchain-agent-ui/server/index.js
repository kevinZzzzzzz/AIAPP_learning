import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import { TavilySearch } from '@langchain/tavily'
import { ChatDeepSeek } from '@langchain/deepseek'
import { MemorySaver } from '@langchain/langgraph'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { HumanMessage } from '@langchain/core/messages'

const PORT = process.env.PORT || 3001
const app = express()
app.use(cors())
app.use(express.json())

// 初始化 Agent: LLM + Tools + Memory
const agentTools = [new TavilySearch({ maxResults: 3 })]
const agentModel = new ChatDeepSeek({ model: 'deepseek-chat', temperature: 0 })
const agentCheckpoint = new MemorySaver()

const agent = createReactAgent({
  llm: agentModel,
  tools: agentTools,
  checkpointSaver: agentCheckpoint,
})

// SSE 聊天接口
app.post('/api/chat', async (req, res) => {
  const { message, threadId } = req.body
  if (!message) {
    return res.status(400).json({ error: 'message is required' })
  }

  const tid = threadId || 'default'

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  try {
    const stream = await agent.stream(
      { messages: [new HumanMessage(message)] },
      { configurable: { thread_id: tid }, streamMode: 'updates' }
    )

    for await (const step of stream) {
      const nodeName = Object.keys(step)[0]
      const data = step[nodeName]

      // 如果有消息内容，推给前端
      if (data?.messages) {
        const lastMsg = data.messages[data.messages.length - 1]
        if (lastMsg?.content) {
          const content =
            typeof lastMsg.content === 'string'
              ? lastMsg.content
              : JSON.stringify(lastMsg.content)
          res.write(`data: ${JSON.stringify({ type: 'token', content })}\n\n`)
        }
      }

      // 如果有工具调用，通知前端
      if (data?.messages?.[0]?.tool_calls?.length) {
        const toolName = data.messages[0].tool_calls[0].name
        res.write(
          `data: ${JSON.stringify({ type: 'tool_call', toolName })}\n\n`
        )
      }
    }

    res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`)
    res.end()
  } catch (err) {
    console.error('Agent error:', err)
    res.write(
      `data: ${JSON.stringify({ type: 'error', content: err.message })}\n\n`
    )
    res.end()
  }
})

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' })
})

app.listen(PORT, () => {
  console.log(`Agent server running on http://localhost:${PORT}`)
})
