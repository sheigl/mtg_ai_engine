import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import (
    GameState, PlayerState, Card, Permanent,
)
from mtg_engine.engine.replacement import (
    GameEvent, process_event,
    create_prevention_effect,
    remove_expired_prevention_effects,
    create_draw_replacement,
    process_draw_event,
)


def _make_game() -> GameState:
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    return GameState(
        game_id="t", seed=1, active_player="p1",
        priority_holder="p1", players=[p1, p2],
    )


def _make_permanent(name: str, controller: str, keywords: list[str] | None = None) -> Permanent:
    return Permanent(
        card=Card(
            name=name,
            type_line="Creature — Wizard",
            oracle_text="",
            keywords=keywords or [],
        ),
        controller=controller,
    )


# ─── REP-01: Prevention Effects ──────────────────────────────────────────────

class TestPreventionEffects:
    """Test damage prevention system (REP-01)."""

    def test_prevention_creates_effect(self):
        """Creating a prevention effect adds it to game state."""
        gs = _make_game()
        gs = create_prevention_effect(
            gs,
            controller="p1",
            source_permanent_id="shield_perm",
            amount=5,
            description="Prevent the next 5 damage",
        )
        assert len(gs.prevention_effects) == 1
        eff = gs.prevention_effects[0]
        assert eff.remaining == 5
        assert eff.source_permanent_id == "shield_perm"

    def test_prevention_unlimited(self):
        """Unlimited prevention (until end of turn) has remaining=None."""
        gs = _make_game()
        gs = create_prevention_effect(
            gs,
            controller="p1",
            amount=None,
            description="Prevent all damage until end of turn",
        )
        eff = gs.prevention_effects[0]
        assert eff.remaining is None

    def test_prevention_reduces_damage(self):
        """Prevention effect reduces damage by the prevented amount."""
        gs = _make_game()
        perm = _make_permanent("Target", "p2")
        gs.battlefield.append(perm)

        # Add prevention for 3 damage
        gs = create_prevention_effect(
            gs, controller="p1", amount=3,
        )

        event = GameEvent(
            event_type="damage",
            target_id=perm.id,
            amount=10,
        )
        event, gs = process_event(event, gs)

        assert event.cancelled is False
        assert event.modified_amount == 7  # 10 - 3 = 7

    def test_prevention_cancels_damage_fully(self):
        """When prevention >= damage, event is cancelled."""
        gs = _make_game()
        perm = _make_permanent("Target", "p2")
        gs.battlefield.append(perm)

        gs = create_prevention_effect(
            gs, controller="p1", amount=5,
        )

        event = GameEvent(
            event_type="damage",
            target_id=perm.id,
            amount=5,
        )
        event, gs = process_event(event, gs)

        assert event.cancelled is True
        assert len(gs.prevention_effects) == 0  # consumed

    def test_prevention_unlimited_not_consumed(self):
        """Unlimited prevention is not consumed after one use."""
        gs = _make_game()
        perm = _make_permanent("Target", "p2")
        gs.battlefield.append(perm)

        gs = create_prevention_effect(
            gs, controller="p1", amount=None,
        )

        event = GameEvent(
            event_type="damage",
            target_id=perm.id,
            amount=5,
        )
        event, gs = process_event(event, gs)

        assert event.cancelled is True
        assert len(gs.prevention_effects) == 1  # still active

    def test_prevention_multiple_hits_limited(self):
        """Limited prevention can absorb multiple damage events."""
        gs = _make_game()
        perm = _make_permanent("Target", "p2")
        gs.battlefield.append(perm)

        gs = create_prevention_effect(
            gs, controller="p1", amount=10,
        )

        # First hit: 4 damage
        event1 = GameEvent(event_type="damage", target_id=perm.id, amount=4)
        event1, gs = process_event(event1, gs)
        assert event1.cancelled is True
        assert len(gs.prevention_effects) == 1
        assert gs.prevention_effects[0].remaining == 6

        # Second hit: 6 damage
        event2 = GameEvent(event_type="damage", target_id=perm.id, amount=6)
        event2, gs = process_event(event2, gs)
        assert event2.cancelled is True
        assert len(gs.prevention_effects) == 0  # consumed

    def test_prevention_expires_end_of_turn(self):
        """Prevention effects with end_of_turn expiry are removed."""
        gs = _make_game()
        gs = create_prevention_effect(
            gs, controller="p1", amount=5,
            expires="end_of_turn",
        )
        assert len(gs.prevention_effects) == 1
        gs = remove_expired_prevention_effects(gs, "end_of_turn")
        assert len(gs.prevention_effects) == 0

    def test_prevention_no_expiry_survives_cleanup(self):
        """Prevention without expiry flag survives cleanup."""
        gs = _make_game()
        gs = create_prevention_effect(
            gs, controller="p1", amount=5, expires=None,
        )
        # Verify expires was not set
        assert gs.prevention_effects[0].extra.get("expires") is None
        gs = remove_expired_prevention_effects(gs, "end_of_turn")
        assert len(gs.prevention_effects) == 1


# ─── REP-02: Replacement Draw ────────────────────────────────────────────────

class TestReplacementDraw:
    """Test card draw replacement (REP-02)."""

    def test_draw_replacement_created(self):
        """Creating a draw replacement adds it to game state."""
        gs = _make_game()
        gs = create_draw_replacement(
            gs,
            controller="p1",
            replacement_card_ids=["card_id_1"],
            description="Draw from alternate pool",
        )
        assert len(gs.draw_replacements) == 1

    def test_draw_event_replaced(self):
        """Draw event is replaced with alternate cards."""
        gs = _make_game()
        p1 = gs.players[0]

        # Add a card to draw from
        alt_card = Card(name="Alternate Card", type_line="Instant")
        p1.hand.append(alt_card)

        gs = create_draw_replacement(
            gs,
            controller="p1",
            replacement_card_ids=[alt_card.id],
        )

        event = GameEvent(
            event_type="draw",
            target_id="p1",
            amount=1,
        )
        event, gs = process_draw_event(event, gs)

        assert event.replaced is True

    def test_draw_event_not_replaced_no_effect(self):
        """Draw event passes through when no replacement effect exists."""
        gs = _make_game()
        event = GameEvent(
            event_type="draw",
            target_id="p1",
            amount=1,
        )
        event, gs = process_draw_event(event, gs)
        assert event.replaced is False

    def test_draw_replacement_once(self):
        """Draw replacement effect is consumed after one use."""
        gs = _make_game()
        p1 = gs.players[0]
        alt_card = Card(name="Alternate Card", type_line="Instant")
        p1.hand.append(alt_card)

        gs = create_draw_replacement(
            gs,
            controller="p1",
            replacement_card_ids=[alt_card.id],
            once=True,
        )

        event1 = GameEvent(event_type="draw", target_id="p1", amount=1)
        event1, gs = process_draw_event(event1, gs)
        assert event1.replaced is True

        event2 = GameEvent(event_type="draw", target_id="p1", amount=1)
        event2, gs = process_draw_event(event2, gs)
        assert event2.replaced is False


# ─── REP-03: Effect Duration ─────────────────────────────────────────────────

from mtg_engine.engine.duration import (
    DurationEffect,
    create_duration_effect,
    check_expired_effects,
    remove_expired_effects,
)


class TestEffectDuration:
    """Test 'until end of turn' effect tracking (REP-03)."""

    def test_duration_effect_created(self):
        """Creating a duration effect adds it to game state."""
        gs = _make_game()
        gs = create_duration_effect(
            gs,
            controller="p1",
            description="Target creature gets +2/+2",
            expires="end_of_turn",
            target_id="some_perm",
        )
        assert len(gs.duration_effects) == 1

    def test_duration_expires_end_of_turn(self):
        """Effects expiring at end_of_turn are removed during cleanup."""
        gs = _make_game()
        gs = create_duration_effect(
            gs, controller="p1", expires="end_of_turn",
        )
        gs = remove_expired_effects(gs, "end_of_turn")
        assert len(gs.duration_effects) == 0

    def test_duration_next_turn_survives_cleanup(self):
        """Effects expiring at next turn survive end of current turn."""
        gs = _make_game()
        gs = create_duration_effect(
            gs, controller="p1", expires="player:p1",
        )
        gs = remove_expired_effects(gs, "end_of_turn")
        assert len(gs.duration_effects) == 1

    def test_check_expired_returns_expired(self):
        """check_expired_effects returns list of expired effects."""
        gs = _make_game()
        gs = create_duration_effect(
            gs, controller="p1", expires="end_of_turn",
        )
        gs = create_duration_effect(
            gs, controller="p1", expires="player:p1",
        )
        expired = check_expired_effects(gs, "end_of_turn")
        assert len(expired) == 1

    def test_duration_effect_has_required_fields(self):
        """DurationEffect model has all required fields."""
        eff = DurationEffect(
            controller="p1",
            description="Test effect",
            expires="end_of_turn",
        )
        assert eff.controller == "p1"
        assert eff.expires == "end_of_turn"
        assert eff.target_id is None
