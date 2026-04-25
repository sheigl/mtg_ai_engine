import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top


def test_duress_does_not_fizzle_on_hand_target():
    """BUG-16: Duress targeting a card in opponent's hand should not fizzle.

    The fizzle check in resolve_top() must include hand cards when validating
    targets for hand-targeting spells like Duress.
    """
    duress = Card(
        name="Duress",
        type_line="Sorcery",
        oracle_text="Target opponent reveals their hand. You choose a noncreature, nonland card other than an Island from among them. That player discards it.",
        mana_cost="{B}",
    )
    # Bot's hand contains a noncreature, nonland card (like Lightning Bolt)
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    p1 = PlayerState(
        name="You", life=20, hand=[duress], mana_pool=ManaPool(B=1)
    )
    p2 = PlayerState(
        name="Bot", life=20, hand=[bolt]
    )
    gs = GameState(
        game_id="duress_test", seed=1,
        active_player="You", priority_holder="You",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )

    # Cast Duress targeting the Lightning Bolt card in Bot's hand
    bolt_id = gs.players[1].hand[0].id
    gs = cast_spell(gs, "You", duress.id, targets=[bolt_id], mana_payment={"B": 1})

    assert len(gs.stack) == 1
    assert gs.stack[0].source_card.name == "Duress"
    assert gs.stack[0].targets == [bolt_id]

    # Resolve — this should NOT fizzle because the target card IS in the opponent's hand
    gs = resolve_top(gs)

    # Duress should have resolved (card auto-discarded since only 1 valid card)
    assert len(gs.stack) == 0
    assert gs.players[0].graveyard[0].name == "Duress"

    # Since there's only one valid card, it auto-discards (no choice needed)
    assert gs.pending_discard_choice is None
    assert gs.players[1].hand == []  # bolt was discarded
    assert gs.players[1].graveyard[0].name == "Lightning Bolt"


def test_duress_queues_choice_when_multiple_valid_cards():
    """Duress should queue a discard choice when opponent has multiple valid cards."""
    duress = Card(
        name="Duress",
        type_line="Sorcery",
        oracle_text="Target opponent reveals their hand. You choose a noncreature, nonland card other than an Island from among them. That player discards it.",
        mana_cost="{B}",
    )
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    brainstorm = Card(
        name="Brainstorm",
        type_line="Instant",
        oracle_text="Brainstorm. Draw three cards, then put three cards from your hand on top of your library.",
        mana_cost="{U}",
    )
    p1 = PlayerState(
        name="You", life=20, hand=[duress], mana_pool=ManaPool(B=1)
    )
    p2 = PlayerState(
        name="Bot", life=20, hand=[bolt, brainstorm]
    )
    gs = GameState(
        game_id="duress_choice_test", seed=1,
        active_player="You", priority_holder="You",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )

    # Target the first card
    bolt_id = gs.players[1].hand[0].id
    gs = cast_spell(gs, "You", duress.id, targets=[bolt_id], mana_payment={"B": 1})
    gs = resolve_top(gs)

    assert len(gs.stack) == 0
    assert gs.players[0].graveyard[0].name == "Duress"
    # Should have queued a choice since 2 valid cards
    assert gs.pending_discard_choice is not None
    assert gs.pending_discard_choice["player"] == "You"
    assert gs.pending_discard_choice["is_duress_effect"] is True
    assert len(gs.pending_discard_choice["opponent_hand"]) == 2


def test_duress_fizzles_when_all_targets_invalid():
    """Duress should fizzle if the target card is no longer in the target zone."""
    duress = Card(
        name="Duress",
        type_line="Sorcery",
        oracle_text="Target opponent reveals their hand. You choose a noncreature, nonland card other than an Island from among them. That player discards it.",
        mana_cost="{B}",
    )
    p1 = PlayerState(
        name="You", life=20, hand=[duress], mana_pool=ManaPool(B=1)
    )
    p2 = PlayerState(name="Bot", life=20, hand=[])  # Opponent has no cards
    gs = GameState(
        game_id="duress_fizzle_test", seed=1,
        active_player="You", priority_holder="You",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )

    # Cast Duress targeting a card that doesn't exist
    fake_id = "00000000-0000-0000-0000-000000000000"
    gs = cast_spell(gs, "You", duress.id, targets=[fake_id], mana_payment={"B": 1})

    assert len(gs.stack) == 1

    # Resolve — should fizzle because no valid targets
    gs = resolve_top(gs)

    assert len(gs.stack) == 0
    assert gs.players[0].graveyard[0].name == "Duress"
    assert gs.pending_discard_choice is None


def test_duress_fizzles_when_target_moved_from_hand():
    """Duress should fizzle if target card was moved from opponent's hand between cast and resolve."""
    duress = Card(
        name="Duress",
        type_line="Sorcery",
        oracle_text="Target opponent reveals their hand. You choose a noncreature, nonland card other than an Island from among them. That player discards it.",
        mana_cost="{B}",
    )
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    p1 = PlayerState(
        name="You", life=20, hand=[duress], mana_pool=ManaPool(B=1)
    )
    p2 = PlayerState(name="Bot", life=20, hand=[bolt])
    gs = GameState(
        game_id="duress_move_test", seed=1,
        active_player="You", priority_holder="You",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )

    bolt_id = gs.players[1].hand[0].id

    # Cast Duress
    gs = cast_spell(gs, "You", duress.id, targets=[bolt_id], mana_payment={"B": 1})

    # Simulate: opponent discards the card via some other effect
    gs.players[1].hand[:] = []
    gs.players[1].graveyard.append(bolt)

    # Resolve — should fizzle because target card no longer in hand
    gs = resolve_top(gs)

    assert len(gs.stack) == 0
    assert len(gs.players[0].graveyard) == 1
    assert gs.pending_discard_choice is None
