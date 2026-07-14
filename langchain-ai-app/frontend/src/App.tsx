import { useState } from 'react'
import './App.css'
import Chat from './components/Chat'
import PromptTemplate from './components/PromptTemplate'
import ChainDemo from './components/ChainDemo'
import RAGQA from './components/RAGQA'

type Page = 'chat' | 'prompt' | 'chain' | 'rag'

const NAV_ITEMS: { key: Page; label: string }[] = [
  { key: 'chat', label: '基础对话' },
  { key: 'prompt', label: 'Prompt 模板' },
  { key: 'chain', label: '链式调用' },
  { key: 'rag', label: 'RAG 文档问答' },
]

const NAV_TO_ARTICLE = {
  chat: '文章 2.1 - 基础对话（最入门，类似前端调用接口）',
  prompt: '文章 2.2 - Prompt 模板（前端模板化思维适配）',
  chain: '文章 2.3 - 链式调用（类似前端流水线）',
  rag: '文章 2.4 - RAG 文档问答（前端高频需求）',
} as const

export default function App() {
  const [page, setPage] = useState<Page>('chat')

  const renderPage = () => {
    switch (page) {
      case 'chat':
        return <Chat />
      case 'prompt':
        return <PromptTemplate />
      case 'chain':
        return <ChainDemo />
      case 'rag':
        return <RAGQA />
    }
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>LangChain AI 应用</h1>
        <span className="subtitle">前端开发程序员版 · React + Python</span>
      </header>

      <div className="app-body">
        <nav className="app-sidebar">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${page === item.key ? 'active' : ''}`}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <main className="app-content">
          {renderPage()}
        </main>
      </div>
    </div>
  )
}
