import { User, Bell, Shield, Key } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export function SettingsPage() {
  const { user } = useAuth()

  const sections = [
    {
      icon: User,
      title: 'Profile',
      items: [
        { label: 'Name', value: user?.displayName || 'Not set' },
        { label: 'Email', value: user?.email || 'Not set' },
      ],
    },
    {
      icon: Key,
      title: 'API Configuration',
      items: [
        { label: 'API Endpoint', value: '/api/v1' },
        { label: 'Auth Method', value: 'Firebase Authentication' },
      ],
    },
    {
      icon: Bell,
      title: 'Notifications',
      items: [
        { label: 'Analysis Complete', value: 'In-app' },
        { label: 'Processing Errors', value: 'In-app' },
      ],
    },
    {
      icon: Shield,
      title: 'Security',
      items: [
        { label: 'Authentication', value: 'Firebase (Google)' },
        { label: 'Session', value: 'Active' },
      ],
    },
  ]

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Settings</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Manage your account and preferences
        </p>
      </div>

      <div className="space-y-4">
        {sections.map((section) => (
          <div key={section.title} className="border" style={{ borderColor: 'var(--color-border)' }}>
            <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
              <section.icon size={16} style={{ color: 'var(--color-text-secondary)' }} />
              <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{section.title}</h2>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
              {section.items.map((item) => (
                <div key={item.label} className="flex items-center justify-between px-4 py-3">
                  <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{item.label}</span>
                  <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
