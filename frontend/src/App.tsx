import { Routes, Route } from 'react-router-dom'
import { GameList } from './components/GameList'
import { GameBoard } from './components/GameBoard'
import { HumanGameBoard } from './components/HumanGameBoard'
import { HumanGameCreator } from './components/HumanGameCreator'
import { ThemeToggle } from './components/ThemeToggle'

export function App() {
  return (
    <>
      <div style={{
        position: 'fixed',
        bottom: '0.75rem',
        right: '0.75rem',
        zIndex: 300,
      }}>
        <ThemeToggle />
      </div>
      <Routes>
        <Route path="/" element={<GameList />} />
        <Route path="/game/:gameId" element={<GameBoard />} />
        <Route path="/human-game/create" element={<HumanGameCreator />} />
        <Route path="/human-game/:gameId" element={<HumanGameBoard />} />
      </Routes>
      <footer style={{
        textAlign: 'center',
        padding: '0.5rem',
        fontSize: '0.65rem',
        color: 'var(--text-muted)',
        borderTop: '1px solid var(--border-muted)',
      }}>
        Card images © Wizards of the Coast. Powered by{' '}
        <a href="https://scryfall.com" target="_blank" rel="noopener noreferrer">Scryfall</a>.
      </footer>
    </>
  )
}
