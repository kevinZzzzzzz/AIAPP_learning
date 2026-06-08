/** 单条聊天消息 */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  isStreaming?: boolean
  isError?: boolean
}

/** 发送给后端的请求 */
export interface ChatRequest {
  message: string
  session_id: string
  temperature?: number
}

/** SSE 数据块 */
export interface SSEChunk {
  token?: string
  done?: boolean
  status?: string
  error?: boolean
  message?: string
  session_id?: string
  history_length?: number
}
