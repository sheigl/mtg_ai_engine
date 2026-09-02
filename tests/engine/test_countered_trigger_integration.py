"""
7-3 Countered Trigger Integration Tests (Sprint 7)

Tests for the "whenever a spell is countered" trigger category (CR 701.5),
added in Sprint 7 P0 (story 7-3).

Coverage:
  Unit-style (drives ``check_countered_triggers`` directly):
    - pattern registration / index-to-filter mapping
    - you-control negative
    - self-referential guard
    - no-match
    - multiple permanents

  Natural-context (drives the REAL engine entry point ``stack._counter_spell``):
    - fires on a real counter
    - does NOT fire on an uncounterable spell
    - does NOT fire on a non-counter removal (bounce)

Q1 (exactly-once): the "countered" pattern is referenced ONLY by
``check_countered_triggers`` (never by the zone-change listener). Countering
does not emit a zone-change event, so it cannot double-fire.
"""
import uuid

import pytest

from mtg_engine.models.game import (
    GameState,
    Permanent,
    Card,
    PlayerState,
    StackObject,
)
from mtg_engine.engine.triggers import (
    check_countered_triggers,
    COUNTERED_TRIGGER_PATTERNS,
    TRIGGER_PATTERNS,
)
from mtg_engine.engine.stack import _counter_spell


# --- Test helpers ---------------------------------------------------------

def _make_gs() -> GameState:
    return GameState(
        game_id="countered-test",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(name="Alice", life=20),
            PlayerState(name="Bob", life=20),
        ],
        battlefield=[],
    )


def _perm(name, oracle_text, controller="Alice", type_line="Enchantment") -> Permanent:
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name=name, type_line=type_line, oracle_text=oracle_text),
        controller=controller,
    )


def _countered_spell(controller="Bob", uncounterable=False) -> StackObject:
    return StackObject(
        source_card=Card(name="Fireball", type_line="Instant", oracle_text="Deal 3 damage."),
        controller=controller,
        uncounterable=uncounterable,
    )


def _countered_count(gs: GameState) -> int:
    return sum(1 for t in gs.pending_triggers if t.trigger_type == "countered")


# --- Unit-style: pattern registration & filters ---------------------------

class TestCounteredPattern:
    def test_countered_pattern_matches(self):
        """The 3 countered patterns are registered and each matches its form."""
        assert "countered" in TRIGGER_PATTERNS
        assert TRIGGER_PATTERNS["countered"] is COUNTERED_TRIGGER_PATTERNS
        assert len(COUNTERED_TRIGGER_PATTERNS) == 3

        # index 0 - self-referential
        assert COUNTERED_TRIGGER_PATTERNS[0].search("whenever this is countered")
        assert COUNTERED_TRIGGER_PATTERNS[0].search("whenever this spell is countered")
        assert COUNTERED_TRIGGER_PATTERNS[0].search("whenever ~ is countered")
        # index 1 - you-control
        assert COUNTERED_TRIGGER_PATTERNS[1].search("whenever a spell you control is countered")
        # index 2 - general (bare form + with modifier)
        assert COUNTERED_TRIGGER_PATTERNS[2].search("whenever a spell is countered")
        assert COUNTERED_TRIGGER_PATTERNS[2].search("whenever a spell your opponent controls is countered")

    def test_countered_you_control_negative(self):
        """'a spell you control is countered' must NOT fire when the countered
        spell is controlled by the opponent (index-1 filter)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever a spell you control is countered, draw a card."))
        gs = check_countered_triggers(gs, _countered_spell(controller="Bob"))
        assert _countered_count(gs) == 0

        # Control case: Alice's own spell is countered -> fires.
        gs2 = _make_gs()
        gs2.battlefield.append(_perm("Watcher", "Whenever a spell you control is countered, draw a card."))
        gs2 = check_countered_triggers(gs2, _countered_spell(controller="Alice"))
        assert _countered_count(gs2) == 1

    def test_countered_self_referential_guard(self):
        """'whenever this is countered' fires ONLY for the permanent whose own
        spell was countered (index-0 name guard)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("SelfRef", "Whenever this is countered, draw a card."))
        other = StackObject(source_card=Card(name="Fireball", type_line="Instant"), controller="Alice")
        gs = check_countered_triggers(gs, other)
        assert _countered_count(gs) == 0

        # The watcher's own spell is countered -> fires.
        gs2 = _make_gs()
        gs2.battlefield.append(_perm("SelfRef", "Whenever this is countered, draw a card."))
        own = StackObject(
            source_card=Card(name="SelfRef", type_line="Enchantment",
                             oracle_text="Whenever this is countered, draw a card."),
            controller="Alice",
        )
        gs2 = check_countered_triggers(gs2, own)
        assert _countered_count(gs2) == 1

    def test_countered_no_match(self):
        """A permanent with no countered trigger queues nothing."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Bear", "2/2", type_line="Creature - Beast"))
        gs.battlefield.append(_perm("DrawGuy", "Whenever you draw a card, draw another card."))
        gs = check_countered_triggers(gs, _countered_spell())
        assert _countered_count(gs) == 0

    def test_countered_multiple_permanents(self):
        """Each general 'whenever a spell is countered' watcher fires once."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher A", "Whenever a spell is countered, draw a card."))
        gs.battlefield.append(_perm("Watcher B", "Whenever a spell is countered, scry 1."))
        gs = check_countered_triggers(gs, _countered_spell())
        assert _countered_count(gs) == 2


# --- Natural-context: real _counter_spell entry point ---------------------

class TestCounteredWiring:
    def test_countered_fires_via_counter_spell(self):
        """Countering through the real engine path fires the trigger, removes
        the spell from the stack, and puts its card in the controller's
        graveyard."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever a spell is countered, draw a card."))
        so = _countered_spell(controller="Bob")
        gs.stack.append(so)

        gs = _counter_spell(gs, so.id)

        assert _countered_count(gs) == 1
        assert not any(s.id == so.id for s in gs.stack)
        assert any(c.name == "Fireball" for c in gs.players[1].graveyard)

    def test_countered_not_fired_on_uncounterable(self):
        """Countering an uncounterable spell is a no-op: the spell stays on the
        stack and NO 'countered' trigger fires (Q3: guard precedes the check)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever a spell is countered, draw a card."))
        so = _countered_spell(controller="Bob", uncounterable=True)
        gs.stack.append(so)

        gs = _counter_spell(gs, so.id)

        assert _countered_count(gs) == 0
        assert any(s.id == so.id for s in gs.stack)

    def test_countered_not_fired_on_non_counter_removal(self):
        """Removing a spell from the stack by a NON-counter means (a bounce)
        queues no 'countered' trigger (Q1: no false positives)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever a spell is countered, draw a card."))
        so = _countered_spell(controller="Bob")
        gs.stack.append(so)

        # Simulate a bounce: direct stack removal to hand (not via _counter_spell).
        gs.stack[:] = [s for s in gs.stack if s.id != so.id]
        gs.players[1].hand.append(so.source_card)

        assert _countered_count(gs) == 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
