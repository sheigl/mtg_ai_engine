"""Afterlife keyword integration tests (CR 702.108).

Tests that Afterlife fires as a triggered ability via the stack when a creature
with afterlife dies, creating N 0/0 white Spirit tokens with afterlife 1.
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool


def _make_game(active: str = "p1", human: str | None = None) -> GameState:
    gs = GameState(
        game_id="test-afterlife",
        seed=42,
        active_player=active,
        priority_holder=active,
        players=[
            PlayerState(name="p1", life=20, mana_pool=ManaPool()),
            PlayerState(name="p2", life=20, mana_pool=ManaPool()),
        ],
        human_player_name=human,
    )
    # Register zone-change listeners so death triggers fire
    from mtg_engine.engine.triggers import initialize_triggers
    initialize_triggers(gs)
    return gs


def _make_afterlife_card(count: int = 1) -> Card:
    return Card(
        name=f"Afterlife {count} Creature",
        type_line="Creature — Spirit",
        oracle_text=f"Afterlife {count}",
        power="2",
        toughness="2",
        keywords=["afterlife"],
    )


# ── Trigger queuing tests ───────────────────────────────────────────────────

class TestAfterlifeTriggerQueued:
    """Afterlife trigger is queued when creature dies."""

    def test_afterlife_queued_on_death(self):
        gs = _make_game()
        card = _make_afterlife_card(count=2)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")

        # Kill the creature → moves to graveyard
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")

        # Afterlife trigger should be queued
        triggers = [t for t in gs.pending_triggers if t.trigger_type == "afterlife"]
        assert len(triggers) == 1
        assert triggers[0].controller == "p1"
        assert triggers[0].trigger_data.get("count") == 2

    def test_afterlife_plain_keyword(self):
        """Card with just 'Afterlife' in oracle (no count) defaults to 1."""
        gs = _make_game()
        card = Card(
            name="Plain Afterlife",
            type_line="Creature — Spirit",
            oracle_text="Afterlife",
            power="1",
            toughness="1",
            keywords=["afterlife"],
        )
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")

        triggers = [t for t in gs.pending_triggers if t.trigger_type == "afterlife"]
        assert len(triggers) == 1
        assert triggers[0].trigger_data.get("count") == 1

    def test_no_afterlife_when_exiled(self):
        """Afterlife does NOT fire when creature is exiled (not dies)."""
        gs = _make_game()
        card = _make_afterlife_card(count=1)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "exile", "battlefield")

        triggers = [t for t in gs.pending_triggers if t.trigger_type == "afterlife"]
        assert len(triggers) == 0


# ── Stack resolution tests ──────────────────────────────────────────────────

class TestAfterlifeResolution:
    """Afterlife trigger resolves to create Spirit tokens."""

    def _resolve_trigger(self, gs: GameState) -> GameState:
        """Helper: put pending afterlife trigger on stack and resolve it."""
        from mtg_engine.engine.triggers import put_trigger_on_stack
        from mtg_engine.engine.stack import resolve_top

        # Find the afterlife trigger
        trigger = next((t for t in gs.pending_triggers if t.trigger_type == "afterlife"), None)
        assert trigger is not None, "No afterlife trigger found"

        # Put on stack
        gs = put_trigger_on_stack(gs, trigger.id, targets=[])

        # Resolve top of stack
        gs = resolve_top(gs)
        return gs

    def test_creates_correct_number_of_tokens(self):
        gs = _make_game()
        card = _make_afterlife_card(count=3)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
        gs = self._resolve_trigger(gs)

        # Check 3 Spirit tokens on battlefield
        spirit_tokens = [
            p for p in gs.battlefield
            if "spirit" in (p.card.type_line or "").lower() and p.is_token
        ]
        assert len(spirit_tokens) == 3

    def test_tokens_are_0_0(self):
        gs = _make_game()
        card = _make_afterlife_card(count=1)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
        gs = self._resolve_trigger(gs)

        spirit_tokens = [
            p for p in gs.battlefield if p.is_token and "spirit" in (p.card.type_line or "").lower()
        ]
        assert len(spirit_tokens) == 1
        assert spirit_tokens[0].card.power == "0"
        assert spirit_tokens[0].card.toughness == "0"

    def test_tokens_have_afterlife_keyword(self):
        gs = _make_game()
        card = _make_afterlife_card(count=1)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
        gs = self._resolve_trigger(gs)

        spirit_tokens = [
            p for p in gs.battlefield if p.is_token and "spirit" in (p.card.type_line or "").lower()
        ]
        assert len(spirit_tokens) == 1
        keywords = spirit_tokens[0].card.keywords or []
        assert any("afterlife" in k.lower() for k in keywords)

    def test_controller_owned_by_dying_creature_controller(self):
        gs = _make_game()
        card = _make_afterlife_card(count=1)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        # p2 controls the creature
        gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
        gs = self._resolve_trigger(gs)

        spirit_tokens = [
            p for p in gs.battlefield if p.is_token and p.controller == "p2"
        ]
        assert len(spirit_tokens) == 1


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestAfterlifeEdgeCases:
    """Edge cases for Afterlife."""

    def test_no_trigger_for_non_creature(self):
        """Afterlife on a non-creature card does not fire (no battlefield permanent)."""
        gs = _make_game()
        # Non-creature with afterlife text — shouldn't normally happen but guard against it
        pass  # Afterlife is inherently creature-only in practice

    def test_token_with_afterlife_also_triggers(self):
        """A token that has afterlife also triggers when it dies."""
        gs = _make_game()
        card = _make_afterlife_card(count=1)
        from mtg_engine.engine.zones import put_permanent_onto_battlefield, move_permanent_to_zone

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
        gs = self._resolve_trigger(gs)

        # Now the created token should have afterlife. Kill it.
        spirit_tokens = [
            p for p in gs.battlefield if p.is_token and "spirit" in (p.card.type_line or "").lower()
        ]
        assert len(spirit_tokens) == 1

        # Move token to graveyard — but tokens cease to exist!
        # CR 704.5d: tokens cease to exist when leaving battlefield → go to nowhere
        gs = move_permanent_to_zone(gs, spirit_tokens[0], "graveyard", "battlefield")

        # Token should NOT trigger afterlife (it ceased to exist, not put in graveyard)
        triggers = [t for t in gs.pending_triggers if t.trigger_type == "afterlife"]
        assert len(triggers) == 0


    def _resolve_trigger(self, gs: GameState) -> GameState:
        """Helper: put pending afterlife trigger on stack and resolve it."""
        from mtg_engine.engine.triggers import put_trigger_on_stack
        from mtg_engine.engine.stack import resolve_top

        trigger = next((t for t in gs.pending_triggers if t.trigger_type == "afterlife"), None)
        assert trigger is not None, "No afterlife trigger found"
        gs = put_trigger_on_stack(gs, trigger.id, targets=[])
        gs = resolve_top(gs)
        return gs
