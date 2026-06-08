import { useState, useRef, useCallback } from 'react'

/**
 * useChatStream Hook —— 管理 SSE 流式聊天
 *
 * 核心逻辑：
 * 1. POST 请求到 /api/chat，body 包含 message + history
 * 2. 接收 SSE 流（data: {token: "...", done: false}）
 * 3. 每收到一个 token 调用 onToken 回调
 * 4. 流结束后调用 onDone
 * 5. 支持 AbortController 中断请求
 *
 * @param {Object} callbacks
 * @param {Function} callbacks.onStart  - 开始发送时回调，参数：(userMessage)
 * @param {Function} callbacks.onToken  - 收到 token 时回调，参数：(token)
 * @param {Function} callbacks.onDone   - 流结束回调
 * @param {Function} callbacks.onError  - 出错回调，参数：(errorMessage)
 */
export function useChatStream({ onStart, onToken, onDone, onError } = {}) {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortControllerRef = useRef(null)

  /**
   * 发送消息
   */
  const sendMessage = useCallback(async (message, history = []) => {
    if (isStreaming) return

    setIsStreaming(true)
    onStart?.(message)

    // 创建 AbortController 用于中断
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          history: history.map(m => ({ role: m.role, content: m.content })),
          model: 'gpt-4o-mini',
          stream: true,
          temperature: 0.7,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      // 读取 SSE 流
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 数据（以 \n\n 分隔）
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''  // 保留不完整的最后一段

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          try {
            const data = JSON.parse(line.slice(6))

            if (data.error) {
              throw new Error(data.message || '未知错误')
            }

            if (data.done) {
              // 流结束
              onDone?.()
              setIsStreaming(false)
              return
            }

            if (data.token) {
              onToken?.(data.token)
            }
          } catch (e) {
            // 非 JSON 行跳过（如 [DONE]）
            if (e instanceof SyntaxError) continue
            throw e
          }
        }
      }

      // 正常结束
      onDone?.()
    } catch (error) {
      if (error.name === 'AbortError') {
        // 用户主动中断，静默处理
        return
      }

      const errorMsg = error.message || '网络错误'
      console.error('Chat stream error:', errorMsg)
      onError?.(errorMsg)
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }, [isStreaming, onStart, onToken, onDone, onError])

  /**
   * 中断流式输出
   */
  const abortStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [])

  return {
    isStreaming,
    sendMessage,
    abortStream,
  }
}
