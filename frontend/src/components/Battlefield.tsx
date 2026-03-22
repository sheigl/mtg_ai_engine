import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import type { Permanent } from '../types/game'
import { CardView } from './CardView'
import '../styles/board.css'

interface BattlefieldProps {
  permanents: Permanent[]
  isOpponent?: boolean
}

export function Battlefield({ permanents, isOpponent = false }: BattlefieldProps) {
  if (permanents.length === 0) {
    return (
      <div className={`battlefield${isOpponent ? ' opponent' : ''}`}>
        <div className="battlefield-empty">No permanents</div>
      </div>
    )
  }

  return (
    <LayoutGroup>
      <div className={`battlefield${isOpponent ? ' opponent' : ''}`}>
        <AnimatePresence mode="popLayout">
          {permanents.map((perm) => (
            <motion.div
              key={perm.id}
              layout
              layoutId={perm.card.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            >
              <CardView card={perm.card} permanent={perm} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}
