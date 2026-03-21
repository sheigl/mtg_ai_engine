# Research: Commander Format Support

**Branch**: `009-commander-format` | **Date**: 2026-03-21

## Decision 1: Where to Store Command Zone Data

**Decision**: Add `command_zone: list[Card]` to `PlayerState` and `commander_name: str | None` + `commander_cast_count: int` to `PlayerState`.

**Rationale**: The command zone is per-player. Storing it on `PlayerState` keeps the existing zone architecture consistent — every other per-player zone (hand, library, graveyard, exile) is already there. Adding to `PlayerState` means command zone contents are automatically included in all `GET /game/{id}` responses via `model_dump()` with zero extra serialization work.

**Alternatives considered**:
- Separate top-level `command_zones: dict[str, list[Card]]` on `GameState` — adds symmetry with battlefield (shared zone) but breaks the per-player zone pattern
- Separate `CommandZoneState` model — over-engineered; the zone holds at most one card

---

## Decision 2: Commander Damage Tracking Storage

**Decision**: Add `commander_damage: dict[str, dict[str, int]]` to `GameState`, keyed as `commander_permanent_id → defending_player_name → total_combat_damage`.

**Rationale**: Commander damage is associated with a specific permanent on the battlefield (the commander creature), not with a player or card name. Using permanent ID as the outer key correctly handles the case where the same card enters the battlefield multiple times — each re-cast is a new permanent object with a new ID, so past damage is preserved on the old ID and new damage accumulates on the new ID. This matches CR 903.10: commander damage is tracked per object.

**Alternatives considered**:
- Keyed by card name — incorrect per rules; a re-cast commander that deals 10 then re-enters and deals 11 more should count 21 total (same object's history), but name-keying would attribute them to different "objects"
- Stored on `PlayerState` as `received_commander_damage` — harder to query "how much did commander X deal to Y"; present structure allows both queries
- Keyed by `(commander_player, defender)` — loses identity if a player somehow has multiple commanders (out of scope, but future-safe)

---

## Decision 3: Commander Zone Redirection — Auto vs. Pending Choice

**Decision**: When a commander would move to graveyard or exile, **automatically redirect it to the command zone** on behalf of the controller (no player input required).

**Rationale**: In practice, commanders always go to the command zone on any graveyard/exile event — passing on the redirect is essentially never correct and creates an awkward UI state for both the AI and API. The AI has no meaningful basis for choosing to leave its commander in exile. Auto-redirect simplifies the zone-change hook, removes the need for a new pending-choice API, and matches how most implementations handle this (including MTGO and Arena).

**Rules note**: CR 903.9 says the controller "may" put the commander in the command zone; it's optional. Auto-redirecting is a simplifying assumption documented in the spec's Assumptions section.

**Alternatives considered**:
- Add a pending choice API like `pending_triggers` — correct per rules but adds significant complexity with no practical game-play difference for AI players
- Add a `POST /game/{id}/redirect-commander` endpoint — same complexity concern

---

## Decision 4: Commander Tax Calculation

**Decision**: Commander tax is tracked via `commander_cast_count: int` on `PlayerState`. When `cast_commander` is submitted, the engine adds `2 × commander_cast_count` generic mana to the commander's base mana cost before payment validation.

**Rationale**: Tax is always `2 × number_of_times_cast_from_command_zone`. Storing the count is simpler and more space-efficient than storing a running tax total. The count is incremented on each successful command-zone cast. It is NOT reset when the commander changes zones.

**Alternatives considered**:
- Storing computed `current_tax` — redundant; derivable from count; risks getting out of sync

---

## Decision 5: Deck Validation — Singleton + Color Identity

**Decision**: Add `load_commander_deck(card_names, commander_name)` to `deck_loader.py` (or a new `commander_validator.py`). Validates: exactly 100 cards, singleton non-basics, commander is legendary creature, all deck cards match commander's color identity.

**Rationale**: Keeping validation in the deck-loading layer (same as the 60-card minimum check) means `GameManager.create_game()` sees already-validated `Card` lists. Adding a separate function rather than a flag parameter keeps `load_deck()` unchanged (no regressions).

**Color identity source**: The Scryfall API returns `color_identity` in the raw card JSON. The `_build_card()` method in `scryfall.py` does NOT currently persist it; we add `color_identity: list[str]` to the `Card` model and populate it from the raw Scryfall response.

**Alternatives considered**:
- Parse color identity from oracle text ourselves — error-prone; Scryfall already does this correctly including hybrid mana symbols in reminder text
- Validate at the API request level (not deck-loader) — inconsistent with existing pattern

---

## Decision 6: `cast_commander` Action Type

**Decision**: Add a new `action_type: "cast_commander"` to the legal-actions response when the player's commander is in their command zone and they can pay the mana cost + tax. The existing `/cast` endpoint handles the submission (commander casting is mechanically identical to casting from hand, just with a different source zone and tax).

**Rationale**: The `_compute_legal_actions()` function in `game.py` already iterates hand cards. We add a parallel block that checks the command zone card(s). Reusing the `/cast` endpoint with an additional `from_command_zone: bool` flag avoids a new endpoint while allowing the engine to apply the tax and increment `commander_cast_count`.

**Alternatives considered**:
- New `POST /game/{id}/cast-commander` endpoint — cleaner isolation but duplicates most of the cast logic
- Include commander in the hand-card loop — mixes zones, harder to display correctly in prompts

---

## Decision 7: Default Commander Deck for AI Client

**Decision**: Use a 100-card mono-green stompy Commander deck with Multani, Maro-Sorcerer as the default commander. Cards used are only those already in the Scryfall cache or reliably available: 38 Forest, Multani (commander), and 61 green creatures/spells from the existing card set the engine already uses.

**Rationale**: The default deck must be legal (singleton, 100 cards, color identity) and use only cards the engine can resolve. Mono-green avoids color identity issues and uses cards from the existing DEFAULT_DECK plus basics.

**Practical default deck** (100 cards):
- 1× Multani, Maro-Sorcerer (commander — in command zone, not in deck)
- 37× Forest (basic land, singleton rule exempt)
- 4× Llanowar Elves
- 4× Elvish Mystic
- 4× Grizzly Bears
- 4× Giant Growth
- 4× Elvish Warrior
- 4× Troll Ascetic
- 4× Leatherback Baloth
- 4× Garruk's Companion
- 4× Rancor
- 4× Reclaim
- 4× Giant Spider
- 4× Kalonian Tusker
- 4× Prey Upon
- 4× Titanic Growth
- 4× Stampede Driver
- 3× Woodfall Primus

Total in deck: 99 cards + 1 commander in command zone = 100 card deck.

**Note**: If any card above is unavailable in the cache, the AI client will fall back to a safe mono-green list using only known-available cards. This is a best-effort default.

**Alternatives considered**:
- Require users to always provide `--deck` in Commander mode — too much friction; quick-start value is lost
- Use the existing 60-card DEFAULT_DECK padded to 100 — would violate singleton rules
