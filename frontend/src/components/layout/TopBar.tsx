import { useLocation, Link } from 'react-router-dom'
import { Sun, Moon, ChevronRight } from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'

const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/upload': 'Upload',
  '/analysis': 'Analysis',
  '/settings': 'Settings',
}

export function TopBar() {
  const { theme, toggle } = useTheme()
  const location = useLocation()

  const segments = location.pathname.split('/').filter(Boolean)
  const breadcrumbs = segments.map((seg, i) => {
    const path = '/' + segments.slice(0, i + 1).join('/')
    const label = routeLabels[path] ?? (seg.length > 20 ? 'Details' : seg.charAt(0).toUpperCase() + seg.slice(1))
    return { path, label, isLast: i === segments.length - 1 }
  })

  return (
    <header
      className="h-16 flex items-center justify-between px-6 lg:px-8 border-b shrink-0 glass"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <nav className="flex items-center gap-1.5 text-sm min-w-0">
        {breadcrumbs.length === 0 ? (
          <span className="font-medium" style={{ color: 'var(--color-text)' }}>Home</span>
        ) : (
          breadcrumbs.map((crumb, i) => (
            <span key={crumb.path} className="flex items-center gap-1.5 min-w-0">
              {i > 0 && <ChevronRight size={14} style={{ color: 'var(--color-text-muted)' }} className="shrink-0" />}
              {crumb.isLast ? (
                <span className="font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                  {crumb.label}
                </span>
              ) : (
                <Link
                  to={crumb.path}
                  className="font-medium truncate transition-colors hover:opacity-80"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          ))
        )}
      </nav>

      <button
        onClick={toggle}
        className="p-2.5 border transition-colors"
        style={{ background: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)', borderColor: 'var(--color-border)' }}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
    </header>
  )
}
