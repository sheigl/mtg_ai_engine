"""SA-04 Evoke integration tests (CR 702.41).

Evoke is a keyword ability that appears as an additional mana cost on certain
creatures. When a creature with evoke enters the battlefield, its controller
must sacrifice it at the beginning of the next end step. This is mandatory, not optional.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player
from mtg_engine.engine.evoke import (
    parse_evoke_cost,
    has_evoke,
    queue_evoke_sacrifice,
    resolve_evoke_sacrifice,
    resolve_evoke_with_ai,
)


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-evoke",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )


def _make_evoke_card(name: str = "Fledgling Djinn", power: str = "3", toughness: str = "2") -> Card:
    return Card(
        name=name,
        type_line="Creature — Djinn",
        oracle_text=f"Evoke {{1}}\nFlying\n{power}/{toughness}",
        mana_cost="{2}{U}",
        power=power,
        toughness=toughness,
        keywords=["evoke"],
    )


# --- Detection & Parsing Tests ---

def test_parse_evoke_cost_basic():
    """parse_evoke_cost extracts {1} from standard evoke text."""
    assert parse_evoke_cost("Evoke {1}") == "{1}"


def test_parse_evoke_cost_colored():
    """parse_evoke_cost handles colored mana costs."""
    assert parse_evoke_cost("Evoke {2}{B}") == "{2}{B}"


def test_parse_evoke_cost_none():
    """parse_evoke_cost returns None for cards without evoke."""
    assert parse_evoke_cost("") is None
    assert parse_evoke_cost("Flying") is None
    assert parse_evoke_cost(None) is None


def test_has_evoke_true():
    """has_evoke detects evoke ability in oracle text."""
    assert has_evoke("Evoke {1}") is True
    assert has_evoke("Some text. Evoke {2}{G}. More text.") is True


def test_has_evoke_false():
    """has_evoke returns False for cards without evoke."""
    assert has_evoke("") is False
    assert has_evoke(None) is False
    assert has_evoke("Flying") is False


# --- Queue Evoke Sacrifice Tests ---

def test_queue_evoke_sacrifice_sets_pending():
    """queue_evoke_sacrifice sets pending_evoke_sacrifice on GameState."""
    gs = _make_game()

    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")

    assert gs.pending_evoke_sacrifice is not None
    assert gs.pending_evoke_sacrifice["player"] == "p1"
    assert gs.pending_evoke_sacrifice["permanent_id"] == "perm-1"
    assert gs.pending_evoke_sacrifice["card_name"] == "Fledgling Djinn"


def test_queue_evoke_sacrifice_pure_transform():
    """queue_evoke_sacrifice returns a new GameState object."""
    gs = _make_game()

    old_id = id(gs)
    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")

    assert id(gs) != old_id


# --- Resolve Evoke Sacrifice Tests ---

def test_resolve_evoke_sacrifice_moves_to_graveyard():
    """resolve_evoke_sacrifice moves the permanent from battlefield to graveyard."""
    gs = _make_game()
    card = _make_evoke_card(power="3", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    # Queue the sacrifice first
    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")

    # Resolve it
    gs = resolve_evoke_sacrifice(gs)

    # Permanent should be gone from battlefield
    assert not any(p.id == "perm-1" for p in gs.battlefield)
    # Card should be in graveyard
    player = get_player(gs, "p1")
    assert len(player.graveyard) == 1
    assert player.graveyard[0].name == card.name


def test_resolve_evoke_sacrifice_clears_pending():
    """resolve_evoke_sacrifice clears pending_evoke_sacrifice."""
    gs = _make_game()
    card = _make_evoke_card(power="3", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")
    assert gs.pending_evoke_sacrifice is not None

    gs = resolve_evoke_sacrifice(gs)
    assert gs.pending_evoke_sacrifice is None


def test_resolve_evoke_sacrifice_perm_not_found():
    """resolve_evoke_sacrifice handles missing permanent gracefully."""
    gs = _make_game()
    # Queue sacrifice for a perm that doesn't exist on battlefield
    gs = queue_evoke_sacrifice(gs, "nonexistent", "p1", "Ghost")

    gs = resolve_evoke_sacrifice(gs)

    # Should clear pending state even if perm not found
    assert gs.pending_evoke_sacrifice is None


def test_resolve_evoke_sacrifice_no_pending():
    """resolve_evoke_sacrifice is no-op when there's no pending sacrifice."""
    gs = _make_game()

    gs_before_id = id(gs)
    gs = resolve_evoke_sacrifice(gs)

    assert id(gs) == gs_before_id


def test_resolve_evoke_sacrifice_pure_transform():
    """resolve_evoke_sacrifice returns a new GameState object."""
    gs = _make_game()
    card = _make_evoke_card(power="3", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")

    old_id = id(gs)
    gs = resolve_evoke_sacrifice(gs)

    assert id(gs) != old_id


# --- AI Resolution Tests ---

def test_ai_resolves_evoke_sacrifice():
    """AI auto-resolves evoke sacrifice (always sacrifices as mandatory)."""
    gs = _make_game()
    card = _make_evoke_card(power="3", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", "Fledgling Djinn")
    gs = resolve_evoke_with_ai(gs)

    assert not any(p.id == "perm-1" for p in gs.battlefield)
    player = get_player(gs, "p1")
    assert len(player.graveyard) == 1


# --- Integration: Full Evoke Flow ---

def test_full_evoke_flow():
    """Full evoke flow: queue sacrifice -> resolve at end step."""
    gs = _make_game()
    card = _make_evoke_card(power="3", toughness="2")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    # Step 1: Queue evoke sacrifice (simulating ETB from cast via evoke cost)
    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", card.name)
    assert gs.pending_evoke_sacrifice is not None

    # Step 2: End step — resolve sacrifice
    gs = resolve_evoke_sacrifice(gs)
    assert gs.pending_evoke_sacrifice is None
    assert not any(p.id == "perm-1" for p in gs.battlefield)

    player = get_player(gs, "p1")
    assert len(player.graveyard) == 1


def test_multiple_evoked_creatures():
    """Multiple evoked creatures can be queued and resolved independently."""
    gs = _make_game()
    card1 = _make_evoke_card(name="Fledgling Djinn", power="3", toughness="2")
    card2 = Card(
        name="Second Evoke", type_line="Creature — Elemental",
        oracle_text="Evoke {2}", mana_cost="{3}{R}", power="4", toughness="1", keywords=["evoke"],
    )

    perm1 = Permanent(card=card1, controller="p1", id="perm-1")
    perm2 = Permanent(card=card2, controller="p1", id="perm-2")
    gs.battlefield.append(perm1)
    gs.battlefield.append(perm2)

    # Queue first evoke sacrifice
    gs = queue_evoke_sacrifice(gs, "perm-1", "p1", card1.name)
    assert gs.pending_evoke_sacrifice["permanent_id"] == "perm-1"

    # Resolve it
    gs = resolve_evoke_sacrifice(gs)
    assert len([p for p in gs.battlefield if p.id == "perm-1"]) == 0
    assert len([p for p in gs.battlefield if p.id == "perm-2"]) == 1

    # Queue second evoke sacrifice
    gs = queue_evoke_sacrifice(gs, "perm-2", "p1", card2.name)
    gs = resolve_evoke_sacrifice(gs)

    player = get_player(gs, "p1")
    assert len(player.graveyard) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
