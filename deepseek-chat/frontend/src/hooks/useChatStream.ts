import { useState, useRef, useCallback } from 'react'
import type { SSEChunk } from '../types/chat'

interface Callbacks {
  onStart?: (userMessage: string) => void
  onToken?: (token: string) => void
  onDone?: () => void
  onError?: (error: string) => void
}

interface UseChatStreamReturn {
  isStreaming: boolean
  sendMessage: (message: string, sessionId: string) => void
  abortStream: () => void
}

export function useChatStream(callbacks: Callbacks = {}): UseChatStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (message: string, sessionId: string) => {
      if (isStreaming) return

      setIsStreaming(true)
      callbacks.onStart?.(message)

      const controller = new AbortController()
      controllerRef.current = controller

      try {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            session_id: sessionId,
            temperature: 0.7,
          }),
          signal: controller.signal,
        })

        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${response.status}`)
        }

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const data: SSEChunk = JSON.parse(line.slice(6))

              if (data.error) throw new Error(data.message || 'stream error')
              if (data.token) callbacks.onToken?.(data.token)
              if (data.done) {
                callbacks.onDone?.()
                setIsStreaming(false)
                return
              }
            } catch (e) {
              if (e instanceof SyntaxError) continue
              throw e
            }
          }
        }

        callbacks.onDone?.()
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }
        const msg = error instanceof Error ? error.message : '网络错误'
        console.error('Stream error:', msg)
        callbacks.onError?.(msg)
      } finally {
        setIsStreaming(false)
        controllerRef.current = null
      }
    },
    [isStreaming, callbacks],
  )

  const abortStream = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    setIsStreaming(false)
  }, [])

  return { isStreaming, sendMessage, abortStream }
}
