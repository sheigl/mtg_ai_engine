# Spec: MTG Rules Engine

## Purpose

A Python-based Magic: The Gathering rules engine that enforces the full
Comprehensive Rules, exposes a REST API, and allows AI agents to play
complete games against each other. The primary output is structured
training data for downstream MTG AI model training.

## Problem Statement

Training an MTG AI requires exposure to real game situations — legal
board states, correct priority sequences, valid action sets, and outcome
labels. Hand-crafted examples are slow and limited. This engine enables
AI self-play at scale, generating thousands of labeled game records
automatically without human involvement in each game.

## Context

- Standalone Python service, runs locally alongside Ollama
- AI agents (LLMs via Ollama or scripted bots) call the REST API to
  take actions; the engine enforces legality and advances game state
- Four types of training data are exported per game:
    1. Game state snapshots (board state → legal actions → chosen action)
    2. Play-by-play decision transcripts (full annotated game log)
    3. Rules Q&A pairs derived from actual rule triggers during play
    4. Win/loss outcome records for reinforcement learning
- Card data sourced from Scryfall API (or local cache); engine does not
  hard-code card text — it reads oracle text and interprets it via a
  card ability parser
- Integrates with existing MongoDB instance for training data storage

## Success Criteria

- Two AI agents can play a full game from opening hand to game over
  with zero unhandled exceptions on any legal card interaction
- All four training data types are exported for every completed game
- Full competitive rules coverage: layers (613), replacement effects,
  state-based actions, split-second, copy effects, and the stack
- REST API response time under 200ms per action on local hardware
- Engine correctly handles a suite of 50 known-tricky interactions
  (e.g. Humility + Opalescence, Leyline of Anticipation + split second,
  clone entering as a copy, damage prevention replacement effects)
- Training data output is valid JSON conforming to defined schemas

## Performance Considerations

- Benchmark deck load times for decks with 100+ cards (REQ-P01)
- Ensure API latency remains under 200ms for all core game actions (REQ-P02)
- Support 100+ concurrent game sessions without degradation (REQ-P03)

## Security Validation

- Validate all file uploads for malicious content (REQ-S01)
- Enforce strict content-type validation for uploaded deck files (REQ-S02)
- Implement rate-limiting for file upload endpoints (REQ-S03)

## User Interface & Experience

- Import workflow includes: file selection → format validation → preview → confirmation (REQ-U01)
- Clear error messages for invalid deck formats (REQ-U02)
- Progress indicators for large file uploads (REQ-U03)

## Error Code Alignment

- Map all error responses to specific requirement numbers in `requirements.md`:
  - 400: Invalid deck format → REQ-D01
  - 403: File upload rejected → REQ-S02
  - 500: Internal rule engine error → REQ-R01

## Test Coverage

- Integration tests for edge cases:
  - Invalid file formats (REQ-T01)
  - Large file uploads (>10MB) (REQ-T02)
  - Concurrent imports (REQ-T03)
  - Malformed JSON in deck files (REQ-T04)

## Out of Scope (v1)

- Multiplayer (more than 2 players)
- Commander-specific rules (commander tax, command zone, partner)
- Ante rules
- Subgames (Shahrazad)
- Silver-bordered / acorn cards
- Digital-only mechanics (perpetually, conjure, etc.)
- Draft or sealed deck simulation
- GUI or human-facing interface

## Architecture Overview

```
AI Agent (LLM / bot)
        |
        | HTTP REST
        v
 ┌─────────────────┐
 │   FastAPI App   │  ← game router, data export router
 └────────┬────────┘
          |
 ┌────────▼────────┐     ┌─────────────────┐
 │  GameEngine     │────▶│  RulesEngine    │  ← CR 613 layers,
 │  (state mgr)   │     │  (legality &    │     SBAs, stack,
 └────────┬────────┘     │   resolution)   │     replacement fx
          |              └─────────────────┘
 ┌────────▼────────┐     ┌─────────────────┐
 │  CardResolver   │────▶│  ScryfallClient │  ← oracle text,
 │  (ability parse)│     │  (card data)    │     type line, etc.
 └────────┬────────┘     └─────────────────┘
          |
 ┌────────▼────────┐
 │  DataExporter   │────▶ MongoDB (training data)
 └─────────────────┘
```

## Key Constraints

- Python 3.11+
- FastAPI for the REST layer
- Pydantic v2 for all game state models (enables clean JSON serialization)
- Must be runnable with `uvicorn` on localhost, no Docker required
- Card ability parsing must be data-driven (oracle text → effect objects),
  not a giant if/else tree of card names
- All game state must be fully serializable to JSON at any point
- Engine must be deterministic given a fixed random seed (for replay)

## Non-Goals

- The engine does not decide what action an AI should take — it only
  enforces legality, resolves actions, and reports state. Strategy is
  entirely the AI agent's responsibility.
- The engine does not train models — it generates data consumed by the
  existing training pipeline.

---

## Bug Fix Log

### 2026-03-22 — AI self-play correctness fixes

**BUG-01: Basic land mana abilities not parsed**
- **File**: `mtg_engine/card_data/ability_parser.py`
- **Root cause**: Basic lands store their mana ability wrapped in parentheses
  (`({T}: Add {W}.)`) as reminder text. `_parse_segment` did not strip the
  outer parens before attempting to match the `cost: effect` pattern, so all
  five basic lands produced `UnparsedAbility` and never appeared in legal
  `activate` actions.
- **Effect**: AI players could not tap basic lands for mana. Mana pool stayed
  empty all game. No spells were ever offered as castable. Games ended by
  max-turns with zero meaningful actions taken.
- **Fix**: Strip leading/trailing parentheses from a segment before parsing.

**BUG-02: Mana payment serialised as string instead of dict**
- **File**: `ai_client/game_loop.py`
- **Root cause**: `_map_action_to_request` extracted `mana_cost` from the
  legal-action payload (a string such as `"{1}{G}"`) and passed it directly
  as `mana_payment`. `CastRequest.mana_payment` is typed `dict[str, int]`;
  Pydantic coerced the string to an empty dict, causing every cast attempt
  to fail mana validation with a 422.
- **Effect**: AI could never successfully cast a spell even after tapping mana.
- **Fix**: Added `_parse_mana_cost_to_payment(mana_cost, pool)` which parses
  mana symbols into `{"G": 1, "W": 1, ...}` using the player's current pool
  to cover generic costs.

**BUG-03: Engine offered useless mana-tap actions**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`)
- **Root cause**: Mana-producing `activate` actions were included in legal
  actions regardless of whether any spell in hand could be paid for with the
  produced mana. The AI would tap a Plains for `{W}` when its hand contained
  only green spells, wasting the mana (which drains at end of step).
- **Effect**: AI appeared to "play randomly" — tapping lands for no reason,
  burning mana, passing with nothing cast.
- **Fix**: For pure mana abilities (`Add {X}`), simulate adding the mana to
  the pool and check `_any_spell_castable(pool_after)`. Only include the
  action if at least one spell becomes payable.

**BUG-04: Default AI client deck had wrong colour identity**
- **File**: `ai_client/prompts.py`
- **Root cause**: `DEFAULT_DECK` contained 24 Plains (produces `{W}`) and
  8 Forests (`{G}`), but all spells required `{G}`, `{R}`, or `{U}{U}`.
  Lightning Bolt and Counterspell could never be cast (no red or blue sources).
- **Effect**: Games stalled immediately; both players passed every priority.
- **Fix**: Replaced with a 60-card mono-green deck (24 Forest + 9×4 green
  creatures/spells) where every spell is castable with Forest mana.

**BUG-05: `useTranscript` hook did not unwrap API envelope**
- **File**: `frontend/src/hooks/useTranscript.ts`
- **Root cause**: `GET /export/{id}/transcript` returns `{"data": [...]}` but
  the hook treated the whole response as an array and called `.filter()` on
  it, throwing `TypeError: r.data.filter is not a function` and crashing the
  GameBoard component on mount.
- **Effect**: Selecting any game in the observer UI caused an immediate blank
  screen.
- **Fix**: Unwrap `json.data` before returning from the query function.

**BUG-07: Engine offered redundant mana-tap actions causing over-tapping**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`)
- **Root cause**: BUG-03's fix only checked whether tapping *any* land would enable *any*
  spell, but did not check whether the current pool already enables spells. Once a player
  had tapped one Forest (pool=G:1) to cast a `{G}` spell, additional Forests remained in
  the legal actions because "pool_after(G:2) enables the spell" was still true. The AI
  would tap all its lands before casting, floating wasted mana.
- **Effect**: AI visibly over-tapped (tapping 3+ lands for a 1-mana spell).
- **Fix**: Replaced the single-tap check with a two-level filter: (1) if the current pool
  already casts everything reachable by tapping all available sources, no taps are offered;
  (2) if a single tap enables new spells beyond the current pool, it is offered; (3) if a
  single tap alone is insufficient but the combined available mana eventually reaches a
  spell, it is offered (handles multi-tap cases like `{1}{G}` needing two Forests).

**BUG-11: Targeted spells offered when no valid target exists**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`)
- **Root cause**: The cast action section offered every payable spell without checking
  whether required targets existed. Spells like Giant Growth ("target creature gets
  +3/+3") and Rancor (an Aura that must enchant a creature) were offered with
  `valid_targets=[]` even when the battlefield had no creatures. The AI would cast
  them sorcery-main-phase, spending mana on a spell that had no effect.
- **Effect**: On Turn 1, AI tapped a land and cast Giant Growth or Rancor with no
  creatures on the field, wasting the mana. No creatures were ever played and the game
  stalled as both players ran out of action-enabling mana early.
- **Fix**: Added `_has_required_targets(card)` check. Cards with "target creature" in
  oracle text or "enchant creature" in oracle/type are suppressed when no creatures
  exist on the battlefield. Full target validation (opponent vs own, protection, etc.)
  is deferred; this handles the common targetless-cast case.

**BUG-10: Creatures with summoning sickness could tap for mana (CR 302.6 violation)**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`)
- **Root cause**: The tap-cost check only blocked activation when `perm.tapped`, not when a
  creature had summoning sickness. CR 302.6 prohibits activating a creature's `{T}` ability
  unless the creature has been under its controller's control since the start of their most
  recent turn. Non-creature permanents (lands, artifacts) are unaffected by this rule.
- **Effect**: AI would cast a mana dork (e.g. Llanowar Elves) and immediately tap it for
  mana the same turn. The dork would be tapped when combat arrived, producing "no untapped
  creatures to attack with" — a wasted turn of attacking. `_total_available_pool` also
  over-counted available mana by including summoning-sick creatures.
- **Fix**: Changed the tap guard to `perm.tapped or (is_creature and perm.summoning_sick)`.
  Added matching guard in `_total_available_pool` to skip summoning-sick creatures.
  Non-creature permanents (lands) still tap freely regardless of summoning-sick flag.

**BUG-08: Engine offered legal actions during untap step**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`)
- **Root cause**: `advance_step` correctly skips setting `priority_holder` during untap
  (CR 502.4: no priority is granted in the untap step), but `_advance_turn` sets
  `priority_holder` before entering the new turn's untap step. The game loop would
  poll `GET /game/{id}/legal_actions` and receive a full action list — including mana
  taps — during untap. The AI would tap forests for mana; mana drained at the end of
  untap; creatures tapped for mana couldn't attack in the subsequent combat step.
- **Effect**: AI tapped creatures/lands for mana during untap, wasting the mana and
  leaving creatures unable to attack, producing "no untapped creatures" log messages.
- **Fix**: Added early return in `_compute_legal_actions` when `gs.step == Step.UNTAP`,
  returning only `[pass]`. The AI passes immediately and the game advances to upkeep.

**BUG-09: Mana-tap filter counted sorcery-speed spells as castable during non-main phases**
- **File**: `mtg_engine/api/routers/game.py` (`_compute_legal_actions`, `_castable_count`)
- **Root cause**: `_castable_count` counted all non-land cards in hand that were
  mana-payable, without checking whether those cards could legally be cast at the
  current phase/step. During upkeep or draw, sorcery-speed creatures registered as
  "castable" for the mana filter's purposes, so Forest taps were offered. The AI
  tapped lands during upkeep, the mana drained at end of upkeep, and no spells were cast.
- **Effect**: AI tapped mana sources during upkeep/draw/combat when hand contained only
  sorcery-speed spells, burning mana every turn with no spells cast.
- **Fix**: Added a timing guard to `_castable_count`: a card only counts if it is either
  instant-speed (`not _is_sorcery_speed(card)`) or sorcery-speed-timing is currently
  available (`_can_cast_at_sorcery_speed(gs, player_name)`).

**BUG-06: No unit tests for `_compute_legal_actions`**
- **File**: `tests/rules/test_legal_actions.py` (new)
- **Root cause**: The legal-actions function had only integration-level bot
  tests that checked for 500 errors, not correctness. All five basic land
  types, sorcery-speed timing, split-second, mana filtering, commander tax,
  and flash were untested at the unit level.
- **Fix**: Added 76 unit tests across 7 classes covering every action type in
  both standard and commander formats (inclusion and exclusion cases).

---

## 2026-04-24 — Human Game Fixes

**BUG-12: Human turn phases auto-skipping**
- **Files**: `mtg_engine/engine/turn_manager.py`, `mtg_engine/api/routers/game.py`, `ai_client/game_loop.py`
- **Root cause**: Auto-pass and stuck detection loops ran for all players, including humans. Also phase-skip logic skipped phases when only pass was available.
- **Effect**: Human player's phases auto-advanced without their input.
- **Fix**: Added human player checks to:
  - `can_skip_phase()` - returns False when human_player_name is set
  - `_should_auto_pass()` - returns False for human player
  - Auto-pass loop in game.py - breaks when human has priority
  - Stuck detection in game_loop.py - skips for human player

**BUG-13: No pass action available in UI**
- **File**: `mtg_engine/api/routers/game.py`
- **Root cause**: Pass action was only added in certain early-return cases, not universally.
- **Effect**: Human player couldn't pass priority.
- **Fix**: Added pass action at end of every code path in `_compute_legal_actions()`.

**BUG-14: Token creation with prowess/multi-color not working**
- **File**: `mtg_engine/engine/stack.py`
- **Root cause**: Token creation with "with prowess" or "blue and red" patterns weren't matched, and stub functions existed.
- **Effect**: Stormchaser's Talent ETB created no token.
- **Fix**: Added regex patterns and implemented token creation functions.

**BUG-15: ETB choice not detected for shocklands**
- **File**: `mtg_engine/engine/zones.py`
- **Root cause**: Regex pattern was too strict: `it enters tapped` vs `it enters tapped.` (with period).
- **Fix**: Changed to greedy match: `r"as .*? enters.*? you may pay (\d+) life.*?enters tapped"`

**BUG-16: Duress-type discard effects not working**
- **File**: `mtg_engine/engine/stack.py`, `frontend/src/components/HumanGameBoard.tsx`
- **Root cause**: Fizzle check in `resolve_top()` only validated targets against battlefield/players/stack, not hands/graveyards. Duress targeting a hand card failed validation, spell fizzled to graveyard without queuing `pending_discard_choice`.
- **Effect**: Casting Duress resolved without showing opponent's hand or letting player choose.
- **Fix**: Updated fizzle check to include hand cards and graveyard cards in target validation (lines 516-517). Fizzle now correctly identifies hand-targeting spell targets.
- **Tests**: Added `tests/rules/test_duress_fizzle.py` with 4 tests (all passing). Full test suite: 605 passed, 1 pre-existing failure unrelated.

**BUG-17: Optional discard from own hand (e.g., Abandon Attachments)**
- **Files**: `mtg_engine/engine/stack.py`, `mtg_engine/api/routers/game.py`, `frontend/src/components/ChoiceModal.tsx`
- **Root cause**: "You may discard" spells resolved immediately without choice.
- **Effect**: Cards like Abandon Attachments resolved without letting player choose.
- **Fix**: Queue choice instead of resolving immediately. Two options:
  - Choose to discard → discard card, draw X cards  
  - Choose not to discard → spell goes to graveyard, no cards drawn

**Pattern Examples**:
- "You may discard a card. If you do, draw two cards."
- "You may discard a card."
- "Target opponent reveals their hand..."

**BUG-18: Mana cost parsing issue**
- **File**: `mtg_engine/engine/mana.py`
- **Root cause**: `{2}{U}` being parsed incorrectly
- **Effect**: Cards costing {2}{U} incorrectly require red mana
- **Status**: Unable to reproduce - mana parsing appears correct. Need more context to verify.

**BUG-19: Winternight Stories effect not resolving**
- **Files**: `mtg_engine/engine/stack.py`, `mtg_engine/api/routers/game.py`
- **Root cause**: Card has complex multi-part effect not handled
- **Card text**: "Draw three cards. Then discard two cards unless you discard a creature card."
- **Effect**: Spell resolves to graveyard without effect
- **Status**: Fixed (draws 3, queues conditional discard, handles creature check)

**BUG-20: Harmonize not supported**
- **Files**: `mtg_engine/api/routers/game.py`
- **Root cause**: "harmonize" keyword not in graveyard cast keywords
- **Effect**: Cannot cast cards with harmonize from graveyard
- **Status**: Fixed (added harmonize to _GRAVEYARD_CAST_KW)

**BUG-21: Sleight of Hand effect not resolving**
- **Files**: `mtg_engine/engine/stack.py`, `mtg_engine/api/routers/game.py`, `frontend/.../HumanGameBoard.tsx`, `ai_client/...`
- **Root cause**: Card has "look at top N, put one in hand" pattern not handled
- **Card text**: "Look at the top two cards of your library. Put one of them into your hand and the other on the bottom of your library."
- **Effect**: Spell resolves to graveyard without effect
- **Status**: Fixed (added reveal_and_choose pattern, effect_type flag, all 3 player types)

**BUG-22: Empty mana_payment causes cast failure**
- **Files**: `mtg_engine/engine/stack.py`
- **Root cause**: Bot/AI sends empty `mana_payment={}` but backend requires payment dict
- **Effect**: Cards cannot be cast, "Insufficient mana to cast" error
- **Status**: Fixed (auto-calculate payment if not provided)

**BUG-23: Landfall triggers not firing**
- **Files**: `mtg_engine/card_data/ability_parser.py`, `mtg_engine/engine/triggers.py`, `mtg_engine/engine/stack.py`
- **Root cause**: Landfall keyword not detected, trigger matching incomplete, counter effect not self-targeted
- **Effect**: Landfall abilities like Sazh's Chocobo don't trigger when land enters
- **Status**: Fixed (added landfall detection, trigger patterns, self-target counter)

**BUG-24: Shockland ETB choice UnboundLocalError**
- **Files**: `mtg_engine/api/routers/game.py`
- **Root cause**: `get_player` not accessible in choice handler
- **Effect**: 500 error on ETB choice resolution
- **Status**: Fixed (added local import in etb_pay handler)

**BUG-25: Stock Up / multi-card reveal effect not resolving**
- **Files**: `mtg_engine/engine/stack.py`, `mtg_engine/api/routers/game.py`, `ai_client/...`
- **Root cause**: Card has "look at top N, put M into hand" pattern not handled
- **Card text**: "Look at the top five cards of your library. Put two of them into your hand and the rest on the bottom..."
- **Effect**: Spell resolves to graveyard without effect
- **Status**: Fixed (added reveal_and_choose_multi pattern, all player types)

**BUG-26: Spree mechanic not implemented**
- **Files**: `mtg_engine/api/routers/game.py`, `mtg_engine/engine/stack.py`, `mtg_engine/models/game.py`, `ai_client/...`
- **Card**: Insatiable Avarice
- **Root cause**: Spree keyword allows choosing additional costs (+ {2}, + {B}{B})
- **Card text**: "Spree (Choose one or more additional costs.) + {2} — Search... + {B}{B} — Target player draws..."
- **Effect**: Card resolves without mode selection, no effect applied
- **Status**: Partial (Spree detection, choice queued, mode selection works, effect resolution incomplete)
