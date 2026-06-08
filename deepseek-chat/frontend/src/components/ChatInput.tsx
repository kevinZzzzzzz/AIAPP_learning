import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react'

interface Props {
  onSend: (text: string) => void
  isStreaming: boolean
  onStop: () => void
  placeholder: string
  disabled: boolean
}

export default function ChatInput({
  onSend,
  isStreaming,
  onStop,
  placeholder,
  disabled,
}: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus()
  }, [disabled])

  const adjustHeight = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  }

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    adjustHeight()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
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
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
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
