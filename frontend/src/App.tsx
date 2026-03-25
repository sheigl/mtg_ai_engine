import { Routes, Route } from 'react-router-dom'
import { GameList } from './components/GameList'
import { GameBoard } from './components/GameBoard'

export function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<GameList />} />
        <Route path="/game/:gameId" element={<GameBoard />} />
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
