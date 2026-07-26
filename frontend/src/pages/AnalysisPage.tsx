import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FlaskConical, Search, Plus, ArrowRight, Loader2, X, FileUp, FileCheck } from 'lucide-react'
import { analysisApi, documentsApi, type AnalysisSession, type Document } from '../services/api'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState } from '../components/ui/EmptyState'
import { StatusBadge } from '../components/ui/StatusBadge'

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

  const resetForm = () => {
    setShowNew(false)
    setName('')
    setSelectedDrafts([])
    setSelectedPapers([])
  }

  return (
    <div className="max-w-4xl animate-fade-in">
      <PageHeader
        title="Analysis"
        description="Compare drafts against research papers to find alignments and contradictions"
        action={
          <button
            onClick={() => setShowNew(!showNew)}
            className="btn btn-primary btn-md"
          >
            {showNew ? <X size={16} /> : <Plus size={16} />}
            {showNew ? 'Cancel' : 'New Analysis'}
          </button>
        }
      />

      {showNew && (
        <div className="card p-6 mb-6" style={{ boxShadow: 'var(--shadow-md)' }}>
          <h2 className="text-base font-bold mb-1" style={{ color: 'var(--color-text)' }}>
            Create Analysis Session
          </h2>
          <p className="text-sm mb-5" style={{ color: 'var(--color-text-secondary)' }}>
            Select at least one draft and one paper to compare
          </p>

          <input
            type="text"
            placeholder="Session name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input mb-5"
          />

          <div className="grid sm:grid-cols-2 gap-4 mb-5">
            <div className="border p-4" style={{ borderColor: 'var(--color-border)' }}>
              <div className="flex items-center gap-2 mb-3">
                <FileUp size={16} style={{ color: 'var(--color-warning)' }} />
                <p className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
                  Drafts
                </p>
                <span className="badge badge-neutral ml-auto">{drafts.length}</span>
              </div>
              {drafts.length === 0 ? (
                <p className="text-xs py-4 text-center" style={{ color: 'var(--color-text-muted)' }}>
                  No completed drafts available
                </p>
              ) : (
                <div className="space-y-1 max-h-44 overflow-y-auto">
                  {drafts.map((d) => (
                    <label
                      key={d.id}
                      className={`flex items-center gap-2.5 px-3 py-2 text-sm border cursor-pointer transition-colors ${
                        selectedDrafts.includes(d.id) ? 'bg-[var(--color-primary-light)]' : 'hover:bg-[var(--color-surface-hover)]'
                      }`}
                      style={{ borderColor: 'var(--color-border)' }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedDrafts.includes(d.id)}
                        onChange={() => toggleDraft(d.id)}
                        className="accent-[var(--color-primary)]"
                      />
                      <span className="truncate font-medium" style={{ color: 'var(--color-text)' }}>{d.filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="border p-4" style={{ borderColor: 'var(--color-border)' }}>
              <div className="flex items-center gap-2 mb-3">
                <FileCheck size={16} style={{ color: 'var(--color-success)' }} />
                <p className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
                  Papers
                </p>
                <span className="badge badge-neutral ml-auto">{papers.length}</span>
              </div>
              {papers.length === 0 ? (
                <p className="text-xs py-4 text-center" style={{ color: 'var(--color-text-muted)' }}>
                  No completed papers available
                </p>
              ) : (
                <div className="space-y-1 max-h-44 overflow-y-auto">
                  {papers.map((d) => (
                    <label
                      key={d.id}
                      className={`flex items-center gap-2.5 px-3 py-2 text-sm border cursor-pointer transition-colors ${
                        selectedPapers.includes(d.id) ? 'bg-[var(--color-primary-light)]' : 'hover:bg-[var(--color-surface-hover)]'
                      }`}
                      style={{ borderColor: 'var(--color-border)' }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedPapers.includes(d.id)}
                        onChange={() => togglePaper(d.id)}
                        className="accent-[var(--color-primary)]"
                      />
                      <span className="truncate font-medium" style={{ color: 'var(--color-text)' }}>{d.filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={createSession}
              disabled={selectedDrafts.length === 0 || selectedPapers.length === 0 || creating}
              className="btn btn-primary btn-md"
            >
              {creating ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              {creating ? 'Creating...' : 'Start Analysis'}
            </button>
            <button onClick={resetForm} className="btn btn-ghost btn-md">
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="spinner" />
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Loading sessions...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Search}
            title="No analysis sessions yet"
            description="Upload documents and create a new analysis to compare drafts against papers."
            action={
              <button onClick={() => setShowNew(true)} className="btn btn-primary btn-sm">
                <Plus size={14} />
                Create your first analysis
              </button>
            }
          />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
              All Sessions ({sessions.length})
            </h2>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/analysis/${s.id}`)}
                className="flex items-center gap-4 px-5 py-4 w-full text-left transition-colors hover:bg-[var(--color-surface-hover)] group"
              >
                <div
                  className="w-10 h-10 flex items-center justify-center shrink-0 border"
                  style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
                >
                  <FlaskConical size={18} style={{ color: 'var(--color-primary)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                    {s.name || 'Unnamed Analysis'}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                    {new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
                <StatusBadge status={s.status} />
                <ArrowRight
                  size={16}
                  className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: 'var(--color-primary)' }}
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
