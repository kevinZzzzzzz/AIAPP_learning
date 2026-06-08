import type { ChatMessage as ChatMessageType } from '../types/chat'

interface Props {
  message: ChatMessageType
  onRetry?: (text: string) => void
}

export default function ChatMessage({ message, onRetry }: Props) {
  const { role, content, isStreaming, isError } = message
  const isUser = role === 'user'

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {isUser ? '\u{1F468}' : '\u{1F916}'}
      </div>
      <div className="message-content">
        {isUser ? (
          <span>{content}</span>
        ) : (
          <>
            {renderMarkdown(content)}
            {isStreaming && <span className="cursor-blink" />}
          </>
        )}
        {isError && onRetry && (
          <div style={{ marginTop: 8 }}>
            <button
              className="btn-retry"
              onClick={() => onRetry(content)}
            >
              重试
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/** 简易 Markdown 渲染：代码块、行内代码、加粗、列表 */
function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null

  const lines = text.split('\n')
  const nodes: React.ReactNode[] = []
  let inCode = false
  let codeBuf = ''

  lines.forEach((line, i) => {
    if (line.startsWith('```')) {
      if (inCode) {
        nodes.push(
          <pre key={`pre-${i}`}><code>{codeBuf.trim()}</code></pre>,
        )
        codeBuf = ''
        inCode = false
      } else {
        inCode = true
      }
      return
    }

    if (inCode) {
      codeBuf += line + '\n'
      return
    }

    if (!line.trim()) {
      nodes.push(<div key={i} style={{ height: 8 }} />)
      return
    }

    if (/^[-*]\s/.test(line)) {
      nodes.push(<li key={i}>{renderInline(line.replace(/^[-*]\s/, ''))}</li>)
      return
    }
    if (/^\d+\.\s/.test(line)) {
      nodes.push(<li key={i}>{renderInline(line.replace(/^\d+\.\s/, ''))}</li>)
      return
    }

    nodes.push(<p key={i}>{renderInline(line)}</p>)
  })

  if (inCode) {
    nodes.push(
      <pre key="unclosed"><code>{codeBuf.trim()}</code></pre>,
    )
  }

  return nodes
}

/** 行内渲染：加粗和行内代码 */
function renderInline(text: string): React.ReactNode {
  const regex = /(\*\*(.+?)\*\*)|(`([^`]+)`)/g
  const parts: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null

  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    if (m[1]) parts.push(<strong key={m.index}>{m[2]}</strong>)
    else if (m[3]) parts.push(<code key={m.index}>{m[4]}</code>)
    last = m.index + m[0].length
  }

  if (last < text.length) parts.push(text.slice(last))
  return parts.length ? parts : text
}
