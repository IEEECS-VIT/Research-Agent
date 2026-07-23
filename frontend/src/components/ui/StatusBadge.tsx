type Status = 'completed' | 'processing' | 'failed' | 'pending' | string

const statusMap: Record<string, { className: string; label?: string }> = {
  completed: { className: 'badge-success', label: 'Completed' },
  processing: { className: 'badge-info', label: 'Processing' },
  failed: { className: 'badge-danger', label: 'Failed' },
  pending: { className: 'badge-neutral', label: 'Pending' },
}

export function StatusBadge({ status }: { status: Status }) {
  const config = statusMap[status] ?? { className: 'badge-neutral' }
  return (
    <span className={`badge ${config.className}`}>
      {config.label ?? status}
    </span>
  )
}
