import { useState, useRef, useEffect } from 'react'
import './App.css'

export default function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好！我是 AI Agent，可以帮你查询天气等信息。试试问 "北京今天天气怎么样？"' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentTool, setCurrentTool] = useState(null)
  const msgEndRef = useRef(null)
  const threadId = useRef('thread_' + Date.now())

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentTool])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)
    setCurrentTool(null)

    // 加一个空的 assistant 消息，用于流式追加
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, threadId: threadId.current }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'token') {
              setMessages((prev) => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last.role === 'assistant') {
                  last.content += data.content
                }
                return copy
              })
            } else if (data.type === 'tool_call') {
              setCurrentTool(data.toolName)
            } else if (data.type === 'done') {
              setCurrentTool(null)
              setLoading(false)
            } else if (data.type === 'error') {
              setMessages((prev) => [
                ...prev,
                { role: 'assistant', content: '出错了：' + data.content },
              ])
              setLoading(false)
            }
          } catch (err) {
            // 忽略解析错误
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '请求失败：' + err.message },
      ])
    }
    setLoading(false)
    setCurrentTool(null)
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Agent Chat</h1>
        <span className="badge">ReAct Agent · LangChain.js</span>
      </header>

      <div className="chat">
        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="bubble">{msg.content}</div>
            </div>
          ))}

          {currentTool && (
            <div className="tool-indicator">
              🔧 正在调用工具: <code>{currentTool}</code>
            </div>
          )}

          <div ref={msgEndRef} />
        </div>
      </div>

      <form className="input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题，例如：北京今天天气怎么样？"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? '思考中...' : '发送'}
        </button>
      </form>
    </div>
  )
}
