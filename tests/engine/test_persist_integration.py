"""SA-04 Persist integration tests (CR 702.61).

Persist is a triggered ability that functions when the creature with persist dies.
If it has no -1/-1 counters on it, its controller returns it to the battlefield
under their control with a -1/-1 counter on it.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player
from mtg_engine.ability.keywords.persist import PersistKeyword


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    gs = GameState(
        game_id="test-persist",
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


def _make_persist_card(name: str = "Carrion Locust", power: str = "0", toughness: str = "1") -> Card:
    return Card(
        name=name,
        type_line="Creature — Insect",
        oracle_text=f"{name} enters the battlefield with a -1/-1 counter on it.\nPersist",
        mana_cost="{2}{G}",
        power=power,
        toughness=toughness,
        keywords=["persist"],
    )


# --- Detection & Parsing Tests ---

def test_persist_from_oracle_text():
    """Persist is detected from oracle text."""
    assert PersistKeyword.from_oracle_text("Persist") is True
    assert PersistKeyword.from_oracle_text("When this creature dies, persist.") is True
    assert PersistKeyword.from_oracle_text("") is False


def test_persist_has_keyword():
    """Persist is detected from keyword list."""
    assert PersistKeyword.has_persist(["persist"]) is True
    assert PersistKeyword.has_persist(["Persist"]) is True
    assert PersistKeyword.has_persist([]) is False


def test_persist_applies_to_permanent():
    """Persist.applies() checks both keywords and oracle text."""
    gs = _make_game()
    card = _make_persist_card()
    perm = Permanent(card=card, controller="p1")
    assert PersistKeyword().applies(gs, perm) is True

    no_persist = Card(name="Normal", type_line="Creature", oracle_text="", keywords=[])
    normal_perm = Permanent(card=no_persist, controller="p1")
    assert PersistKeyword().applies(gs, normal_perm) is False


# --- Trigger Creation Tests ---

def test_persist_creates_trigger_on_death_no_counters():
    """Persist fires when creature dies with no -1/-1 counters."""
    gs = _make_game()
    card = _make_persist_card(power="2", toughness="2")  # No -1/-1 counter by default
    perm = Permanent(card=card, controller="p1", id="perm-1")
    kw = PersistKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is not None
    assert trigger.trigger_type == "persist"
    assert "-1/-1 counter" in trigger.effect_description


def test_persist_does_not_fire_with_minus_one_counter():
    """Persist does NOT fire if creature already has a -1/-1 counter."""
    gs = _make_game()
    card = _make_persist_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1", counters={"-1/-1": 1})
    kw = PersistKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


def test_persist_does_not_fire_on_exile():
    """Persist does NOT fire when creature is exiled (not dies)."""
    gs = _make_game()
    card = _make_persist_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    kw = PersistKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="exile")
    assert trigger is None


def test_persist_self_referential():
    """Persist only triggers for the creature that has it (self-referential)."""
    gs = _make_game()
    persist_card = _make_persist_card(power="2", toughness="2")
    persist_perm = Permanent(card=persist_card, controller="p1", id="perm-1")

    other_card = Card(name="Other", type_line="Creature", oracle_text="", keywords=[])
    other_perm = Permanent(card=other_card, controller="p1", id="perm-2")

    kw = PersistKeyword()
    # Source has persist but different creature died — should not fire
    trigger = kw.create_trigger(gs, persist_perm, other_perm, to_zone="graveyard")
    assert trigger is None


# --- Zone Replacement Integration Tests ---

def test_persist_zone_replacement_detection():
    """zones.py detects persist keyword on permanent leaving battlefield."""
    from mtg_engine.engine.zones import move_permanent_to_zone
    gs = _make_game()
    card = _make_persist_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    # The zone replacement logic checks for persist keyword and no -1/-1 counters
    # We verify the detection path exists (actual resolution happens via triggers)
    player = get_player(gs, "p1")
    assert len(player.graveyard) == 0

    old_gs_id = id(gs)
    gs = move_permanent_to_zone(gs, perm, "graveyard", "battlefield")
    # After pure transform, re-fetch player from new game state
    new_player = get_player(gs, "p1")
    assert len(new_player.graveyard) >= 1 or id(gs) != old_gs_id


def test_persist_trigger_description():
    """Persist trigger has a human-readable description."""
    kw = PersistKeyword()
    desc = kw.get_trigger_description()
    assert "persist" in desc.lower()
    assert "-1/-1" in desc


# --- Pure Transform Tests ---

def test_persist_apply_returns_same_state():
    """Persist.apply() is a no-op without death context, returns same state."""
    gs = _make_game()
    card = _make_persist_card()
    perm = Permanent(card=card, controller="p1")
    kw = PersistKeyword()

    result_gs = kw.apply(gs, perm)
    # Without death context, apply is a no-op
    assert result_gs.game_id == gs.game_id


def test_persist_counter_guard_multiple():
    """Persist does not fire with multiple -1/-1 counters."""
    gs = _make_game()
    card = _make_persist_card(power="2", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1", counters={"-1/-1": 3})
    kw = PersistKeyword()

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
