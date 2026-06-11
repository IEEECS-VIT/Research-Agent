import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, CheckCircle, HelpCircle, BarChart3 } from 'lucide-react'
import { analysisApi, type ComparisonResult } from '../services/api'

const statusConfig: Record<string, { icon: any; color: string; label: string }> = {
  CONFIRMED: { icon: CheckCircle, color: 'var(--color-success)', label: 'Confirmed' },
  REJECTED: { icon: AlertCircle, color: 'var(--color-danger)', label: 'Rejected' },
  SCOPE_MISMATCH: { icon: HelpCircle, color: 'var(--color-warning)', label: 'Scope Mismatch' },
}

const relationConfig: Record<string, { label: string; color: string }> = {
  SUPPORT: { label: 'Supports', color: 'var(--color-success)' },
  CONTRADICT: { label: 'Contradicts', color: 'var(--color-danger)' },
  MIXED: { label: 'Mixed', color: 'var(--color-warning)' },
}

export function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)

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
      <div className="flex justify-center py-12">
        <Loader2 size={20} className="animate-spin" style={{ color: 'var(--color-text-secondary)' }} />
      </div>
    )
  }

  if (!session) return null

  const comparisons: ComparisonResult[] = session.comparisons || []
  const avgSupport = comparisons.length
    ? comparisons.reduce((s, c) => s + c.support_score, 0) / comparisons.length
    : 0
  const avgContradiction = comparisons.length
    ? comparisons.reduce((s, c) => s + c.contradiction_score, 0) / comparisons.length
    : 0
  const avgConfidence = comparisons.length
    ? comparisons.reduce((s, c) => s + c.confidence, 0) / comparisons.length
    : 0

  return (
    <div className="max-w-5xl">
      <button
        onClick={() => navigate('/analysis')}
        className="flex items-center gap-1.5 text-xs font-medium mb-4 transition-colors hover:opacity-70"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        <ArrowLeft size={14} />
        Back to Analysis
      </button>

      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
          {session.name || 'Analysis Session'}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {new Date(session.created_at).toLocaleDateString()} &middot; {session.status}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Avg Support</p>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-success)' }}>
            {(avgSupport * 100).toFixed(0)}%
          </p>
        </div>
        <div className="p-4 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Avg Contradiction</p>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-danger)' }}>
            {(avgContradiction * 100).toFixed(0)}%
          </p>
        </div>
        <div className="p-4 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Avg Confidence</p>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
            {(avgConfidence * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {comparisons.length === 0 ? (
        <div className="text-center py-12 border" style={{ borderColor: 'var(--color-border)' }}>
          <BarChart3 size={32} className="mx-auto mb-3" style={{ color: 'var(--color-text-secondary)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            No comparison results yet
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Results will appear once processing completes
          </p>
        </div>
      ) : (
        <div className="border" style={{ borderColor: 'var(--color-border)' }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              Comparison Results ({comparisons.length})
            </h2>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {comparisons.map((c) => {
              const status = statusConfig[c.verifier_status || '']
              const relation = relationConfig[c.relation_type || '']
              const StatusIcon = status?.icon || HelpCircle

              return (
                <div key={c.id} className="p-4">
                  <div className="flex items-start gap-3 mb-3">
                    <StatusIcon size={16} style={{ color: status?.color || 'var(--color-text-secondary)', marginTop: 2 }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {relation && (
                          <span className="text-xs font-medium px-2 py-0.5" style={{ backgroundColor: `${relation.color}20`, color: relation.color }}>
                            {relation.label}
                          </span>
                        )}
                        {status && (
                          <span className="text-xs font-medium px-2 py-0.5" style={{ backgroundColor: `${status.color}20`, color: status.color }}>
                            {status.label}
                          </span>
                        )}
                        <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                          Confidence: {(c.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 mt-2">
                        <div className="p-2 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg)' }}>
                          <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Source</p>
                          <p className="text-xs leading-relaxed line-clamp-3" style={{ color: 'var(--color-text)' }}>
                            {c.source_text || 'No text'}
                          </p>
                        </div>
                        <div className="p-2 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg)' }}>
                          <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Target</p>
                          <p className="text-xs leading-relaxed line-clamp-3" style={{ color: 'var(--color-text)' }}>
                            {c.target_text || 'No text'}
                          </p>
                        </div>
                      </div>

                      <div className="flex gap-4 mt-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        <span>Support: {(c.support_score * 100).toFixed(0)}%</span>
                        <span>Contradiction: {(c.contradiction_score * 100).toFixed(0)}%</span>
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
