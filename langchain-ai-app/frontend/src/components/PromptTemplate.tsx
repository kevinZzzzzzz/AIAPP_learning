import { useState, useEffect } from 'react'
import { getPromptTemplates, applyPrompt } from '../hooks/useApi'

export default function PromptTemplate() {
  const [templates, setTemplates] = useState<any[]>([])
  const [selectedTpl, setSelectedTpl] = useState<string | null>(null)
  const [variables, setVariables] = useState<Record<string, string>>({})
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getPromptTemplates().then((data) => {
      setTemplates(data.templates)
    }).catch(() => {})
  }, [])

  const selected = templates.find((t) => t.id === selectedTpl)

  const handleSelect = (id: string) => {
    setSelectedTpl(id)
    setVariables({})
    setResult('')
  }

  const handleApply = async () => {
    if (!selectedTpl) return
    setLoading(true)
    setResult('')
    try {
      const data = await applyPrompt(selectedTpl, variables)
      setResult(data.result)
    } catch (e: any) {
      setResult(`错误: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="page-title">Prompt 模板</h2>
      <p className="page-desc">
        文章 2.2 - 借鉴前端模板化思维，将 Prompt 做成可复用的模板
      </p>

      <div className="card">
        <div className="card-title">选择模板</div>
        {templates.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>
            正在加载模板列表...
          </div>
        ) : (
          <div className="template-grid">
            {templates.map((tpl) => (
              <div
                key={tpl.id}
                className={`template-card ${selectedTpl === tpl.id ? 'selected' : ''}`}
                onClick={() => handleSelect(tpl.id)}
              >
                <div className="tpl-name">{tpl.label}</div>
                <div className="tpl-desc">{tpl.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="card">
          <div className="card-title">填写参数: {selected.label}</div>
          {selected.variables.map((v: string) => (
            <div className="form-group" key={v}>
              <label className="form-label">{v}</label>
              <textarea
                className="form-textarea"
                value={variables[v] || ''}
                onChange={(e) =>
                  setVariables((prev) => ({ ...prev, [v]: e.target.value }))
                }
                placeholder={`输入 ${v}`}
                rows={v === 'code' || v === 'requirement' ? 4 : 2}
              />
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleApply} disabled={loading}>
            {loading ? <span className="loading-spinner" /> : null}
            {loading ? '处理中...' : '应用模板并生成'}
          </button>

          {result && (
            <div className="result-box">
              <div style={{ fontWeight: 500, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
                生成结果:
              </div>
              {result}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
