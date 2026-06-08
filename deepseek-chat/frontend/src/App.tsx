import { useState, useRef, useCallback, useEffect } from 'react'
import ChatContainer from './components/ChatContainer'
import ChatInput from './components/ChatInput'
import { useChatStream } from './hooks/useChatStream'
import type { ChatMessage } from './types/chat'

/** 生成唯一 ID */
const genId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8)

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId] = useState(() => `session-${genId()}`)
  const [apiStatus, setApiStatus] = useState<'loading' | 'online' | 'offline'>('loading')

  // 检查后端状态
  useEffect(() => {
    fetch('/')
      .then((r) => r.json())
      .then(() => setApiStatus('online'))
      .catch(() => setApiStatus('offline'))
  }, [])

  const { isStreaming, sendMessage, abortStream } = useChatStream({
    onStart: (userMessage) => {
      setMessages((prev) => [
        ...prev,
        { id: genId(), role: 'user', content: userMessage },
        { id: genId(), role: 'assistant', content: '', isStreaming: true },
      ])
    },
    onToken: (token) => {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          next[next.length - 1] = { ...last, content: last.content + token }
        }
        return next
      })
    },
    onDone: () => {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          next[next.length - 1] = { ...last, isStreaming: false }
        }
        return next
      })
    },
    onError: (err) => {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          next[next.length - 1] = {
            ...last,
            content: `[错误] ${err}`,
            isStreaming: false,
            isError: true,
          }
        }
        return next
      })
    },
  })

  const handleSend = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return
      sendMessage(text, sessionId)
    },
    [isStreaming, sessionId, sendMessage],
  )

  const handleClear = useCallback(async () => {
    abortStream()
    await fetch(`/api/session/${sessionId}`, { method: 'DELETE' })
    setMessages([])
  }, [abortStream, sessionId])

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo">DeepSeek Chat</div>
          <span className="header-subtitle">Powered by LangChain + DeepSeek</span>
        </div>
        <div className="header-right">
          <ApiStatusBadge status={apiStatus} />
          <button
            className="btn-clear"
            onClick={handleClear}
            disabled={messages.length === 0}
          >
            清空对话
          </button>
        </div>
      </header>

      {/* Chat Area */}
      <main className="app-main">
        <ChatContainer
          messages={messages}
          isStreaming={isStreaming}
          onRetry={handleSend}
        />
      </main>

      {/* Input */}
      <footer className="app-footer">
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          onStop={abortStream}
          disabled={apiStatus === 'offline'}
          placeholder={
            apiStatus === 'offline'
              ? '后端未启动，请先运行 backend...'
              : '输入消息，Enter 发送，Shift+Enter 换行'
          }
        />
      </footer>
    </div>
  )
}

/** API 状态徽章 */
function ApiStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    online: { label: 'DeepSeek 在线', cls: 'badge-green' },
    offline: { label: '后端断开', cls: 'badge-red' },
    loading: { label: '连接中...', cls: 'badge-gray' },
  }
  const { label, cls } = map[status] || map.loading
  return <span className={`badge ${cls}`}>{label}</span>
}
