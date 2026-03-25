# Quickstart: Scryfall Card Art Integration

## What's changing

The `CardView` component in the frontend gains a card-art background image loaded directly from Scryfall's CDN using the existing `scryfall_id` field. No backend changes are required.

## Files to modify

| File | Change |
|------|--------|
| `frontend/src/components/CardView.tsx` | Add `scryfallImageUrl` call; render background image or fallback |
| `frontend/src/styles/card.css` | Add `.card-art` image style; add `.card-has-art` overlay variant |
| `frontend/src/utils/scryfall.ts` | **NEW** — utility to build Scryfall CDN URLs |

## Run locally

```bash
# Backend (no changes needed)
uvicorn mtg_engine.api.main:app --reload

# Frontend dev server
cd frontend && npm run dev
```

## Verify it works

1. Open the UI at `http://localhost:5173/ui/`
2. Create a game (both players will use default decks)
3. Card images should appear on cards in hand and battlefield
4. Tapping a card should show the image rotated 90°
5. Face-down cards should show the generic MTG card back

## Verify fallback

1. Open DevTools → Network → set "Offline" mode
2. Refresh — previously loaded card images should still show (browser cache)
3. Cards not yet loaded should fall back to text display (name + type visible)

## Attribution

Scryfall attribution must appear in the app footer (FR-006). The `GameBoard` or `App` component footer should include:
> "Card images © Wizards of the Coast. Powered by [Scryfall](https://scryfall.com)."
