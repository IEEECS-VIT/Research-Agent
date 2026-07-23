import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  Search,
  Settings,
  LogOut,
  FlaskConical,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/analysis', label: 'Analysis', icon: Search },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside
      className="w-64 shrink-0 flex flex-col h-screen border-r"
      style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}
    >
      <div className="h-16 flex items-center gap-3 px-5 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <div
          className="w-9 h-9 flex items-center justify-center border"
          style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
        >
          <FlaskConical size={20} style={{ color: 'var(--color-primary)' }} />
        </div>
        <div>
          <span className="font-bold text-sm tracking-tight block" style={{ color: 'var(--color-text)' }}>
            Research Agent
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>
            AI Research
          </span>
        </div>
      </div>

      <nav className="flex-1 p-3 flex flex-col gap-1">
        <p className="text-[10px] font-semibold uppercase tracking-wider px-3 py-2" style={{ color: 'var(--color-text-muted)' }}>
          Menu
        </p>
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
          >
            <Icon size={18} className="nav-icon shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <div
          className="flex items-center gap-3 p-2.5 border mb-2"
          style={{ background: 'var(--color-surface-hover)', borderColor: 'var(--color-border)' }}
        >
          {user?.photoURL ? (
            <img src={user.photoURL} alt="" className="w-9 h-9 object-cover border" style={{ borderColor: 'var(--color-border)' }} />
          ) : (
            <div
              className="w-9 h-9 flex items-center justify-center text-xs font-bold uppercase border"
              style={{ background: 'var(--color-primary)', color: '#fff', borderColor: 'var(--color-border)' }}
            >
              {user?.displayName?.[0] || user?.email?.[0] || '?'}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
              {user?.displayName || 'User'}
            </p>
            <p className="text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>
              {user?.email}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="nav-link w-full text-left"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
