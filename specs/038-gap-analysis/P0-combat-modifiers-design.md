# Design: P0 Combat Modifiers Refactor (Deathtouch, Lifelink, Infect)

## Overview
Refactor three combat-modifying keywords—**Deathtouch**, **Lifelink**, and **Infect**—from inline engine mutations into GameState-aware keyword modules using `model_copy` pure transforms. Currently, all modifier logic is scattered across `combat/core.py`, `stack.py`, and `replacement.py` with direct mutations of `player.life`, `perm.damage_marked`, and `perm.counters`. This design consolidates that logic into the existing keyword classes while preserving the `__deathtouch_damage__` counter mechanism required by SBA.

## User Story Reference
- Gap analysis category: **169 keywords** from `specs/038-gap-analysis/plan.md`
- Priority P0 — these three keywords are actively used in combat, spell damage, and replacement effects across the engine

## Architecture Decisions

### 1. All three keywords remain `PassiveKeyword` subclasses
Deathtouch, Lifelink, and Infect are static abilities (CR 702.2, 702.15, 702.90) — they don't trigger; they modify how damage is processed. They inherit from `PassiveKeyword`, which already provides the correct `applies()` default implementation.

**Trade-off considered**: Could create a new `DamageModifierKeyword` subclass. Rejected because `PassiveKeyword` already has the right semantics and all three keywords share the same pattern: check presence, modify damage application.

### 2. Each keyword gets module-level GameState-aware functions
The base class `apply(game_state, permanent, target)` signature is too generic for damage modifiers. We add module-level functions like `apply_deathtouch_damage()`, `apply_lifelink_to_gamestate()`, and `apply_infect_damage()` that take `(game_state, source_perm, target_id/perm, damage_amount)` and return a new `GameState` with the appropriate side effects applied (life gain, poison counters, -1/-1 counters, deathtouch tracking).

**Trade-off considered**: Could overload `apply()`. Rejected because module-level functions are more discoverable via import and match the existing pattern used by hexproof/shroud (`is_hexproof(gs, perm_id)`).

### 3. Damage application follows a unified dispatch pattern
Engine code calls into keyword modules via a centralized `_apply_damage_modifiers()` helper in each integration point, rather than checking keywords inline:

```python
# Before (inline):
has_deathtouch = _has_keyword(source, "deathtouch")
has_lifelink   = _has_keyword(source, "lifelink")
has_infect     = _has_keyword(source, "infect")
if has_infect: ...
elif has_deathtouch: ...

# After (dispatch):
game_state, was_infect = _apply_damage_modifiers(game_state, source_perm, target_id, damage_amount)
```

**Trade-off considered**: Could use the keyword registry for dispatch. Rejected because we only need these three specific keywords; a registry lookup adds indirection without benefit.

### 4. `__deathtouch_damage__` counter mechanism is preserved exactly
SBA (`sba.py` lines 170-205) checks `perm.counters.get("__deathtouch_damage__", 0) > 0` to destroy deathtouch-damaged creatures. The refactored Deathtouch module MUST continue setting this counter on the target permanent. No changes to SBA logic are needed or desired.

### 5. Infect and Wither share a common damage application pattern
Infect (CR 702.90) and Wither (CR 702.129) both put -1/-1 counters on creatures instead of marking damage. The difference: Infect also converts player damage to poison counters; Wither does not. We implement this as a shared helper `_apply_infect_or_wither_damage_to_creature()` in `infect.py` that both keywords can use.

### 6. Poisonous remains out of scope for main refactor
Poisonous (CR 702.118) is a triggered ability, not a passive damage modifier. It's already partially implemented in `infect.py` but has mutability bugs (`player.poison_counters += ...`). We fix the mutability as part of T3 but don't wire it into the dispatcher — that's deferred to a separate task.

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/ability/keywords/deathtouch.py` | Add `apply_deathtouch_damage()` function returning new GameState via model_copy; add `has_deathtouch_perm()` query helper | Consolidate deathtouch damage logic from inline engine code |
| `mtg_engine/ability/keywords/lifelink.py` | Add `apply_lifelink_to_gamestate()` function returning new GameState via model_copy; add `has_lifelink_perm()` query helper | Consolidate lifelink life-gain from inline engine code |
| `mtg_engine/ability/keywords/infect.py` | Refactor `InfectKeyword` to inherit from `PassiveKeyword`; add `apply_infect_damage()` function; refactor `WitherKeyword` similarly; fix `PoisonousKeyword.apply()` mutability | Consolidate infect/wither damage logic, align with keyword class hierarchy |
| `mtg_engine/engine/combat/core.py` | Replace inline deathtouch/lifelink/infect handling (lines 617-683) with calls to keyword module functions; convert all direct mutations to model_copy transforms | Remove ~60 lines of inline modifier logic, fix mutability |
| `mtg_engine/engine/stack.py` | Replace `_deal_damage()` deathtouch tracking (lines 1462-1492) with keyword module call; add lifelink/infect handling to spell damage path | Unify spell damage and combat damage modifier application |
| `mtg_engine/engine/replacement.py` | Replace inline deathtouch/lifelink/infect in `apply_damage_event()` (lines 269-307) with keyword module calls; convert mutations to model_copy | Remove duplicate modifier logic from replacement effects |

### New Files
None — all changes are to existing files.

## Data Models / Interfaces

### Deathtouch Module Interface (`deathtouch.py`)

```python
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Deathtouch(PassiveKeyword):
    """Deathtouch keyword ability (CR 702.2)."""

    name = "deathtouch"

    @staticmethod
    def has_deathtouch(keywords: list[str]) -> bool:
        return "deathtouch" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return "deathtouch" in oracle_text.lower()

    @staticmethod
    def is_lethal(damage: int, target_toughness: int) -> bool:
        return damage > 0

    @staticmethod
    def min_lethal_damage() -> int:
        return 1


def has_deathtouch_perm(game_state: GameState, perm_id: str) -> bool:
    """Query helper: check if a permanent on the battlefield has deathtouch."""
    for perm in game_state.battlefield:
        if perm.id == perm_id:
            return Deathtouch.has_deathtouch(perm.card.keywords or [])
    return False


def apply_deathtouch_damage(
    game_state: GameState,
    source_perm: Permanent,
    target_perm: Permanent | None,
    damage_amount: int,
) -> GameState:
    """Apply deathtouch tracking to a damaged creature.

    CR 702.2b: Any amount of damage greater than 0 that's dealt to a creature
    by a source with deathtouch is considered to be lethal damage.

    Sets __deathtouch_damage__ counter on target for SBA destruction (CR 704.5h).

    Args:
        game_state: Current game state.
        source_perm: The permanent dealing the damage (must have deathtouch).
        target_perm: The creature receiving damage (None if player/planeswalker).
        damage_amount: Amount of damage dealt.

    Returns:
        New GameState with __deathtouch_damage__ counter set on target.
    """
    if not Deathtouch.has_deathtouch(source_perm.card.keywords or []):
        return game_state

    if damage_amount <= 0:
        return game_state

    if target_perm is None:
        return game_state

    # Target is a planeswalker — deathtouch doesn't apply to PWs
    if "planeswalker" in (target_perm.card.type_line or "").lower():
        return game_state

    new_counters = dict(target_perm.counters)
    current = new_counters.get("__deathtouch_damage__", 0)
    new_counters["__deathtouch_damage__"] = current + damage_amount

    new_target = target_perm.model_copy(update={"counters": new_counters})

    battlefield = [
        new_target if p.id == target_perm.id else p
        for p in game_state.battlefield
    ]

    return game_state.model_copy(update={"battlefield": battlefield})
```

### Lifelink Module Interface (`lifelink.py`)

```python
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Lifelink(PassiveKeyword):
    """Lifelink keyword ability (CR 702.15)."""

    name = "lifelink"

    @staticmethod
    def has_lifelink(keywords: list[str]) -> bool:
        return "lifelink" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return "lifelink" in oracle_text.lower()

    @staticmethod
    def apply_lifelink_gain(controller_life: int, damage: int) -> int:
        return controller_life + damage


def has_lifelink_perm(game_state: GameState, perm_id: str) -> bool:
    """Query helper: check if a permanent on the battlefield has lifelink."""
    for perm in game_state.battlefield:
        if perm.id == perm_id:
            return Lifelink.has_lifelink(perm.card.keywords or [])
    return False


def apply_lifelink_to_gamestate(
    game_state: GameState,
    source_perm: Permanent,
    damage_amount: int,
) -> GameState:
    """Apply lifelink life gain to the source's controller.

    CR 702.15b: Whenever a source you control with lifelink deals damage,
    you gain that much life.

    Args:
        game_state: Current game state.
        source_perm: The permanent dealing the damage (must have lifelink).
        damage_amount: Amount of damage dealt.

    Returns:
        New GameState with controller's life increased by damage amount.
    """
    if not Lifelink.has_lifelink(source_perm.card.keywords or []):
        return game_state

    if damage_amount <= 0:
        return game_state

    new_players = []
    for player in game_state.players:
        if player.name == source_perm.controller:
            new_life = player.life + damage_amount
            new_players.append(player.model_copy(update={"life": new_life}))
        else:
            new_players.append(player)

    return game_state.model_copy(update={"players": new_players})
```

### Infect Module Interface (`infect.py`)

```python
from __future__ import annotations
import re
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class InfectKeyword(PassiveKeyword):
    """Infect keyword (CR 702.90)."""

    name = "infect"

    @staticmethod
    def has_infect(keywords: list[str]) -> bool:
        return "infect" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return "infect" in oracle_text.lower()


class WitherKeyword(PassiveKeyword):
    """Wither keyword (CR 702.129)."""

    name = "wither"

    @staticmethod
    def has_wither(keywords: list[str]) -> bool:
        return "wither" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return "wither" in oracle_text.lower()


def _apply_infect_or_wither_damage_to_creature(
    game_state: GameState,
    target_perm: Permanent,
    damage_amount: int,
) -> GameState:
    """Put -1/-1 counters on a creature instead of marking damage.

    Used by both Infect (CR 702.90b) and Wither (CR 702.129b).
    Returns new GameState with updated battlefield.
    """
    new_counters = dict(target_perm.counters)
    current = new_counters.get("-1/-1", 0)
    new_counters["-1/-1"] = current + damage_amount

    new_target = target_perm.model_copy(update={"counters": new_counters})

    battlefield = [
        new_target if p.id == target_perm.id else p
        for p in game_state.battlefield
    ]

    return game_state.model_copy(update={"battlefield": battlefield})


def apply_infect_damage(
    game_state: GameState,
    source_perm: Permanent,
    target_id: str,
    damage_amount: int,
) -> GameState:
    """Apply infect damage to a creature or player.

    CR 702.90b: Damage dealt to creatures by a source with infect causes
    that many -1/-1 counters to be put on that creature.
    CR 702.90c: Damage dealt to a player by a source with infect causes
    that player to get that many poison counters.

    Returns new GameState with -1/-1 counters on creatures or poison on players.
    """
    if not InfectKeyword.has_infect(source_perm.card.keywords or []):
        return game_state

    if damage_amount <= 0:
        return game_state

    target_perm = None
    for perm in game_state.battlefield:
        if perm.id == target_id:
            target_perm = perm
            break

    if target_perm is not None:
        # Infect damage to creature -> -1/-1 counters (CR 702.90b)
        return _apply_infect_or_wither_damage_to_creature(
            game_state, target_perm, damage_amount
        )

    # Target is a player -> poison counters (CR 702.90c)
    new_players = []
    for player in game_state.players:
        if player.name == target_id:
            new_poison = player.poison_counters + damage_amount
            new_has_lost = True if new_poison >= 10 else False
            new_players.append(player.model_copy(
                update={"poison_counters": new_poison, "has_lost": new_has_lost}
            ))
        else:
            new_players.append(player)

    return game_state.model_copy(update={"players": new_players})


def apply_wither_damage(
    game_state: GameState,
    source_perm: Permanent,
    target_id: str,
    damage_amount: int,
) -> GameState:
    """Apply wither damage to a creature.

    CR 702.129b: Damage dealt to creatures by a source with wither causes
    that many -1/-1 counters to be put on that creature.

    Unlike infect, wither does NOT affect player damage (normal life loss).
    """
    if not WitherKeyword.has_wither(source_perm.card.keywords or []):
        return game_state

    if damage_amount <= 0:
        return game_state

    target_perm = None
    for perm in game_state.battlefield:
        if perm.id == target_id:
            target_perm = perm
            break

    if target_perm is not None:
        return _apply_infect_or_wither_damage_to_creature(
            game_state, target_perm, damage_amount
        )

    # Wither doesn't modify player damage — caller handles normal life loss
    return game_state


class PoisonousKeyword(PassiveKeyword):
    """Poisonous keyword (CR 702.118)."""

    name = "poisonous"
    poison_amount: int = 0

    @staticmethod
    def from_oracle_text(oracle_text: str) -> Optional["PoisonousKeyword"]:
        if not oracle_text:
            return None
        m = re.search(r"poisonous\s+(\d+)", oracle_text.lower())
        if m:
            return PoisonousKeyword(poison_amount=int(m.group(1)))
        return None

    def apply_poisonous(
        self, game_state: GameState, target_player_name: str
    ) -> GameState:
        """Apply poisonous effect — add poison counters to player.

        Returns new GameState with updated player state (pure transform).
        """
        new_players = []
        for player in game_state.players:
            if player.name == target_player_name:
                new_poison = player.poison_counters + self.poison_amount
                new_has_lost = True if new_poison >= 10 else False
                new_players.append(player.model_copy(
                    update={"poison_counters": new_poison, "has_lost": new_has_lost}
                ))
            else:
                new_players.append(player)

        return game_state.model_copy(update={"players": new_players})
```

### Unified Damage Modifier Dispatcher

A shared helper function that engine code calls to apply all three modifiers at once. Defined in each integration point (combat/core.py, stack.py, replacement.py):

```python
def _apply_damage_modifiers(
    game_state: GameState,
    source_perm: Permanent,
    target_id: str,
    damage_amount: int,
) -> tuple[GameState, bool]:
    """Apply deathtouch/lifelink/infect modifiers to a damage event.

    Returns (new_game_state, was_infect_damage).
    The boolean indicates if infect handled the creature/player damage, so the caller
    knows NOT to also mark normal damage or subtract life from the target.
    """
    from mtg_engine.ability.keywords.deathtouch import apply_deathtouch_damage
    from mtg_engine.ability.keywords.lifelink import apply_lifelink_to_gamestate
    from mtg_engine.ability.keywords.infect import apply_infect_damage, InfectKeyword

    source_keywords = source_perm.card.keywords or []

    # 1. Check if infect handles the damage (replaces normal damage on creatures/players)
    has_infect = InfectKeyword.has_infect(source_keywords)

    if has_infect:
        game_state = apply_infect_damage(game_state, source_perm, target_id, damage_amount)
        return game_state, True  # Infect handled it — caller skips normal damage

    # 2. Deathtouch tracking (doesn't replace damage, just adds counter for SBA)
    target_perm = next((p for p in game_state.battlefield if p.id == target_id), None)
    game_state = apply_deathtouch_damage(game_state, source_perm, target_perm, damage_amount)

    # 3. Lifelink life gain (doesn't replace damage, just adds life to controller)
    game_state = apply_lifelink_to_gamestate(game_state, source_perm, damage_amount)

    return game_state, False
```

## Task Breakdown (Ordered by Dependency)

### T1: Refactor `deathtouch.py` — Add GameState-aware functions
- **Files**: `mtg_engine/ability/keywords/deathtouch.py`
- **Description**: Keep existing static helpers (`has_deathtouch`, `from_oracle_text`, `is_lethal`, `min_lethal_damage`). Add two new module-level functions:
  - `has_deathtouch_perm(game_state, perm_id) -> bool`: battlefield query helper
  - `apply_deathtouch_damage(game_state, source_perm, target_perm, damage_amount) -> GameState`: pure transform that sets `__deathtouch_damage__` counter on target creature via model_copy. Must handle: planeswalker targets (no-op), zero/negative damage (no-op), non-creature targets (no-op).
- **Acceptance Criteria**: Existing unit tests in `tests/ability/keywords/test_deathtouch.py` still pass; new functions are importable and return correct GameState objects

### T2: Refactor `lifelink.py` — Add GameState-aware functions
- **Files**: `mtg_engine/ability/keywords/lifelink.py`
- **Description**: Keep existing static helpers. Add two new module-level functions:
  - `has_lifelink_perm(game_state, perm_id) -> bool`: battlefield query helper
  - `apply_lifelink_to_gamestate(game_state, source_perm, damage_amount) -> GameState`: pure transform that increases controller's life by damage amount via model_copy. Must handle zero/negative damage (no-op).
- **Acceptance Criteria**: Existing unit tests in `tests/ability/keywords/test_lifelink.py` still pass; new functions are importable and return correct GameState objects

### T3: Refactor `infect.py` — Full module rewrite
- **Files**: `mtg_engine/ability/keywords/infect.py`
- **Description**: Major refactor of existing module:
  - Change `InfectKeyword` to inherit from `PassiveKeyword` (currently standalone)
  - Change `WitherKeyword` to inherit from `PassiveKeyword` (currently standalone)
  - Add `_apply_infect_or_wither_damage_to_creature()` shared helper for -1/-1 counter application
  - Add `apply_infect_damage(game_state, source_perm, target_id, damage_amount) -> GameState`: handles both creature (-1/-1 counters) and player (poison counters + has_lost check at >=10) targets
  - Add `apply_wither_damage(game_state, source_perm, target_id, damage_amount) -> GameState`: only affects creatures; returns unchanged state for player targets
  - Fix `PoisonousKeyword.apply_poisonous()` mutability: convert direct mutation to model_copy transform (out of scope for dispatcher wiring)
- **Acceptance Criteria**: Existing unit tests in `tests/ability/keywords/test_infect.py` still pass; new functions are importable and return correct GameState objects

### T4: Refactor `combat/core.py` — Replace inline modifier logic
- **Files**: `mtg_engine/engine/combat/core.py`
- **Description**: In the combat damage assignment loop (lines 617-683), replace all inline deathtouch/lifelink/infect handling with calls to `_apply_damage_modifiers()`. The current flow:
  1. Loop over attacker/defender pairs
  2. For each pair, check keywords inline and mutate `player.life`, `perm.damage_marked`, `perm.counters` directly
  3. Set `__deathtouch_damage__` counter for deathtouch tracking

  New flow:
  1. Loop over attacker/defender pairs (unchanged)
  2. Call `_apply_damage_modifiers(gs, source_perm, target_id, damage)` — returns new gs and was_infect flag
  3. If `was_infect` is False, proceed with normal damage marking (`perm.damage_marked += damage`) via model_copy
  4. If `was_infect` is True, skip normal damage marking (infect already handled counters)
  5. All player life changes go through model_copy transforms

- **Acceptance Criteria**: Existing tests in `tests/rules/test_combat.py`, `tests/ability/keywords/test_deathtouch.py`, `test_lifelink.py` still pass; no direct mutations of player.life or perm.damage_marked remain in the combat damage loop

### T5: Refactor `stack.py` — Unify spell damage modifier application
- **Files**: `mtg_engine/engine/stack.py`
- **Description**: In `_deal_damage()` (lines 1462-1492), replace inline deathtouch tracking with keyword module call. Currently only handles deathtouch via direct mutation of `__deathtouch_damage__` counter. New flow:
  1. Call `_apply_damage_modifiers(gs, source_perm, target_id, damage)` 
  2. If `was_infect`, skip normal damage application (infect handled it)
  3. Otherwise, apply normal damage to creature (`damage_marked`) or player (`life -= damage`) via model_copy

- **Acceptance Criteria**: Existing tests in `tests/rules/test_combat.py` and any spell-damage-related tests still pass; no direct mutations remain in `_deal_damage()`

### T6: Refactor `replacement.py` — Replace inline modifier logic
- **Files**: `mtg_engine/engine/replacement.py`
- **Description**: In `apply_damage_event()` (lines 254-307), replace inline deathtouch/lifelink/infect handling with keyword module calls. Convert all direct mutations to model_copy transforms. Same pattern as T4/T5: call `_apply_damage_modifiers()`, check was_infect flag, apply normal damage if needed via model_copy.

- **Acceptance Criteria**: Existing tests in `tests/rules/test_replacement.py` still pass; no direct mutations remain in `apply_damage_event()`

### T7: Create integration test suite
- **Files**: `tests/engine/test_combat_modifiers_integration.py` (new file)
- **Description**: 14-scenario integration test covering all three keywords across combat, spell damage, and replacement effects. See Testing Strategy section for scenario table. Each test verifies:
  - Correct side effect (counters, life gain, poison)
  - Pure transform (original GameState unchanged)
  - Interaction with SBA where applicable

- **Acceptance Criteria**: All 14 scenarios pass; original GameState objects are verified immutable after each function call

### T8: Regression verification and cleanup
- **Files**: All test files in `tests/`
- **Description**: Run full test suite to verify zero regressions. Update any existing tests that may have relied on internal implementation details (e.g., direct counter manipulation). Clean up dead code paths if any remain from the old inline logic.

- **Acceptance Criteria**: Full test suite passes with 0 regressions; no `__deathtouch_damage__` mutations outside of `deathtouch.py`; no lifelink/infect logic outside of their respective keyword modules

## Testing Strategy

### Test Scenarios (14 total)

| # | Scenario | Keyword(s) | Context | Expected Outcome |
|---|----------|-----------|---------|-----------------|
| 1 | Deathtouch kills larger creature | Deathtouch | Combat damage | `__deathtouch_damage__` counter set, SBA destroys target |
| 2 | Deathtouch on planeswalker (no-op) | Deathtouch | Combat damage | No counter set, PW takes normal damage |
| 3 | Deathtouch zero damage (no-op) | Deathtouch | Spell damage | No counter set |
| 4 | Lifelink gains life from combat | Lifelink | Combat damage | Controller life += damage amount |
| 5 | Lifelink gains life from spell | Lifelink | Stack resolution | Controller life += damage amount |
| 6 | Infect puts -1/-1 on creature | Infect | Combat damage | Target gets N -1/-1 counters, no `damage_marked` |
| 7 | Infect gives poison to player | Infect | Combat damage | Target player gets N poison counters |
| 8 | Infect poison >= 10 triggers loss | Infect | Spell damage | Player.has_lost = True at 10+ poison |
| 9 | Wither puts -1/-1 on creature | Wither | Combat damage | Target gets N -1/-1 counters, no `damage_marked` |
| 10 | Wither normal player damage | Wither | Spell damage to player | Normal life loss (wither doesn't affect players) |
| 11 | Deathtouch + Lifelink combined | Both | Combat damage | Counter set AND controller gains life |
| 12 | Infect + SBA interaction | Infect | Combat damage | -1/-1 counters accumulate, SBA destroys at P/T=0 |
| 13 | Pure transform verification | All | Any | Original GameState unchanged after each call |
| 14 | Poisonous mutability fix | Poisonous | Triggered ability | Player poison_counters updated via model_copy |

### Unit Tests (Existing — Must Continue Passing)
- `tests/ability/keywords/test_deathtouch.py` — Deathtouch keyword helpers and SBA tracking
- `tests/ability/keywords/test_lifelink.py` — Lifelink keyword helpers and combat integration
- `tests/ability/keywords/test_infect.py` — Infect/Wither/Poisonous detection

### Integration Tests (Existing — Must Continue Passing)
- `tests/rules/test_combat.py` — Combat damage with deathtouch/lifelink (`test_deathtouch_kills_larger_creature`, `test_lifelink_gains_life`)
- `tests/rules/test_sba.py` — SBA destruction via `__deathtouch_damage__` counter (line 143)
- `tests/rules/test_replacement.py` — Infect damage-to-creature-as-counters (`test_infect_damage_to_creature_as_counters`, line 50)
- `tests/engine/test_proliferate_integration.py` — Proliferate excludes `__deathtouch_damage__` (line 185)

### New Integration Tests
- `tests/engine/test_combat_modifiers_integration.py` — 14 scenarios from table above, organized into test classes:
  - `TestDeathtouchIntegration` (scenarios 1-3)
  - `TestLifelinkIntegration` (scenarios 4-5)
  - `TestInfectIntegration` (scenarios 6-8)
  - `TestWitherIntegration` (scenarios 9-10)
  - `TestCombinedModifiers` (scenario 11)
  - `TestSBAInteraction` (scenario 12)
  - `TestPureTransforms` (scenario 13)
  - `TestPoisonousMutabilityFix` (scenario 14)

## Potential Risks

### Risk 1: SBA destruction breaks if `__deathtouch_damage__` counter is not set correctly
- **Impact**: Deathtouch creatures no longer kill targets at state-based actions
- **Mitigation**: T1 explicitly preserves the exact same counter name and increment logic. The integration test (scenario 1) verifies SBA destruction still works end-to-end.

### Risk 2: Infect + normal damage double-application
- **Impact**: Target creature gets both -1/-1 counters AND `damage_marked`, effectively taking double damage
- **Mitigation**: The `_apply_damage_modifiers()` dispatcher returns a boolean flag indicating whether infect handled the damage. Callers in T4/T5/T6 check this flag and skip normal damage application when True.

### Risk 3: Model_copy chain depth causes performance issues
- **Impact**: Each modifier creates a new GameState; chaining three modifiers means three copies of battlefield/player lists
- **Mitigation**: The dispatcher applies all modifiers in sequence, accumulating changes into one GameState object per damage event. This is the same pattern used throughout the codebase (e.g., monarch, commander zone replacement).

### Risk 4: Existing tests rely on internal implementation details
- **Impact**: Tests that directly check `perm.counters["__deathtouch_damage__"]` may break if counter key changes
- **Mitigation**: Counter name remains exactly `__deathtouch_damage__`. All existing test assertions are preserved. If any test fails, it's a signal to update the test, not change the implementation.

### Risk 5: Wither player damage edge case
- **Impact**: Wither source deals damage to a player — should be normal life loss, but dispatcher might incorrectly route through infect path
- **Mitigation**: `apply_wither_damage()` explicitly returns unchanged GameState for player targets (target_perm is None). The dispatcher only calls wither when the source has wither keyword; it does NOT call `apply_infect_damage()` for wither sources.

## Handoff to Implementer

**Design Document**: `specs/038-gap-analysis/P0-combat-modifiers-design.md`
**User Story**: Gap analysis P0 keywords — Deathtouch, Lifelink, Infect refactor from inline engine mutations to GameState-aware keyword modules
**Estimated Complexity**: Medium (6 files modified, 1 new test file, 14 integration scenarios)
**Key Files**: 
1. `mtg_engine/ability/keywords/deathtouch.py` — New GameState functions
2. `mtg_engine/ability/keywords/lifelink.py` — New GameState functions
3. `mtg_engine/ability/keywords/infect.py` — Full module rewrite
4. `mtg_engine/engine/combat/core.py` — Replace inline modifier logic (lines 617-683)
5. `mtg_engine/engine/stack.py` — Unify spell damage modifiers (lines 1462-1492)

**Start With**: T1 (deathtouch.py refactor) — it's the simplest module and establishes the pattern for T2/T3. The `__deathtouch_damage__` counter mechanism is critical to preserve correctly before touching combat/core.py.

**Acceptance Criteria**: 
- All existing tests pass with 0 regressions
- No direct mutations of player.life, perm.damage_marked, or perm.counters in combat/core.py, stack.py, or replacement.py for these three keywords
- New integration test suite (14 scenarios) passes
- `__deathtouch_damage__` counter mechanism preserved exactly for SBA compatibility
