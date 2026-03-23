# Quickstart: Rules Engine Completeness (014)

**Date**: 2026-03-23

Integration scenarios for validating each user story independently.

---

## US1: Deck-Out Loss

```python
# Setup: player with empty library draws a card
from mtg_engine.engine.zones import draw_card
from mtg_engine.engine.sba import check_and_apply_sbas

# player.library is empty
gs, card = draw_card(gs, "player_1")
assert card is None
gs, events = check_and_apply_sbas(gs)
assert gs.is_game_over
assert gs.winner == "player_2"
```

---

## US2: Combat Damage Trigger

```python
# Setup: attacker with "whenever this deals combat damage to a player, draw a card"
from mtg_engine.engine.combat import assign_combat_damage

gs = assign_combat_damage(gs)  # attacker deals damage to player
# Trigger should be queued
assert any(t.trigger_type == "combat_damage" for t in gs.pending_triggers)
```

---

## US3: Hybrid Mana Validation

```python
from mtg_engine.engine.mana import can_pay_cost
from mtg_engine.models.game import ManaPool

# Pool has only Green; hybrid {G/W} card should be castable
pool = ManaPool(G=1)
assert can_pay_cost(pool, "{G/W}") == True

# Pool has no Green or White; hybrid {G/W} should not be castable
pool_empty = ManaPool(U=3)
assert can_pay_cost(pool_empty, "{G/W}") == False

# Phyrexian mana: castable with 2 life even without green
pool_no_green = ManaPool(U=2)
# Phyrexian requires player state for life check — see pay_phyrexian_cost()
```

---

## US4: Fog Prevention

```python
# Setup: prevent_all_combat_damage is True (Fog resolved)
gs.prevent_all_combat_damage = True

# Combat damage should be 0
from mtg_engine.engine.combat import assign_combat_damage
pre_life = gs.players[1].life
gs = assign_combat_damage(gs)
assert gs.players[1].life == pre_life  # no damage dealt
```

---

## US5: Control-Change Layer (Layer 2)

```python
# Setup: Control Magic aura on opponent's creature (layer 2 effect)
from mtg_engine.engine.layers import apply_continuous_effects

# Before: creature.controller = "player_2"
gs = apply_continuous_effects(gs)
# After: creature.controller = "player_1" (due to Control Magic)
creature = next(p for p in gs.battlefield if p.id == creature_id)
assert creature.controller == "player_1"
```

---

## US6: Propaganda Cost Enforcement

```python
# Setup: Propaganda on battlefield (cost_to_attack {2} for all creatures)
# Legal actions for active player should exclude all creature attackers
# unless player has ≥2 colorless mana per creature
from mtg_engine.api.routers.game import _compute_legal_actions

actions = _compute_legal_actions(gs, "player_1")
attacker_actions = [a for a in actions if a["type"] == "declare_attackers"]
# No attacker actions if player has no mana
assert len(attacker_actions) == 0
```

---

## US7: Copy Spell

```python
# Setup: burn spell on stack, copy effect applied
from mtg_engine.engine.stack import copy_spell_on_stack

initial_stack_len = len(gs.stack)
gs = copy_spell_on_stack(gs, spell_id, new_targets=["player_2"])
assert len(gs.stack) == initial_stack_len + 1
copy = gs.stack[-1]
assert copy.is_copy == True
assert copy.targets == ["player_2"]
```

---

## Running the Tests

```bash
# Run all rules tests
python -m pytest tests/rules/ -v

# Run specific user story tests
python -m pytest tests/rules/test_sba.py -v              # US1
python -m pytest tests/rules/test_triggers.py -v         # US2
python -m pytest tests/rules/test_mana.py -v             # US3
python -m pytest tests/rules/test_replacement.py -v      # US4
python -m pytest tests/rules/test_layers.py -v           # US5
python -m pytest tests/rules/test_legal_actions.py -v    # US6
python -m pytest tests/rules/test_stack.py -v            # US7

# Full suite (must stay green)
python -m pytest tests/ -v
```
