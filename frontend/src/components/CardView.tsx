import type { Card, Permanent } from '../types/game'
import '../styles/card.css'

interface CardViewProps {
  card: Card
  permanent?: Permanent
}

function getColorAttr(card: Card): string {
  if ('type_line' in card && card.type_line.toLowerCase().includes('land')) {
    return 'land'
  }
  const colors = card.colors
  if (!colors || colors.length === 0) return 'C'
  if (colors.length > 1) return 'multi'
  return colors[0]
}

function formatManaCost(cost: string | null): string {
  if (!cost) return ''
  return cost.replace(/\{|\}/g, '')
}

export function CardView({ card, permanent }: CardViewProps) {
  const isTapped = permanent?.tapped ?? false
  const isSummoningSick = permanent?.summoning_sick ?? false
  const isCreature = card.type_line.toLowerCase().includes('creature')
  const counters = permanent?.counters ?? {}
  const counterEntries = Object.entries(counters).filter(([, v]) => v > 0)

  return (
    <div
      className={`card${isTapped ? ' tapped' : ''}${isSummoningSick && isCreature ? ' card-summoning-sick' : ''}`}
      data-colors={getColorAttr(card)}
      title={`${card.name}\n${card.type_line}${card.oracle_text ? '\n' + card.oracle_text : ''}`}
    >
      {card.mana_cost && (
        <span className="card-mana-cost">{formatManaCost(card.mana_cost)}</span>
      )}

      {counterEntries.length > 0 && (
        <div className="card-counters">
          {counterEntries.map(([type, count]) => (
            <span key={type} className="card-counter-badge">{type}: {count}</span>
          ))}
        </div>
      )}

      <span className="card-name">{card.name}</span>

      <span className="card-type">{card.type_line}</span>

      {isCreature && card.power != null && card.toughness != null && (
        <span className="card-pt">
          {permanent && permanent.damage_marked > 0
            ? `${card.power}/${parseInt(card.toughness) - permanent.damage_marked}`
            : `${card.power}/${card.toughness}`
          }
        </span>
      )}

      {card.loyalty != null && (
        <span className="card-loyalty">{card.loyalty}</span>
      )}

      {permanent?.is_token && (
        <span className="card-token-badge">TOKEN</span>
      )}
    </div>
  )
}
