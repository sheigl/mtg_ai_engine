# Quickstart: Commander Format

**Branch**: `009-commander-format` | **Date**: 2026-03-21

## Prerequisites

Same as standard games — MTG engine and at least one LLM server running:

```bash
uvicorn mtg_engine.api.main:app --reload
```

---

## Minimal Commander Game (default decks)

```bash
python -m ai_client \
  --format commander \
  --player "Alice,http://localhost:8080/v1,llama3.2" \
  --player "Bob,http://localhost:8080/v1,llama3.2" \
  --commander "Multani, Maro-Sorcerer" \
  --commander "Ghalta, Primal Hunger"
```

Both players use the built-in 99-card mono-green default deck. The designated commander is placed in the command zone automatically.

---

## Commander Game via API (curl)

```bash
curl -s -X POST http://localhost:8000/game \
  -H "Content-Type: application/json" \
  -d '{
    "player1_name": "Alice",
    "player2_name": "Bob",
    "format": "commander",
    "commander1": "Multani, Maro-Sorcerer",
    "commander2": "Ghalta, Primal Hunger",
    "deck1": ["Forest","Forest","Forest","Llanowar Elves",...],
    "deck2": ["Forest","Forest","Forest","Grizzly Bears",...]
  }' | jq '.data.game_id'
```

Check command zones:

```bash
curl -s http://localhost:8000/game/<game_id> | jq '.data.players[].command_zone[].name'
```

Check legal actions (including cast_commander when available):

```bash
curl -s http://localhost:8000/game/<game_id>/legal-actions | jq '.data.legal_actions[] | select(.action_type == "cast_commander")'
```

Cast commander from command zone:

```bash
curl -s -X POST http://localhost:8000/game/<game_id>/cast \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": "<commander_card_id>",
    "mana_payment": {"G": 2, "C": 4},
    "targets": [],
    "from_command_zone": true
  }'
```

Check commander damage totals:

```bash
curl -s http://localhost:8000/game/<game_id> | jq '.data.commander_damage'
```

---

## Sample Console Output (Commander Mode)

```
Starting MTG AI Game [Commander]
Engine  : http://localhost:8000
Players : Alice (llama3.2 @ http://localhost:8080/v1) — Commander: Multani, Maro-Sorcerer
          Bob (llama3.2 @ http://localhost:8080/v1) — Commander: Ghalta, Primal Hunger
Game ID : d4395122-3219-4411-9755-4abe53254f7c

─────────────────────────────────────────
Turn 1 | BEGINNING / DRAW
Player: Alice (life: 40)
Commander: Multani, Maro-Sorcerer [Command Zone] (tax: 0)
Reasoning: I draw my card for the turn.
Action: Pass priority
─────────────────────────────────────────

─────────────────────────────────────────
Turn 1 | PRECOMBAT_MAIN / MAIN
Player: Alice (life: 40)
Commander: Multani, Maro-Sorcerer [Command Zone] (tax: 0)
Reasoning: I have 6 mana available. Casting my commander now gives me a strong threat.
Action: Cast Multani, Maro-Sorcerer from command zone (cost: {4}{G}{G})
─────────────────────────────────────────

...

════════════════════════════════════════
GAME OVER
Winner : Alice
Game ID: d4395122-3219-4411-9755-4abe53254f7c
Turns  : 14
Decisions made: 58
Reason : commander_damage  ← or: game_over / max_turns_reached
Commander Damage:
  Alice's Multani dealt 21 to Bob
════════════════════════════════════════
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `SINGLETON_VIOLATION` on game create | Deck has duplicate non-basic cards | Remove duplicates; only basic lands may repeat |
| `COLOR_IDENTITY_VIOLATION` | A card's color identity exceeds the commander's | Replace the offending card with one matching the commander's colors |
| `INVALID_COMMANDER` | Commander card name misspelled or not legendary | Check the exact card name and ensure it is a Legendary Creature |
| `cast_commander` never appears in legal actions | Commander on battlefield, or insufficient mana | Commander must be in command zone and mana must cover base cost + tax |
| Commander damage not reaching 21 | Blockers or removal prevent combat damage | Normal game play; AI may need to find alternate win condition |
