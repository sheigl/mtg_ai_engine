import { useRef, useState } from 'react'
import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import type { Permanent } from '../types/game'
import { CardView } from './CardView'
import '../styles/board.css'

interface BattlefieldProps {
  permanents: Permanent[]
  isOpponent?: boolean
  permanentOrder?: string[]
  onReorder?: (newOrder: string[]) => void
  isPending?: boolean
}

export function Battlefield({
  permanents,
  isOpponent = false,
  permanentOrder,
  onReorder,
  isPending,
}: BattlefieldProps) {
  const reorderDragId = useRef<string | null>(null)
  const [dragOverId, setDragOverId] = useState<string | null>(null)

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

  // Sort by permanentOrder if provided
  const sortedVisible = permanentOrder
    ? [
        ...permanentOrder.filter(id => visible.some(p => p.id === id)).map(id => visible.find(p => p.id === id)!),
        ...visible.filter(p => !permanentOrder.includes(p.id)),
      ]
    : visible

  if (sortedVisible.length === 0) {
    return (
      <div className={`battlefield${isOpponent ? ' opponent' : ''}`}>
        <div className="battlefield-empty">No permanents</div>
      </div>
    )
  }

  const canReorder = !isOpponent && !!permanentOrder && !!onReorder

  function handleReorderDrop(targetId: string, e: React.DragEvent) {
    const dragId = reorderDragId.current
    if (!dragId || dragId === targetId || !permanentOrder || !onReorder) return
    const order = permanentOrder.filter(id => visible.some(p => p.id === id))
    const fromIdx = order.indexOf(dragId)
    const toIdx = order.indexOf(targetId)
    if (fromIdx === -1 || toIdx === -1) return
    const next = [...order]
    next.splice(fromIdx, 1)
    next.splice(toIdx, 0, dragId)
    onReorder(next)
    e.stopPropagation()
  }

  return (
    <LayoutGroup>
      <div className={`battlefield${isOpponent ? ' opponent' : ''}`}>
        <AnimatePresence mode="popLayout">
          {sortedVisible.map((perm) => (
            <motion.div
              key={perm.id}
              layout
              layoutId={perm.card.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              style={{
                outline: dragOverId === perm.id ? '2px dashed #aaa' : undefined,
                borderRadius: 6,
              }}
            >
              {/* Inner div handles HTML5 drag events (motion.div uses Framer drag types) */}
              <div
                draggable={canReorder && !isPending}
                onDragStart={canReorder && !isPending ? (e: React.DragEvent) => {
                  reorderDragId.current = perm.id
                  e.dataTransfer.setData('reorder-battlefield', perm.id)
                  e.dataTransfer.effectAllowed = 'move'
                  e.stopPropagation()
                } : undefined}
                onDragOver={canReorder ? (e: React.DragEvent) => {
                  if (reorderDragId.current && reorderDragId.current !== perm.id) {
                    e.preventDefault()
                    e.stopPropagation()
                    setDragOverId(perm.id)
                  }
                } : undefined}
                onDragLeave={canReorder ? () => {
                  if (dragOverId === perm.id) setDragOverId(null)
                } : undefined}
                onDrop={canReorder ? (e: React.DragEvent) => {
                  if (e.dataTransfer.getData('reorder-battlefield')) {
                    e.preventDefault()
                    handleReorderDrop(perm.id, e)
                    setDragOverId(null)
                  }
                } : undefined}
                onDragEnd={canReorder ? () => {
                  reorderDragId.current = null
                  setDragOverId(null)
                } : undefined}
                style={{ cursor: canReorder && !isPending ? 'grab' : undefined }}
              >
                <CardView card={perm.card} permanent={perm} attachedAuras={aurasByHost[perm.id]} />
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}
