"""SA-04 Morph integration tests (CR 702.35).

Morph is a static ability that functions while the card with morph is in hand.
Turning a face-down creature face up doesn't use the stack, so it isn't a spell
and can't be countered or responded to. CR 702.35b: You may turn a face-down
creature you control face up any time you have priority by paying its morph cost.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player
from mtg_engine.engine.morph import (
    parse_morph_cost,
    has_morph,
    apply_morph_turn_face_up,
    resolve_morph_with_ai,
)


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-morph",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )


def _make_morph_card(name: str = "Giant Spider", power: str = "4", toughness: str = "3") -> Card:
    return Card(
        name=name,
        type_line="Creature — Spider",
        oracle_text=f"Morph {{3}}\n{power}/{toughness}",
        mana_cost=f"{{2}}{{R}}",
        power=power,
        toughness=toughness,
        keywords=["morph"],
    )


# --- Detection & Parsing Tests ---

def test_parse_morph_cost_basic():
    """parse_morph_cost extracts {3} from standard morph text."""
    assert parse_morph_cost("Morph {3}") == "{3}"


def test_parse_morph_cost_colored():
    """parse_morph_cost handles colored mana costs."""
    assert parse_morph_cost("Morph {1}{U}") == "{1}{U}"


def test_parse_morph_cost_none():
    """parse_morph_cost returns None for cards without morph."""
    assert parse_morph_cost("") is None
    assert parse_morph_cost("Flying") is None
    assert parse_morph_cost(None) is None


def test_has_morph_true():
    """has_morph detects morph ability in oracle text."""
    assert has_morph("Morph {3}") is True
    assert has_morph("Some text. Morph {2}{G}. More text.") is True


def test_has_morph_false():
    """has_morph returns False for cards without morph."""
    assert has_morph("") is False
    assert has_morph(None) is False
    assert has_morph("Flying") is False


# --- Face-Up Application Tests ---

def _make_face_down_perm(card: Card, controller: str = "p1", perm_id: str = "perm-1") -> Permanent:
    """Create a face-down permanent (2/2 morph creature)."""
    return Permanent(
        card=card,
        controller=controller,
        id=perm_id,
        is_face_down=True,
        power_bonus=0,
        toughness_bonus=0,
    )


def test_morph_turn_face_up_basic():
    """Turning a face-down creature face up works with sufficient mana."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    # Give p1 enough mana to pay {3}
    player = get_player(gs, "p1")
    player.mana_pool.C = 5

    gs = apply_morph_turn_face_up(gs, perm.id)

    # Verify permanent is now face up
    updated_perm = next(p for p in gs.battlefield if p.id == perm.id)
    assert updated_perm.is_face_down is False


def test_morph_turn_face_up_deducts_mana():
    """Turning face up deducts morph cost from mana pool."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    player.mana_pool.C = 5

    gs = apply_morph_turn_face_up(gs, perm.id)

    updated_player = get_player(gs, "p1")
    assert updated_player.mana_pool.C == 2  # Paid {3}


def test_morph_turn_face_up_insufficient_mana():
    """Cannot turn face up if player can't afford morph cost."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    # Player has only 1 generic mana, needs {3}
    player = get_player(gs, "p1")
    player.mana_pool.C = 1

    gs_before_id = id(gs)
    gs = apply_morph_turn_face_up(gs, perm.id)

    # Should return same state (no-op when can't afford)
    assert id(gs) == gs_before_id


def test_morph_turn_face_up_already_face_up():
    """No-op if permanent is already face up."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = Permanent(card=card, controller="p1", id="perm-1", is_face_down=False)
    gs.battlefield.append(perm)

    gs_before_id = id(gs)
    gs = apply_morph_turn_face_up(gs, perm.id)

    assert id(gs) == gs_before_id


def test_morph_turn_face_up_perm_not_found():
    """No-op if permanent ID doesn't exist on battlefield."""
    gs = _make_game()
    gs = apply_morph_turn_face_up(gs, "nonexistent-id")

    # Should return same state
    assert len(gs.battlefield) == 0


def test_morph_turn_face_up_pure_transform():
    """apply_morph_turn_face_up returns a new GameState object."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    player.mana_pool.C = 5

    old_id = id(gs)
    gs = apply_morph_turn_face_up(gs, perm.id)

    assert id(gs) != old_id


# --- AI Resolution Tests ---

def test_ai_resolves_morph_when_affordable():
    """AI auto-resolves morph face-up when it can afford the cost."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    player.mana_pool.C = 5

    gs = resolve_morph_with_ai(gs, perm.id)

    updated_perm = next(p for p in gs.battlefield if p.id == perm.id)
    assert updated_perm.is_face_down is False


def test_ai_skips_morph_when_unaffordable():
    """AI skips morph face-up when it can't afford the cost."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    player.mana_pool.C = 0

    gs_before_id = id(gs)
    gs = resolve_morph_with_ai(gs, perm.id)

    assert id(gs) == gs_before_id


# --- Edge Cases ---

def test_morph_cleared_pending_payment():
    """Turning face up clears pending_morph_payment field."""
    gs = _make_game()
    card = _make_morph_card(power="4", toughness="3")
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)
    gs.pending_morph_payment = {"player": "p1", "permanent_id": perm.id}

    player = get_player(gs, "p1")
    player.mana_pool.C = 5

    gs = apply_morph_turn_face_up(gs, perm.id)
    assert gs.pending_morph_payment is None


def test_morph_colored_cost():
    """Morph with colored mana cost pays correctly."""
    card = Card(
        name="Colored Morph",
        type_line="Creature — Beast",
        oracle_text="Morph {2}{R}",
        mana_cost="{3}{R}",
        power="3",
        toughness="3",
        keywords=["morph"],
    )
    gs = _make_game()
    perm = _make_face_down_perm(card)
    gs.battlefield.append(perm)

    player = get_player(gs, "p1")
    player.mana_pool.C = 5
    player.mana_pool.R = 2

    gs = apply_morph_turn_face_up(gs, perm.id)

    updated_player = get_player(gs, "p1")
    assert updated_player.mana_pool.R == 1  # Paid {R}
    assert updated_player.mana_pool.C == 3  # Paid {2}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
