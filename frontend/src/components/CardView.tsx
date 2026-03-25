import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import type { Card, Permanent } from '../types/game'
import { scryfallImageUrl, CARD_BACK_URL } from '../utils/scryfall'
import '../styles/card.css'

const CARD_BACK_ZOOM_URL =
  'https://cards.scryfall.io/normal/back/0/0/0aeebaf5-8c7d-4636-9e82-8c27447861f7.jpg'

const ZOOM_PANEL_W = 310   // 300px image + a little breathing room
const ZOOM_PANEL_H = 430   // normal image is ~416px tall at 300px wide
const ZOOM_GAP = 12        // px between card edge and zoom panel

interface CardViewProps {
  card: Card
  permanent?: Permanent
  attachedAuras?: string[]
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

export function CardView({ card, permanent, attachedAuras }: CardViewProps) {
  const [artError, setArtError] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const [zoomPos, setZoomPos] = useState<{ x: number; y: number } | null>(null)

  const handleMouseEnter = () => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    // Default: appear to the right of the card
    let x = rect.right + ZOOM_GAP
    // Flip left if it would overflow the right edge
    if (x + ZOOM_PANEL_W > window.innerWidth) {
      x = rect.left - ZOOM_PANEL_W - ZOOM_GAP
    }
    // Clamp vertically so the panel stays within the viewport
    let y = rect.top
    if (y + ZOOM_PANEL_H > window.innerHeight) {
      y = window.innerHeight - ZOOM_PANEL_H - ZOOM_GAP
    }
    y = Math.max(ZOOM_GAP, y)
    setZoomPos({ x, y })
  }

  const isTapped = permanent?.tapped ?? false
  const isSummoningSick = permanent?.summoning_sick ?? false
  const isCreature = card.type_line.toLowerCase().includes('creature')
  const counters = permanent?.counters ?? {}
  const counterEntries = Object.entries(counters).filter(([, v]) => v > 0)

  // Determine image URL: face-down → card back, else derive from scryfall_id
  let imageUrl: string | null = null
  if (permanent?.is_face_down) {
    imageUrl = CARD_BACK_URL
  } else if (card.scryfall_id) {
    imageUrl = scryfallImageUrl(card.scryfall_id)
  }

  // Reset error state whenever the image URL changes
  useEffect(() => {
    setArtError(false)
  }, [imageUrl])

  const showArt = imageUrl !== null && !artError

  // Zoom uses normal-size image; face-down shows normal-size card back
  let zoomImageUrl: string | null = null
  if (permanent?.is_face_down) {
    zoomImageUrl = CARD_BACK_ZOOM_URL
  } else if (card.scryfall_id) {
    zoomImageUrl = scryfallImageUrl(card.scryfall_id, 'front', 'normal')
  }

  const zoomPanel = zoomPos && (
    <div
      className="card-zoom-panel"
      style={{ left: zoomPos.x, top: zoomPos.y }}
    >
      {zoomImageUrl
        ? <img src={zoomImageUrl} alt={card.name} />
        : (
          <div className="card-zoom-fallback">
            <strong>{card.name}</strong>
            <br />
            <span>{card.type_line}</span>
            {card.oracle_text && <p>{card.oracle_text}</p>}
          </div>
        )
      }
    </div>
  )

  return (
    <>
    <div
      ref={cardRef}
      className={`card${isTapped ? ' tapped' : ''}${isSummoningSick && isCreature ? ' card-summoning-sick' : ''}${showArt ? ' card-has-art' : ''}`}
      data-colors={getColorAttr(card)}
      title={`${card.name}\n${card.type_line}${card.oracle_text ? '\n' + card.oracle_text : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setZoomPos(null)}
    >
      {showArt && (
        <img
          className="card-art"
          src={imageUrl!}
          alt=""
          loading="lazy"
          onError={() => setArtError(true)}
        />
      )}

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

      {attachedAuras && attachedAuras.length > 0 && (
        <div className="card-auras">
          {attachedAuras.map(name => (
            <span key={name} className="card-aura-badge" title={`Enchanted by ${name}`}>
              ✦ {name}
            </span>
          ))}
        </div>
      )}
    </div>
    {zoomPanel && createPortal(zoomPanel, document.body)}
    </>
  )
}
