import { useState, useEffect } from 'react'
import { getChains, runChain } from '../hooks/useApi'

export default function ChainDemo() {
  const [chains, setChains] = useState<any[]>([])
  const [selectedChain, setSelectedChain] = useState<string | null>(null)
  const [variables, setVariables] = useState<Record<string, string>>({})
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getChains().then((data) => {
      setChains(data.chains)
    }).catch(() => {})
  }, [])

  const selected = chains.find((c) => c.id === selectedChain)

  const handleSelect = (id: string) => {
    setSelectedChain(id)
    setVariables({})
    setResult(null)
  }

  const handleRun = async () => {
    if (!selectedChain) return
    setLoading(true)
    setResult(null)
    try {
      const data = await runChain(selectedChain, variables)
      setResult(data.result)
    } catch (e: any) {
      setResult({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const renderResult = () => {
    if (!result) return null
    if (result.error) {
      return <div className="status-error">{result.error}</div>
    }
    return (
      <div>
        {result.ideas && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
              创意方案:
            </div>
            <div className="result-box">{result.ideas}</div>
          </div>
        )}
        {result.evaluation && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
              评估结果:
            </div>
            <div className="result-box">{result.evaluation}</div>
          </div>
        )}
        {result.original_code && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
              原始代码:
            </div>
            <div className="result-box">{result.original_code}</div>
          </div>
        )}
        {result.optimized_result && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
              优化结果:
            </div>
            <div className="result-box">{result.optimized_result}</div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <h2 className="page-title">链式调用</h2>
      <p className="page-desc">
        文章 2.3 - 将多个 LLM 调用串联成流水线，前一输出作为后一输入
      </p>

      <div className="card">
        <div className="card-title">选择链</div>
        {chains.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>
            正在加载链列表...
          </div>
        ) : (
          <div className="chain-grid">
            {chains.map((c) => (
              <div
                key={c.id}
                className={`chain-card ${selectedChain === c.id ? 'selected' : ''}`}
                onClick={() => handleSelect(c.id)}
              >
                <div className="chain-name">{c.label}</div>
                <div className="chain-desc">{c.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="card">
          <div className="card-title">填写参数: {selected.label}</div>
          {selected.variables.map((v: any) => (
            <div className="form-group" key={v.name}>
              <label className="form-label">{v.label}</label>
              <textarea
                className="form-textarea"
                value={variables[v.name] || ''}
                onChange={(e) =>
                  setVariables((prev) => ({ ...prev, [v.name]: e.target.value }))
                }
                placeholder={`输入 ${v.label}`}
                rows={3}
              />
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleRun} disabled={loading}>
            {loading ? <span className="loading-spinner" /> : null}
            {loading ? '执行中...' : '运行链'}
          </button>

          {(result || loading) && (
            <div style={{ marginTop: 16 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-secondary)' }}>
                  <span className="loading-spinner" /> 链式调用正在执行，请稍候...
                </div>
              ) : (
                renderResult()
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
