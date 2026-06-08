import { useState, useRef, useEffect } from 'react'

/**
 * 聊天输入框组件
 *
 * 交互功能：
 * - Enter 发送（Shift+Enter 换行）
 * - 自动调整高度
 * - 流式输出时显示停止按钮
 * - 禁用状态
 */
export default function ChatInput({
  onSend,
  isStreaming,
  onStop,
  placeholder,
  disabled,
}) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)

  // 自动聚焦
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus()
    }
  }, [disabled])

  // 自动调整高度
  const adjustHeight = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  }

  const handleChange = (e) => {
    setText(e.target.value)
    adjustHeight()
  }

  const handleKeyDown = (e) => {
    // Enter 发送（Shift+Enter 换行）
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming || disabled) return

    onSend(trimmed)
    setText('')
    // 重置高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  return (
    <div className="chat-input-wrapper">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
      />

      {isStreaming ? (
        <button className="btn-stop" onClick={onStop} title="停止生成">
          &#x25A0;
        </button>
      ) : (
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          title="发送 (Enter)"
        >
          &#x2191;
        </button>
      )}
    </div>
  )
}
