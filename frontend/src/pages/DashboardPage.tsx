import { useEffect, useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Search, Upload, ArrowRight, FileUp, FlaskConical, FileCheck, Plus } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { documentsApi, analysisApi, type Document, type AnalysisSession } from '../services/api'
import { EmptyState } from '../components/ui/EmptyState'
import { StatusBadge } from '../components/ui/StatusBadge'

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [docs, setDocs] = useState<Document[]>([])
  const [sessions, setSessions] = useState<AnalysisSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      documentsApi.list({ limit: 5 }),
      analysisApi.listSessions(),
    ])
      .then(([docRes, sessRes]) => {
        setDocs(docRes.data.documents)
        setSessions(sessRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const firstName = user?.displayName?.split(' ')[0]

  const stats = [
    {
      label: 'Documents',
      value: docs.length,
      icon: FileText,
      accent: 'var(--color-primary)',
      action: () => navigate('/upload'),
    },
    {
      label: 'Analyses',
      value: sessions.length,
      icon: Search,
      accent: 'var(--color-accent)',
      action: () => navigate('/analysis'),
    },
    {
      label: 'Drafts',
      value: docs.filter((d) => d.source_type === 'draft').length,
      icon: FileUp,
      accent: 'var(--color-warning)',
      action: () => navigate('/upload'),
    },
    {
      label: 'Papers',
      value: docs.filter((d) => d.source_type === 'paper').length,
      icon: FileCheck,
      accent: 'var(--color-success)',
      action: () => navigate('/upload'),
    },
  ]

  return (
    <div>
      <div className="mb-8 animate-fade-in">
        <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-text)' }}>
          Welcome back{firstName ? `, ${firstName}` : ''} 👋
        </h1>
        <p className="text-sm mt-1.5" style={{ color: 'var(--color-text-secondary)' }}>
          Here's an overview of your research workspace
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s, i) => (
          <button
            key={s.label}
            onClick={s.action}
            className={`stat-card p-5 text-left animate-fade-in animate-fade-in-delay-${i + 1}`}
            style={{ '--stat-accent': s.accent } as CSSProperties}
          >
            <div
              className="w-10 h-10 flex items-center justify-center mb-4 border"
              style={{ background: `color-mix(in srgb, ${s.accent} 12%, transparent)`, borderColor: 'var(--color-border)' }}
            >
              <s.icon size={20} style={{ color: s.accent }} />
            </div>
            <p className="text-3xl font-extrabold tracking-tight" style={{ color: 'var(--color-text)' }}>
              {loading ? (
                <span className="inline-block w-8 h-8 skeleton" />
              ) : (
                s.value
              )}
            </p>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {s.label}
            </p>
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-6 animate-fade-in animate-fade-in-delay-2">
        <button onClick={() => navigate('/upload')} className="btn btn-primary btn-md">
          <Plus size={16} />
          Upload Documents
        </button>
        <button onClick={() => navigate('/analysis')} className="btn btn-secondary btn-md">
          <Search size={16} />
          New Analysis
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card overflow-hidden animate-fade-in animate-fade-in-delay-3">
          <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>Recent Documents</h2>
            <button
              onClick={() => navigate('/upload')}
              className="flex items-center gap-1 text-xs font-semibold transition-colors hover:opacity-70"
              style={{ color: 'var(--color-primary)' }}
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          {loading ? (
            <div className="p-5 space-y-3">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-12 skeleton" />
              ))}
            </div>
          ) : docs.length === 0 ? (
            <EmptyState
              icon={Upload}
              title="No documents yet"
              description="Upload your first research paper or draft to get started."
              action={
                <button onClick={() => navigate('/upload')} className="btn btn-primary btn-sm">
                  Upload your first document
                </button>
              }
            />
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
              {docs.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-[var(--color-surface-hover)]">
                  <div
                    className="w-9 h-9 flex items-center justify-center shrink-0 border"
                    style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
                  >
                    <FileText size={16} style={{ color: 'var(--color-primary)' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                      {doc.filename}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                      {doc.source_type} · {doc.total_sections} sections · v{doc.version_id}
                    </p>
                  </div>
                  <StatusBadge status={doc.processing_status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card overflow-hidden animate-fade-in animate-fade-in-delay-4">
          <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>Recent Analyses</h2>
            <button
              onClick={() => navigate('/analysis')}
              className="flex items-center gap-1 text-xs font-semibold transition-colors hover:opacity-70"
              style={{ color: 'var(--color-primary)' }}
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          {loading ? (
            <div className="p-5 space-y-3">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-12 skeleton" />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <EmptyState
              icon={FlaskConical}
              title="No analyses yet"
              description="Upload documents and run your first alignment analysis."
              action={
                <button onClick={() => navigate('/analysis')} className="btn btn-primary btn-sm">
                  Start an analysis
                </button>
              }
            />
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => navigate(`/analysis/${s.id}`)}
                  className="flex items-center gap-3 px-5 py-3.5 w-full text-left transition-colors hover:bg-[var(--color-surface-hover)] group"
                >
                  <div
                    className="w-9 h-9 flex items-center justify-center shrink-0 border"
                    style={{ background: 'var(--color-accent-light)', borderColor: 'var(--color-border)' }}
                  >
                    <FlaskConical size={16} style={{ color: 'var(--color-accent)' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                      {s.name || 'Unnamed Analysis'}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                      {new Date(s.created_at).toLocaleDateString()} · {s.status}
                    </p>
                  </div>
                  <ArrowRight
                    size={16}
                    className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: 'var(--color-primary)' }}
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
