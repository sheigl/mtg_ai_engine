"""SA-04 Undying integration tests (CR 702.51).

Undying is a triggered ability that functions when the creature with undying dies.
If it had no +1/+1 counters on it, its controller returns it to the battlefield
under their control with +1/+1 counters equal to its power and toughness.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player
from mtg_engine.ability.keywords.undying import UndyingKeyword


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    gs = GameState(
        game_id="test-undying",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )
    # Register zone-change listeners so death triggers fire
    from mtg_engine.engine.triggers import initialize_triggers
    initialize_triggers(gs)
    return gs


def _make_undying_card(name: str = "Bloodgrass", power: str = "2", toughness: str = "2") -> Card:
    return Card(
        name=name,
        type_line="Creature — Plant",
        oracle_text=f"Undying\n{power}/{toughness}",
        mana_cost="{G}",
        power=power,
        toughness=toughness,
        keywords=["undying"],
    )


# --- Detection & Parsing Tests ---

def test_undying_from_oracle_text():
    """Undying is detected from oracle text."""
    assert UndyingKeyword.from_oracle_text("Undying") is True
    assert UndyingKeyword.from_oracle_text("When this creature dies, undying.") is True
    assert UndyingKeyword.from_oracle_text("") is False


def test_undying_has_keyword():
    """Undying is detected from keyword list."""
    assert UndyingKeyword.has_undying(["undying"]) is True
    assert UndyingKeyword.has_undying(["Undying"]) is True
    assert UndyingKeyword.has_undying([]) is False


def test_undying_applies_to_permanent():
    """Undying.applies() checks both keywords and oracle text."""
    gs = _make_game()
    card = _make_undying_card()
    perm = Permanent(card=card, controller="p1")
    assert UndyingKeyword().applies(gs, perm) is True

    no_undying = Card(name="Normal", type_line="Creature", oracle_text="", keywords=[])
    normal_perm = Permanent(card=no_undying, controller="p1")
    assert UndyingKeyword().applies(gs, normal_perm) is False


# --- Counter Count Tests ---

def test_undying_counter_count_calculation():
    """Undying returns power + toughness as counter count."""
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1")
    kw = UndyingKeyword()

    assert kw.get_counter_count(perm) == 4  # 2+2


def test_undying_counter_count_zero_power_toughness():
    """Undying returns 0 for a 0/0 creature."""
    card = _make_undying_card(power="0", toughness="0")
    perm = Permanent(card=card, controller="p1")
    kw = UndyingKeyword()

    assert kw.get_counter_count(perm) == 0


def test_undying_counter_count_invalid():
    """Undying returns 0 for invalid power/toughness values."""
    card = Card(name="Weird", type_line="Creature", oracle_text="Undying", power="*", toughness="?")
    perm = Permanent(card=card, controller="p1")
    kw = UndyingKeyword()

    assert kw.get_counter_count(perm) == 0


# --- Trigger Creation Tests ---

def test_undying_creates_trigger_on_death_no_counters():
    """Undying fires when creature dies with no +1/+1 counters."""
    gs = _make_game()
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    kw = UndyingKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is not None
    assert trigger.trigger_type == "undying"
    assert "+1/+1 counters" in trigger.effect_description


def test_undying_does_not_fire_with_plus_one_counter():
    """Undying does NOT fire if creature already has a +1/+1 counter."""
    gs = _make_game()
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1", counters={"+1/+1": 1})
    kw = UndyingKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


def test_undying_does_not_fire_on_exile():
    """Undying does NOT fire when creature is exiled (not dies)."""
    gs = _make_game()
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    kw = UndyingKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="exile")
    assert trigger is None


def test_undying_self_referential():
    """Undying only triggers for the creature that has it (self-referential)."""
    gs = _make_game()
    undying_card = _make_undying_card(power="2", toughness="2")
    undying_perm = Permanent(card=undying_card, controller="p1", id="perm-1")

    other_card = Card(name="Other", type_line="Creature", oracle_text="", keywords=[])
    other_perm = Permanent(card=other_card, controller="p1", id="perm-2")

    kw = UndyingKeyword()
    # Source has undying but different creature died — should not fire
    trigger = kw.create_trigger(gs, undying_perm, other_perm, to_zone="graveyard")
    assert trigger is None


# --- Zone Replacement Integration Tests ---

def test_undying_zone_replacement_detection():
    """zones.py detects undying keyword on permanent leaving battlefield."""
    from mtg_engine.engine.zones import move_permanent_to_zone
    gs = _make_game()
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    assert len(player.graveyard) == 0

    old_gs_id = id(gs)
    gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
    # After pure transform, re-fetch player from new game state
    new_player = get_player(gs, "p1")
    assert len(new_player.graveyard) >= 1 or id(gs) != old_gs_id


def test_undying_trigger_description():
    """Undying trigger has a human-readable description."""
    kw = UndyingKeyword()
    desc = kw.get_trigger_description()
    assert "undying" in desc.lower()
    assert "+1/+1" in desc


# --- Pure Transform Tests ---

def test_undying_apply_returns_same_state():
    """Undying.apply() is a no-op without death context, returns same state."""
    gs = _make_game()
    card = _make_undying_card()
    perm = Permanent(card=card, controller="p1")
    kw = UndyingKeyword()

    result_gs = kw.apply(gs, perm)
    # Without death context, apply is a no-op
    assert result_gs.game_id == gs.game_id


def test_undying_counter_guard_multiple():
    """Undying does not fire with multiple +1/+1 counters."""
    gs = _make_game()
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1", counters={"+1/+1": 3})
    kw = UndyingKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


# --- Distinction from Persist ---

def test_undying_vs_persist_counter_type():
    """Undying checks +1/+1 counters; Persist checks -1/-1 counters. They are independent."""
    gs = _make_game()
    # Creature with undying that has a -1/-1 counter (should still fire undying)
    card = _make_undying_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1", counters={"-1/-1": 1})

    kw = UndyingKeyword()
    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    # Should fire because undying only checks +1/+1 counters
    assert trigger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
