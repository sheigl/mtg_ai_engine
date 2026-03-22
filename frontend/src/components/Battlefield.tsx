import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import type { Permanent } from '../types/game'
import { CardView } from './CardView'
import '../styles/board.css'

interface BattlefieldProps {
  permanents: Permanent[]
  isOpponent?: boolean
}

export function Battlefield({ permanents, isOpponent = false }: BattlefieldProps) {
  // Build lookup of aura names attached to each permanent
  const aurasByHost: Record<string, string[]> = {}
  for (const perm of permanents) {
    if (perm.attached_to && perm.card.type_line.toLowerCase().includes('aura')) {
      if (!aurasByHost[perm.attached_to]) aurasByHost[perm.attached_to] = []
      aurasByHost[perm.attached_to].push(perm.card.name)
    }
  }

  // Only render permanents that are not attached auras (they show on host card)
  const visible = permanents.filter(
    p => !(p.attached_to && p.card.type_line.toLowerCase().includes('aura'))
  )

  if (visible.length === 0) {
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
          {visible.map((perm) => (
            <motion.div
              key={perm.id}
              layout
              layoutId={perm.card.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            >
              <CardView card={perm.card} permanent={perm} attachedAuras={aurasByHost[perm.id]} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}
