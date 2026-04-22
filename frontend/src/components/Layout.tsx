import { Link, useLocation } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'
import { ConnectionStatus } from './ConnectionStatus'
import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  isError?: boolean
  isLoading?: boolean
}

function getPageTitle(path: string): string {
  if (path === '/' || path === '/ui') return 'Games'
  if (path.startsWith('/game/')) return 'Observer'
  if (path.startsWith('/human-game/create')) return 'Play vs AI'
  if (path.startsWith('/human-game/')) return 'Game'
  return 'MTG Engine'
}

export function Layout({ children, isError = false, isLoading = false }: LayoutProps) {
  const location = useLocation()
  const title = getPageTitle(location.pathname)
  const isHome = location.pathname === '/' || location.pathname === '/ui'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 200,
        background: 'var(--surface-elevated)',
        borderBottom: '1px solid var(--border-subtle)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 var(--space-4)',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <Link to="/" style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              textDecoration: 'none',
              color: 'var(--text-primary)',
            }}>
              <span style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, var(--mtg-blue), var(--mtg-black))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1rem',
                fontWeight: 700,
                color: '#fff',
                flexShrink: 0,
              }}>
                M
              </span>
              <span style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 700,
                letterSpacing: '-0.02em',
                display: 'none',
              }} className="show-md">
                MTG Engine
              </span>
            </Link>

            {!isHome && (
              <>
                <span style={{ color: 'var(--border-strong)' }}>/</span>
                <span style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--text-secondary)',
                }}>
                  {title}
                </span>
              </>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <ConnectionStatus isError={isError} isLoading={isLoading} />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: 'center',
        padding: 'var(--space-4) var(--space-4)',
        fontSize: 'var(--text-xs)',
        color: 'var(--text-muted)',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--surface-elevated)',
      }}>
        Card images © Wizards of the Coast. Powered by{' '}
        <a href="https://scryfall.com" target="_blank" rel="noopener noreferrer">Scryfall</a>.
      </footer>
    </div>
  )
}
