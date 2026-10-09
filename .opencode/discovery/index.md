# Discovery Index

## Game Mechanics (Completed)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Commander Rules (CR 903) — CMD-01 | story-gm-commander.md | High | none | ✅ |
| 2 | Monarch (CR 702.147) — MON-01 | story-gm-monarch.md | High | none | ✅ |
| 3 | Venture/Dungeon (CR 701.61) — VEN-01 | story-gm-venture.md | High | Initiative | ✅ |
| 4 | Proliferate (CR 702.39) — PRO-01 | story-gm-proliferate.md | High | none | ✅ |
| 5 | Day/Night Cycle (CR 702.148) — DNG-01 | story-gm-day-night.md | High | none | ✅ |
| 6 | Initiative (CR 702.148) — INT-01 | story-gm-initiative.md | High | Venture/Dungeon | ✅ |
| 7 | Companion (CR 903.5) — COM-01 | story-gm-companion.md | High | Commander Rules | ✅ |
| 8 | MDFC / Transform (CR 711) | story-gm-mdfc.md | High | Day/Night Cycle | ✅ |

## API Features (Completed)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Card Search API (APP-01) | story-api-card-search.md | High | none | ✅ |
| 2 | Deck Building AI (APP-02) | story-api-deck-build.md | High | FMT-01 | ✅ |
| 3 | Game Replay (APP-03) | story-api-replay.md | Medium | none | ✅ |
| 4 | Spectate WebSocket (APP-04) | story-api-spectate.md | Medium | none | ✅ |
| 5 | Draft/Sealed Simulation (APP-05) | story-api-draft-sealed.md | Medium | Deck Building AI | ✅ |
| 6 | Player Stats / ELO (APP-06) | story-api-player-stats.md | Low | MongoDB | ✅ |

---

## Turn Structure (CR 500-514)

Core turn structure phases, steps, and game flow rules. These represent fundamental MTG game engine infrastructure.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Beginning Phase (CR 500.1) | story-turn-beginning-phase.md | High | none | 📋 |
| 2 | Untap Step (CR 502) | story-turn-untap-step.md | High | #1 | 📋 |
| 3 | Upkeep Step (CR 503) | story-turn-upkeep-step.md | High | #2 | 📋 |
| 4 | Draw Step (CR 504) | story-turn-draw-step.md | High | #3 | 📋 |
| 5 | Main Phase (CR 505) | story-turn-main-phase.md | High | #4 | 📋 |
| 6 | Combat Phase (CR 506) | story-turn-combat-phase.md | High | #5 | 📋 |
| 7 | Declare Attackers Step (CR 508) | story-turn-declare-attackers.md | High | #6 | 📋 |
| 8 | Declare Blockers Step (CR 509) | story-turn-declare-blockers.md | High | #7 | 📋 |
| 9 | First Strike / Double Strike Damage (CR 510.4) | story-turn-first-strike-damage.md | High | #8 | 📋 |
| 10 | Combat Damage Step (CR 510) | story-turn-combat-damage.md | High | #9 | 📋 |
| 11 | End of Combat Step (CR 511) | story-turn-end-of-combat.md | High | #10 | 📋 |
| 12 | Ending Phase (CR 512) | story-turn-ending-phase.md | High | #5, #11 | 📋 |
| 13 | End Step (CR 513) | story-turn-end-step.md | High | #12 | 📋 |
| 14 | Cleanup Step (CR 514) | story-turn-cleanup-step.md | High | #13 | 📋 |
| 15 | Priority System (CR 117) | story-turn-priority-system.md | High | all step stories | 📋 |
| 16 | Mana Pool / Mana Burn (CR 106, 118) | story-turn-mana-pool.md | High | #15 | 📋 |
| 17 | Maximum Hand Size (CR 402.2) | story-turn-max-hand-size.md | High | #14 | 📋 |
| 18 | Mulligan Rules (CR 103.4) | story-turn-mulligan.md | High | none | 📋 |
| 19 | Conceding / Drawing the Game (CR 104) | story-turn-concede-draw.md | High | none | 📋 |

---

## Game Actions (CR 116, 305, 502, 601-602, 701-707, 711, 715)

Core game actions that players and the engine execute during gameplay. These actions form the fundamental operations of the Magic game engine.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Casting a Spell (CR 601) | story-action-cast-spell.md | High | Turn Structure | 📋 |
| 2 | Activating an Ability (CR 602) | story-action-activate-ability.md | High | Turn Structure | 📋 |
| 3 | Playing a Land (CR 305) | story-action-play-land.md | High | Special Actions | 📋 |
| 4 | Turning a Card Face Up (CR 701.27) | story-action-turn-face-up.md | High | Special Actions, Morph | 📋 |
| 5 | Exert (CR 701.26) | story-action-exert.md | High | Declare Attackers | 📋 |
| 6 | Investigate (CR 701.32) | story-action-investigate.md | High | Token Rules | 📋 |
| 7 | Surveil (CR 701.41) | story-action-surveil.md | High | Library Ops | 📋 |
| 8 | Venture into the Dungeon (CR 701.61) | story-action-venture.md | High | story-gm-venture.md | 📋 |
| 9 | Proliferate (CR 702.39) | story-action-proliferate.md | High | story-gm-proliferate.md | 📋 |
| 10 | Scry (CR 701.20) | story-action-scry.md | High | story-kw-scry.md | 📋 |
| 11 | Mill (CR 701.14) | story-action-mill.md | High | Zone Management | 📋 |
| 12 | Fight (CR 701.6) | story-action-fight.md | High | Damage System | 📋 |
| 13 | Clash (CR 701.23) | story-action-clash.md | Medium | Library Ops | 📋 |
| 14 | Regenerate (CR 701.15) | story-action-regenerate.md | Medium | Replacement Effects | 📋 |
| 15 | Learn (CR 701.42) | story-action-learn.md | Medium | Sideboard, Draw | 📋 |
| 16 | Boast (CR 702.XX) | story-action-boast.md | Medium | Activated Abilities | 📋 |
| 17 | Foretell (CR 702.XX) | story-action-foretell.md | Medium | Special Actions | 📋 |
| 18 | Plot (CR 702.XX) | story-action-plot.md | Medium | Special Actions | 📋 |
| 19 | Suspend (CR 702.62) | story-action-suspend.md | High | story-kw-suspend.md | 📋 |
| 20 | Encore (CR 702.XX) | story-action-encore.md | Medium | Token Rules, Haste | 📋 |
| 21 | Embalm / Eternalize (CR 702.XX) | story-action-embalm-eternalize.md | Medium | Graveyard, Tokens | 📋 |
| 22 | Companion (CR 903.5) | story-action-companion.md | Medium | story-gm-companion.md | 📋 |
| 23 | Adventure (CR 715) | story-action-adventure.md | High | MDFC, Exile | 📋 |
| 24 | Transform / MDFC (CR 711) | story-action-transform-mdfc.md | High | story-gm-mdfc.md | 📋 |
| 25 | Modal Double-Faced Cards (CR 711) | story-action-modal-dfc.md | High | story-gm-mdfc.md | 📋 |
| 26 | Day/Night Bound (CR 702.148) | story-action-day-night.md | High | story-gm-day-night.md | 📋 |
| 27 | Perpetual Effects (CR 702.XX) | story-action-perpetual.md | Low | Layer System | 📋 |
| 28 | Conjure (CR 702.XX) | story-action-conjure.md | Low | Card Creation | 📋 |
| 29 | Seek (CR 702.XX) | story-action-seek.md | Low | Library Ops | 📋 |
| 30 | Spell Copy Rules (CR 706) | story-action-spell-copy.md | High | story-rule-copy-effects.md | 📋 |
| 31 | Split Second (CR 702.61) | story-action-split-second.md | Medium | story-rule-split-second.md | 📋 |
| 32 | Kicker / Multi-kicker (CR 702.33) | story-action-kicker.md | High | story-kw-kicker.md | 📋 |
| 33 | Companions / Commanders from Sideboard (CR 903.5) | story-action-companion-commander-sideboard.md | Medium | Companion, Commander | 📋 |
| 34 | Special Actions (CR 116) | story-action-special-actions.md | High | All Special Action stories | 📋 |
| 35 | Extra Turns (CR 502.3) | story-action-extra-turns.md | Medium | Turn Structure | 📋 |
| 36 | Flipping a Coin (CR 701.24) | story-action-flip-coin.md | Medium | RNG, Replacement Effects | 📋 |
| 37 | Rolling a Die (CR 701.25) | story-action-roll-die.md | Medium | RNG, Replacement Effects | 📋 |
| 38 | Voting (CR 701.23) | story-action-voting.md | Medium | Turn Order | 📋 |
| 39 | Planar Die (CR 901.5) | story-action-planar-die.md | Low | Die Roll, Planechase | 📋 |
| 40 | Subgames (CR 716) | story-action-subgames.md | Low | Full Engine | 📋 |
| 41 | Ante (CR 707) | story-action-ante.md | Low | Zone Management | 📋 |

---

## Sprint 4: Format Validation

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Format Rules Engine (FMT-01) | FMT-01-story.md | High | none | ✅ |

## Sprint 5: Application Features

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Card Search API (APP-01) | story-app01-card-search.md | High | none | ✅ |
| 2 | Deck Building AI (APP-02) | story-app02-deck-building-ai.md | High | FMT-01 ✅ | ✅ |
| 3 | Game Replay (APP-03) | story-app03-game-replay.md | Medium | none | ✅ |
| 4 | Spectate / WebSocket (APP-04) | story-app04-spectate-websocket.md | Medium | none | ✅ |
| 5 | Draft / Sealed Simulation (APP-05) | story-app05-draft-sealed.md | Medium | APP-02 ✅ | ✅ |
| 6 | Player Stats / ELO (APP-06) | story-app06-player-stats.md | Low | none | ✅ |

## Sprint 6: Keyword Ability Grounding & Expansion

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | CR Reference + Spec Template (SA-05) | — | High | none | ✅ |
| 2 | Retroactive Specs: 13 fully-implemented keywords | KW-INDEX.md | High | SA-05 ✅ | ✅ |
| 3 | Stub Modules: P0 combat modifiers (Deathtouch, Lifelink, Infect) | KW-INDEX.md | High | Phase 2 ✅ | ✅ |
| 4 | Stub Modules: P1 death triggers (Afterlife, Undying, Persist, Sunburst) | see below | Medium | Phase 3 ✅ | 🔄 decomposed |

### Sprint 6.4: P1 Death Triggers (decomposed from Story #4)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 4a | Afterlife death trigger (CR 702.108) | story-kw04-afterlife.md | High | none | ✅ |
| 4b | Undying death trigger (CR 702.51) + zones.py refactor | story-kw04-undying.md | High | none | ✅ |
| 4c | Persist death trigger (CR 702.61) + zones.py refactor | story-kw04-persist.md | High | none | ✅ |
| 4d | Sunburst ETB counter effect (CR 702.103) | story-kw04-sunburst.md | Medium | none | ✅ |

---

## Completed Keywords (Individual Story Files)

Each keyword with a real `apply()` implementation using pure `model_copy` transforms and integration tests.

| # | Story | File | Priority | Status |
|---|-------|------|----------|--------|
| 1 | Deathtouch (CR 702.2) | story-kw-deathtouch.md | High | ✅ |
| 2 | Lifelink (CR 702.15) | story-kw-lifelink.md | High | ✅ |
| 3 | Infect (CR 702.90) | story-kw-infect.md | High | ✅ |
| 4 | Kicker (CR 702.33) | story-kw-kicker.md | Medium | ✅ |
| 5 | Flashback (CR 702.34) | story-kw-flashback.md | Medium | ✅ |
| 6 | Escape (CR 702.45) | story-kw-escape.md | Medium | ✅ |
| 7 | Delve (CR 702.86) | story-kw-delve.md | Medium | ✅ |
| 8 | Madness (CR 702.35) | story-kw-madness.md | Medium | ✅ |
| 9 | Dredge (CR 702.60) | story-kw-dredge.md | Medium | ✅ |
| 10 | Ninjutsu (CR 702.61) | story-kw-ninjutsu.md | Medium | ✅ |
| 11 | Dash (CR 702.138) | story-kw-dash.md | Medium | ✅ |
| 12 | Reach (CR 702.17) | story-kw-reach.md | Medium | ✅ |
| 13 | Hexproof (CR 702.11) | story-kw-hexproof.md | Medium | ✅ |
| 14 | Shroud (CR 702.18) | story-kw-shroud.md | Medium | ✅ |
| 15 | Menace (CR 702.111) | story-kw-menace.md | Medium | ✅ |
| 16 | Afterlife (CR 702.108) | story-kw04-afterlife.md | High | ✅ |
| 17 | Undying (CR 702.51) | story-kw04-undying.md | High | ✅ |
| 18 | Persist (CR 702.61) | story-kw04-persist.md | High | ✅ |
| 19 | Sunburst (CR 702.103) | story-kw04-sunburst.md | Medium | ✅ |
| 20 | Storm (CR 702.40) | story-kw-storm.md | Medium | ✅ |
| 21 | Cascade (CR 702.85) | story-kw-cascade.md | Medium | ✅ |

---

## Sprint 7: Keyword Module Architecture Consolidation & Forge Parity

### Gap Analysis Reference
See **[FORGE-GAP-ANALYSIS.md](FORGE-GAP-ANALYSIS.md)** for the complete comparison of our 49 keyword files against Forge's 201 keywords, and our 32 trigger patterns against Forge's ~140 trigger types.

**Key findings:**
- **Keywords**: 21 real implementations, 28 stubs (NOOP apply), ~25+ completely missing
- **Triggers**: 32 categories defined, ~18 wired into engine, ~13 dead code (check fn exists but not called), ~95 completely missing

### P0: Architecture Wiring (existing story)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-1 | Wire trigger-based keyword modules to use their own apply() methods (Afterlife, Undying, Persist, Evoke, Morph, Suspend) | SPRINT7-P0-keyword-wiring.md | High | none | ✅ |

### P0: Trigger Wiring — Dead Code → Working Features (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-2 | Wire 13 dead-code trigger check functions into engine event flow (sacrifice, life_gain_lost, fight, transformed, tutor, becomes_target, attach, mana_spent, draw, discard, token, counter, mana_production) | SPRINT7-P0-trigger-wiring.md | High | none | ✅ |

#### P0.1: Dead-Code Trigger Wiring (decomposed from #7-2)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-2a | Sacrifice (CR 701.19) | story-trg-sacrifice.md | High | none | ✅ |
| 7-2b | Life Gain/Lost (CR 701.12/701.13) | story-trg-life-gain-lost.md | High | none | ✅ |
| 7-2c | Fight (CR 701.6) | story-trg-fight.md | High | none | ✅ |
| 7-2d | Transformed (CR 711.3) | story-trg-transformed.md | High | none | ✅ |
| 7-2e | Tutor/Search Library (CR 400.8/400.9) | story-trg-tutor.md | High | none | ✅ |
| 7-2f | Becomes Target (CR 109.3) | story-trg-becomes-target.md | High | none | ✅ |
| 7-2g | Attach (CR 702.5/702.54a) | story-trg-attach.md | High | none | ✅ |
| 7-2h | Mana Spent (CR 118.9) | story-trg-mana-spent.md | High | none | ✅ |
| 7-2i | Draw (CR 701.16) | story-trg-draw.md | High | none | ✅ |
| 7-2j | Discard (CR 701.18) | story-trg-discard.md | High | none | ✅ |
| 7-2k | Token Created (CR 110.5/110.6) | story-trg-token-created.md | High | none | ✅ |
| 7-2l | Counter Placed (CR 122.1) | story-trg-counter-placed.md | High | none | ✅ |
| 7-2m | Mana Production (CR 502.4) | story-trg-mana-production.md | High | none | ✅ |

### P0: Missing Triggers — Countered + Investigated (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-3 | Countered and Investigated trigger patterns with regex, check functions, engine wiring | SPRINT7-P0-missing-triggers.md | High | none | ✅ (shipped 2026-08-20; plan → plans/SPRINT7-P0-missing-triggers-plan.md) |

### P1: Trigger Fidelity Follow-ups (NEW — from 7-2 code review, 2026-08-19)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-17 | Trigger fidelity minors: CR 903.9 sacrifice redirect, unattach call site (pre-removal controller capture), per-token trigger firing (CR 110.6), sacrifice "you control" negative test, cycling/Fading-route integration tests | SPRINT7-P1-trigger-fidelity-minors.md | Medium | 7-2 ✅, 7-3 ✅ | ✅ shipped 2026-08-27 — full suite 2919 passed / 0 failed / 3 skipped / 13 xfailed (baseline 2816 post-7-3 → 2907 after Fortify P0 → +12 net from 7-17). Code Review r2 APPROVED after Item-2 integration test fix. |

### P0: Fortify Keyword Module (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-4 | Fortify keyword module (CR 702.54a) — most common missing mechanic | SPRINT7-P0-fortify-keyword.md | High | none | ✅ shipped 2026-08-26 (rule text adjudicated 2026-08-25: attach-to-land, not counters; plan → plans/SPRINT7-P0-fortify-keyword-plan.md); full suite 2907 passed / 0 failed / 3 skipped / 13 xfailed (baseline 2816 + 91 new Fortify tests) |

### P0: Stub Keywords — Common Mechanics (6 keywords, existing story)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-5 | Crew, Equip, Cycle/Cycling, Scry, Ward, Toxic real apply() + tests | SPRINT7-P0-stub-keywords-common.md | High | none | ✅ shipped 2026-08-31 — All six P0 stub keywords implemented + tested (Crew, Equip, Cycle/Cycling, Scry, Ward, Toxic); suite grew 2919→3046. |

#### P0.1: Crew (decomposed from #7-5)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-5a | Crew (CR 702.147) | story-kw-crew.md | High | none | ✅ shipped 2026-08-29 — Crew module implemented, suite 2942/0/3/13 (+23 net from 7-17 baseline). Part of umbrella Story 7-5. |
| 7-5b | Equip (CR 702.6) | story-kw-equip.md | High | none | ✅ shipped 2026-08-29 — Equip module implemented: apply() replaced prior no-op (Equip(CostKeyword) with has_equip/parse_equip_cost/parse_equip_bonus, sorcery-speed gate, _eligible_creatures); pure-transform apply() (human queues pending_equip_choice with eligible list, AI auto-resolves to first valid creature if affordable) + _apply_equip_bonus/clear_equip_bonus; added GameState field pending_equip_choice (models/game.py:460); wired stack.py:_apply_equip (line 1585) + equip_confirm choice handler (line 1976) + legal-action branch (line 2466) in game.py; 32 tests in tests/engine/test_equip_integration.py; suite 2974/0/3/13 (+32 net from Crew baseline). Part of umbrella Story 7-5. |
| 7-5c | Cycle/Cycling (CR 702.36 + 702.46) | story-kw-cycle.md | High | none | ✅ shipped 2026-08-31 — Cycling module implemented for regular cycling (CR 702.36) and type-cycling (CR 702.46); latent NameError bug fixed in both apply() methods; live /cycle route unified to cycle.py single source of truth; suite 2991/0/3/13 (+17 net from Equip baseline). Part of umbrella Story 7-5. |
| 7-5d | Scry (CR 701.20) | story-kw-scry.md | High | none | ✅ shipped 2026-08-31 — Scry module implemented: apply() replaced NOOP stub; human queues pending_scri_choice with effect_type reorder marker (field at models/game.py:350 already existed), AI reorders revealed top-N cards via model_copy heuristic (high-CMC non-lands surfaced, lands buried); added "scry" choice handler + legal-action branch in game.py; 22 tests; suite 3013/0/3/13 (+22 net from Cycle baseline). Part of umbrella Story 7-5. |
| 7-5e | Ward (CR 702.145) | story-kw-ward.md | High | none | ✅ shipped 2026-08-31 — Ward module implemented as a triggered ability firing via stack.py cast_spell becomes-target flow; ward_pay/ward_counter choice handlers + mandatory-counter legal actions in game.py (no pass bypass); CR 702.145b self-targeting bypass + multiple-wards-independent; Q4 pure-transform fix to the AI-counter graveyard path; 18 tests (13 engine + 5 API); suite 3031/0/3/13. Part of umbrella Story 7-5. |
| 7-5f | Toxic (CR 702.134) | story-kw-toxic.md | High | none | ✅ shipped 2026-08-31 — Toxic module implemented: apply_toxic refactored from in-place mutation to pure transform (player.model_copy on poison_counters + players-list rebuild, no in-place +=); wired into combat/core.py assign_combat_damage "Target is a player" branch (guard: toxic keyword + damage > 0); fires once per combat damage event (not per point), non-combat damage does NOT trigger; 10+ poison = loss handled by EXISTING SBA (sba.py ~94-98, CR 704.5c) not re-implemented; 15 new integration tests + 4 updated unit tests; suite 3046/0/3/13 (+15 net from Ward baseline). Part of umbrella Story 7-5 — FINAL keyword, umbrella complete. |

### P1: Stub Keywords — Alternative Casting Costs (6 keywords, existing story)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-6 | Buyback, Entwine, Overload, Miracle, Bloodthirst, Convoke real apply() + tests | SPRINT7-P1-stub-keywords-casting.md | Medium | none | ✅ shipped 2026-09-02 — All six alternative-casting-cost keywords implemented + tested; suite grew 3139→3167. |

#### P1.1: Alternative Casting Costs (decomposed from #7-6)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-6a | Buyback (CR 702.27) | story-kw-buyback.md | Medium | none | ⏳ |
| 7-6b | Entwine (CR 702.41) | story-kw-entwine.md | Medium | none | ⏳ |
| 7-6c | Overload (CR 702.95) | story-kw-overload.md | Medium | none | ⏳ |
| 7-6d | Miracle (CR 702.93) | story-kw-miracle.md | Medium | none | ⏳ |
| 7-6e | Bloodthirst (CR 702.22) | story-kw-bloodthirst.md | Medium | none | ✅ shipped 2026-09-02 — Bloodthirst module implemented: real apply() replacing NOOP; damage tracking via damage_dealt_this_turn (combat + non-combat, CR 702.22b); ETB wiring in zones.py put_permanent_onto_battlefield; 19 integration tests; suite 3149/0/3/13 (+10 net from Miracle baseline). Part of umbrella Story 7-6. |
| 7-6f | Convoke (CR 702.43) | story-kw-convoke.md | Medium | none | ✅ shipped 2026-09-02 — Convoke module implemented: real apply() with cost reduction via tapping creatures; pending_convoke_choice field; stack.py cast_spell interception; API /cast flow with convoke_pay/convoke_pass; 9 integration tests; suite 3167/0/3/13 (+18 net from Bloodthirst baseline). Part of umbrella Story 7-6. |

### P1: High-Frequency Modern Keywords (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-7 | Phasing, Modulate, Saddle, Prototype new modules + tests | SPRINT7-P1-modern-keywords.md | High | none | 🔄 in progress — sub-stories below (discovery complete) |

#### 7-7: Modern Keyword Sub-Stories (discovery complete; plans authored)

| # | Story | File | Plan | Priority | Dependencies | Status |
|---|-------|------|------|----------|--------------|--------|
| 7-7a | Phasing (CR 702.26) — end-of-untap phase out/in, phased-out treated as nonexistent | story-kw-phasing.md | plans/story-kw-phasing-plan.md | High | none (turn_manager UNTAP hook is the one external dep) | 📋 ready to implement |
| 7-7b | Saddle (BLI 2025, no CR yet) — ETB attaches like Equipment, reuses `_apply_equip` infra | story-kw-saddle.md | plans/story-kw-saddle-plan.md | High | none (zones.py put_permanent_onto_battlefield is the one external dep) | 📋 ready to implement |
| 7-7c | Modulate (MOM 2023, no CR yet) — exile creature, create X/X artifact-creature token copy | story-kw-modulate.md | plans/story-kw-modulate-plan.md | High | none (token-copy extension is the one external dep) | 📋 ready to implement |
| 7-7d | Prototype (BLI 2025, no CR yet) — alternative cost: exile artifact from graveyard, enter as copy w/o mana cost | story-kw-prototype.md | plans/story-kw-prototype-plan.md | High | none (stack.py cast_spell interception is the one external dep) | 📋 ready to implement |

**Recommended implementation order:** 7-7a Phasing first (safest, most rules-defined; isolated turn_manager hook), then 7-7b Saddle (most infra reuse via `_apply_equip`), then 7-7c Modulate and 7-7d Prototype in parallel (both self-contained). Each adds one new `pending_*_choice` GameState field and its own integration test file; no cross-dependencies between the four.

### P2: Common Modern Mechanics (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-8 | Amass, Explore, Goad, Detain new modules + tests | SPRINT7-P2-common-modern-keywords.md | Medium | none | ⏳ |

### P2: Remaining Stub Keywords — Batch A (8 keywords, decomposed from #7-9)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-9a | Unearth (CR 702.83) | story-kw-unearth.md | Medium | none | ⏳ |
| 7-9b | Transmute (CR 702.95) | story-kw-transmute.md | Medium | none | ⏳ |
| 7-9c | Replicate (CR 702.55) | story-kw-replicate.md | Medium | none | ⏳ |
| 7-9d | Surge (CR 702.126) | story-kw-surge.md | Medium | none | ⏳ |
| 7-9e | Extort (CR 702.63b) | story-kw-extort.md | Medium | none | ⏳ |
| 7-9f | Scavenge (CR 702.96) | story-kw-scavenge.md | Medium | none | ⏳ |
| 7-9g | Counter Spell / Counter placement (CR 701.5) | story-kw-counter.md | Medium | none | ⏳ |
| 7-9h | Meld (CR 702.146b) | story-kw-meld.md | Medium | none | ⏳ |

### P2: Remaining Stub Keywords — Batch B (6 remaining stub keywords)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-14a | Level Up (CR 702.84) | story-kw-level.md | Medium | none | ⏳ |
| 7-14b | Flanking (CR 702.25) | story-kw-flanking.md | Medium | none | ⏳ |
| 7-14c | Leave/LTB Triggers | story-kw-leave.md | Medium | none | ⏳ |
| 7-14d | Evoke (CR 702.74) | story-kw-evoke.md | Medium | none | ⏳ |
| 7-14e | Morph (CR 702.37) | story-kw-morph.md | Medium | none | ⏳ |
| 7-14f | Suspend (CR 702.62) | story-kw-suspend.md | Medium | none | ⏳ |

### P2: Missing Trigger Patterns (existing story — now supplemented by 7-3 and 7-10)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-10 | Sacrificed, Countered, Becomes Target, Fight, Investigated, Searched Library, Tapped For Mana, Attached/Unattach, Transformed | SPRINT7-P2-trigger-patterns.md | Medium | none | ⏳ |

### P3: Additional Missing Triggers (NEW)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-11 | Scry, Cycled, Abandoned, Mutates, Loyalty Change trigger patterns + wiring | SPRINT7-P3-additional-triggers.md | Medium | none | ⏳ |

### P3: Newer Mechanics Batch 1 (5 mechanics, existing story)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-12 | Amass, Incubate, Forage, Explore, Connive new modules + tests | SPRINT7-P3-newer-mechanics-batch1.md | Medium | none | ⏳ |

### P4: Newer Mechanics Batch 2 (5 mechanics, existing story)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-13 | Goad, Detain, Heist/Protect, Battle/Siege, Intensify new modules + tests | SPRINT7-P4-newer-mechanics-batch2.md | Low | none | ⏳ |

### P4: Low-Frequency Missing Triggers — Batch 3 (40 new story files)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-16a | Flipped Coin (CR 701.24) | story-trg-flipped-coin.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16b | Forage (CR 702.XX) | story-trg-forage.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16c | Foretell (CR 702.XX) | story-trg-foretell.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16d | Give Gift (CR 702.XX) | story-trg-give-gift.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16e | Loses Game (CR 104.3) | story-trg-loses-game.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16f | Mana Added (CR 502.4) | story-trg-mana-added.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16g | Mana Expend (CR 118.9) | story-trg-mana-expend.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16h | Manifest Dread (CR 702.XX) | story-trg-manifest-dread.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16i | Mentored (CR 702.134) | story-trg-mentored.md | Low | story-kw-mentor.md | ⏳ |
| 7-16j | Milled Once (CR 701.14) | story-trg-milled-once.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16k | Pay Cumulative Upkeep (CR 702.26) | story-trg-pay-cumulative-upkeep.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16l | Pay Echo (CR 702.28) | story-trg-pay-echo.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16m | Pay Life (CR 701.12) | story-trg-pay-life.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16n | Proliferated (CR 702.39) | story-trg-proliferated.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16o | Ring Tempts You (CR 702.XX) | story-trg-ring-tempts-you.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16p | Rolled Die (CR 701.25) | story-trg-rolled-die.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16q | Rolled Die Once (CR 701.25) | story-trg-rolled-die-once.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16r | Sacrificed Once (CR 701.19) | story-trg-sacrificed-once.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16s | Searched Library (CR 400.8) | story-trg-searched-library.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16t | Set In Motion (CR 702.XX) | story-trg-set-in-motion.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16u | Shuffled (CR 400.9) | story-trg-shuffled.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16v | Spell Cast / Ability Activated (CR 601.2) | story-trg-spell-cast.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16w | Surveil (CR 701.41) | story-trg-surveil.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16x | Takes Initiative (CR 702.148) | story-trg-takes-initiative.md | Low | story-gm-initiative.md | ⏳ |
| 7-16y | Token Created General (CR 110.5) | story-trg-token-created-gen.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16z | Trains (CR 702.XX) | story-trg-trains.md | Low | story-kw-training.md | ⏳ |
| 7-16aa | Turn Face Up (CR 702.37) | story-trg-turn-face-up.md | Low | story-kw-morph.md | ⏳ |
| 7-16ab | Unattach (CR 702.5) | story-trg-unattach.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ac | Vote (CR 701.23) | story-trg-vote.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ad | Waiting / Planar Delay (CR 702.XX) | story-trg-waiting.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ae | Proliferated Once (CR 702.39) | story-trg-proliferated-once.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16af | Become Monarch (CR 702.147) | story-trg-become-monarch.md | Low | story-gm-monarch.md | ⏳ |
| 7-16ag | Planar Dice (CR 702.XX) | story-trg-planar-dice.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ah | Planeswalk (CR 702.91) | story-trg-planeswalk.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ai | Planeswalked From/To (CR 702.91) | story-trg-planeswalked-from.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16aj | Ability Triggered (CR 603.2) | story-trg-ability-triggered.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16ak | Damage Prevented Once (CR 119.3) | story-trg-damage-prevented.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16al | Delayed Trigger Framework (CR 603.7) | story-trg-delayed-trigger.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16am | Instant/Sorcery Cast (CR 601.2) | story-trg-instant-sorcery-cast.md | Low | STORY-GUIDELINES | ⏳ |
| 7-16an | Creature Enter (CR 302.3) | story-trg-creature-enter.md | Low | STORY-GUIDELINES | ⏳ |

### P4: Completely Missing Keyword Modules — Batch 1 (25 new story files)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 7-15a | Affinity (CR 702.41) | story-kw-affinity.md | Medium | none | 📋 |
| 7-15b | Amplify (CR 702.53) | story-kw-amplify.md | Low | none | 📋 |
| 7-15c | Ascend (CR 702.130) | story-kw-ascend.md | Medium | none | 📋 |
| 7-15d | Bestow (CR 702.69) | story-kw-bestow.md | Medium | none | 📋 |
| 7-15e | Blitz (CR 702.136) | story-kw-blitz.md | Medium | none | 📋 |
| 7-15f | Casualty (CR 702.137) | story-kw-casualty.md | Medium | none | 📋 |
| 7-15g | Champion (CR 702.28) | story-kw-champion.md | Low | none | 📋 |
| 7-15h | Devour (CR 702.66) | story-kw-devour.md | Low | none | 📋 |
| 7-15i | Evolve (CR 702.100) | story-kw-evolve.md | Medium | none | 📋 |
| 7-15j | Fabricate (CR 702.78) | story-kw-fabricate.md | Medium | none | 📋 |
| 7-15k | Mentor (CR 702.134) | story-kw-mentor.md | Medium | none | 📋 |
| 7-15l | Modular (CR 702.42) | story-kw-modular.md | Medium | none | 📋 |
| 7-15m | Mutate (CR 702.149) | story-kw-mutate.md | Medium | none | 📋 |
| 7-15n | Myriad (CR 702.117) | story-kw-myriad.md | Medium | none | 📋 |
| 7-15o | Prowess (CR 702.119) | story-kw-prowess.md | Medium | none | 📋 |
| 7-15p | Riot (CR 702.135) | story-kw-riot.md | Medium | none | 📋 |
| 7-15q | Training (CR 702.128) | story-kw-training.md | Medium | none | 📋 |
| 7-15r | Living Weapon (CR 702.70) | story-kw-living-weapon.md | Medium | none | 📋 |
| 7-15s | Disturb (CR 702.138) | story-kw-disturb.md | Medium | none | 📋 |
| 7-15t | Fortify (CR 702.54a) | story-kw-fortify.md | High | none | 📋 |
| 7-15u | Phasing (CR 702.26) | story-kw-phasing.md | Medium | none | 📋 |
| 7-15v | Saddle (CR 702.XX — OTJ) | story-kw-saddle.md | Medium | none | 📋 |
| 7-15w | Prototype (CR 702.XX — BRO) | story-kw-prototype.md | Low | none | 📋 |
| 7-15x | Craft (CR 702.XX — MH3) | story-kw-craft.md | Low | none | 📋 |
| 7-15y | Bargain (CR 702.XX — WOE) | story-kw-bargain.md | Low | none | 📋 |

---

### P0/P1: Highest-Frequency Missing Triggers — Batch 1 (25 new stories)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Attacks — refined patterns (CR 508.1) | story-trg-attacks.md | High | STORY-GUIDELINES | ⏳ |
| 2 | Blocks — refined patterns (CR 509.1) | story-trg-blocks.md | High | STORY-GUIDELINES | ⏳ |
| 3 | Destroyed (CR 701.7) | story-trg-destroyed.md | High | STORY-GUIDELINES | ⏳ |
| 4 | Exiled (CR 701.8) | story-trg-exiled.md | High | STORY-GUIDELINES | ⏳ |
| 5 | Life Gained (CR 701.12) | story-trg-life-gained.md | High | STORY-GUIDELINES | ⏳ |
| 6 | Life Lost (CR 701.13) | story-trg-life-lost.md | High | STORY-GUIDELINES | ⏳ |
| 7 | Countered (CR 701.5) | story-trg-countered.md | High | STORY-GUIDELINES | ⏳ |
| 8 | Investigated (CR 701.32) | story-trg-investigated.md | High | STORY-GUIDELINES | ⏳ |
| 9 | Land Played / Landfall — refined (CR 305.1) | story-trg-land-played.md | High | STORY-GUIDELINES | ⏳ |
| 10 | Token Created "One or More" (CR 110.5) | story-trg-token-created-once.md | High | STORY-GUIDELINES | ⏳ |
| 11 | Exerts (CR 701.26) | story-trg-exerted.md | Medium | STORY-GUIDELINES | ⏳ |
| 12 | Explores (CR 701.33) | story-trg-explores.md | Medium | STORY-GUIDELINES | ⏳ |
| 13 | Cycled (CR 702.28) | story-trg-cycled.md | Medium | story-kw-cycle.md | ⏳ |
| 14 | Scry (CR 701.19) | story-trg-scry.md | Medium | STORY-GUIDELINES | ⏳ |
| 15 | Mutates (CR 702.149) | story-trg-mutates.md | Medium | STORY-GUIDELINES | ⏳ |
| 16 | Taps / Becomes Tapped (CR 302.6) | story-trg-taps.md | Medium | STORY-GUIDELINES | ⏳ |
| 17 | Untaps / Becomes Untapped (CR 302.6) | story-trg-untaps.md | Medium | STORY-GUIDELINES | ⏳ |
| 18 | Milled (CR 701.14) | story-trg-milled.md | Medium | STORY-GUIDELINES | ⏳ |
| 19 | Attacker Blocked (CR 509.1) | story-trg-attacker-blocked.md | Medium | STORY-GUIDELINES | ⏳ |
| 20 | Attacker Unblocked (CR 509.1) | story-trg-attacker-unblocked.md | Medium | STORY-GUIDELINES | ⏳ |
| 21 | Dealt Damage / Receives Damage (CR 119.3) | story-trg-dealt-damage.md | Medium | STORY-GUIDELINES | ⏳ |
| 22 | Enchanted / Becomes Enchanted (CR 303.4) | story-trg-enchanted.md | Medium | STORY-GUIDELINES | ⏳ |
| 23 | Crewed / Saddled / Becomes Creature (CR 702.121a) | story-trg-crewed.md | Medium | story-kw-crew.md | ⏳ |
| 24 | Transformed — refined "becomes creature" (CR 711.3) | story-trg-transformed-once.md | Medium | STORY-GUIDELINES | ⏳ |
| 25 | Phase In/Out (CR 702.26) | story-trg-phase-in.md | Low | STORY-GUIDELINES | ⏳ |

---

### P1: Medium-Frequency Missing Triggers — Batch 2 (30 new stories)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Abandoned (CR 702.XX) | story-trg-abandoned.md | Medium | STORY-GUIDELINES | ⏳ |
| 2 | Adapt (CR 702.XX) | story-trg-adapt.md | Medium | STORY-GUIDELINES | ⏳ |
| 3 | Become Monstrous (CR 702.31) | story-trg-become-monstrous.md | Medium | STORY-GUIDELINES | ⏳ |
| 4 | Become Renowned (CR 702.81) | story-trg-become-renowned.md | Medium | STORY-GUIDELINES | ⏳ |
| 5 | Becomes Crewed (CR 702.121a) | story-trg-becomes-crewed.md | Medium | story-kw-crew.md | ⏳ |
| 6 | Becomes Plotted (CR 702.XX) | story-trg-becomes-plotted.md | Medium | STORY-GUIDELINES | ⏳ |
| 7 | Becomes Saddled (CR 702.XX) | story-trg-becomes-saddled.md | Medium | story-kw-saddle.md | ⏳ |
| 8 | Changes Controller (CR 108.3) | story-trg-changes-controller.md | Medium | STORY-GUIDELINES | ⏳ |
| 9 | Changes Zone (CR 400.1) | story-trg-changes-zone.md | Medium | STORY-GUIDELINES | ⏳ |
| 10 | Chaos Ensues (CR 702.XX) | story-trg-chaos-ensues.md | Medium | STORY-GUIDELINES | ⏳ |
| 11 | Claim Prize (CR 702.XX) | story-trg-claim-prize.md | Medium | STORY-GUIDELINES | ⏳ |
| 12 | Clashed (CR 701.23) | story-trg-clashed.md | Medium | STORY-GUIDELINES | ⏳ |
| 13 | Class Level Gained (CR 702.XX) | story-trg-class-level-gained.md | Medium | STORY-GUIDELINES | ⏳ |
| 14 | Collect Evidence (CR 701.XX) | story-trg-collect-evidence.md | Medium | STORY-GUIDELINES | ⏳ |
| 15 | Commit Crime (CR 701.XX) | story-trg-commit-crime.md | Medium | STORY-GUIDELINES | ⏳ |
| 16 | Completed Dungeon (CR 701.61) | story-trg-completed-dungeon.md | Medium | story-gm-venture.md | ⏳ |
| 17 | Connives (CR 702.XX) | story-trg-connives.md | Medium | STORY-GUIDELINES | ⏳ |
| 18 | Counter Added All (CR 122.1) | story-trg-counter-added-all.md | Medium | STORY-GUIDELINES | ⏳ |
| 19 | Counter Removed (CR 122.1) | story-trg-counter-removed.md | Medium | STORY-GUIDELINES | ⏳ |
| 20 | Crank Contraption (CR 702.XX) | story-trg-crank-contraption.md | Medium | STORY-GUIDELINES | ⏳ |
| 21 | Damage Dealt Once (CR 119.3) | story-trg-damage-dealt-once.md | Medium | STORY-GUIDELINES | ⏳ |
| 22 | Damage Dealt By Controller (CR 119.3) | story-trg-damage-dealt-by-controller.md | Medium | STORY-GUIDELINES | ⏳ |
| 23 | Day Time Changes (CR 702.148) | story-trg-day-time-changes.md | Medium | story-gm-day-night.md | ⏳ |
| 24 | Devoured (CR 702.66) | story-trg-devoured.md | Medium | STORY-GUIDELINES | ⏳ |
| 25 | Discarded All (CR 701.18) | story-trg-discarded-all.md | Medium | STORY-GUIDELINES | ⏳ |
| 26 | Discover (CR 701.XX) | story-trg-discover.md | Medium | STORY-GUIDELINES | ⏳ |
| 27 | Elementalbend (CR 702.XX) | story-trg-elementalbend.md | Medium | STORY-GUIDELINES | ⏳ |
| 28 | Entered Room (CR 701.61) | story-trg-entered-room.md | Medium | story-gm-venture.md | ⏳ |
| 29 | Excess Damage (CR 702.19) | story-trg-excess-damage.md | Medium | STORY-GUIDELINES | ⏳ |
| 30 | Exploited (CR 702.109) | story-trg-exploited.md | Medium | STORY-GUIDELINES | ⏳ |

## Sprint 8: Multiplayer & Match Systems (future)

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Turn order for 3+ players, Two-Headed Giant variant, Best-of-X match support with sideboarding | sprint-d-multiplayer-match.md | Low | Sprint 7 ✅ | ⏳ |

---

## Ability Type Framework (Foundational)

Foundational ability type categories per the MTG Comprehensive Rules. These define the core framework that all keyword abilities, spell effects, and game mechanics build upon.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Activated Abilities (CR 602) | story-ab-activated-abilities.md | High | none | 📋 |
| 2 | Triggered Abilities (CR 603) | story-ab-triggered-abilities.md | High | none | 📋 |
| 3 | Static Abilities (CR 604) | story-ab-static-abilities.md | High | none | 📋 |
| 4 | Mana Abilities (CR 605) | story-ab-mana-abilities.md | High | Activated, Triggered, Static | 📋 |
| 5 | Loyalty Abilities (CR 606) | story-ab-loyalty-abilities.md | High | Activated Abilities | 📋 |
| 6 | Spell Abilities (CR 601) | story-ab-spell-abilities.md | High | none | 📋 |
| 7 | Alternative Costs (CR 118.8) | story-ab-alternative-costs.md | High | Spell Abilities | 📋 |
| 8 | Additional Costs (CR 118.9) | story-ab-additional-costs.md | High | Spell Abilities, Alternative Costs | 📋 |
| 9 | Optional Additional Costs (CR 118.10) | story-ab-optional-costs.md | High | Spell Abilities, Additional Costs | 📋 |

---

## Story Count Summary (Sprint 7)

| Priority | Stories | Keywords/Triggers Covered |
|----------|---------|--------------------------|
| P0 (High) | 6 stories + 20 sub-stories (#7-1 through #7-5, #7-2a through #7-2m, #7-5a through #7-5f, #7-15t) + 10 new trigger stories | Architecture wiring, 13 trigger wirings (dead-code → live), 2 new trigger patterns, Fortify, Crew, Equip, Cycling, Scry, Ward, Toxic, +10 high-frequency triggers (Attacks, Blocks, Destroyed, Exiled, Life Gained, Life Lost, Countered, Investigated, Landfall, Token Created Once) |
| P1 (Medium-High) | 2 stories + 6 sub-stories (#7-6, #7-7, #7-6a through #7-6f) + 30 new trigger stories | Buyback, Entwine, Overload, Miracle, Bloodthirst, Convoke, 4 modern keywords (Phasing/Modulate/Saddle/Prototype), 30 medium-frequency trigger patterns |
| P2 (Medium) | 3 stories + 14 sub-stories (#7-8 through #7-10, #7-9a through #7-9h, #7-14a through #7-14f) | 4 common modern mechanics, 14 remaining stubs (Unearth, Transmute, Replicate, Surge, Extort, Scavenge, Counter, Meld, Level Up, Flanking, Leave, Evoke, Morph, Suspend), 9 trigger patterns |
| P3 (Medium-Low) | 2 stories (#7-11, #7-12) | 5 additional triggers, 5 newer mechanics batch 1 |
| P4 (Low) | 2 stories + 65 sub-stories (#7-13, #7-15a through #7-15y, #7-16a through #7-16an) | 5 newer mechanics batch 2, 25 completely missing keywords (Affinity, Amplify, Ascend, Bestow, Blitz, Casualty, Champion, Devour, Evolve, Fabricate, Mentor, Modular, Mutate, Myriad, Prowess, Riot, Training, Living Weapon, Disturb, Fortify, Phasing, Saddle, Prototype, Craft, Bargain), 40 low-frequency missing trigger patterns |

**Total Sprint 7 stories: 13 parent + 159 decomposed** (covering ~207 keywords/triggers across all priority levels)

---

## Game Rules: Comprehensive Rules Grounding (CR 1-903)

Individual story files covering foundational Magic rules and mechanics, grounded in the Comprehensive Rules. These complement the keyword and game-mechanic stories by focusing on rules-layer interactions.

### Foundational Game Rules

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | State-Based Actions (CR 704) | story-rule-state-based-actions.md | High | none | 📋 |
| 2 | Replacement Effects (CR 614) | story-rule-replacement-effects.md | High | SBA (CR 704) | 📋 |
| 3 | Prevention Effects (CR 615) | story-rule-prevention-effects.md | Medium | Replacement Effects | 📋 |
| 4 | Targeting Rules (CR 115, 601.2c) | story-rule-targeting.md | High | SBA (CR 704) | 📋 |
| 5 | Legend Rule (CR 704.5j) | story-rule-legend-rule.md | Medium | SBA (CR 704) | 📋 |
| 6 | Layer System (CR 613) | story-rule-layer-system.md | High | none | 📋 |
| 7 | Token Rules (CR 110.5-110.8) | story-rule-tokens.md | Medium | SBA (CR 704) | 📋 |
| 8 | Copy Effects (CR 707) | story-rule-copy-effects.md | High | Layer System, Tokens | 📋 |
| 9 | Split Cards / Fuse (CR 709) | story-rule-split-cards.md | Medium | Targeting, Modal Spells | 📋 |
| 10 | Mutate Rules (CR 702.149) | story-rule-mutate.md | Medium | Targeting, Copy Effects | 📋 |
| 11 | Modal Spells (CR 700.2) | story-rule-modal-spells.md | Medium | Targeting, Copy Effects | 📋 |
| 12 | Cost Reduction / Modification (CR 118.7) | story-rule-cost-modification.md | Medium | Mana Cost/Value | 📋 |
| 13 | Mana Cost / Mana Value (CR 107.4, 202) | story-rule-mana-cost-value.md | Medium | Color Rules | 📋 |
| 14 | Color Rules (CR 105) | story-rule-color-rules.md | Medium | Layer System | 📋 |
| 15 | Color Identity (CR 903.4) | story-rule-color-identity.md | Medium | Color Rules, FMT-01 | 📋 |
| 16 | Protection (CR 702.16) | story-rule-protection.md | Medium | Targeting, SBA | 📋 |
| 17 | Snow Mana / Snow Permanents | story-rule-snow-mana.md | Medium | Mana Cost/Value | 📋 |
| 18 | Phased Out Permanents (CR 702.26) | story-rule-phased-out.md | Medium | SBA, Tokens | 📋 |
| 19 | Bestow (CR 702.69) — wrapper ref | story-rule-bestow.md | Medium | story-kw-bestow.md | 📋 |
| 20 | Fortify (CR 702.54a) — wrapper ref | story-rule-fortify.md | High | story-kw-fortify.md | 📋 |
| 22 | Banding (CR 702.21) | story-rule-banding.md | Low | Trample, SBA | 📋 |
| 23 | Equip Timing / Sorcery Speed (CR 702.6) | story-rule-equip-timing.md | Low | Targeting | 📋 |
| 24 | Hexproof vs Shroud Distinction | story-rule-hexproof-shroud.md | Low | Targeting | 📋 |
| 25 | Indestructible (CR 702.12) | story-rule-indestructible.md | Medium | SBA, Deathtouch | 📋 |
| 26 | Deathtouch Damage Rules (CR 702.2) | story-rule-deathtouch-damage.md | Medium | Trample, SBA | 📋 |
| 27 | Trample Damage Assignment (CR 702.19) | story-rule-trample.md | Medium | Deathtouch, SBA | 📋 |
| 28 | Double Strike Timing (CR 702.4) | story-rule-double-strike.md | Medium | First Strike, SBA | 📋 |
| 29 | First Strike Timing (CR 702.7) | story-rule-first-strike.md | Medium | Double Strike, SBA | 📋 |
| 30 | Vigilance (CR 702.20) | story-rule-vigilance.md | Low | none | 📋 |
| 31 | Haste (CR 702.10) | story-rule-haste.md | Low | none | 📋 |
| 32 | Flash (CR 702.8) | story-rule-flash.md | Low | none | 📋 |
| 33 | Defender (CR 702.3) | story-rule-defender.md | Low | none | 📋 |
| 34 | Shadow (CR 702.27) | story-rule-shadow.md | Medium | none | 📋 |
| 35 | Horsemanship (CR 702.30) | story-rule-horsemanship.md | Low | none | 📋 |
| 36 | Fear (CR 702.24) | story-rule-fear.md | Low | none | 📋 |
| 37 | Intimidate (CR 702.13) | story-rule-intimidate.md | Low | none | 📋 |
| 38 | Skulk (CR 702.120) | story-rule-skulk.md | Low | none | 📋 |
| 39 | Soulbond (CR 702.90) | story-rule-soulbond.md | Medium | none | 📋 |
| 40 | Split Second (CR 702.61) | story-rule-split-second.md | Medium | none | 📋 |
| 41 | Face-Down Creature Rules (CR 702.37, 708) | story-rule-face-down.md | Medium | Tokens, Morph | 📋 |
| 42 | Transform Rules (CR 701.28) | story-rule-transform.md | Medium | Day/Night Cycle | 📋 |
| 43 | Day/Night Cycle (CR 702.148) | story-rule-day-night.md | Medium | Transform | 📋 |

### Card Type Rules (CR 301-310, 705, 714, 716, 901-902)

Individual story files for each Magic card type, covering their core type rules, subtypes, and game behaviors as defined by the Comprehensive Rules.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| 1 | Creature Rules (CR 302) | story-cardtype-creatures.md | High | State-Based Actions (CR 704), Combat System | 📋 |
| 2 | Land Rules (CR 305) | story-cardtype-lands.md | High | Mana Abilities (CR 605), Mana Pool (CR 106, 118) | 📋 |
| 3 | Artifact Rules (CR 301) | story-cardtype-artifacts.md | High | Equip (CR 702.6), Crew (CR 702.121a), Fortify (CR 702.54a) | 📋 |
| 4 | Enchantment Rules (CR 303) | story-cardtype-enchantments.md | High | Aura Rules, Enchant (CR 702.5), SBA (CR 704) | 📋 |
| 5 | Planeswalker Rules (CR 306) | story-cardtype-planeswalkers.md | High | Loyalty Abilities (CR 606), Legend Rule (CR 704.5j), SBA (CR 704) | 📋 |
| 6 | Instant Rules (CR 307) | story-cardtype-instants.md | High | Priority System (CR 117), Spell Abilities (CR 601) | 📋 |
| 7 | Sorcery Rules (CR 308) | story-cardtype-sorceries.md | High | Priority System (CR 117), Spell Abilities (CR 601), Flash (CR 702.8) | 📋 |
| 8 | Battle Rules (CR 310) | story-cardtype-battles.md | High | Transform Rules (CR 711), Combat System (CR 506-511) | 📋 |
| 9 | Aura Rules (CR 303.4) | story-cardtype-auras.md | High | Enchant (CR 702.5), Targeting Rules (CR 115, 601.2c), SBA (CR 704) | 📋 |
| 10 | Equipment Rules (CR 301.5) | story-cardtype-equipment.md | High | Artifact Rules (CR 301), Equip (CR 702.6) | 📋 |
| 11 | Vehicle Rules (CR 301.7) | story-cardtype-vehicles.md | High | Artifact Rules (CR 301), Crew (CR 702.121a) | 📋 |
| 12 | Saga Rules (CR 714) | story-cardtype-sagas.md | High | Enchantment Rules (CR 303), Triggered Abilities (CR 603), SBA (CR 704) | 📋 |
| 13 | Class Rules (CR 716) | story-cardtype-classes.md | Medium | Enchantment Rules (CR 303), Level Up (CR 702.84) | 📋 |
| 14 | Tribal Rules (CR 308.2) | story-cardtype-tribals.md | Medium | Creature Types, paired type rules | 📋 |
| 15 | Plane Rules (CR 901) — Planechase | story-cardtype-planes.md | Low | Command Zone (CR 400.2), Triggered Abilities (CR 603) | 📋 |
| 16 | Conspiracy Rules (CR 705) | story-cardtype-conspiracies.md | Low | Command Zone (CR 400.2), Hidden Agenda | 📋 |
| 17 | Phenomena Rules (CR 702) — Planechase | story-cardtype-phenomena.md | Low | Plane Rules (CR 901), Triggered Abilities (CR 603) | 📋 |
