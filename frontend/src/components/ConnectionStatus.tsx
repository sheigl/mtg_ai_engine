interface ConnectionStatusProps {
  isError: boolean
  isLoading: boolean
}

export function ConnectionStatus({ isError, isLoading }: ConnectionStatusProps) {
  if (!isError && !isLoading) return null

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-2)',
      padding: 'var(--space-1) var(--space-3)',
      borderRadius: 'var(--radius-full)',
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      background: isError ? 'var(--danger-subtle)' : 'var(--surface-hover)',
      color: isError ? 'var(--danger)' : 'var(--text-secondary)',
      border: `1px solid ${isError ? 'var(--danger)' : 'var(--border-subtle)'}`,
      transition: 'all var(--transition-fast)',
    }}>
      <span style={{
        display: 'inline-block',
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: isError ? 'var(--danger)' : 'var(--accent)',
        animation: isError ? 'pulse 1.5s ease-in-out infinite' : 'pulse 2s ease-in-out infinite',
      }} />
      {isError ? 'Reconnecting' : 'Loading'}
    </div>
  )
}
