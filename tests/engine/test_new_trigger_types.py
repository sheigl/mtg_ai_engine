"""
TRG-20 Part B: Tests for 5 new trigger types.
Tests check_draw_triggers, check_discard_triggers, check_token_triggers,
check_counter_triggers, and check_planeswalk_triggers.
"""
import pytest
import uuid

from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool
from mtg_engine.engine.triggers import (
    check_draw_triggers,
    check_discard_triggers,
    check_token_triggers,
    check_counter_triggers,
    check_planeswalk_triggers,
)


def _make_gs() -> GameState:
    """Create a minimal 2-player game."""
    return GameState(
        game_id="t-triggers",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[
            PlayerState(name="p1", life=20, mana_pool=ManaPool()),
            PlayerState(name="p2", life=20, mana_pool=ManaPool()),
        ],
    )


def _card(
    name: str, oracle_text: str = "", type_line: str = "Creature — Human"
) -> Card:
    return Card(
        id=f"card-{uuid.uuid4().hex[:8]}",
        name=name,
        type_line=type_line,
        oracle_text=oracle_text,
    )


def _perm(gs: GameState, card: Card, controller: str) -> tuple[GameState, Permanent]:
    """Add a card as a permanent to the battlefield."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    return put_permanent_onto_battlefield(gs, card, controller, from_zone="hand")


# ─── Draw Triggers ──────────────────────────────────────────────────────


class TestDrawTriggers:
    """Test check_draw_triggers()."""

    def test_basic_fire_you_draw(self):
        gs = _make_gs()
        card = _card(
            "Agent of Acquisitions",
            oracle_text="Whenever you draw a card, you may reveal the top card of your library.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_draw_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "draw"
        assert trig.source_permanent_id == perm.id
        assert trig.controller == "p1"

    def test_you_pattern_no_fire_for_opponent(self):
        """'Whenever you draw a card' does NOT fire when opponent draws."""
        gs = _make_gs()
        card = _card(
            "Agent of Acquisitions",
            oracle_text="Whenever you draw a card, you may reveal the top card of your library.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_draw_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before

    def test_no_match_unrelated_oracle(self):
        """Unrelated oracle text does not trigger."""
        gs = _make_gs()
        card = _card("Bear", oracle_text="2/2")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_draw_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before


# ─── Discard Triggers ───────────────────────────────────────────────────


class TestDiscardTriggers:
    """Test check_discard_triggers()."""

    def test_basic_fire_you_discard(self):
        gs = _make_gs()
        card = _card(
            "Geth's Grimoire",
            oracle_text="Whenever you discard a card, draw a card.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_discard_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "discard"
        assert trig.source_permanent_id == perm.id

    def test_you_pattern_no_fire_for_opponent(self):
        """'Whenever you discard a card' does NOT fire when opponent discards."""
        gs = _make_gs()
        card = _card(
            "Geth's Grimoire",
            oracle_text="Whenever you discard a card, draw a card.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_discard_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before

    def test_no_match_unrelated_oracle(self):
        """Unrelated oracle text does not trigger."""
        gs = _make_gs()
        card = _card("Island", oracle_text="{T}: Add {U}.", type_line="Basic Land")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_discard_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before


# ─── Token Triggers ─────────────────────────────────────────────────────


class TestTokenTriggers:
    """Test check_token_triggers()."""

    def test_basic_fire_token_enters(self):
        gs = _make_gs()
        card = _card(
            "Lathiel, Bountiful Dawn",
            oracle_text="Whenever a token enters the battlefield under your control, create a 1/1 white Human creature token.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_token_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "token"
        assert trig.source_permanent_id == perm.id

    def test_you_pattern_no_fire_for_opponent(self):
        """'Whenever you create a token' does NOT fire when opponent creates."""
        gs = _make_gs()
        card = _card(
            "Cloudstone Curio",
            oracle_text="Whenever you create a token, that token gets +1/+1.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_token_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before

    def test_no_match_unrelated_oracle(self):
        """Unrelated oracle text does not trigger."""
        gs = _make_gs()
        card = _card("Knight", oracle_text="First strike. 3/2")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_token_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before


# ─── Counter Triggers ──────────────────────────────────────────────────


class TestCounterTriggers:
    """Test check_counter_triggers()."""

    def test_basic_fire_counter_put_on(self):
        gs = _make_gs()
        card = _card(
            "Boros Charm",
            oracle_text="Whenever a +1/+1 counter is put on a creature you control, that creature gets +1/+1 until end of turn.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_counter_triggers(gs, perm.id, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "counter"
        assert trig.source_permanent_id == perm.id

    def test_you_pattern_no_fire_for_opponent(self):
        """Counter trigger with 'you' pattern does NOT fire for opponent."""
        gs = _make_gs()
        card = _card(
            "Boros Charm",
            oracle_text="Whenever a +1/+1 counter is put on a creature you control, that creature gets +1/+1 until end of turn.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_counter_triggers(gs, perm.id, "p2")
        assert len(gs.pending_triggers) == before

    def test_no_match_unrelated_oracle(self):
        """Unrelated oracle text does not trigger."""
        gs = _make_gs()
        card = _card("Bear", oracle_text="Vigilance. 3/4")
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_counter_triggers(gs, perm.id, "p1")
        assert len(gs.pending_triggers) == before


# ─── Planeswalk Triggers ────────────────────────────────────────────────


class TestPlaneswalkTriggers:
    """Test check_planeswalk_triggers()."""

    def test_basic_fire_this_planeswalker(self):
        gs = _make_gs()
        card = _card(
            "Nicol Bolas, Planeswalker",
            oracle_text="Whenever this planeswalker planeswalks, draw two cards.",
            type_line="Planeswalker — Nicol Bolas",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_planeswalk_triggers(gs, perm.id, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "planeswalk"
        assert trig.source_permanent_id == perm.id

    def test_this_planeswalker_no_fire_wrong_perm(self):
        """'Whenever this planeswalker planeswalks' does NOT fire for a different PW."""
        gs = _make_gs()
        card = _card(
            "Nicol Bolas, Planeswalker",
            oracle_text="Whenever this planeswalker planeswalks, draw two cards.",
            type_line="Planeswalker — Nicol Bolas",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        # Pass a different perm_id so the self-referential guard blocks it
        gs = check_planeswalk_triggers(gs, "different-pw-id", "p1")
        assert len(gs.pending_triggers) == before

    def test_no_match_unrelated_oracle(self):
        """Unrelated oracle text does not trigger."""
        gs = _make_gs()
        card = _card("Bear", oracle_text="2/2")
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_planeswalk_triggers(gs, perm.id, "p1")
        assert len(gs.pending_triggers) == before
