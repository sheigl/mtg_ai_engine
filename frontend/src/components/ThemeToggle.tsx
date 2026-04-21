import { useTheme } from '../context/ThemeContext'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-default)',
        borderRadius: '6px',
        color: 'var(--text-secondary)',
        cursor: 'pointer',
        fontSize: '1rem',
        lineHeight: 1,
        padding: '0.35rem 0.5rem',
        transition: 'background var(--transition-fast), color var(--transition-fast)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'var(--bg-secondary)'
        e.currentTarget.style.color = 'var(--text-primary)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'var(--bg-tertiary)'
        e.currentTarget.style.color = 'var(--text-secondary)'
      }}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}
