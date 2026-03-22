import '../styles/animations.css'

interface ConnectionStatusProps {
  isError: boolean
  isLoading: boolean
}

export function ConnectionStatus({ isError, isLoading }: ConnectionStatusProps) {
  if (!isError && !isLoading) return null

  return (
    <div style={{
      position: 'fixed',
      top: '0.75rem',
      right: '0.75rem',
      padding: '0.5rem 1rem',
      borderRadius: '6px',
      fontSize: '0.8rem',
      fontWeight: 600,
      zIndex: 200,
      background: isError ? 'var(--life-low)' : 'var(--bg-tertiary)',
      color: isError ? '#fff' : 'var(--text-secondary)',
      border: `1px solid ${isError ? 'var(--life-low)' : 'var(--border-default)'}`,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }}>
      <span
        className="animate-pulse"
        style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: isError ? '#fff' : 'var(--active-glow)' }}
      />
      {isError ? 'Reconnecting...' : 'Loading...'}
    </div>
  )
}
