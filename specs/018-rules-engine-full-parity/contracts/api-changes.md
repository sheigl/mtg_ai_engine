# API Contracts: Feature 018

All changes are backwards-compatible — new fields are optional with defaults.

## Modified Request Models

### POST /game/{id}/cast  → CastRequest
```json
{
  "card_id": "string",
  "targets": ["string"],
  "mana_payment": {"R": 1},
  "alternative_cost": null,
  "modes_chosen": [0],
  "x_value": 3,
  "kicker_paid": false,
  "jump_start_discard_id": null,
  "from_graveyard": false,
  "dry_run": false
}
```
New fields: `x_value` (int, default 0), `kicker_paid` (bool, default false), `jump_start_discard_id` (str|null, default null).

---

## Modified Response Models

### GET /game/{id}/actions  → LegalActionsResponse

New action types in `legal_actions[]`:

**X Spell Variants**
```json
{
  "action_type": "cast",
  "card_id": "fireball_001",
  "card_name": "Fireball",
  "mana_options": [{"mana_cost": "{4}{R}", "x_value": 4}],
  "x_value": 4,
  "description": "cast Fireball (X=4)"
}
```

**Kicker Variants**
```json
{
  "action_type": "cast",
  "card_id": "card_001",
  "card_name": "Skizzik",
  "kicker_paid": true,
  "description": "cast Skizzik with kicker"
}
```

**Suspend**
```json
{
  "action_type": "suspend",
  "card_id": "card_001",
  "card_name": "Ancestral Vision",
  "description": "suspend Ancestral Vision"
}
```

**Foretell**
```json
{
  "action_type": "foretell",
  "card_id": "card_001",
  "card_name": "Behold the Multiverse",
  "description": "foretell Behold the Multiverse"
}
```

---

## Modified GameState Response

New top-level fields in game state JSON:

```json
{
  "pending_scry_choice": {
    "player": "Alice",
    "cards": [{"name": "Forest", ...}, {"name": "Lightning Bolt", ...}],
    "n": 2
  },
  "pending_surveil_choice": null,
  "pending_tutor_choice": null,
  "pending_discard_choice": null,
  "pending_ward_payment": null,
  "spells_cast_this_turn": 1,
  "spells_cast_last_turn": 0
}
```

---

## Error Responses

### Menace blocker rejection (HTTP 400)
```json
{
  "error": "Menace creature requires 2 or more blockers, got 1",
  "error_code": "INVALID_BLOCKER_COUNT"
}
```

### Ward cost not paid (results in counter, not 400)
Ward payment failure results in the targeting spell being countered — not an HTTP error. The engine processes the ward trigger automatically.
