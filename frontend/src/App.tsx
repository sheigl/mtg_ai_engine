import { Routes, Route } from 'react-router-dom'
import { GameList } from './components/GameList'
import { GameBoard } from './components/GameBoard'
import { HumanGameBoard } from './components/HumanGameBoard'
import { HumanGameCreator } from './components/HumanGameCreator'
import { Layout } from './components/Layout'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><GameList /></Layout>} />
      <Route path="/game/:gameId" element={<Layout><GameBoard /></Layout>} />
      <Route path="/human-game/create" element={<Layout><HumanGameCreator /></Layout>} />
      <Route path="/human-game/:gameId" element={<Layout><HumanGameBoard /></Layout>} />
    </Routes>
  )
}
