import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div
        className="w-14 h-14 flex items-center justify-center mb-4 border"
        style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
      >
        <Icon size={28} style={{ color: 'var(--color-primary)' }} />
      </div>
      <p className="text-sm font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
        {title}
      </p>
      {description && (
        <p className="text-sm max-w-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
