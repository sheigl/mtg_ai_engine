import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, PlayerState, Card, ExileStack
from mtg_engine.engine.zones import (
    move_card_to_zone,
    draw_card,
    get_player,
    # ZN-01: Exile zone functions
    create_exile_stack,
    get_exile_stack,
    get_exile_stacks_by_reason,
    add_to_exile_stack,
    remove_from_exile_stack,
    exile_card_with_reason,
    clear_exile_stack,
    # ZN-02: Graveyard functions
    get_graveyard_top,
    get_graveyard_size,
    search_graveyard,
    reorder_graveyard,
    # ZN-03: Command zone functions
    get_command_zone_cards,
    move_card_from_command_zone,
    move_card_to_command_zone,
    # ZN-04: Sideboard functions
    swap_sideboard_card,
    get_sideboard_size,
    search_sideboard,
)


def _make_game() -> GameState:
    card = Card(name="Forest", type_line="Basic Land — Forest")
    p1 = PlayerState(name="p1", library=[card])
    p2 = PlayerState(name="p2")
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2]
    )


# ============================================================================
# ZN-01: Exile Zone Enhancement Tests
# ============================================================================

def test_create_exile_stack():
    """Creating an exile stack adds it to game_state.exile_stacks."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    stack = create_exile_stack(gs, [card], "spell_resolution", "p1")
    assert isinstance(stack, ExileStack)
    assert stack.reason == "spell_resolution"
    assert stack.controller == "p1"
    assert len(stack.cards) == 1
    assert stack.cards[0].name == "Forest"
    assert len(gs.exile_stacks) == 1


def test_exile_stack_face_down():
    """Face-down exile stacks (e.g., foretell) are tracked."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    stack = create_exile_stack(gs, [card], "foretell", "p1", face_down=True)
    assert stack.face_down is True


def test_get_exile_stack():
    """Retrieve an exile stack by its ID."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    stack = create_exile_stack(gs, [card], "suspend", "p1")
    retrieved = get_exile_stack(gs, stack.stack_id)
    assert retrieved is not None
    assert retrieved.stack_id == stack.stack_id
    assert retrieved.cards[0].id == card.id


def test_get_exile_stack_not_found():
    """Getting a non-existent stack returns None."""
    gs = _make_game()
    result = get_exile_stack(gs, "nonexistent-id")
    assert result is None


def test_get_exile_stacks_by_reason():
    """Filter exile stacks by reason."""
    gs = _make_game()
    c1 = Card(name="Card1", type_line="Instant")
    c2 = Card(name="Card2", type_line="Sorcery")
    c3 = Card(name="Card3", type_line="Creature — Cat")
    get_player(gs, "p1").hand.extend([c1, c2, c3])

    create_exile_stack(gs, [c1], "suspend", "p1")
    create_exile_stack(gs, [c2], "foretell", "p1")
    create_exile_stack(gs, [c3], "suspend", "p2")

    suspend_stacks = get_exile_stacks_by_reason(gs, "suspend")
    assert len(suspend_stacks) == 2

    p1_suspend = get_exile_stacks_by_reason(gs, "suspend", controller="p1")
    assert len(p1_suspend) == 1
    assert p1_suspend[0].cards[0].name == "Card1"


def test_add_to_exile_stack():
    """Adding a card to an existing exile stack."""
    gs = _make_game()
    c1 = Card(name="First", type_line="Instant")
    c2 = Card(name="Second", type_line="Sorcery")
    get_player(gs, "p1").hand.extend([c1, c2])

    stack = create_exile_stack(gs, [c1], "group_exile", "p1")
    result = add_to_exile_stack(gs, stack.stack_id, c2)

    assert result is not None
    assert len(result.cards) == 2
    assert result.cards[1].name == "Second"


def test_add_to_exile_stack_not_found():
    """Adding to non-existent stack returns None."""
    gs = _make_game()
    card = Card(name="Test", type_line="Instant")
    result = add_to_exile_stack(gs, "nonexistent", card)
    assert result is None


def test_remove_from_exile_stack():
    """Removing a card from an exile stack."""
    gs = _make_game()
    c1 = Card(name="First", type_line="Instant")
    c2 = Card(name="Second", type_line="Sorcery")
    get_player(gs, "p1").hand.extend([c1, c2])

    stack = create_exile_stack(gs, [c1, c2], "group_exile", "p1")
    assert len(stack.cards) == 2

    removed = remove_from_exile_stack(gs, stack.stack_id, c1.id)
    assert removed is not None
    assert removed.name == "First"
    assert len(stack.cards) == 1
    assert stack.cards[0].name == "Second"


def test_remove_from_exile_stack_card_not_found():
    """Removing non-existent card from stack returns None."""
    gs = _make_game()
    card = Card(name="Test", type_line="Instant")
    stack = create_exile_stack(gs, [card], "test", "p1")
    removed = remove_from_exile_stack(gs, stack.stack_id, "nonexistent-id")
    assert removed is None


def test_exile_card_with_reason():
    """Exiling a card with reason creates both flat exile and stack."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")

    stack = exile_card_with_reason(gs, card, "hand", "p1", "suspend")

    assert isinstance(stack, ExileStack)
    assert stack.reason == "suspend"
    assert len(get_player(gs, "p1").hand) == 0
    assert len(get_player(gs, "p1").exile) == 1
    assert len(gs.exile_stacks) == 1


def test_exile_card_with_reason_face_down():
    """Face-down exile for foretell-like effects."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")

    stack = exile_card_with_reason(gs, card, "hand", "p1", "foretell", face_down=True)

    assert stack.face_down is True


def test_clear_exile_stack():
    """Clearing an exile stack removes it and its cards."""
    gs = _make_game()
    c1 = Card(name="First", type_line="Instant")
    c2 = Card(name="Second", type_line="Sorcery")
    get_player(gs, "p1").hand.extend([c1, c2])

    stack = create_exile_stack(gs, [c1, c2], "group_exile", "p1")
    # Also add to flat exile for realistic scenario
    get_player(gs, "p1").exile.extend([c1, c2])

    cleared = clear_exile_stack(gs, stack.stack_id)

    assert len(cleared) == 2
    assert len(gs.exile_stacks) == 0
    assert len(get_player(gs, "p1").exile) == 0


def test_clear_exile_stack_not_found():
    """Clearing non-existent stack returns empty list."""
    gs = _make_game()
    cleared = clear_exile_stack(gs, "nonexistent")
    assert cleared == []


# ============================================================================
# ZN-02: Graveyard Enhancement Tests
# ============================================================================

def test_get_graveyard_top():
    """Get the top card of graveyard (most recently added = last appended)."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    c2 = Card(name="Mountain", type_line="Basic Land — Mountain")
    # Graveyard uses append, so most recent is at the end
    get_player(gs, "p1").graveyard.extend([c1, c2])

    top = get_graveyard_top(gs, "p1")
    assert top is not None
    assert top.name == "Mountain"  # Most recently added (last appended)


def test_get_graveyard_top_empty():
    """Empty graveyard returns None."""
    gs = _make_game()
    top = get_graveyard_top(gs, "p1")
    assert top is None


def test_get_graveyard_size():
    """Get the number of cards in graveyard."""
    gs = _make_game()
    assert get_graveyard_size(gs, "p1") == 0

    gs, _ = draw_card(gs, "p1")
    gs = move_card_to_zone(gs, get_player(gs, "p1").hand[0], "hand", "graveyard", "p1")
    assert get_graveyard_size(gs, "p1") == 1


def test_search_graveyard_by_name():
    """Search graveyard for cards by name."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    c2 = Card(name="Mountain", type_line="Basic Land — Mountain")
    c3 = Card(name="Forest", type_line="Basic Land — Forest")
    get_player(gs, "p1").graveyard.extend([c1, c2, c3])

    results = search_graveyard(gs, "p1", card_name="Forest")
    assert len(results) == 2

    results = search_graveyard(gs, "p1", card_name="Mountain")
    assert len(results) == 1


def test_search_graveyard_by_type():
    """Search graveyard for cards by type."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    c2 = Card(name="Grizzly Bears", type_line="Creature — Bear")
    c3 = Card(name="Lightning Bolt", type_line="Instant")
    get_player(gs, "p1").graveyard.extend([c1, c2, c3])

    lands = search_graveyard(gs, "p1", card_type="Land")
    assert len(lands) == 1

    creatures = search_graveyard(gs, "p1", card_type="Creature")
    assert len(creatures) == 1


def test_search_graveyard_no_match():
    """Search graveyard with no matches returns empty list."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    get_player(gs, "p1").graveyard.append(c1)

    results = search_graveyard(gs, "p1", card_name="Nonexistent")
    assert len(results) == 0


def test_reorder_graveyard():
    """Reorder graveyard by card IDs."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    c2 = Card(name="Mountain", type_line="Basic Land — Mountain")
    c3 = Card(name="Island", type_line="Basic Land — Island")
    get_player(gs, "p1").graveyard.extend([c1, c2, c3])

    # Reorder: c3, c1, c2
    reorder_graveyard(gs, "p1", [c3.id, c1.id, c2.id])

    grav = get_player(gs, "p1").graveyard
    assert grav[0].id == c3.id
    assert grav[1].id == c1.id
    assert grav[2].id == c2.id


def test_reorder_graveyard_partial():
    """Partial reorder puts unspecified cards at bottom."""
    gs = _make_game()
    c1 = Card(name="Forest", type_line="Basic Land — Forest")
    c2 = Card(name="Mountain", type_line="Basic Land — Mountain")
    c3 = Card(name="Island", type_line="Basic Land — Island")
    get_player(gs, "p1").graveyard.extend([c1, c2, c3])

    # Only reorder c3 to top
    reorder_graveyard(gs, "p1", [c3.id])

    grav = get_player(gs, "p1").graveyard
    assert grav[0].id == c3.id
    assert len(grav) == 3


# ============================================================================
# ZN-03: Command Zone Tests
# ============================================================================

def test_command_zone_exists():
    """Command zone exists on PlayerState."""
    gs = _make_game()
    player = get_player(gs, "p1")
    assert hasattr(player, "command_zone")
    assert isinstance(player.command_zone, list)
    assert len(player.command_zone) == 0


def test_move_card_to_command_zone():
    """Moving a card to command zone works (does not remove from source — for redirects)."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")

    gs = move_card_to_command_zone(gs, card, "p1")

    assert len(get_player(gs, "p1").command_zone) == 1
    assert get_player(gs, "p1").command_zone[0].name == "Forest"
    # Note: move_card_to_command_zone does NOT remove from source zone;
    # it's designed for commander redirect where removal is handled separately


def test_move_card_to_command_zone_via_move_to_zone():
    """Moving a card to command zone via move_card_to_zone removes from source."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")

    gs = move_card_to_zone(gs, card, "hand", "command_zone", "p1")

    assert len(get_player(gs, "p1").command_zone) == 1
    assert get_player(gs, "p1").command_zone[0].name == "Forest"
    assert len(get_player(gs, "p1").hand) == 0


def test_get_command_zone_cards():
    """Get all cards in command zone."""
    gs = _make_game()
    c1 = Card(name="Commander", type_line="Legendary Creature — God")
    c2 = Card(name="Partner", type_line="Legendary Creature — God")
    get_player(gs, "p1").command_zone.extend([c1, c2])

    cards = get_command_zone_cards(gs, "p1")
    assert len(cards) == 2


def test_move_card_from_command_zone():
    """Move a card from command zone to another zone."""
    gs = _make_game()
    card = Card(name="Commander", type_line="Legendary Creature — God")
    get_player(gs, "p1").command_zone.append(card)

    gs = move_card_from_command_zone(gs, card, "p1", "library")

    assert len(get_player(gs, "p1").command_zone) == 0
    assert len(get_player(gs, "p1").library) == 2  # Original Forest + Commander


def test_commander_redirect_to_command_zone():
    """Commander going to graveyard is redirected to command zone."""
    c1 = Card(name="My Commander", type_line="Legendary Creature — God")
    p1 = PlayerState(
        name="p1",
        library=[c1],
        commander_name="My Commander",
    )
    p2 = PlayerState(name="p2")
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2], format="commander"
    )

    gs, _ = draw_card(gs, "p1")
    gs = move_card_to_zone(gs, c1, "hand", "graveyard", "p1")

    assert len(get_player(gs, "p1").graveyard) == 0
    assert len(get_player(gs, "p1").command_zone) == 1
    assert get_player(gs, "p1").command_zone[0].name == "My Commander"


# ============================================================================
# ZN-04: Sideboard Tests
# ============================================================================

def test_sideboard_exists():
    """Sideboard zone exists on PlayerState."""
    gs = _make_game()
    player = get_player(gs, "p1")
    assert hasattr(player, "sideboard")
    assert isinstance(player.sideboard, list)
    assert len(player.sideboard) == 0


def test_get_sideboard_size():
    """Get sideboard size."""
    gs = _make_game()
    assert get_sideboard_size(gs, "p1") == 0

    c1 = Card(name="Sideboard Card", type_line="Instant")
    get_player(gs, "p1").sideboard.append(c1)
    assert get_sideboard_size(gs, "p1") == 1


def test_swap_sideboard_card():
    """Swap a hand card with a sideboard card."""
    gs = _make_game()
    hand_card = Card(name="Hand Card", type_line="Instant")
    side_card = Card(name="Side Card", type_line="Sorcery")
    get_player(gs, "p1").hand.append(hand_card)
    get_player(gs, "p1").sideboard.append(side_card)

    gs, returned_hand, returned_side = swap_sideboard_card(
        gs, "p1", hand_card.id, side_card.id
    )

    hand_names = {c.name for c in get_player(gs, "p1").hand}
    side_names = {c.name for c in get_player(gs, "p1").sideboard}

    assert "Side Card" in hand_names
    assert "Hand Card" in side_names
    assert returned_hand.name == "Hand Card"
    assert returned_side.name == "Side Card"


def test_swap_sideboard_card_hand_not_found():
    """Swapping non-existent hand card raises error."""
    gs = _make_game()
    side_card = Card(name="Side Card", type_line="Sorcery")
    get_player(gs, "p1").sideboard.append(side_card)

    try:
        swap_sideboard_card(gs, "p1", "nonexistent-id", side_card.id)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found in" in str(e)


def test_swap_sideboard_card_sideboard_not_found():
    """Swapping non-existent sideboard card raises error."""
    gs = _make_game()
    hand_card = Card(name="Hand Card", type_line="Instant")
    get_player(gs, "p1").hand.append(hand_card)

    try:
        swap_sideboard_card(gs, "p1", hand_card.id, "nonexistent-id")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found in" in str(e)


def test_search_sideboard_by_name():
    """Search sideboard for cards by name."""
    gs = _make_game()
    c1 = Card(name="Counterspell", type_line="Instant")
    c2 = Card(name="Doom Blade", type_line="Sorcery")
    c3 = Card(name="Counterspell", type_line="Instant")
    get_player(gs, "p1").sideboard.extend([c1, c2, c3])

    results = search_sideboard(gs, "p1", card_name="Counterspell")
    assert len(results) == 2

    results = search_sideboard(gs, "p1", card_name="Doom Blade")
    assert len(results) == 1


def test_search_sideboard_by_type():
    """Search sideboard for cards by type."""
    gs = _make_game()
    c1 = Card(name="Counterspell", type_line="Instant")
    c2 = Card(name="Doom Blade", type_line="Sorcery")
    c3 = Card(name="Stoneforge Mystic", type_line="Creature — Artificer")
    get_player(gs, "p1").sideboard.extend([c1, c2, c3])

    instants = search_sideboard(gs, "p1", card_type="Instant")
    assert len(instants) == 1

    creatures = search_sideboard(gs, "p1", card_type="Creature")
    assert len(creatures) == 1


def test_move_card_to_sideboard():
    """Moving a card to sideboard via move_card_to_zone."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")

    gs = move_card_to_zone(gs, card, "hand", "sideboard", "p1")

    assert len(get_player(gs, "p1").hand) == 0
    assert len(get_player(gs, "p1").sideboard) == 1
    assert get_player(gs, "p1").sideboard[0].name == "Forest"


def test_move_card_from_sideboard():
    """Moving a card from sideboard to hand via move_card_to_zone."""
    gs = _make_game()
    card = Card(name="Sideboard Card", type_line="Instant")
    get_player(gs, "p1").sideboard.append(card)

    gs = move_card_to_zone(gs, card, "sideboard", "hand", "p1")

    assert len(get_player(gs, "p1").sideboard) == 0
    assert len(get_player(gs, "p1").hand) == 1
    assert get_player(gs, "p1").hand[0].name == "Sideboard Card"
