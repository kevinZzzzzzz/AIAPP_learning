import { useState, useRef, useEffect } from 'react'
import { chat } from '../hooks/useApi'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: '你好！我是 AI 助手。有什么可以帮助你的？' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')

    const userMsg: Message = { role: 'user', content: text }
    const updated = [...messages, userMsg]
    setMessages(updated)

    // 过滤 system 消息（只用于展示，不传给 API）
    const apiMessages = updated.filter((m) => m.role !== 'system')
    setLoading(true)
    try {
      const { reply } = await chat(apiMessages)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `错误: ${e.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div>
      <h2 className="page-title">基础对话</h2>
      <p className="page-desc">
        文章 2.1 - 类似前端调用后端接口的方式，调用 LLM 进行对话
      </p>

      <div className="card">
        <div className="message-list" ref={listRef}>
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.content}
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <span className="loading-spinner" /> 思考中...
            </div>
          )}
        </div>

        <div className="chat-input-row">
          <input
            className="form-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题，按 Enter 发送..."
            disabled={loading}
          />
          <button className="btn btn-primary" onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? <span className="loading-spinner" /> : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
