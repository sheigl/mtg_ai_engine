"""SA-04 Suspend integration tests (CR 702.61).

Suspend is a keyword ability that can be used to cast a card from outside the
normal casting process. To suspend a card, pay the suspend cost and exile it with N time counters.
At the beginning of your upkeep, remove a time counter. When the last is removed,
cast the spell without paying its mana cost if legal.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.engine.zones import get_player
from mtg_engine.engine.suspend import (
    parse_suspend,
    has_suspend,
    remove_time_counter,
    get_suspend_ready_cards,
)


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-suspend",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )


def _make_suspend_card(name: str = "Cinder Cloud", suspend_n: int = 3) -> Card:
    return Card(
        name=name,
        type_line="Sorcery",
        oracle_text=f"Suspend {suspend_n}—{{1}}\n{name} deals 2 damage to target creature.",
        mana_cost="{4}{R}",
        keywords=["suspend"],
    )


# --- Detection & Parsing Tests ---

def test_parse_suspend_basic():
    """parse_suspend extracts (N, cost) from standard suspend text."""
    result = parse_suspend("Suspend 3—{1}")
    assert result == (3, "{1}")


def test_parse_suspend_colored_cost():
    """parse_suspend handles colored mana costs."""
    result = parse_suspend("Suspend 2—{2}{U}")
    assert result == (2, "{2}{U}")


def test_parse_suspend_none():
    """parse_suspend returns None for cards without suspend."""
    assert parse_suspend("") is None
    assert parse_suspend("Flying") is None
    assert parse_suspend(None) is None


def test_has_suspend_true():
    """has_suspend detects suspend ability in oracle text."""
    assert has_suspend("Suspend 3—{1}") is True
    assert has_suspend("Some text. Suspend 2—{G}. More text.") is True


def test_has_suspend_false():
    """has_suspend returns False for cards without suspend."""
    assert has_suspend("") is False
    assert has_suspend(None) is False
    assert has_suspend("Flying") is False


# --- Time Counter Removal Tests ---

def _make_suspended_card(card: Card, remaining_counters: int) -> Card:
    """Create a card in suspended state with N time counters remaining."""
    return card.model_copy(update={"parse_status": f"suspended:{remaining_counters}"})


def test_remove_time_counter_decrements():
    """remove_time_counter decrements the counter by 1."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    suspended = _make_suspended_card(card, remaining_counters=3)

    player = get_player(gs, "p1")
    player.suspended_cards.append(suspended)

    gs = remove_time_counter(gs, "p1")

    updated_player = get_player(gs, "p1")
    assert len(updated_player.suspended_cards) == 1
    assert updated_player.suspended_cards[0].parse_status == "suspended:2"


def test_remove_time_counter_releases_to_hand():
    """When last counter is removed, card moves to hand with suspend_ready status."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    suspended = _make_suspended_card(card, remaining_counters=1)

    player = get_player(gs, "p1")
    player.suspended_cards.append(suspended)
    hand_before = len(player.hand)

    gs = remove_time_counter(gs, "p1")

    updated_player = get_player(gs, "p1")
    assert len(updated_player.suspended_cards) == 0  # No longer suspended
    assert len(updated_player.hand) == hand_before + 1  # Moved to hand
    assert updated_player.hand[-1].parse_status == "suspend_ready"


def test_remove_time_counter_pure_transform():
    """remove_time_counter returns a new GameState object."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    suspended = _make_suspended_card(card, remaining_counters=2)

    player = get_player(gs, "p1")
    player.suspended_cards.append(suspended)

    old_id = id(gs)
    gs = remove_time_counter(gs, "p1")

    assert id(gs) != old_id


def test_remove_time_counter_wrong_player():
    """remove_time_counter only affects the specified player's cards."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    suspended = _make_suspended_card(card, remaining_counters=2)

    p1 = get_player(gs, "p1")
    p1.suspended_cards.append(suspended)

    # Remove counter for p2 (who has no suspended cards)
    gs = remove_time_counter(gs, "p2")

    updated_p1 = get_player(gs, "p1")
    assert len(updated_p1.suspended_cards) == 1
    assert updated_p1.suspended_cards[0].parse_status == "suspended:2"


def test_remove_time_counter_no_suspended():
    """remove_time_counter is no-op when player has no suspended cards."""
    gs = _make_game()

    gs_before_id = id(gs)
    gs = remove_time_counter(gs, "p1")

    assert id(gs) == gs_before_id


# --- Suspend Ready Cards Tests ---

def test_get_suspend_ready_cards():
    """get_suspend_ready_cards returns cards with suspend_ready status."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    ready_card = card.model_copy(update={"parse_status": "suspend_ready"})

    player = get_player(gs, "p1")
    player.hand.append(ready_card)

    ready_list = get_suspend_ready_cards(gs, "p1")
    assert len(ready_list) == 1
    assert ready_list[0]["name"] == card.name
    assert ready_list[0]["mana_cost"] == ""  # Cast without paying mana cost


def test_get_suspend_ready_cards_excludes_suspended():
    """get_suspend_ready_cards excludes cards still in suspended state."""
    gs = _make_game()
    card1 = _make_suspend_card(suspend_n=3)
    ready_card = card1.model_copy(update={"parse_status": "suspend_ready"})

    card2 = _make_suspend_card(name="Another", suspend_n=2)
    still_suspended = _make_suspended_card(card2, remaining_counters=1)

    player = get_player(gs, "p1")
    player.hand.append(ready_card)
    player.suspended_cards.append(still_suspended)

    ready_list = get_suspend_ready_cards(gs, "p1")
    assert len(ready_list) == 1


def test_get_suspend_ready_cards_wrong_player():
    """get_suspend_ready_cards returns empty list for player with no cards."""
    gs = _make_game()

    ready_list = get_suspend_ready_cards(gs, "p2")
    assert ready_list == []


# --- Multi-Turn Suspend Flow Tests ---

def test_full_suspend_flow_three_turns():
    """Full suspend flow: 3 counters -> 2 -> 1 -> released to hand."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)
    suspended = _make_suspended_card(card, remaining_counters=3)

    player = get_player(gs, "p1")
    player.suspended_cards.append(suspended)

    # Turn 1: upkeep — counter goes from 3 to 2
    gs = remove_time_counter(gs, "p1")
    p1 = get_player(gs, "p1")
    assert len(p1.suspended_cards) == 1
    assert p1.suspended_cards[0].parse_status == "suspended:2"

    # Turn 2: upkeep — counter goes from 2 to 1
    gs = remove_time_counter(gs, "p1")
    p1 = get_player(gs, "p1")
    assert len(p1.suspended_cards) == 1
    assert p1.suspended_cards[0].parse_status == "suspended:1"

    # Turn 3: upkeep — last counter removed, card released to hand
    gs = remove_time_counter(gs, "p1")
    p1 = get_player(gs, "p1")
    assert len(p1.suspended_cards) == 0
    assert len(p1.hand) == 1
    assert p1.hand[0].parse_status == "suspend_ready"


def test_multiple_suspended_cards_independent():
    """Multiple suspended cards track counters independently."""
    gs = _make_game()
    card1 = _make_suspend_card(name="Cinder Cloud", suspend_n=3)
    card2 = _make_suspend_card(name="Another Spell", suspend_n=2)

    s1 = _make_suspended_card(card1, remaining_counters=3)
    s2 = _make_suspended_card(card2, remaining_counters=2)

    player = get_player(gs, "p1")
    player.suspended_cards.extend([s1, s2])

    # Turn 1: both decrement
    gs = remove_time_counter(gs, "p1")
    p1 = get_player(gs, "p1")
    statuses = {c.parse_status for c in p1.suspended_cards}
    assert "suspended:2" in statuses
    assert "suspended:1" in statuses

    # Turn 2: card2 released, card1 still suspended
    gs = remove_time_counter(gs, "p1")
    p1 = get_player(gs, "p1")
    assert len(p1.suspended_cards) == 1
    assert p1.suspended_cards[0].parse_status == "suspended:1"
    assert len(p1.hand) == 1


def test_suspend_ready_card_stays_in_hand_on_subsequent_upkeeps():
    """A suspend_ready card that wasn't cast stays in hand on next upkeep."""
    gs = _make_game()
    card = _make_suspend_card(suspend_n=3)

    # Card is already ready (simulating it was released last turn but not cast)
    ready_card = card.model_copy(update={"parse_status": "suspend_ready"})
    player = get_player(gs, "p1")
    player.hand.append(ready_card)

    gs = remove_time_counter(gs, "p1")

    # Card should still be in hand (it's not in suspended_cards so it won't be touched)
    p1 = get_player(gs, "p1")
    assert len(p1.hand) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
