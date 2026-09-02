# Story: Fortify Keyword Module (CR 702.54a)

## User Story
As an MTG engine developer, I want the Fortify keyword implemented as a full keyword module with detection, parsing, activation (attach a Fortification to a target land), SBA unattach, legal actions, and integration tests, so that Fortification cards (Darksteel Garrison, C.A.M.P.) produce correct game state instead of silently no-op'ing.

## Context

### Rule Text Adjudication (CR 702.54a) — CORRECTION TO THE DRAFT
The original draft of this story described Fortify as *"put +N/+N counters on target creature."* **That is incorrect.** The authoritative sources (Scryfall card database and the MTG Comprehensive Rules) confirm that Fortify is an **attach-to-land** mechanic — the land-analogue of Equip — not a counters mechanic.

**CR 702.54a** (old CR numbering; **702.67a** in the current CR, as of the TMNT set / 2025-11-14):
> "Fortify is an activated ability of Fortification cards. 'Fortify [cost]' means '[cost]: **Attach this Fortification to target land you control.** Activate this ability only any time you could cast a sorcery.'"

**CR 301.7 (Fortifications):**
> "A Fortification is an artifact with the land subtype Fortification. A Fortification enters the battlefield unattached and stays on the battlefield if the land it's attached to leaves."

The draft's "counters" description appears to have been a confusion with C.A.M.P.'s *triggered* ability ("Whenever fortified land is tapped for mana, put a +1/+1 counter on target creature you control..."), which is a separate ability on the card, not the Fortify keyword itself.

### Real Card Oracle Texts
**Local Scryfall SQLite cache: ZERO Fortify cards.** The local cache (`mtg_engine/card_data/cache.db`) contains 319 cards total, none with "fortify" in their `keywords` array or oracle text. Per the task instructions, this is documented here and the rule text falls back to the CR text above.

The following two real Fortify card texts were retrieved from the **Scryfall API** (authoritative, `keyword:fortify` search returns exactly 2 cards) as supplementary evidence:

1. **Darksteel Garrison** (Future Sight, 2007) — `Artifact — Fortification`, mana cost `{2}`, CMC 2:
   > "Fortified land has indestructible.
   > Whenever fortified land becomes tapped, target creature gets +1/+1 until end of turn.
   > **Fortify {3}** ({3}: Attach to target land you control. Fortify only as a sorcery. This card enters unattached and stays on the battlefield if the land leaves.)"

2. **C.A.M.P.** (Fallout, 2024) — `Artifact — Fortification`, mana cost `{3}`, CMC 3:
   > "Whenever fortified land is tapped for mana, put a +1/+1 counter on target creature you control. If that creature shares a color with the mana that land produced, create a Junk token. (It's an artifact with '{T}, Sacrifice this token: Exile the top card of your library. You may play that card this turn. Activate only as a sorcery.')
   > **Fortify {3}** ({3}: Attach to target land you control. Fortify only as a sorcery.)"

Note: the Fortify reminder text reads **"(Fortify only as a sorcery.)"**, not "(Activate only as a sorcery.)" — this matters for the timing-restriction parser (see the plan).

### Why This Matters
Fortifications are the only card type that uses the Fortify keyword, and they are lands (artifact lands with the Fortification subtype). Today the engine has no Fortify module: the Fortify activated ability is parsed only by the generic oracle-text scanner, and the activation path in `POST /game/{id}/activate` silently no-ops the attach effect (it only handles "add {X}" and "regenerate"). Additionally, because a Fortification's type line is "Artifact — Fortification" (no literal "land"), the engine's ad-hoc `"land" in type_line` checks do not treat it as a land, so it cannot even be played as a land drop.

## Acceptance Criteria

### Detection and Parsing
- [ ] Create `mtg_engine/ability/keywords/fortify.py` with a `Fortify` keyword class (base class per the plan) exposing:
  - [ ] `parse_fortify_cost(oracle_text) -> str | None` — parses the cost from a "Fortify {cost}" clause (e.g., "Fortify {3}" → "{3}"; "Fortify {2}{R}" → "{2}{R}")
  - [ ] `has_fortify(card) -> bool` / `from_oracle_text(oracle_text) -> bool` — detection via the "Fortify" keyword and/or the "Fortify {cost}" clause
  - [ ] `is_fortification(card) -> bool` — True when the card's type line contains the "Fortification" subtype (these are lands per CR 301.7a)

### Fortification Land Handling (prerequisite)
- [ ] Fortifications are treated as **lands** for the land-drop rule: a Fortification in hand can be played as a land during the controller's main phase (one land per turn), reusing the existing `play_land` flow
- [ ] Fortifications remain lands even while attached to another land (they do not stop being lands on attach)

### Apply / Activation Method
- [ ] `Fortify.apply(game_state, permanent, target_land_id=None) -> GameState` implements the full Fortify logic (CR 702.54a):
  - [ ] Validates the Fortification is on the battlefield and controlled by the acting player
  - [ ] Validates the target is a **land the acting player controls** (a Fortification is itself a legal target, since it is a land)
  - [ ] Enforces **sorcery-speed** timing (controller's main phase, empty stack) — CR 702.54a "Activate only as a sorcery"
  - [ ] Pays the Fortify cost (mana only — Fortify costs do not include a tap)
  - [ ] Attaches the Fortification to the target land by setting `attached_to` on the Fortification and appending to the target land's `attachments` list (reusing the existing attachment infrastructure, mirroring `_apply_equip`)
  - [ ] Fires the existing attach trigger (`check_attach_triggers`) so "whenever this becomes attached to another permanent" patterns work
  - [ ] Pure transform: returns a new `GameState` via `model_copy(update={...})`; never mutates in place
- [ ] AI auto-resolution: a module-level `resolve_fortify_with_ai(game_state, permanent_id) -> GameState` that auto-attaches to a valid target land the AI controls (deterministic selection, e.g., first legal land) when the AI can pay the cost; no-op (unchanged state) when the AI cannot pay or has no legal land target

### State-Based Actions
- [ ] A Fortification that is attached to a permanent that is **not a land** (or to nothing) becomes **unattached** as a state-based action and **stays on the battlefield** (mirrors the existing Equipment SBA at `sba.py` CR 704.5n; CR 301.7 "stays on the battlefield if the land leaves")

### Integration / API Wiring
- [ ] `POST /game/{id}/activate` handles the Fortify effect: when the activated ability's effect is a Fortify attach, it validates the target land, enforces sorcery speed, pays the cost, and attaches (no silent no-op)
- [ ] The timing-restriction parser recognizes the Fortify reminder text "(Fortify only as a sorcery.)" so the existing US20 T162 sorcery-speed guard applies (see plan for the exact regex change)
- [ ] `_compute_legal_actions()` in `api/routers/game.py` includes a `fortify` legal action (with `valid_targets` = the acting player's lands) when a Fortification the player controls is on the battlefield, the player has priority, and timing is sorcery-speed

### Tests
- [ ] Unit tests in `tests/ability/keywords/test_fortify.py`: cost parsing (single symbol, multi-symbol, no-cost/no-op), detection (true/false/absent), `is_fortification`, human activation (attach + pure transform), AI auto-resolution (attach + no-op when unaffordable / no target), sorcery-timing guard
- [ ] Integration tests in `tests/engine/test_fortify_integration.py`: play a Fortification as a land, activate Fortify to attach to a target land, verify `attached_to`/`attachments`, verify attach trigger fires, SBA unattach when the attached land leaves or is no longer a land, Fortification stays a land while attached, legal actions include `fortify` with correct `valid_targets`, API `/activate` end-to-end (attach) and timing rejection at instant speed

## Dependencies
- None (independent of other stories; reuses the existing attachment infrastructure introduced for Auras/Equipment: `Permanent.attached_to`, `Permanent.attachments`, the Equipment SBA unattach pattern, and `check_attach_triggers`). Equip (7-5b) is a separate story and is **not** designed for here.

## Priority: High

## Estimated Effort: M (~1.5–2 days including tests)

## Notes
- **Fortify vs Equip**: Fortify attaches a Fortification to a **land**; Equip attaches an Equipment to a **creature**. Both reuse the same `attached_to`/`attachments` infrastructure. This story must not implement or modify Equip behavior.
- **Out of scope — "fortified land" reference resolution**: The static/triggered abilities on the two real cards reference the "fortified land" (e.g., Darksteel Garrison's "Fortified land has indestructible", C.A.M.P.'s "Whenever fortified land is tapped for mana..."). Resolving "fortified land" references in static/triggered ability text is a separate, larger feature and is **not** in scope for this story. This story makes the Fortify *activated ability* (the attach) work; the attached Fortification's own abilities that reference the fortified land are a follow-up.
- **Fortifications are lands**: Because a Fortification's type line is "Artifact — Fortification" (no literal "land"), the engine's ad-hoc `"land" in type_line` checks must be extended (in a centralized, minimal way) so Fortifications can be played as lands and are legal Fortify targets. See the plan for the exact approach.
- **Sorcery-speed reminder text differs**: The Fortify reminder text is "(Fortify only as a sorcery.)", not "(Activate only as a sorcery.)". The existing `_TIMING_RE` regex in `ability_parser.py` will not match it, so the parser must be extended (see plan) or the `/activate` endpoint must enforce sorcery speed for Fortify explicitly.
- **No pending choice needed**: Unlike Dash/Ninjutsu (which have an optional cost the player chooses to pay or not), Fortify's cost is mandatory on activation, so there is no `pending_fortify_choice` — the human path is a direct `/activate` call with the chosen target land, and the AI path is an auto-activation. The only persistent state is the attachment itself.
- **Only 2 cards in the entire MTG database** have the Fortify keyword (Darksteel Garrison, C.A.M.P.), so test fixtures should model both.
