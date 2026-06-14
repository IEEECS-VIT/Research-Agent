import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FlaskConical, Search, Plus, ArrowRight, Loader2 } from 'lucide-react'
import { analysisApi, documentsApi, type AnalysisSession, type Document } from '../services/api'

export function AnalysisPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<AnalysisSession[]>([])
  const [docs, setDocs] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [name, setName] = useState('')
  const [selectedDrafts, setSelectedDrafts] = useState<string[]>([])
  const [selectedPapers, setSelectedPapers] = useState<string[]>([])
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    Promise.all([analysisApi.listSessions(), documentsApi.list()])
      .then(([sessRes, docRes]) => {
        setSessions(sessRes.data)
        setDocs(docRes.data.documents)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const drafts = docs.filter((d) => d.source_type === 'draft' && d.processing_status === 'completed')
  const papers = docs.filter((d) => d.source_type === 'paper' && d.processing_status === 'completed')

  const toggleDraft = (id: string) => {
    setSelectedDrafts((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }
  const togglePaper = (id: string) => {
    setSelectedPapers((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const createSession = async () => {
    if (selectedDrafts.length === 0 || selectedPapers.length === 0) return
    setCreating(true)
    try {
      const res = await analysisApi.createSession({
        name: name || undefined,
        draft_document_ids: selectedDrafts,
        paper_document_ids: selectedPapers,
      })
      navigate(`/analysis/${res.data.id}`)
    } catch (err) {
      console.error(err)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Analysis</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Compare drafts against research papers
          </p>
        </div>
        <button
          onClick={() => setShowNew(!showNew)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
        >
          <Plus size={14} />
          New Analysis
        </button>
      </div>

      {showNew && (
        <div className="mb-6 border p-4" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Create Analysis Session</h2>
          <input
            type="text"
            placeholder="Session name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 text-sm border mb-4 bg-transparent"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
          />

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                Drafts ({drafts.length})
              </p>
              {drafts.length === 0 ? (
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>No completed drafts</p>
              ) : (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {drafts.map((d) => (
                    <label key={d.id} className="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5">
                      <input
                        type="checkbox"
                        checked={selectedDrafts.includes(d.id)}
                        onChange={() => toggleDraft(d.id)}
                        className="accent-current"
                      />
                      <span className="truncate" style={{ color: 'var(--color-text)' }}>{d.filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                Papers ({papers.length})
              </p>
              {papers.length === 0 ? (
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>No completed papers</p>
              ) : (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {papers.map((d) => (
                    <label key={d.id} className="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5">
                      <input
                        type="checkbox"
                        checked={selectedPapers.includes(d.id)}
                        onChange={() => togglePaper(d.id)}
                        className="accent-current"
                      />
                      <span className="truncate" style={{ color: 'var(--color-text)' }}>{d.filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>

          <button
            onClick={createSession}
            disabled={selectedDrafts.length === 0 || selectedPapers.length === 0 || creating}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors disabled:opacity-40"
            style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
          >
            {creating ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            {creating ? 'Creating...' : 'Start Analysis'}
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={20} className="animate-spin" style={{ color: 'var(--color-text-secondary)' }} />
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 border" style={{ borderColor: 'var(--color-border)' }}>
          <Search size={32} className="mx-auto mb-3" style={{ color: 'var(--color-text-secondary)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>No analysis sessions yet</p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Upload documents and create a new analysis
          </p>
        </div>
      ) : (
        <div className="border" style={{ borderColor: 'var(--color-border)' }}>
          <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/analysis/${s.id}`)}
                className="flex items-center gap-3 px-4 py-3 w-full text-left transition-colors hover:bg-black/5 dark:hover:bg-white/5"
              >
                <FlaskConical size={18} style={{ color: 'var(--color-text-secondary)' }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                    {s.name || 'Unnamed Analysis'}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {new Date(s.created_at).toLocaleDateString()} &middot; {s.status}
                  </p>
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 ${
                  s.status === 'completed'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : s.status === 'processing'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                  {s.status}
                </span>
                <ArrowRight size={14} style={{ color: 'var(--color-text-secondary)' }} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
