/**
 * 单条聊天消息组件
 *
 * 功能：
 * - 根据 role 显示不同的头像和样式
 * - 流式消息显示闪烁光标
 * - 简单 Markdown 渲染（代码块、加粗、列表）
 * - 错误消息显示重试按钮
 */
export default function ChatMessage({ message, onRetry }) {
  const { role, content, isStreaming } = message
  const isUser = role === 'user'
  const isError = content.startsWith('[错误]')

  return (
    <div className={`message ${role}`}>
      {/* 头像 */}
      <div className="message-avatar">
        {isUser ? '\u{1F468}' : '\u{1F916}'}
      </div>

      {/* 消息内容 */}
      <div className="message-content">
        {isUser ? (
          content
        ) : (
          <>
            {renderMarkdown(content)}
            {isStreaming && <span className="cursor-blink" />}
          </>
        )}

        {/* 错误时显示重试按钮 */}
        {isError && (
          <div className="message-actions">
            <button className="btn-retry" onClick={() => onRetry?.(content)}>
              重试
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 简易 Markdown 渲染（无需引入第三方库）
 * 支持：代码块、行内代码、加粗、无序列表、有序列表
 */
function renderMarkdown(text) {
  if (!text) return null

  const lines = text.split('\n')
  const elements = []
  let inCodeBlock = false
  let codeContent = ''
  let codeLanguage = ''

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // 代码块
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        // 结束代码块
        elements.push(
          <pre key={`code-${i}`}>
            <code>{codeContent.trim()}</code>
          </pre>
        )
        codeContent = ''
        inCodeBlock = false
      } else {
        // 开始代码块
        codeLanguage = line.slice(3).trim()
        inCodeBlock = true
      }
      i++
      continue
    }

    if (inCodeBlock) {
      codeContent += line + '\n'
      i++
      continue
    }

    // 空行
    if (!line.trim()) {
      elements.push(<div key={i} style={{ height: 8 }} />)
      i++
      continue
    }

    // 无序列表
    if (line.match(/^[-*]\s/)) {
      elements.push(
        <li key={i}>{renderInline(line.replace(/^[-*]\s/, ''))}</li>
      )
      i++
      continue
    }

    // 有序列表
    if (line.match(/^\d+\.\s/)) {
      elements.push(
        <li key={i}>{renderInline(line.replace(/^\d+\.\s/, ''))}</li>
      )
      i++
      continue
    }

    // 普通段落
    elements.push(<p key={i}>{renderInline(line)}</p>)
    i++
  }

  // 未闭合的代码块
  if (inCodeBlock) {
    elements.push(
      <pre key="unclosed">
        <code>{codeContent.trim()}</code>
      </pre>
    )
  }

  return elements
}

/**
 * 行内渲染：加粗 **text** 和 行内代码 `code`
 */
function renderInline(text) {
  if (!text) return null

  // 分割 **加粗**
  const boldRegex = /\*\*(.+?)\*\*/g
  // 分割 `行内代码`
  const codeRegex = /`([^`]+)`/g

  // 简单处理：只处理一种格式
  const parts = []
  let lastIndex = 0
  let match

  // 先用一个简单的方法：依次替换 **bold** 和 `code`
  const combinedRegex = /(\*\*(.+?)\*\*)|(`([^`]+)`)/g

  while ((match = combinedRegex.exec(text)) !== null) {
    // 添加前面的文本
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    if (match[1]) {
      // **加粗**
      parts.push(<strong key={match.index}>{match[2]}</strong>)
    } else if (match[3]) {
      // `行内代码`
      parts.push(<code key={match.index}>{match[4]}</code>)
    }

    lastIndex = match.index + match[0].length
  }

  // 添加剩余文本
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length > 0 ? parts : text
}
