import { useRef, useEffect } from 'react'
import ChatMessage from './ChatMessage'
import type { ChatMessage as ChatMessageType } from '../types/chat'

interface Props {
  messages: ChatMessageType[]
  isStreaming: boolean
  onRetry: (text: string) => void
}

export default function ChatContainer({ messages, isStreaming, onRetry }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-container">
        <div className="empty-state">
          <div className="empty-icon">{'\u{1F4AC}'}</div>
          <h2>DeepSeek 智能助手</h2>
          <p>
            基于 LangChain + DeepSeek-V3 构建的聊天机器人，
            支持多轮对话和流式输出，前端的你也能轻松搭建。
          </p>
          <div className="example-prompts">
            {[
              '用Python写一个快速排序',
              '解释一下LangChain的LCEL',
              '帮我写一段React Hook',
              '前端转AI该学什么',
            ].map((text) => (
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
    <div className="chat-container">
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} onRetry={onRetry} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
