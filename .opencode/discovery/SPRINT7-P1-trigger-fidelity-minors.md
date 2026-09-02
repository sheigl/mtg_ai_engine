# Story: P1 Trigger Fidelity Minors (Story 7-17)

## User Story
As an MTG engine developer, I want the remaining minor trigger-fidelity gaps from the Sprint 7
trigger work fixed and pinned with tests, so that trigger behavior matches the Comprehensive
Rules in the edge cases that the main P0/P1 wiring stories (7-2, 7-3) deliberately left as
documented "known gaps."

## Context
The Sprint 7 trigger stories are complete and the full suite is green
(**2816 passed / 3 skipped / 13 xfailed** — post-7-3 baseline; 2798 + 18 new 7-3 tests):
- **7-1** — trigger-based keyword modules wired to their own `apply()`.
- **7-2** — 13 dead-code trigger check functions wired into the engine event flow.
- **7-3** — Countered (CR 701.5) and Investigated (CR 701.32) trigger patterns, check
  functions, and engine wiring (see `plans/SPRINT7-P0-missing-triggers-plan.md`).

During 7-2's code review (2026-08-19), a set of **minor** trigger-fidelity gaps were identified
and deferred because they were lower priority than getting the core trigger types firing. This
story captures those **5 known gaps** as discrete, independently verifiable acceptance criteria.

These are **fidelity** issues — the triggers mostly work, but specific edge cases deviate from
the CRs or lack test coverage. None are as critical as the missing trigger types (7-3), hence
P1 / Medium priority.

The 5 known gaps (from the 7-2 story's KNOWN GAPS section):
1. CR 903.9 Commander replacement bypass on sacrifice
2. Unattach trigger path latent (no call site)
3. Multi-token creation under-fires "token created" (CR 110.6)
4. Missing negative unit test for "a creature you control is sacrificed"
5. Integration coverage gaps (cycling endpoint route, Fading upkeep route)

## Acceptance Criteria

### 1. CR 903.9 Commander replacement on sacrifice
- [ ] `_sacrifice_permanent` (`mtg_engine/engine/zones.py:826`) applies the CR 903.9
      replacement effect to a sacrificed Commander: for a **human** player, queue the
      Commander-zone choice (`pending_commander_zone_choice` or equivalent) so the player can
      send it to the Command zone; for an **AI** player, auto-redirect to the Command zone.
- [ ] A sacrificed Commander with Emerge/Fading is no longer silently sent to the graveyard —
      it is offered the Command-zone replacement.
- [ ] Integration test: sacrificing a human player's Commander offers the Command-zone choice;
      sacrificing an AI player's Commander auto-redirects to the Command zone.
- [ ] If the team decides a full pending-choice is out of scope, document it as an **accepted
      gap** in this story's Notes with a rationale (do not silently leave it).

### 2. Unattach trigger path
- [ ] `check_attach_triggers(..., attach_event="unattach")` gains a real call site so
      "whenever this enchantment is unattached" / "whenever an aura you control is unattached"
      triggers actually fire.
- [ ] The aura's controller is captured **before** the aura leaves the battlefield — the
       `attached_controller` lookup (`triggers.py:1125`) must not return `""` for the unattach
      event, or the "you control" filter can never match.
- [ ] Integration test: unattaching an aura (e.g. via a "remove all enchantments" effect) fires
      the unattach trigger; the "you control" filter matches the aura's original controller.

### 3. Multi-token creation fires one "token created" trigger per token (CR 110.6)
- [ ] When an effect creates N tokens, `check_token_triggers` fires **N times** (one per token),
      not once after the creation loop.
- [ ] Applies to all token-creation call sites: `stack.py:1341`, `stack.py:2097`, `stack.py:2133`,
       `effects/base.py:288`, `loyalty.py:235` (stack.py refs re-verified 2026-08-20; shifted by 7-3 insertions).
- [ ] Integration test: an effect that creates 3 tokens queues 3 "token created" triggers for a
      "whenever a token enters the battlefield" watcher.

### 4. Negative unit test for "a creature you control is sacrificed"
- [ ] Add a unit test pinning that "whenever a creature you control is sacrificed" does **NOT**
      fire when an **opponent's** creature is sacrificed (`sac.controller != watcher.controller`).
- [ ] The existing positive and any-player cases remain passing.

### 5. Integration coverage for the two untested routes
- [ ] Natural-context integration test for the **cycling API endpoint** route
       (`mtg_engine/api/routers/game.py:968`) — drive the real endpoint and assert the cycle
      discard + draw happen and any "whenever a card is cycled" trigger fires.
- [ ] Natural-context integration test for the **Fading counter-removed upkeep** route
       (`mtg_engine/engine/turn_manager.py:~207-232`) — drive the real upkeep and assert the
      Fading permanent is discarded and any "whenever this permanent is discarded" trigger fires.

### Cross-cutting
- [ ] All changes follow the pure-transform convention (functions return a new `GameState` via
      `model_copy`; call sites capture the returned state).
- [ ] Full test suite passes with the new tests added: baseline **2816 passed / 3 skipped /
       13 xfailed** (post-7-3), 0 failures, skip/xfail set byte-identical.

## Dependencies
- Depends on **7-2** (trigger wiring, ✅) and **7-3** (countered/investigated, ✅ closed 2026-08-20)
   being complete — this story builds on and refines their work.
- No dependency on other in-flight Sprint 7 stories.

## Priority: Medium

## Notes

### Deferred pre-existing items (context / future scope — NOT acceptance criteria)
These were identified during Sprint 7 but are larger or more ambiguous, so they are explicitly
**out of scope** for 7-17 and tracked here for future sprints:
1. **Saga sacrifice dead scheduled trigger** — `sacrifice_saga:{perm.id}` is scheduled at
   `turn_manager.py:279` but has no resolver; the trigger is queued but never resolved.
2. **`mana_spent` does not fire for non-cast payments** — kicker / buyback / replicate /
   activated-ability mana payments do not emit the `mana_spent` trigger (only spell-cast
   payments do).
3. **Cycling endpoint does not deduct the cycle cost** — the cycling API route does not subtract
   the cycle cost from the mana pool (pre-existing, documented at `game.py:~1001`).
4. **`pending_triggers` shallow copy under `model_copy`** — the `pending_triggers` list is a
   shallow copy when a `GameState` is copied; a deep-copy pass is a future task.
5. ~~**Investigate token-creation double-queues for token-fallback-phrased watchers** (7-3)~~
   — **RESOLVED in 7-3 test round 1 fix** (pattern-ownership split: token-ETB phrasings
   "whenever a/an [clue|investigate] token enters the battlefield" are owned by the
   token-trigger path `check_token_triggers`; removed from `INVESTIGATED_TRIGGER_PATTERNS` so
   each watcher fires exactly once).

### Suggested ordering within the story
Item **4** (negative unit test) and item **5** (coverage) are the lowest-risk, test-only
additions — start there. Items **1**, **2**, **3** are behavioral fixes and should each be
verified with a full regression run.

### Ambiguity note (item 1)
The CR 903.9 Commander-on-sacrifice fix could be a full pending-choice implementation or a
documented accepted gap. The team should decide which; the acceptance criteria cover both
outcomes.

### Relationship to 7-10 / 7-16ab
`SPRINT7-P2-trigger-patterns.md` (7-10) and `story-trg-unattach.md` (7-16ab) may also touch
attach/unattach patterns. If 7-10 lands first, item 2 here should be re-scoped to avoid
duplicate work — coordinate before implementing.

**Resolved 2026-08-20 (readiness audit):** 7-10's 9-pattern list is fully superseded by 7-2/7-3 —
see the "Implementation Status Audit" appended to `SPRINT7-P2-trigger-patterns.md`. Its only
remaining work is the unattach call site, which is exactly this story's item 2. Item 2 here is
therefore the **canonical owner** of the unattach work; `story-trg-unattach.md` (low priority,
no code refs) is a duplicate to close/consolidate at planning time.

### Readiness audit (2026-08-20, code review agent — pre-implementation)
- Code refs refreshed against post-7-3 line numbers: `triggers.py:1092`→`1125` (attached_controller lookup); `stack.py:1317/2023/2054`→`1341/2097/2133` (check_token_triggers import+call lines; `effects/base.py:288` and `loyalty.py:235` verified unchanged); `game.py:966`→`968` (cycle endpoint); `turn_manager.py:224-227`→`~207-232` (Fading upkeep block); `turn_manager.py:265-275`→`279` (sacrifice_saga scheduling). `zones.py:826` (`_sacrifice_permanent`) verified unchanged.
- Test baseline updated: 2798 → **2816** passed (3 skipped / 13 xfailed) — the 7-3 story added 18 tests after this file's baseline was written.
- Dependency status updated: 7-3 closed 2026-08-20 (Code Review r3 APPROVED).
- Deferred note 3 (cycling endpoint cost-not-deducted) re-verified still accurate — the limitation comment sits at `game.py:1001-1002`.
- Suggested ordering stands: items **4** + **5** (test-only) are the safe starting point.
