import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'

export function TopBar() {
  const { theme, toggle } = useTheme()

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <div />
      <button
        onClick={toggle}
        className="p-2 transition-colors hover:bg-black/5 dark:hover:bg-white/10"
        style={{ color: 'var(--color-text-secondary)' }}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
    </header>
  )
}
