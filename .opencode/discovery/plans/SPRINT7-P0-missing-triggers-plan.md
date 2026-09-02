# Technical Plan: P0 Missing Triggers — Countered and Investigated (Story 7-3)

> Companion plan for `.opencode/discovery/SPRINT7-P0-missing-triggers.md`.
> This document is the **how**: architecture, exact wiring points, task breakdown, and test plan.
> The story file is the **what/why**.

---

## 1. Overview

Two trigger categories are completely absent from `mtg_engine/engine/triggers.py` (no regex
patterns, no check functions) and are not fired anywhere in the engine:

1. **Countered** (CR 701.5) — "whenever a spell is countered" / "whenever a spell you control
   is countered" / "whenever this is countered". Needed for any card that responds to a
   counterspell (e.g. [[Torrent of Souls]], [[Spellstutter Sprite]]).
2. **Investigated** (CR 701.32) — "whenever you investigate" / "whenever a player investigates".
   Needed for clue/investigate-based cards (e.g. [[Tamiyo's Journal]]-style follow-ups).

This plan adds, for each category: a `*_TRIGGER_PATTERNS` regex list, a pure-transform
`check_*_triggers()` function, and an engine call site. It also **implements the investigate
game action itself**, which does not exist in the engine today (verified: the strings
"investigate" and "clue" appear nowhere in `mtg_engine/engine/stack.py`).

Both new trigger types resolve through the **existing** triggered-effect pipeline
(`put_trigger_on_stack` → `_apply_triggered_effect` → `_apply_single_effect_text`); no new
resolution dispatch is required.

**Scope guard:** This story adds trigger detection + wiring + the investigate action. It does
NOT implement the full "sacrifice a Clue token to draw" activated ability of the legacy Clue
token (that is out of scope; see Risks).

---

## 2. CR Grounding

### CR 701.5 — Countered (Counter)
> "To counter a spell or ability means to remove it from the stack. It's put into its owner's
> graveyard. A countered spell or ability doesn't resolve."

- **Game event:** a spell (or ability) on the stack is removed by a counter effect.
- **Triggered-ability phrasing:** "whenever a spell is countered", "whenever a spell you
  control is countered", "whenever this spell is countered" (self-referential).
- **Timing:** the event is observable at the moment the counter takes effect, **before** the
  spell object is removed from `game_state.stack`. Self-referential triggers ("whenever this
  is countered") need the source card's data to still be reachable, so the trigger must be
  queued **before** removal.

### CR 701.32 — Investigate (MODERN rules)
> "To investigate, a player looks at the top card of their library. If it's a land card, they
> reveal it and keep it revealed. Otherwise, they may put that card on the bottom of their
> library. Then they create a 1/1 red Goblin creature token with 'investigate'."

- **Game event:** a player performs the investigate action.
- **Triggered-ability phrasing:** "whenever you investigate", "whenever a player investigates".
- **Token created:** a **1/1 red Goblin creature token** with the **investigate** keyword.

> **DISCREPANCY (resolved):** The companion story `story-trg-investigated.md` and the Notes in
> `SPRINT7-P0-missing-triggers.md` reference the **legacy** Clue-token version of investigate
> (pre-2014: "create a Clue artifact token with '{2}, Sacrifice this artifact: Draw a card'").
> This plan implements the **MODERN CR 701.32** (1/1 red Goblin token with "investigate"), which
> is the current rules text and matches the story's own "1/1 red Goblin" reference in the task
> brief. The legacy Clue-token activated ability is **out of scope** (see Risks §7).

> **PATTERN NOTE (resolved):** The story AC lists a pattern "whenever a land is investigated".
> This is **not a real modern MTG triggered pattern** (investigate does not involve a land).
> This plan implements the real, high-value patterns and treats "whenever a land is
> investigated" as erroneous/low-value — **not implemented** (documented decision). The
> token-based variant "whenever (a|an) clue/investigate token enters the battlefield" IS
> implemented as a generic fallback for cards that key off the token rather than the action.

---

## 3. Current State (verified file:line)

### What exists today
| Item | Location | Notes |
|------|----------|-------|
| Pattern-list convention | `triggers.py:110-225` | `XXX_TRIGGER_PATTERNS = [_re.compile(...), ...]` |
| Combined registry | `triggers.py:228-260` | `TRIGGER_PATTERNS` dict maps `trigger_type -> list` |
| Closest analog check fn | `triggers.py:1381` `check_counter_triggers` | pattern-index selection + `_is_you_pattern` + "this" guard |
| `_is_you_pattern` helper | `triggers.py` (used at 1427) | "you"-controller filter |
| `PendingTrigger` model | `models/game.py` | `id, source_permanent_id, controller, trigger_type, effect_description, source_card_name, is_optional, trigger_data` |
| `put_trigger_on_stack` | `triggers.py:1865` | PendingTrigger → StackObject (`effects=[effect_description]`, `trigger_type`, `trigger_data`) |
| Triggered-effect resolution | `stack.py:806` `_apply_triggered_effect` | special-cases afterlife/undying/persist; **everything else → `_apply_single_effect_text`** |
| Single-effect pipeline | `stack.py:864` `_apply_single_effect_text` | `patterns = [...]` list of `(regex, handler)` |
| **Counter resolution** | `stack.py:1731-1749` `_counter_spell` | **the single counter path** |
| Counterspell effect pattern | `stack.py:1094` | `lambda m: _counter_spell(game_state, stack_obj.targets[0] ...)` |
| Token creation (basic) | `stack.py:1288` `_create_tokens` | hardcodes `keywords=[]`, `colors=[]` — **cannot** represent investigate token |
| Generic token trigger | `stack.py:1317` | `check_token_triggers` already fired on token creation (distinct from "investigated") |
| Zone-change listener | `triggers.py:274` `_on_zone_change` / `_matches_zone_change` | must NOT also fire countered/investigated (exact-once) |

### What does NOT exist (to be added)
- `COUNTERED_TRIGGER_PATTERNS` — absent.
- `check_countered_triggers()` — absent.
- `INVESTIGATED_TRIGGER_PATTERNS` — absent.
- `check_investigated_triggers()` — absent.
- **The investigate action** — absent from `stack.py` entirely.
- A keyword/color-capable token creation path for the 1/1 red Goblin "investigate" token.

### Naming corrections vs. the story
- Story says `_apply_counter()` → **real function is `_counter_spell()`** (`stack.py:1731`).
- Story says `_resolve_triggered_effect()` → **real function is `_apply_triggered_effect()`**
  (`stack.py:806`). No dispatch change needed there.

---

## 4. Architecture

### 4.1 Pattern constants (triggers.py)

Add near the other B1 patterns (after `MANA_SPENT_TRIGGER_PATTERNS`, ~line 225):

```
COUNTERED_TRIGGER_PATTERNS = [
    # index 0 — self-referential: "whenever this is countered" / "whenever ~ is countered"
    _re.compile(r"whenever (?:this|~) (?:spell )?is countered", _re.IGNORECASE),
    # index 1 — "you control" filter: "whenever a spell you control is countered"
    _re.compile(r"whenever (?:a|an) spell you control is countered", _re.IGNORECASE),
    # index 2 — general: "whenever a spell is countered" / "whenever a spell .* is countered"
    _re.compile(r"whenever (?:a|an) spell .*? is countered", _re.IGNORECASE),
]

INVESTIGATED_TRIGGER_PATTERNS = [
    # index 0 — "you" filter: "whenever you investigate"
    _re.compile(r"whenever you investigate", _re.IGNORECASE),
    # index 1 — general: "whenever a player investigates" / "whenever a player investigates"
    _re.compile(r"whenever a player investigates?", _re.IGNORECASE),
    # index 2 — token-based fallback: "whenever (a|an) clue/investigate token enters the battlefield"
    _re.compile(r"whenever (?:a|an) (?:clue|investigate) token enters the battlefield", _re.IGNORECASE),
]
```

Register both in the `TRIGGER_PATTERNS` dict (lines 228-260):
```
"countered": COUNTERED_TRIGGER_PATTERNS,
"investigated": INVESTIGATED_TRIGGER_PATTERNS,
```

**Pattern-index → filter mapping** (mirrors `check_counter_triggers`):
- `COUNTERED`: index 1 is a "you" pattern (`_is_you_pattern(1) == True`); indices 0 and 2 are
  not. Index 0 carries the self-referential "this" guard.
- `INVESTIGATED`: index 0 is a "you" pattern; indices 1 and 2 are not.

> **Exact-once guard:** These patterns are matched ONLY inside their dedicated check functions,
> which are called ONLY from the two new wiring points. They are NOT referenced by
> `_on_zone_change` / `_matches_zone_change`, so a countered spell or an investigate token
> entering the battlefield will not also be picked up by the generic zone-change listener.

### 4.2 Check functions (triggers.py) — pure transforms

Both follow the canonical shape of `check_counter_triggers` (line 1381).

#### `check_countered_triggers(game_state, countered_stack_obj) -> GameState`
- **Args:**
  - `game_state: GameState`
  - `countered_stack_obj: StackObject` — the spell object being countered (still on the stack at
    call time, so its `source_card` data is readable for self-referential triggers).
- **Behavior:**
  - `new_triggers = list(game_state.pending_triggers)`
  - For each `perm` in `game_state.battlefield`:
    - Parse `perm.card.oracle_text` → for each `TriggeredAbility` `ab`:
      - `cond = ab.trigger_condition.lower()`
      - **Self-referential guard (index 0):** if the matched pattern is index 0 ("this"/"~"),
        fire only if the countered spell's source card is this permanent's card
        (`countered_stack_obj.source_card.name == perm.card.name` **and** the spell is this
        permanent's own spell — for a creature's "whenever this is countered" the countered
        object must be a spell/ability sourced by this permanent). Simplest correct check:
        `countered_stack_obj.source_card.name == perm.card.name`.
      - Match against `COUNTERED_TRIGGER_PATTERNS` by index.
      - **"you" filter (index 1):** `_is_you_pattern(1) and perm.controller != countered_stack_obj.controller`
        → skip (a "spell you control is countered" trigger fires only when the countered spell
        is controlled by the watcher).
      - Queue `PendingTrigger(trigger_type="countered", effect_description=ab.effect,
        source_permanent_id=perm.id, controller=perm.controller, source_card_name=perm.card.name,
        is_optional=ab.effect.lower().startswith("you may"))`.
  - `return game_state.model_copy(update={"pending_triggers": new_triggers})`
- **Note:** the "actor" for the "you control" filter is the **controller of the countered spell**
  (`countered_stack_obj.controller`), not a separate player arg — "a spell you control is
  countered" means the watcher controls the countered spell.

#### `check_investigated_triggers(game_state, player_name) -> GameState`
- **Args:**
  - `game_state: GameState`
  - `player_name: str` — the player who just investigated (the "you" for "whenever you
    investigate"; the actor for "whenever a player investigates").
- **Behavior:**
  - `new_triggers = list(game_state.pending_triggers)`
  - For each `perm` in `game_state.battlefield`:
    - Parse `perm.card.oracle_text` → for each `TriggeredAbility` `ab`:
      - `cond = ab.trigger_condition.lower()`
      - Match against `INVESTIGATED_TRIGGER_PATTERNS` by index.
      - **"you" filter (index 0):** `_is_you_pattern(0) and perm.controller != player_name` → skip.
      - Queue `PendingTrigger(trigger_type="investigated", effect_description=ab.effect,
        source_permanent_id=perm.id, controller=perm.controller, source_card_name=perm.card.name,
        is_optional=ab.effect.lower().startswith("you may"))`.
  - `return game_state.model_copy(update={"pending_triggers": new_triggers})`

### 4.3 Wiring points (stack.py)

#### Countered — inside `_counter_spell` (stack.py:1731)
Insert **after** the uncounterable guard (lines 1740-1742) and **before** the stack removal
(line 1743):

```
# (existing) if countered.uncounterable: ... return game_state
# NEW: fire "countered" triggers BEFORE the spell leaves the stack (CR 701.5)
from mtg_engine.engine.triggers import check_countered_triggers as _check_countered
game_state = _check_countered(game_state, countered)
# (existing) game_state.stack[:] = [s for s in game_state.stack if s.id != target_id]
```
- The call site **captures** the returned `game_state` (pure transform).
- Because it runs before line 1743, `countered.source_card` is still intact for self-referential
  triggers.
- The uncounterable early-return (1740-1742) means the trigger does **not** fire when the
  counter effect does nothing (correct per CR 702.102).

#### Investigated — new "investigate" pattern in `_apply_single_effect_text` (stack.py:864)
Add a `(regex, handler)` entry to the `patterns = [...]` list. The handler implements MODERN
CR 701.32:

```
(r"\binvestigate\b", lambda m: _investigate(game_state, stack_obj.controller))
```

New helper `_investigate(game_state, player_name) -> GameState` (place near `_create_tokens`,
~stack.py:1288):
1. `player = get_player(game_state, player_name)`
2. If `player.library` is non-empty:
   - `top = player.library[0]`
   - If `top.type_line` contains "land": reveal + keep revealed. **Representation decision:**
     move `top` from `library` to `player.hand` and log it as revealed (simplest correct
     representation in this engine; document it). *(Alternative: a dedicated revealed zone —
     rejected as over-scope.)*
   - Else: **AI default** = put on bottom (`player.library.append(player.library.pop(0))`);
     **human** = same default for this story (a "may put on bottom" pending-choice is
     out of scope; document as a known simplification).
3. Create the **1/1 red Goblin "investigate" token** (see 4.4).
4. `game_state = check_investigated_triggers(game_state, player_name)` (capture return).
5. `return game_state`

> The pattern `\binvestigate\b` matches the standalone instruction "Investigate." in oracle
> text (e.g. "At the beginning of your upkeep, investigate."). It must be ordered so it is not
> shadowed by a broader pattern; place it with the other action patterns and verify no existing
> pattern already consumes "investigate" (verified: none does).

### 4.4 Token creation for the investigate token
`_create_tokens` (stack.py:1288) hardcodes `keywords=[]` and `colors=[]`, so it cannot build the
investigate token. Two options (choose one; recommend **Option A**):

- **Option A (recommended):** add a small keyword/color-capable helper
  `_create_token_with_pt_and_keywords(game_state, controller, power, toughness, subtypes,
  keywords, colors) -> GameState` that mirrors `_create_tokens` but accepts `keywords` and
  `colors`, and build the token as:
  `name="Goblin Token"`, `type_line="Token Creature — Goblin"`, `power="1"`, `toughness="1"`,
  `keywords=["investigate"]`, `colors=["R"]`. Reuse it from `_investigate`. (This also de-risks
  the 7-17 "per-token firing" follow-up by centralizing token creation.)
- **Option B:** extend `_create_tokens` with optional `keywords=None, colors=None` params
  (backward compatible). Slightly less clean (overloads an existing signature).

Either way, the token is created via `put_permanent_onto_battlefield(..., is_token=True)`, which
already fires the generic `check_token_triggers` (stack.py:1317) — so both "token created" and
"investigated" fire on investigate (correct).

### 4.5 Resolution flow (no change required)
`check_*` queue `PendingTrigger` → `put_trigger_on_stack` (triggers.py:1865) builds a
`StackObject(effects=[effect_description], trigger_type="countered"|"investigated")` →
`_apply_triggered_effect` (stack.py:806) sees a non-keyword `trigger_type` → delegates to
`_apply_single_effect_text`, which resolves the effect text (draw, create token, etc.). **No
dispatch edits** in `_apply_triggered_effect`.

---

## 5. Task Breakdown

Ordered; each task is small and independently verifiable. "Verify" = the listed tests pass and
no regressions.

### Countered
- **T1.** Add `COUNTERED_TRIGGER_PATTERNS` to `triggers.py` + register in `TRIGGER_PATTERNS`
  dict. *Verify:* import succeeds; patterns compile; a quick regex sanity check in a scratch
  test (or the unit tests in T5).
- **T2.** Implement `check_countered_triggers(game_state, countered_stack_obj)` in `triggers.py`
  (pure transform; self-referential guard on index 0; "you" filter on index 1). *Verify:* unit
  tests (T5) — positive, "you control" negative, self-ref guard, no-match.
- **T3.** Wire `check_countered_triggers` into `_counter_spell` (stack.py) **before** line 1743,
  after the uncounterable guard; capture the returned `game_state`. *Verify:* integration test
  (T6) — countered spell fires via the real `_counter_spell` entry point; uncounterable does not.

### Investigated
- **T4.** Add `INVESTIGATED_TRIGGER_PATTERNS` to `triggers.py` + register in `TRIGGER_PATTERNS`
  dict. *Verify:* patterns compile.
- **T4a.** Implement the keyword/color-capable token helper (Option A) in `stack.py`. *Verify:*
  helper creates a 1/1 red Goblin token with `keywords=["investigate"]` (unit test).
- **T4b.** Implement `_investigate(game_state, player_name)` in `stack.py` (modern CR 701.32:
  look at top; land→reveal/keep; else→bottom; create token; call `check_investigated_triggers`).
  *Verify:* unit test — library top land revealed; non-land to bottom; token created; trigger
  queued.
- **T4c.** Add the `investigate` pattern to `_apply_single_effect_text` (stack.py:864) calling
  `_investigate`. *Verify:* integration test (T7) — a resolving "investigate" effect fires the
  trigger through the real pipeline.
- **T5 (unit, both).** Add unit tests for both check functions (pattern matching + filters).
  *Verify:* all pass.
- **T6/T7 (integration, both).** Add natural-context integration tests (see Test Plan). *Verify:*
  all pass.

### Cross-cutting
- **T8.** Run the full regression suite; confirm **2798 passed / 3 skipped / 13 xfailed** with the
  new tests added (skip/xfail set byte-identical). *Verify:* `pytest` green, no regressions.

---

## 6. Test Plan

Follow the two existing conventions:
- **Unit** style: `tests/engine/test_triggers_expanded.py` (call the check function directly,
  assert on `pending_triggers`).
- **Natural-context integration** style: `tests/engine/test_trigger_wiring_integration.py`
  (drive the **real engine entry point**, assert the trigger lands in `pending_triggers` AND the
  real state change happened).

### New file: `tests/engine/test_countered_trigger_integration.py`
Helpers: `_make_gs`, `_perm`, `_trigger_types` (copy the convention from
`test_trigger_wiring_integration.py`).

Unit-style cases (check function directly):
1. `test_countered_pattern_matches` — "whenever a spell is countered" queues a
   `trigger_type="countered"` PendingTrigger.
2. `test_countered_you_control_negative` — "whenever a spell you control is countered" does NOT
   fire when the countered spell is controlled by the opponent (watcher.controller ≠
   countered.controller).
3. `test_countered_self_referential_guard` — "whenever this is countered" fires only when the
   countered spell's source card is this permanent's card.
4. `test_countered_no_match` — a permanent with no countered text queues nothing.

Natural-context cases (real `_counter_spell` entry point):
5. `test_countered_fires_via_counter_spell` — put a watcher ("whenever a spell is countered,
   draw a card") on the battlefield; put a spell on the stack; call
   `_counter_spell(gs, spell_id)`; assert the spell left the stack, moved to graveyard, AND
   `"countered" in _trigger_types(gs)`.
6. `test_countered_not_fired_on_uncounterable` — target spell has `uncounterable=True`;
   `_counter_spell` returns early; assert **no** "countered" trigger and the spell is still on
   the stack.
7. `test_countered_not_fired_on_non_counter_removal` — remove a spell from the stack by a
   non-counter means (e.g. directly, or a "bounce to hand" style removal that does not call
   `_counter_spell`); assert **no** "countered" trigger.
8. `test_countered_multiple_permanents` — two watchers with countered text; one countered spell;
   assert **both** queue triggers.

### New file: `tests/engine/test_investigated_trigger_integration.py`
Unit-style cases:
1. `test_investigated_pattern_matches` — "whenever you investigate" queues
   `trigger_type="investigated"`.
2. `test_investigated_you_negative` — "whenever you investigate" does NOT fire for a watcher
   controlled by the opponent of the investigating player.
3. `test_investigated_no_match` — a permanent with no investigate text queues nothing.

Natural-context cases (real investigate pipeline):
4. `test_investigate_fires_via_effect` — watcher "whenever you investigate, draw a card"; a
   resolving effect with oracle text "investigate" (drive `_apply_single_effect_text` / a cast
   that resolves it); assert a 1/1 red Goblin "investigate" token is on the battlefield AND
   `"investigated" in _trigger_types(gs)`.
5. `test_investigate_non_investigate_token_does_not_fire` — create a token via a non-investigate
   effect (e.g. `_create_tokens` for a Bird); assert **no** "investigated" trigger (only the
   generic "token" trigger, if any).
6. `test_investigate_multiple_permanents` — two watchers; one investigate; assert both fire.
7. `test_investigate_token_is_1_1_red_goblin` — assert the created token has `power="1"`,
   `toughness="1"`, `colors=["R"]`, subtype "Goblin", `keywords` contains "investigate".

### Regression
- Full suite: `pytest` → expect **2798 + (new) passed / 3 skipped / 13 xfailed**, 0 failures,
  skip/xfail set byte-identical to baseline.

---

## 7. Risks / Edge Cases

1. **Legacy Clue-token activated ability (out of scope).** Modern investigate creates a Goblin
   token with "investigate", not a Clue artifact with "{2}, Sacrifice: Draw". This plan does NOT
   implement the Clue token's sacrifice-to-draw ability. If a card in a test deck relies on it,
   that is a separate story. **Mitigation:** document explicitly; scope the token to the modern
   representation.
2. **"whenever a land is investigated" is not a real pattern.** Not implemented (documented
   decision in §2). If a future card genuinely uses such phrasing, add a pattern then.
3. **Self-referential "whenever this is countered" semantics.** A creature's "whenever this is
   countered" refers to the creature's own spell/ability being countered. The simple
   name-equality check (`countered.source_card.name == perm.card.name`) is the pragmatic
   approximation used elsewhere in this engine. Edge: two different cards sharing a name could
   false-match — acceptable given the engine's existing name-based identity model.
4. **Investigate "may put on bottom" for humans.** This story auto-puts non-land cards on the
   bottom (no pending choice). A human "may" choice is a known simplification; document it.
   **Mitigation:** keep the decision in one place (`_investigate`) so a pending-choice can be
   added later without touching the trigger wiring.
5. **Revealed-land representation.** Moving the revealed land to `hand` is the simplest correct
   representation. If the engine later gains a dedicated revealed/face-up-out-of-library zone,
   relocate this. **Mitigation:** isolate in `_investigate`.
6. **Exact-once / double-fire.** Ensure the new patterns are referenced ONLY by their check
   functions and NOT by `_on_zone_change`/`_matches_zone_change`. A countered spell leaving the
   stack and an investigate token entering the battlefield both emit zone-change events; the
   generic listener must not also queue "countered"/"investigated". **Mitigation:** the patterns
   are not added to any zone-change path; add a negative test (T6.7 / T5.5) proving no
   double-fire.
7. **Pattern shadowing in `_apply_single_effect_text`.** The `investigate` pattern must not be
   consumed by a broader earlier pattern. **Mitigation:** verify ordering; the standalone
   `\binvestigate\b` is specific enough, and no existing pattern matches it (verified).
8. **Token helper choice (Option A vs B).** Option A (new helper) is cleaner and de-risks the
   7-17 per-token follow-up; Option B overloads an existing signature. **Mitigation:** pick
   Option A; keep `_create_tokens` untouched for backward compatibility.

---

## 8. Quality Bars Checklist (from 7-2 lessons)

- [ ] **Q1 — Exact-once registration.** Each new pattern lives in exactly one pattern-list
      constant (`COUNTERED_TRIGGER_PATTERNS` / `INVESTIGATED_TRIGGER_PATTERNS`) + the
      `TRIGGER_PATTERNS` dict. Countered/Investigated do NOT double-fire through the generic
      zone-change listener (`_on_zone_change`/`_matches_zone_change`). Negative tests prove it.
- [ ] **Q2 — Self-referential + "you" filters.** "this"/"~" guard on countered index 0;
      `_is_you_pattern` controller filter on countered index 1 and investigated index 0.
- [ ] **Q3 — Pre-removal capture.** `check_countered_triggers` is called in `_counter_spell`
      **before** the stack removal (line 1743), so self-referential triggers can read the card.
- [ ] **Q4 — Pure transforms.** Both check functions return a new `GameState` via
      `model_copy(update={"pending_triggers": ...})`; every call site captures the return
      (`gs = check_...(gs, ...)`).
- [ ] **Q5 — Unit + natural-context tests.** Unit tests (check functions) AND ≥1 natural-context
      integration test per wiring driving the REAL entry point (`_counter_spell`; the
      investigate effect pattern). Each trigger type has ≥4 integration tests: positive,
      negative, self-ref guard, multiple permanents.
- [ ] **Q6 — Regression baseline.** Full suite: **2798 passed / 3 skipped / 13 xfailed**; new
      tests only ADD passed; skip/xfail set byte-identical.
