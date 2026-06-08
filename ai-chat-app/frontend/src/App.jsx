import { useState, useRef, useCallback } from 'react'
import ChatContainer from './components/ChatContainer.jsx'
import ChatInput from './components/ChatInput.jsx'
import { useChatStream } from './hooks/useChatStream.js'

/**
 * 根组件 —— 管理全局状态
 *
 * 状态设计：
 * - messages: 对话历史 [{ id, role, content, isStreaming? }]
 * - isStreaming: 是否正在接收流式回复
 * - apiMode: 'openai' | 'mock' | 'loading' | 'error'
 */
export default function App() {
  const [messages, setMessages] = useState([])
  const [apiMode, setApiMode] = useState('loading')
  const scrollRef = useRef(null)

  // 检查后端健康状态
  useState(() => {
    fetch('/')
      .then(res => res.json())
      .then(data => setApiMode(data.mode))
      .catch(() => setApiMode('error'))
  }, [])

  const { isStreaming, sendMessage, abortStream } = useChatStream({
    onStart: (userMessage) => {
      // 添加用户消息 + 空的 AI 消息占位
      setMessages(prev => [
        ...prev,
        { id: Date.now().toString(), role: 'user', content: userMessage },
        { id: (Date.now() + 1).toString(), role: 'assistant', content: '', isStreaming: true },
      ])
    },
    onToken: (token) => {
      // 逐字更新 AI 回复
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.role === 'assistant') {
          updated[updated.length - 1] = { ...last, content: last.content + token }
        }
        return updated
      })
    },
    onDone: () => {
      // 标记流式完成
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.role === 'assistant') {
          updated[updated.length - 1] = { ...last, isStreaming: false }
        }
        return updated
      })
    },
    onError: (error) => {
      // 显示错误
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.role === 'assistant') {
          updated[updated.length - 1] = {
            ...last,
            content: `[错误] ${error}`,
            isStreaming: false,
          }
        }
        return updated
      })
    },
  })

  const handleSend = useCallback((text) => {
    if (!text.trim() || isStreaming) return

    // 收集历史消息发送给后端
    const history = messages.map(m => ({
      role: m.role,
      content: m.content,
    }))

    sendMessage(text, history)
  }, [messages, isStreaming, sendMessage])

  const handleClear = useCallback(() => {
    abortStream()
    setMessages([])
  }, [abortStream])

  return (
    <div className="app">
      {/* 顶部导航 */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo">AI Chat</div>
          <span className="header-subtitle">智能对话助手</span>
        </div>
        <div className="header-right">
          <ApiStatusBadge mode={apiMode} />
          <button className="btn-clear" onClick={handleClear} disabled={messages.length === 0}>
            清空对话
          </button>
        </div>
      </header>

      {/* 聊天区域 */}
      <main className="app-main">
        <ChatContainer
          messages={messages}
          isStreaming={isStreaming}
          scrollRef={scrollRef}
          onRetry={(msg) => handleSend(msg)}
        />
      </main>

      {/* 底部输入框 */}
      <footer className="app-footer">
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          onStop={abortStream}
          placeholder={
            apiMode === 'error'
              ? '后端未连接，请先启动 backend...'
              : apiMode === 'mock'
              ? '试试问我"Python"、"FastAPI" 或 "RAG"...'
              : '输入消息，Enter 发送，Shift+Enter 换行...'
          }
          disabled={apiMode === 'error'}
        />
      </footer>
    </div>
  )
}

/**
 * API 状态徽章
 */
function ApiStatusBadge({ mode }) {
  const config = {
    openai:   { label: 'OpenAI API', className: 'badge badge-green' },
    mock:     { label: '模拟模式',   className: 'badge badge-yellow' },
    loading:  { label: '连接中...',  className: 'badge badge-gray' },
    error:    { label: '后端断开',   className: 'badge badge-red' },
  }
  const { label, className } = config[mode] || config.error

  return <span className={className}>{label}</span>
}
