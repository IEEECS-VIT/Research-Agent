import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  Search,
  BarChart3,
  Settings,
  LogOut,
  FlaskConical,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/analysis', label: 'Analysis', icon: Search },
  { to: '/insights', label: 'Insights', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="w-64 border-r shrink-0" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <div className="h-16 flex items-center gap-2 px-6 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <FlaskConical size={22} style={{ color: 'var(--color-primary)' }} />
        <span className="font-semibold text-sm tracking-tight" style={{ color: 'var(--color-text)' }}>
          Research Agent
        </span>
      </div>

      <nav className="p-3 flex flex-col gap-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive ? 'bg-black/5 dark:bg-white/10' : 'hover:bg-black/5 dark:hover:bg-white/5'
              }`
            }
            style={({ isActive }) => ({
              color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              borderLeft: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
            })}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto p-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center gap-3 mb-3 px-2">
          {user?.photoURL ? (
            <img src={user.photoURL} alt="" className="w-8 h-8 object-cover" />
          ) : (
            <div className="w-8 h-8 flex items-center justify-center text-xs font-bold uppercase" style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              {user?.displayName?.[0] || user?.email?.[0] || '?'}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>
              {user?.displayName || 'User'}
            </p>
            <p className="text-xs truncate" style={{ color: 'var(--color-text-secondary)' }}>
              {user?.email}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium transition-colors hover:bg-black/5 dark:hover:bg-white/5"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
