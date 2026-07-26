import { User, Bell, Shield, Key } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { PageHeader } from '../components/ui/PageHeader'
import { useTheme } from '../contexts/ThemeContext'

export function SettingsPage() {
  const { user } = useAuth()
  const { theme, toggle } = useTheme()

  const sections = [
    {
      icon: User,
      title: 'Profile',
      description: 'Your account information',
      items: [
        { label: 'Name', value: user?.displayName || 'Not set' },
        { label: 'Email', value: user?.email || 'Not set' },
      ],
    },
    {
      icon: Key,
      title: 'API Configuration',
      description: 'Connection settings',
      items: [
        { label: 'API Endpoint', value: '/api/v1' },
        { label: 'Auth Method', value: 'Firebase Authentication' },
      ],
    },
    {
      icon: Bell,
      title: 'Notifications',
      description: 'Alert preferences',
      items: [
        { label: 'Analysis Complete', value: 'In-app' },
        { label: 'Processing Errors', value: 'In-app' },
      ],
    },
    {
      icon: Shield,
      title: 'Security',
      description: 'Authentication & sessions',
      items: [
        { label: 'Authentication', value: 'Firebase (Google)' },
        { label: 'Session', value: 'Active' },
      ],
    },
  ]

  return (
    <div className="max-w-3xl animate-fade-in">
      <PageHeader
        title="Settings"
        description="Manage your account and preferences"
      />

      <div className="card p-5 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {user?.photoURL ? (
            <img src={user.photoURL} alt="" className="w-14 h-14 object-cover border" style={{ borderColor: 'var(--color-border)' }} />
          ) : (
            <div
              className="w-14 h-14 flex items-center justify-center text-lg font-bold uppercase border"
              style={{ background: 'var(--color-primary)', color: '#fff', borderColor: 'var(--color-border)' }}
            >
              {user?.displayName?.[0] || user?.email?.[0] || '?'}
            </div>
          )}
          <div>
            <p className="text-base font-bold" style={{ color: 'var(--color-text)' }}>
              {user?.displayName || 'User'}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              {user?.email}
            </p>
          </div>
        </div>
        <button onClick={toggle} className="btn btn-secondary btn-sm">
          {theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode'}
        </button>
      </div>

      <div className="space-y-4">
        {sections.map((section) => (
          <div key={section.title} className="card overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
              <div
                className="w-9 h-9 flex items-center justify-center border"
                style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
              >
                <section.icon size={16} style={{ color: 'var(--color-primary)' }} />
              </div>
              <div>
                <h2 className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>{section.title}</h2>
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{section.description}</p>
              </div>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
              {section.items.map((item) => (
                <div key={item.label} className="flex items-center justify-between px-5 py-3.5">
                  <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{item.label}</span>
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
