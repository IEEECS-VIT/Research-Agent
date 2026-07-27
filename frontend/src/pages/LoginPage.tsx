import { Navigate } from 'react-router-dom'
import { FlaskConical, Sparkles, Upload, Search, BarChart3, Sun, Moon } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { LoadingScreen } from '../components/ui/LoadingScreen'
import { firebaseEnabled } from '../services/firebase'

const features = [
  { icon: Upload, title: 'Upload', desc: 'Papers & drafts in any format' },
  { icon: Search, title: 'Analyze', desc: 'AI-powered alignment checks' },
  { icon: BarChart3, title: 'Discover', desc: 'Contradictions & insights' },
]

export function LoginPage() {
  const { user, loading, signInWithGoogle } = useAuth()
  const { theme, toggle } = useTheme()

  const handleGoogleSignIn = async () => {
    try {
      await signInWithGoogle()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Google sign-in failed.'
      window.alert(message)
    }
  }

  if (loading) return <LoadingScreen />
  if (user) return <Navigate to="/dashboard" replace />

  return (
    <div className="min-h-screen flex mesh-bg" style={{ background: 'var(--color-bg)' }}>
      <div className="flex-1 flex items-center justify-center p-8 lg:p-12">
        <div className="w-full max-w-md animate-fade-in">
          <div className="flex items-center gap-3 mb-8">
            <div
              className="w-11 h-11 flex items-center justify-center border"
              style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
            >
              <FlaskConical size={24} style={{ color: 'var(--color-primary)' }} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--color-text)' }}>
                Research Agent
              </h1>
              <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                AI Research Intelligence
              </p>
            </div>
          </div>

          <div className="card p-8" style={{ boxShadow: 'var(--shadow-lg)' }}>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />
              <h2 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
                Welcome back
              </h2>
            </div>
            <p className="text-sm mb-8 leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
              Sign in to manage your research documents, run alignment analyses, and detect contradictions.
            </p>

            {!firebaseEnabled && (
              <div className="mb-6 p-3 border text-sm" style={{ background: 'var(--color-warning-light)', color: 'var(--color-text)' }}>
                Google sign-in is disabled until the frontend Firebase variables are filled in.
              </div>
            )}

            <button
              onClick={handleGoogleSignIn}
              className="btn btn-secondary btn-lg w-full"
              disabled={!firebaseEnabled}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" className="shrink-0">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              {firebaseEnabled ? 'Continue with Google' : 'Configure Firebase to continue'}
            </button>
          </div>

          <div className="mt-5 flex justify-center">
            <button onClick={toggle} className="btn btn-ghost btn-sm gap-2">
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
          </div>
        </div>
      </div>

      <div
        className="hidden lg:flex flex-1 items-center justify-center p-12 relative overflow-hidden border-l"
        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-hover)' }}
      >
        <div className="relative max-w-lg animate-fade-in">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 border text-xs font-semibold mb-6"
            style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}
          >
            <Sparkles size={12} />
            Powered by AI
          </div>
          <h2 className="text-4xl font-extrabold tracking-tight mb-4 leading-tight" style={{ color: 'var(--color-text)' }}>
            Research alignment,<br />
            <span style={{ color: 'var(--color-primary)' }}>reimagined</span>
          </h2>
          <p className="text-base leading-relaxed mb-10" style={{ color: 'var(--color-text-secondary)' }}>
            Upload research papers and drafts. Our AI analyzes alignment, detects contradictions,
            and maintains research consistency with context-aware semantic comparison.
          </p>
          <div className="grid grid-cols-3 gap-4">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="card p-4 card-hover">
                <div
                  className="w-10 h-10 flex items-center justify-center mb-3 border"
                  style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
                >
                  <Icon size={18} style={{ color: 'var(--color-primary)' }} />
                </div>
                <p className="text-sm font-bold mb-0.5" style={{ color: 'var(--color-text)' }}>{title}</p>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
