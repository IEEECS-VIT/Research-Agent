import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Search, BarChart3, Upload, ArrowRight, FileUp, FlaskConical, FileCheck } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { documentsApi, analysisApi, type Document, type AnalysisSession } from '../services/api'

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

  const stats = [
    {
      label: 'Documents',
      value: docs.length,
      icon: FileText,
      color: 'var(--color-primary)',
      action: () => navigate('/upload'),
    },
    {
      label: 'Analyses',
      value: sessions.length,
      icon: Search,
      color: 'var(--color-accent)',
      action: () => navigate('/analysis'),
    },
    {
      label: 'Drafts',
      value: docs.filter((d) => d.source_type === 'draft').length,
      icon: FileUp,
      color: 'var(--color-success)',
      action: () => navigate('/upload'),
    },
    {
      label: 'Papers',
      value: docs.filter((d) => d.source_type === 'paper').length,
      icon: FileCheck,
      color: 'var(--color-warning)',
      action: () => navigate('/upload'),
    },
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
          Welcome back{user?.displayName ? `, ${user.displayName}` : ''}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Manage your research documents and analysis
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <button
            key={s.label}
            onClick={s.action}
            className="p-4 border text-left transition-colors hover:opacity-80"
            style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}
          >
            <s.icon size={20} style={{ color: s.color }} />
            <p className="text-2xl font-bold mt-3" style={{ color: 'var(--color-text)' }}>
              {loading ? '-' : s.value}
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {s.label}
            </p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="border" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>Recent Documents</h2>
            <button
              onClick={() => navigate('/upload')}
              className="flex items-center gap-1 text-xs font-medium transition-colors hover:opacity-70"
              style={{ color: 'var(--color-primary)' }}
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          {loading ? (
            <div className="p-4 text-xs" style={{ color: 'var(--color-text-secondary)' }}>Loading...</div>
          ) : docs.length === 0 ? (
            <div className="p-6 text-center">
              <Upload size={24} className="mx-auto mb-2" style={{ color: 'var(--color-text-secondary)' }} />
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>No documents yet</p>
              <button
                onClick={() => navigate('/upload')}
                className="mt-3 text-xs font-medium px-3 py-1.5 border transition-colors hover:bg-black/5 dark:hover:bg-white/10"
                style={{ color: 'var(--color-primary)', borderColor: 'var(--color-primary)' }}
              >
                Upload your first document
              </button>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
              {docs.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3 px-4 py-3">
                  <FileText size={16} style={{ color: 'var(--color-text-secondary)' }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>
                      {doc.filename}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                      {doc.source_type} &middot; {doc.total_sections} sections &middot; v{doc.version_id}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 ${
                      doc.processing_status === 'completed'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : doc.processing_status === 'processing'
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                        : doc.processing_status === 'failed'
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {doc.processing_status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>Recent Analyses</h2>
            <button
              onClick={() => navigate('/analysis')}
              className="flex items-center gap-1 text-xs font-medium transition-colors hover:opacity-70"
              style={{ color: 'var(--color-primary)' }}
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          {loading ? (
            <div className="p-4 text-xs" style={{ color: 'var(--color-text-secondary)' }}>Loading...</div>
          ) : sessions.length === 0 ? (
            <div className="p-6 text-center">
              <BarChart3 size={24} className="mx-auto mb-2" style={{ color: 'var(--color-text-secondary)' }} />
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>No analyses yet</p>
              <button
                onClick={() => navigate('/upload')}
                className="mt-3 text-xs font-medium px-3 py-1.5 border transition-colors hover:bg-black/5 dark:hover:bg-white/10"
                style={{ color: 'var(--color-primary)', borderColor: 'var(--color-primary)' }}
              >
                Upload documents to start
              </button>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => navigate(`/analysis/${s.id}`)}
                  className="flex items-center gap-3 px-4 py-3 w-full text-left transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                >
                  <FlaskConical size={16} style={{ color: 'var(--color-text-secondary)' }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>
                      {s.name || 'Unnamed Analysis'}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                      {new Date(s.created_at).toLocaleDateString()} &middot; {s.status}
                    </p>
                  </div>
                  <ArrowRight size={14} style={{ color: 'var(--color-text-secondary)' }} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
