# Implementation Plan: Commander Format Support

**Branch**: `009-commander-format` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-commander-format/spec.md`

## Summary

Extends the MTG engine and AI CLI client to support two-player Commander (Duel Commander). Key changes: 100-card singleton deck validation with color identity enforcement, per-player command zones, commander tax on re-cast, automatic commander redirect on graveyard/exile, commander damage tracking (21 from one commander = loss), and a `--format commander` CLI mode with `--commander NAME` flags.

## Technical Context

**Language/Version**: Python 3.11 (matches existing codebase)
**Primary Dependencies**: FastAPI, Pydantic v2, httpx, openai (all existing)
**Storage**: In-memory game state (existing); SQLite Scryfall cache extended with `color_identity`
**Testing**: pytest (existing suite)
**Target Platform**: Linux server (existing)
**Project Type**: Web service (engine API) + CLI client
**Performance Goals**: Legal-actions response under 200ms (existing REQ-P01 — commander actions add O(1) checks)
**Constraints**: All existing tests must continue to pass; no changes to standard-mode behavior
**Scale/Scope**: Two-player Commander only; partner commanders and multiplayer out of scope

## Constitution Check

No constitution file found — no gate violations to evaluate. Proceeding with standard quality principles:
- ✓ Changes are additive; existing standard game mode is unaffected
- ✓ No new external dependencies introduced
- ✓ Follows existing code patterns (Pydantic models, SBA hook, zone system)

## Project Structure

### Documentation (this feature)

```text
specs/009-commander-format/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── api-changes.md  ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
mtg_engine/
├── models/
│   └── game.py                    ← add color_identity to Card; add command_zone,
│                                      commander_name, commander_cast_count to PlayerState;
│                                      add format, commander_damage to GameState
├── models/
│   └── actions.py                 ← add from_command_zone to CastRequest;
│                                      add "cast_commander" to action_type docs
├── card_data/
│   ├── scryfall.py                ← populate color_identity in _build_card()
│   └── deck_loader.py             ← add load_commander_deck() with 100-card,
│                                      singleton, legendary, and color-identity checks
├── engine/
│   ├── sba.py                     ← add commander damage SBA (21 damage → loss)
│   ├── zones.py                   ← add "command_zone" zone support;
│                                      auto-redirect commander on graveyard/exile move
│   └── combat.py                  ← hook assign_combat_damage to record
│                                      commander_damage when attacker is a commander
└── api/
    └── routers/
        └── game.py                ← extend CreateGameRequest (format, commander1, commander2);
                                       extend create_game() to call load_commander_deck();
                                       extend _compute_legal_actions() for cast_commander;
                                       extend cast() endpoint for from_command_zone logic

ai_client/
├── models.py                      ← add format, commander1, commander2 to GameConfig
├── client.py                      ← pass format/commanders in create_game() payload
├── __main__.py                    ← add --format and --commander flags; validation
└── prompts.py                     ← add DEFAULT_COMMANDER_DECK; update
                                       build_game_state_prompt() with command zone info
```

## Implementation Phases

### Phase 1: Model & Data Layer

**Goal**: Extend data models and Scryfall integration — no behavior change, all existing tests still pass.

**Files**:
- `mtg_engine/models/game.py` — add `color_identity` to `Card`; add `command_zone`, `commander_name`, `commander_cast_count` to `PlayerState`; add `format`, `commander_damage` to `GameState`
- `mtg_engine/models/actions.py` — add `from_command_zone: bool = False` to `CastRequest`
- `mtg_engine/card_data/scryfall.py` — populate `color_identity` from `raw.get("color_identity", [])`

**Checkpoint**: `python -c "from mtg_engine.models.game import GameState, PlayerState, Card; gs = GameState(...); print(gs.format)"` succeeds. All existing tests pass.

---

### Phase 2: Deck Validation

**Goal**: `load_commander_deck()` correctly validates and rejects illegal Commander decks.

**Files**:
- `mtg_engine/card_data/deck_loader.py` — add `load_commander_deck(card_names: list[str], commander_name: str, db_path=None) -> tuple[list[Card], Card]`

**Validation logic**:
1. Resolve all cards via `ScryfallClient` (same as `load_deck`)
2. Find the commander card — raise `ValueError("Commander '{name}' not found in deck")` if absent
3. Verify commander is legendary creature — raise `ValueError("Commander must be a legendary creature")`
4. Remove commander from deck list (it goes to command zone, not library)
5. Check singleton: for each non-basic-land card, count appearances — raise `ValueError(f"Singleton violation: '{name}' appears {n} times")` on duplicate
6. Check deck size == 99 after commander removal — raise `ValueError(f"Commander deck must contain 99 cards (plus commander), got {n}")`
7. Check color identity: for each card, verify `card.color_identity` is a subset of `commander.color_identity` — raise `ValueError(f"Color identity violation: '{name}' ({card.color_identity}) exceeds commander identity ({commander.color_identity})")`
8. Return `(validated_cards, commander_card)`

**Basic land names** (exempt from singleton): `{"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}`

**Checkpoint**: Unit tests for `load_commander_deck` cover all 7 validation error paths and the happy path.

---

### Phase 3: Command Zone & Game Creation

**Goal**: Commander games start with 40 life, commanders in command zones, command zone as a valid zone.

**Files**:
- `mtg_engine/api/routers/game.py` — extend `CreateGameRequest`; extend `create_game()` endpoint
- `mtg_engine/api/game_manager.py` — extend `create_game()` to accept `format`, `commander1_card`, `commander2_card`; set `life=40`, populate `command_zone`, set `commander_name`, `commander_cast_count=0`, `format`
- `mtg_engine/engine/zones.py` — add `"command_zone"` to `_get_player_zone()` zone map; add `move_card_to_command_zone(gs, card, player_name)` helper

**Commander redirect logic** (in `zones.py`):
When `move_card_to_zone()` is called with `to_zone="graveyard"` or `to_zone="exile"`, check if the card's name matches the player's `commander_name`. If so, redirect to `command_zone` instead and emit a zone-change event with `to_zone="command_zone"`.

**Checkpoint**: `POST /game` with `format=commander`, valid decks and commanders returns 200, `players[0].life == 40`, `players[0].command_zone` contains the commander, commander is not in `players[0].library`.

---

### Phase 4: Commander Casting (Legal Actions + Cast Endpoint)

**Goal**: `cast_commander` appears in legal actions when castable; casting applies tax and increments count.

**Files**:
- `mtg_engine/api/routers/game.py` → `_compute_legal_actions()` — add block after hand-card loop: for each player's `command_zone`, compute `tax = 2 × commander_cast_count`, check if player can pay `mana_cost + {tax}`, if yes append `LegalAction(action_type="cast_commander", card_id=..., card_name=..., description=f"Cast {name} from command zone (tax: {tax})", ...)`
- `mtg_engine/api/routers/game.py` → `cast()` endpoint — when `req.from_command_zone is True`: find card in command zone instead of hand; apply tax to mana payment validation; call `cast_spell()`; on success increment `player.commander_cast_count`; remove card from command zone

**Checkpoint**: In a Commander game, legal actions include `cast_commander` when the player has enough mana. Submitting a cast with `from_command_zone=true` moves the commander to the stack, removes it from command zone, and increments `commander_cast_count`.

---

### Phase 5: Commander Damage Tracking & SBA

**Goal**: Combat damage from commanders is tracked; 21+ damage triggers a loss SBA.

**Files**:
- `mtg_engine/engine/combat.py` → `assign_combat_damage()` — after applying damage to players, check if the attacking permanent's card name matches the defending player's `commander_name` (i.e., attacker IS a commander). If so, record damage in `gs.commander_damage[perm_id][defender_name] += damage_dealt`.

  **How to identify a commander attacker**: A permanent is a commander if `perm.card.name == any player's commander_name` AND `perm.controller` is a player who has that card as their commander.

- `mtg_engine/engine/sba.py` → `_check_once()` — add commander damage SBA: for each entry in `gs.commander_damage`, for each `(perm_id, defender_totals)`, for each `(defender, total)`, if `total >= 21` and defender player `not has_lost`, set `has_lost = True` and append SBAEvent.

**Checkpoint**: Submit combat damage with a commander attacker. Verify `commander_damage` dict updated in game state. Submit enough damage to reach 21; verify `is_game_over=True` and `winner` set correctly.

---

### Phase 6: AI Client Commander Mode

**Goal**: `python -m ai_client --format commander --commander X --commander Y` runs a full Commander game.

**Files**:
- `ai_client/models.py` — add `format: str = "standard"`, `commander1: str | None = None`, `commander2: str | None = None` to `GameConfig`
- `ai_client/client.py` → `create_game()` — include `format`, `commander1`, `commander2` in request body when set
- `ai_client/__main__.py` — add `--format` flag; add `--commander` flag (repeatable, `action="append"`); validate exactly 2 commanders when `format=commander`; populate `GameConfig`
- `ai_client/prompts.py` — add `DEFAULT_COMMANDER_DECK` (99-card mono-green singleton list); update `build_game_state_prompt()` to include command zone contents, commander tax, and accumulated commander damage in the prompt text
- `ai_client/game_loop.py` — update `_map_action_to_request()` to handle `cast_commander` → `POST /cast` with `from_command_zone=true`; update startup banner to show Commander mode and commander names; update `print_game_summary()` to show commander damage totals when in Commander mode

**Checkpoint**: `python -m ai_client --format commander --player "A,..." --player "B,..." --commander "Multani, Maro-Sorcerer" --commander "Ghalta, Primal Hunger"` runs a game to completion; startup banner shows `[Commander]` mode; turn logs include command zone state.

---

## Dependencies & Execution Order

```
Phase 1 (Models) → Phase 2 (Deck Validation) → Phase 3 (Command Zone + Game Creation)
                                                        ↓
                                           Phase 4 (Commander Casting)
                                                        ↓
                                           Phase 5 (Commander Damage + SBA)
                                                        ↓
                                           Phase 6 (AI Client)
```

Phases 1→2→3 are strictly sequential (each builds on the last).
Phase 4 and Phase 5 can proceed concurrently after Phase 3.
Phase 6 requires Phase 3 complete; benefits from Phase 4+5 but can stub missing engine features.

---

## Non-Goals (Out of Scope)

- Four-player multiplayer Commander
- Partner commanders
- Emblem generation
- Monarch mechanic
- Color identity enforcement for activated ability mana symbols in oracle text (Scryfall's `color_identity` field handles this automatically)
- Returning a commander to hand or library (non-standard zone choices)
