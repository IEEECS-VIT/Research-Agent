import { useEffect, useState, type CSSProperties } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, AlertCircle, CheckCircle, HelpCircle, BarChart3, TrendingUp, TrendingDown, Shield } from 'lucide-react'
import { analysisApi, documentsApi } from '../services/api'
import type { ComparisonResult } from '../services/api'
import { StatusBadge } from '../components/ui/StatusBadge'
import { EmptyState } from '../components/ui/EmptyState'

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  CONFIRMED: { icon: CheckCircle, color: 'var(--color-success)', label: 'Confirmed' },
  REJECTED: { icon: AlertCircle, color: 'var(--color-danger)', label: 'Rejected' },
  SCOPE_MISMATCH: { icon: HelpCircle, color: 'var(--color-warning)', label: 'Scope Mismatch' },
}

const relationConfig: Record<string, { label: string; color: string; bg: string }> = {
  SUPPORT: { label: 'Supports', color: 'var(--color-success)', bg: 'var(--color-success-light)' },
  CONTRADICT: { label: 'Contradicts', color: 'var(--color-danger)', bg: 'var(--color-danger-light)' },
  MIXED: { label: 'Mixed', color: 'var(--color-warning)', bg: 'var(--color-warning-light)' },
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 overflow-hidden border" style={{ background: 'var(--color-border-subtle)', borderColor: 'var(--color-border)' }}>
      <div
        className="h-full transition-all duration-500"
        style={{ width: `${value * 100}%`, background: color }}
      />
    </div>
  )
}

export function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [annotating, setAnnotating] = useState<Record<string, boolean>>({})

  const handleAnnotate = async (draftId: string) => {
    setAnnotating((prev) => ({ ...prev, [draftId]: true }))
    try {
      const response = await documentsApi.annotate(draftId)
      const blob = new Blob([response.data], { type: 'text/markdown' })
      const url = window.URL.createObjectURL(blob)
      const contentDisposition = response.headers['content-disposition'] as string | undefined
      const filenameMatch = contentDisposition?.match(/filename="?([^";]+)"?/) 
      const downloadName = filenameMatch?.[1] || 'draft_annotated.md'
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', downloadName)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to annotate draft:', err)
      alert('Failed to download annotated draft. Please try again.')
    } finally {
      setAnnotating((prev) => ({ ...prev, [draftId]: false }))
    }
  }


  useEffect(() => {
    if (!id) return
    analysisApi
      .getSession(id)
      .then((res) => setSession(res.data))
      .catch(() => navigate('/analysis'))
      .finally(() => setLoading(false))
  }, [id, navigate])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <div className="spinner" />
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Loading analysis...</p>
      </div>
    )
  }

  if (!session) return null

  const comparisons: ComparisonResult[] = session.comparisons || []
  const uniqueDraftIds = Array.from(new Set(comparisons.map(c => c.source_doc_id)))
  const avgSupport = comparisons.length
    ? comparisons.reduce((s, c) => s + c.support_score, 0) / comparisons.length
    : 0
  const avgContradiction = comparisons.length
    ? comparisons.reduce((s, c) => s + c.contradiction_score, 0) / comparisons.length
    : 0
  const avgConfidence = comparisons.length
    ? comparisons.reduce((s, c) => s + c.confidence, 0) / comparisons.length
    : 0

  const metrics = [
    { label: 'Avg Support', value: avgSupport, icon: TrendingUp, color: 'var(--color-success)', accent: 'var(--color-success-light)' },
    { label: 'Avg Contradiction', value: avgContradiction, icon: TrendingDown, color: 'var(--color-danger)', accent: 'var(--color-danger-light)' },
    { label: 'Avg Confidence', value: avgConfidence, icon: Shield, color: 'var(--color-primary)', accent: 'var(--color-primary-light)' },
  ]

  return (
    <div className="max-w-5xl animate-fade-in">
      <button
        onClick={() => navigate('/analysis')}
        className="btn btn-ghost btn-sm mb-6 -ml-2"
      >
        <ArrowLeft size={16} />
        Back to Analysis
      </button>

      <div className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-text)' }}>
              {session.name || 'Analysis Session'}
            </h1>
            <p className="text-sm mt-1.5" style={{ color: 'var(--color-text-secondary)' }}>
              {new Date(session.created_at).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <StatusBadge status={session.status} />
            {session.status === 'completed' && uniqueDraftIds.map((draftId) => (
              <button
                key={draftId}
                disabled={annotating[draftId]}
                onClick={() => handleAnnotate(draftId)}
                className="btn btn-primary btn-sm mt-2"
              >
                {annotating[draftId] ? 'Annotating...' : 'Annotate Draft'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="stat-card p-5" style={{ '--stat-accent': m.color } as CSSProperties}>
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-9 h-9 flex items-center justify-center border"
                style={{ background: m.accent, borderColor: 'var(--color-border)' }}
              >
                <m.icon size={18} style={{ color: m.color }} />
              </div>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>
                {m.label}
              </p>
            </div>
            <p className="text-3xl font-extrabold tracking-tight mb-2" style={{ color: m.color }}>
              {(m.value * 100).toFixed(0)}%
            </p>
            <ScoreBar value={m.value} color={m.color} />
          </div>
        ))}
      </div>

      {comparisons.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={BarChart3}
            title="No comparison results yet"
            description="Results will appear here once processing completes."
          />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
              Comparison Results
            </h2>
            <span className="badge badge-neutral">{comparisons.length} items</span>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
            {comparisons.map((c) => {
              const status = statusConfig[c.verifier_status || '']
              const relation = relationConfig[c.relation_type || '']
              const StatusIcon = status?.icon || HelpCircle

              return (
                <div key={c.id} className="p-5 transition-colors hover:bg-[var(--color-surface-hover)]">
                  <div className="flex items-start gap-3 mb-4">
                    <div
                      className="w-8 h-8 flex items-center justify-center shrink-0 mt-0.5 border"
                      style={{ background: status ? `${status.color}15` : 'var(--color-surface-hover)', borderColor: 'var(--color-border)' }}
                    >
                      <StatusIcon size={16} style={{ color: status?.color || 'var(--color-text-secondary)' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        {relation && (
                          <span
                            className="text-xs font-bold px-2.5 py-1 border"
                            style={{ background: relation.bg, color: relation.color, borderColor: relation.color }}
                          >
                            {relation.label}
                          </span>
                        )}
                        {status && (
                          <span
                            className="text-xs font-bold px-2.5 py-1 border"
                            style={{ background: `${status.color}15`, color: status.color, borderColor: status.color }}
                          >
                            {status.label}
                          </span>
                        )}
                        <span className="text-xs font-medium ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                          {(c.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-3">
                        <div className="p-4 border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}>
                          <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-muted)' }}>
                            Source
                          </p>
                          <p className="text-sm leading-relaxed line-clamp-4" style={{ color: 'var(--color-text)' }}>
                            {c.source_text || 'No text available'}
                          </p>
                        </div>
                        <div className="p-4 border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}>
                          <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-muted)' }}>
                            Target
                          </p>
                          <p className="text-sm leading-relaxed line-clamp-4" style={{ color: 'var(--color-text)' }}>
                            {c.target_text || 'No text available'}
                          </p>
                        </div>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-4 mt-4">
                        <div>
                          <div className="flex justify-between text-xs mb-1.5">
                            <span style={{ color: 'var(--color-text-muted)' }}>Support</span>
                            <span className="font-semibold" style={{ color: 'var(--color-success)' }}>
                              {(c.support_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <ScoreBar value={c.support_score} color="var(--color-success)" />
                        </div>
                        <div>
                          <div className="flex justify-between text-xs mb-1.5">
                            <span style={{ color: 'var(--color-text-muted)' }}>Contradiction</span>
                            <span className="font-semibold" style={{ color: 'var(--color-danger)' }}>
                              {(c.contradiction_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <ScoreBar value={c.contradiction_score} color="var(--color-danger)" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
