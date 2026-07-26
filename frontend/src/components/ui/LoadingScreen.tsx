export function LoadingScreen() {
  return (
    <div className="h-screen flex flex-col items-center justify-center gap-4 mesh-bg" style={{ background: 'var(--color-bg)' }}>
      <div className="spinner" />
      <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
        Loading...
      </p>
    </div>
  )
}
