/**
 * API 调用封装
 * 对应文章中"类似前端调用第三方接口"的思路
 */

const API_BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `请求失败: ${res.status}`)
  }
  return res.json()
}

/** 基础对话 */
export async function chat(messages: { role: string; content: string }[]) {
  return request<{ reply: string }>('/chat', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  })
}

/** 获取 Prompt 模板列表 */
export async function getPromptTemplates() {
  return request<{ templates: any[] }>('/prompts')
}

/** 应用 Prompt 模板 */
export async function applyPrompt(templateId: string, variables: Record<string, string>) {
  return request<{ result: string }>('/prompts/apply', {
    method: 'POST',
    body: JSON.stringify({ template_id: templateId, variables }),
  })
}

/** 获取可用链列表 */
export async function getChains() {
  return request<{ chains: any[] }>('/chains')
}

/** 运行链 */
export async function runChain(chainId: string, variables: Record<string, string>) {
  return request<{ result: any }>('/chains/run', {
    method: 'POST',
    body: JSON.stringify({ chain_id: chainId, variables }),
  })
}

/** 上传文档到知识库 */
export async function uploadDocument(file: File, collectionName = 'default') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('collection_name', collectionName)
  const res = await fetch(`${API_BASE}/rag/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

/** RAG 问答 */
export async function queryKnowledge(question: string, collectionName = 'default') {
  return request<{ answer: string; sources: any[] }>('/rag/query', {
    method: 'POST',
    body: JSON.stringify({ question, collection_name: collectionName }),
  })
}

/** 知识库文件列表 */
export async function getKnowledgeFiles() {
  return request<{ files: any[] }>('/rag/files')
}
