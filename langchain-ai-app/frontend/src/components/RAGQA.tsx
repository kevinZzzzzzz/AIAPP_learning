import { useState } from 'react'
import { uploadDocument, queryKnowledge, getKnowledgeFiles } from '../hooks/useApi'

export default function RAGQA() {
  const [file, setFile] = useState<File | null>(null)
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [uploading, setUploading] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<any>(null)
  const [queryLoading, setQueryLoading] = useState(false)
  const [files, setFiles] = useState<any[]>([])
  const [showFiles, setShowFiles] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadResult(null)
    try {
      const result = await uploadDocument(file)
      setUploadResult(result)
    } catch (e: any) {
      setUploadResult({ error: e.message })
    } finally {
      setUploading(false)
    }
  }

  const handleQuery = async () => {
    if (!question.trim()) return
    setQueryLoading(true)
    setAnswer(null)
    try {
      const result = await queryKnowledge(question)
      setAnswer(result)
    } catch (e: any) {
      setAnswer({ error: e.message })
    } finally {
      setQueryLoading(false)
    }
  }

  const loadFiles = async () => {
    setShowFiles(!showFiles)
    if (!showFiles) {
      try {
        const data = await getKnowledgeFiles()
        setFiles(data.files)
      } catch (e: any) {
        setFiles([])
      }
    }
  }

  return (
    <div>
      <h2 className="page-title">RAG 文档问答</h2>
      <p className="page-desc">
        文章 2.4 - 上传文档到知识库，基于文档内容进行智能问答
      </p>

      {/* 上传文档 */}
      <div className="card">
        <div className="card-title">上传文档到知识库</div>
        <div className="form-group">
          <label className="form-label">选择文件 (支持 .txt, .md, .pdf, .py, .js, .ts 等)</label>
          <input
            type="file"
            accept=".txt,.md,.pdf,.py,.js,.ts,.jsx,.tsx,.html,.css,.json"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ fontSize: 14, marginBottom: 8 }}
          />
        </div>
        <button className="btn btn-primary" onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? <span className="loading-spinner" /> : null}
          {uploading ? '上传中...' : '上传并添加到知识库'}
        </button>

        {uploadResult && (
          <div style={{ marginTop: 12 }}>
            {uploadResult.error ? (
              <div className="status-error">上传失败: {uploadResult.error}</div>
            ) : (
              <div className="status-success">
                上传成功: {uploadResult.file_name} (已切分为 {uploadResult.chunks_count} 个文本块)
              </div>
            )}
          </div>
        )}
      </div>

      {/* 基于知识库问答 */}
      <div className="card">
        <div className="card-title">知识库问答</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button className="btn btn-secondary" onClick={loadFiles}>
            {showFiles ? '隐藏文件列表' : '查看知识库文件'}
          </button>
        </div>

        {showFiles && (
          <div style={{ marginBottom: 12 }}>
            {files.length === 0 ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
                暂无文件，请先上传文档。
              </div>
            ) : (
              files.map((f, i) => (
                <div key={i} className="source-item">
                  <span className="source-label">{f.name}</span>
                  <span style={{ marginLeft: 8, color: 'var(--color-text-muted)' }}>
                    ({(f.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        <div className="form-group">
          <textarea
            className="form-textarea"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="输入你想问的问题，例如：这篇文档主要讲了什么？"
            rows={3}
          />
        </div>
        <button className="btn btn-primary" onClick={handleQuery} disabled={!question.trim() || queryLoading}>
          {queryLoading ? <span className="loading-spinner" /> : null}
          {queryLoading ? '查询中...' : '提问'}
        </button>

        {answer && (
          <div style={{ marginTop: 16 }}>
            {answer.error ? (
              <div className="status-error">{answer.error}</div>
            ) : (
              <>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontWeight: 500, marginBottom: 6, color: 'var(--color-text-secondary)' }}>
                    回答:
                  </div>
                  <div className="result-box">{answer.answer}</div>
                </div>

                {answer.sources && answer.sources.length > 0 && (
                  <div>
                    <div style={{ fontWeight: 500, marginBottom: 6, color: 'var(--color-text-secondary)' }}>
                      参考来源:
                    </div>
                    {answer.sources.map((s: any, i: number) => (
                      <div key={i} className="source-item">
                        <div className="source-label">来源 {i + 1}: {s.source}</div>
                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{s.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
