import { Navigate } from 'react-router-dom'
import { FlaskConical } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'

export function LoginPage() {
  const { user, loading, signInWithGoogle } = useAuth()
  const { theme, toggle } = useTheme()

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: 'var(--color-bg)' }}>
        <div className="w-6 h-6 border-2 animate-spin" style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }} />
      </div>
    )
  }

  if (user) return <Navigate to="/dashboard" replace />

  return (
    <div className="h-screen flex" style={{ background: 'var(--color-bg)' }}>
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-3 mb-2">
            <FlaskConical size={28} style={{ color: 'var(--color-primary)' }} />
            <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
              Research Agent
            </h1>
          </div>
          <p className="text-sm mb-8" style={{ color: 'var(--color-text-secondary)' }}>
            AI-powered research alignment &amp; contradiction detection
          </p>

          <div className="p-6 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
            <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
              Sign in
            </h2>
            <p className="text-xs mb-6" style={{ color: 'var(--color-text-secondary)' }}>
              Use your Google account to continue
            </p>

            <button
              onClick={signInWithGoogle}
              className="w-full flex items-center justify-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors border"
              style={{
                backgroundColor: 'var(--color-bg)',
                color: 'var(--color-text)',
                borderColor: 'var(--color-border)',
              }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--color-surface)'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--color-bg)'}
            >
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Continue with Google
            </button>
          </div>

          <div className="mt-4 flex justify-center">
            <button
              onClick={toggle}
              className="text-xs px-3 py-1.5 border transition-colors hover:bg-black/5 dark:hover:bg-white/10"
              style={{ color: 'var(--color-text-secondary)', borderColor: 'var(--color-border)' }}
            >
              {theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            </button>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 items-center justify-center p-8" style={{ backgroundColor: 'var(--color-surface)' }}>
        <div className="max-w-md">
          <div className="mb-6">
            <FlaskConical size={48} style={{ color: 'var(--color-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--color-text)' }}>
            Research Alignment Agent
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            Upload research papers and drafts. Our AI analyzes alignment, detects contradictions,
            and maintains research consistency over time. Get instant insights with context-aware
            reasoning and semantic comparison.
          </p>
          <div className="mt-6 flex gap-3">
            {['Upload', 'Analyze', 'Discover'].map((step) => (
              <span
                key={step}
                className="text-xs font-medium px-3 py-1.5 border"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
              >
                {step}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
