# Contracts: Scryfall Card Art Integration

**No new API endpoints are added by this feature.**

## Existing Contract: Card object in game state

All game state endpoints (`GET /game/{game_id}`, `POST /game/{game_id}/action`, etc.) return `Card` objects as part of `PlayerState.hand`, `Permanent.card`, etc.

The `scryfall_id` field — already present in the contract — is the sole field this feature depends on.

### Card object (relevant fields)

```json
{
  "id": "3b4c1f2a-...",
  "scryfall_id": "abc12345-1234-1234-1234-abcdef123456",
  "name": "Lightning Bolt",
  "type_line": "Instant",
  "colors": ["R"],
  ...
}
```

`scryfall_id` is `null` for tokens and engine-generated cards without a Scryfall lookup.

### Permanent object (relevant fields)

```json
{
  "id": "...",
  "card": { ... },
  "is_face_down": false,
  ...
}
```

`is_face_down` drives the front/back image selection.

---

## External Contract: Scryfall CDN

This feature depends on Scryfall's CDN image service (external, not under our control).

| Property | Value |
|----------|-------|
| URL pattern | `https://cards.scryfall.io/{size}/{face}/{id[0]}/{id[1]}/{uuid}.jpg` |
| Stability | Documented, stable |
| Auth | None required |
| Rate limits | None on CDN (only on API) |
| Cache-Control | `max-age=604800` (7 days) |
| ToS | Non-commercial fan content permitted with attribution |
