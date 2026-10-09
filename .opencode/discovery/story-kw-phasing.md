# Story: Phasing (CR 702.26)

## User Story
As a player, I want permanents with the Phasing keyword to phase out at end of untap and phase back in on my next untap step — behaving exactly as though they don't exist while phased out — so that cards like *Dread Statuary* or *Phasing* creatures resolve correctly instead of no-op'ing.

## Context
Phasing (CR 702.26) is a classic mechanic reprinted in modern sets (2019–2025). At the end of the controller's untap step, that player's phased-out-at-end-last-turn permanents phase back in; then any permanent with phasing phases out. While phased out a permanent:
- Is treated as though it doesn't exist (can't be targeted, attacked with against, blocked, affected by anything).
- Keeps its counters.
- Auras/Equipment attached to it also phase out with it and remain attached on return.
- Does NOT untap when it phases back in (it enters the turn already "untapped" for that turn's untap step — no untap event).

Currently only model stubs exist: `Permanent.phased_out` and `Permanent.has_phasing` are declared but unused, and `phasing`/`saddle` appear in the parser keyword list. No engine logic or API wiring exists. This is the most rules-complex of the four keywords (return timing + turn_manager coupling).

## Acceptance Criteria
- [ ] Create `mtg_engine/ability/keywords/phasing.py` with `PhasingKeyword(PassiveKeyword)` class.
- [ ] Detection via regex `\bphasing\b` in oracle text or keywords list; `has_phasing()` / `from_oracle_text()` helpers.
- [ ] End-of-untap hook: at end of the active player's untap step, each of their permanents with phasing that isn't already phased out becomes phased out (`perm.phased_out = True`).
- [ ] Phased-out permanents excluded from targeting, combat declaration, and SBA checks; counters preserved; attachments (Auras/Equipment) remain attached.
- [ ] Return: at the start of the controller's next untap step, the permanent phases back in (`perm.phased_out = False`) — it does NOT fire an untap and is not summoning-sick-blocked by that.
- [ ] Tracking: new `GameState.phased_out_permanents: dict[str, str]` mapping perm_id → controller_name (used to know whose turn drives the phase-in/phase-out). Optionally record phase-out turn for return timing.
- [ ] Pure transform: meaningful changes via `model_copy`; no-op paths return the SAME object (Q4) so repeated events can't double-fire.
- [ ] Integration tests in `tests/engine/test_phasing_integration.py` (8–15): detection, phases out at end of untap, phased-out can't be targeted/attack/block, counters persist through phasing, returns at correct time, doesn't untap on return, pure-transform no-op.

## Technical Plan
**Plan file**: `plans/story-kw-phasing-plan.md`

## Dependencies
- Depends on **turn_manager.py** `begin_step()` UNTAP branch gaining an end-of-untap-step hook (cross-cutting — see plan). This is the one hard external dependency of the four keywords.
- No dependency on Modulate/Saddle/Prototype.

## Priority: High

## Notes / CR Gaps
- **Phasing rules are well-defined (CR 702.26)** — no ambiguity. Key subtlety to nail in the plan: phase-out happens at END of untap step, phase-in at START of next untap step; both driven by `active_player` ownership via `phased_out_permanents`.
- Edge case: a permanent that phases out and its controller never gets another turn (loses game) — just leave it phased out (SBA ends game). 
- Edge case: an effect that removes a phased-out permanent from the game entirely (e.g. exile with "exile/phases out" interaction) — while phased out, it can't be targeted, so this is naturally handled by "doesn't exist".
- The existing `Permanent.has_phasing`/`phased_out` stubs should be reused rather than redefined; plan how they're set.
