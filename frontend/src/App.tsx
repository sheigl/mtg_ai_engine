import { Routes, Route } from 'react-router-dom'
import { GameList } from './components/GameList'
import { GameBoard } from './components/GameBoard'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<GameList />} />
      <Route path="/game/:gameId" element={<GameBoard />} />
    </Routes>
  )
}
