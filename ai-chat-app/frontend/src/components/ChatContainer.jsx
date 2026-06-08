import { useRef, useEffect } from 'react'
import ChatMessage from './ChatMessage.jsx'

/**
 * 聊天消息容器 —— 管理消息列表 + 自动滚动 + 空状态
 */
export default function ChatContainer({ messages, isStreaming, scrollRef, onRetry }) {
  const bottomRef = useRef(null)

  // 新消息来时自动滚到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 空状态
  if (messages.length === 0) {
    return (
      <div className="chat-container">
        <div className="empty-state">
          <div className="empty-icon">&#x1f4ac;</div>
          <h2>开始对话</h2>
          <p>我是你的 AI 学习助手，擅长 Python、FastAPI、RAG 等 AI 开发话题</p>
          <div className="example-prompts">
            {['Python 入门', 'FastAPI 是什么', 'RAG 的原理', '如何搭建 AI 应用'].map(text => (
              <button
                key={text}
                className="example-tag"
                onClick={() => onRetry(text)}
              >
                {text}
              </button>
            ))}
          </div>
        </div>
        <div ref={bottomRef} />
      </div>
    )
  }

  return (
    <div className="chat-container" ref={scrollRef}>
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} onRetry={onRetry} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
