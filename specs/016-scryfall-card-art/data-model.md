# Data Model: Scryfall Card Art Integration

**Feature**: 016-scryfall-card-art

---

## Existing Models (no changes required)

### Card (backend — `mtg_engine/models/game.py`)

```python
class Card(BaseModel):
    id: str                          # instance UUID
    scryfall_id: Optional[str]       # ← used to construct image URLs; already present
    name: str
    mana_cost: Optional[str]
    type_line: str
    oracle_text: Optional[str]
    power: Optional[str]
    toughness: Optional[str]
    loyalty: Optional[str]
    colors: list[str]
    color_identity: list[str]
    keywords: list[str]
    faces: Optional[list[CardFace]]  # DFC face list; faces share parent scryfall_id
    cmc: float
    parse_status: str
```

No schema changes needed. `scryfall_id` is the key field — already populated for all cards
loaded via `ScryfallClient` and serialized through the API.

### Card (frontend — `frontend/src/types/game.ts`)

```typescript
export interface Card {
  id: string
  scryfall_id: string | null   // ← derives image URL; already present
  name: string
  mana_cost: string | null
  type_line: string
  oracle_text: string | null
  power: string | null
  toughness: string | null
  loyalty: string | null
  colors: string[]
  color_identity: string[]
  keywords: string[]
  cmc: number
  parse_status: string
}
```

No type changes needed.

### Permanent (frontend — `frontend/src/types/game.ts`)

```typescript
export interface Permanent {
  id: string
  card: Card
  controller: string
  tapped: boolean
  damage_marked: number
  counters: Record<string, number>
  attached_to: string | null
  attachments: string[]
  is_token: boolean
  turn_entered_battlefield: number
  summoning_sick: boolean
  is_face_down: boolean   // ← used to decide front vs back image
  timestamp: number
}
```

`is_face_down` is already present and used to decide whether to show front or back art.

---

## New Frontend Utility

### `scryfallImageUrl` (frontend — `frontend/src/utils/scryfall.ts`)

Pure utility function; no state, no side effects.

```typescript
export type ScryfallImageSize = 'small' | 'normal' | 'large' | 'png' | 'art_crop' | 'border_crop'
export type ScryfallFace = 'front' | 'back'

// Scryfall official card back (face-down cards)
export const CARD_BACK_URL =
  'https://cards.scryfall.io/small/back/0/0/0aeebaf5-8c7d-4636-9e82-8c27447861f7.jpg'

export function scryfallImageUrl(
  scryfallId: string,
  face: ScryfallFace = 'front',
  size: ScryfallImageSize = 'small'
): string
```

**Logic**: `https://cards.scryfall.io/{size}/{face}/{id[0]}/{id[1]}/{scryfallId}.jpg`

---

## Rendering Logic Summary

| Condition | Image shown |
|-----------|-------------|
| `permanent.is_face_down === true` | `CARD_BACK_URL` |
| `card.scryfall_id !== null` | `scryfallImageUrl(card.scryfall_id, 'front', 'small')` |
| `card.scryfall_id === null` (token, etc.) | No image; text-based fallback |
| Image `onError` fires | No image; text-based fallback |
