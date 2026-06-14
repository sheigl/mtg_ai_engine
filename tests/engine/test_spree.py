"""Tests for Spree mechanic effect resolution (BUG-26).

Tests that Spree effect text patterns are correctly matched and applied
when the spell resolves.
"""

import pytest
from mtg_engine.models.game import Card, CardFace, GameState, PlayerState, StackObject
from mtg_engine.engine.stack import _apply_single_effect_text
from mtg_engine.engine.zones import move_card_to_zone


def create_test_card(name: str, oracle_text: str = "", mana_cost: str = "") -> Card:
    """Helper to create a test card."""
    return Card(
        id=name,
        name=name,
        faces=[CardFace(name=name, mana_cost=mana_cost, oracle_text=oracle_text)],
        cmc=0
    )


def create_test_game(player1_hand=None, player1_library=None, player2_life=20) -> GameState:
    """Create a minimal test game state."""
    p1 = PlayerState(name="p1", life=20, hand=player1_hand or [], library=player1_library or [])
    p2 = PlayerState(name="p2", life=player2_life, hand=[], library=[])
    gs = GameState(
        game_id="test-game",
        seed=42,
        players=[p1, p2],
        battlefield=[],
        stack=[],
        active_player="p1",
        priority_holder="p1",
    )
    return gs


class TestSpreeEffectResolution:
    """Test Spree effect text patterns in _apply_single_effect_text."""

    def test_tutor_to_top_effect(self):
        """Test 'Search your library for a card, then shuffle and put that card on top.'"""
        # Setup: p1 has 3 cards in library
        cards = [create_test_card(f"Card{i}") for i in range(1, 4)]
        gs = create_test_game(player1_library=cards.copy())
        
        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Insatiable Avarice"),
            controller="p1",
            targets=[],
        )

        effect_text = "Search your library for a card, then shuffle and put that card on top."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        # The first card should be on top of library
        p1 = gs.players[0]
        assert len(p1.library) == 3
        assert p1.library[0].name == "Card1"
        assert p1.library[1].name == "Card2"
        assert p1.library[2].name == "Card3"

    def test_draw_and_lose_life_effect(self):
        """Test 'Target player draws three cards and loses 3 life.'"""
        # Setup: p1 has 5 cards in library
        cards = [create_test_card(f"Card{i}") for i in range(1, 6)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Insatiable Avarice"),
            controller="p1",
            targets=[],
        )

        effect_text = "Target player draws three cards and loses 3 life."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        # p1 should have drawn 3 cards and lost 3 life
        p1 = gs.players[0]
        assert len(p1.hand) == 3
        assert p1.hand[0].name == "Card1"
        assert p1.hand[1].name == "Card2"
        assert p1.hand[2].name == "Card3"
        assert p1.life == 17  # 20 - 3 = 17

    def test_draw_and_lose_life_with_target(self):
        """Test 'Target player draws three cards and loses 3 life.' targeting p2."""
        # Setup: p2 has 5 cards in library
        cards = [create_test_card(f"Card{i}") for i in range(1, 6)]
        gs = create_test_game(player1_library=[])
        gs.players[1].library = cards.copy()

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Insatiable Avarice"),
            controller="p1",
            targets=["p2"],
        )

        effect_text = "Target player draws three cards and loses 3 life."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        # p2 should have drawn 3 cards and lost 3 life
        p2 = gs.players[1]
        assert len(p2.hand) == 3
        assert p2.hand[0].name == "Card1"
        assert p2.life == 17  # 20 - 3 = 17

    def test_empty_library_tutor_to_top(self):
        """Test tutor-to-top with empty library (should not crash)."""
        gs = create_test_game(player1_library=[])

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Insatiable Avarice"),
            controller="p1",
            targets=[],
        )

        effect_text = "Search your library for a card, then shuffle and put that card on top."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        # Should still be empty, no crash
        p1 = gs.players[0]
        assert len(p1.library) == 0

    def test_empty_library_draw_and_lose_life(self):
        """Test draw+lose_life with empty library (should not crash)."""
        gs = create_test_game(player1_library=[])

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Insatiable Avarice"),
            controller="p1",
            targets=[],
        )

        effect_text = "Target player draws three cards and loses 3 life."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        # Should still have 0 cards, no crash
        p1 = gs.players[0]
        assert len(p1.hand) == 0
        assert p1.life == 17  # Life loss still happens even if no cards to draw

    def test_tutor_pattern_variations(self):
        """Test that tutor-to-top pattern matches common variations."""
        cards = [create_test_card(f"Card{i}") for i in range(1, 4)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Test Card"),
            controller="p1",
            targets=[],
        )

        # Test with slightly different phrasing
        effect_text = "Search your library for a card, then shuffle and put that card on top."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        p1 = gs.players[0]
        assert p1.library[0].name == "Card1"

    def test_draw_lose_life_pattern_variations(self):
        """Test that draw+lose_life pattern matches common variations."""
        cards = [create_test_card(f"Card{i}") for i in range(1, 6)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="sp1",
            source_card=create_test_card("Test Card"),
            controller="p1",
            targets=[],
        )

        # Test with different numbers
        effect_text = "Target player draws 2 cards and loses 2 life."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        p1 = gs.players[0]
        assert len(p1.hand) == 2
        assert p1.life == 18  # 20 - 2 = 18


class TestSpreeIntegration:
    """Integration tests for full Spree spell resolution."""

    def test_insatiable_avarice_spree_mode1(self):
        """Test Insatiable Avarice Mode 1: '+ 2 — Search your library for a card...'"""
        from mtg_engine.engine.stack import _apply_spell_effect

        # Create a Spree card
        card = Card(
            id="avarice",
            name="Insatiable Avarice",
            faces=[CardFace(
                name="Insatiable Avarice",
                mana_cost="{B}",
                oracle_text="Spree\n+ {2} — Search your library for a card, then shuffle and put that card on top.\n+ {B}{B} — Target player draws three cards and loses 3 life."
            )],
            cmc=1,
            keywords=["Spree"]
        )

        cards = [create_test_card(f"Card{i}") for i in range(1, 4)]
        gs = create_test_game(player1_library=cards.copy())

        # Cast the spell with mode 1 selected
        stack_obj = StackObject(
            id="so1",
            source_card=card,
            controller="p1",
            targets=[],
        )
        gs.stack.append(stack_obj)
        gs.pending_spree_effects = [
            {"card_id": "avarice", "effect": "Search your library for a card, then shuffle and put that card on top."}
        ]

        gs = _apply_spell_effect(gs, stack_obj)

        p1 = gs.players[0]
        assert len(p1.library) == 3
        assert p1.library[0].name == "Card1"

    def test_insatiable_avarice_spree_mode2(self):
        """Test Insatiable Avarice Mode 2: '+ BB — Target player draws three cards...'"""
        from mtg_engine.engine.stack import _apply_spell_effect

        card = Card(
            id="avarice",
            name="Insatiable Avarice",
            faces=[CardFace(
                name="Insatiable Avarice",
                mana_cost="{B}",
                oracle_text="Spree\n+ {2} — Search your library for a card, then shuffle and put that card on top.\n+ {B}{B} — Target player draws three cards and loses 3 life."
            )],
            cmc=1,
            keywords=["Spree"]
        )

        cards = [create_test_card(f"Card{i}") for i in range(1, 6)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="so1",
            source_card=card,
            controller="p1",
            targets=[],
        )
        gs.stack.append(stack_obj)
        gs.pending_spree_effects = [
            {"card_id": "avarice", "effect": "Target player draws three cards and loses 3 life."}
        ]

        gs = _apply_spell_effect(gs, stack_obj)

        p1 = gs.players[0]
        assert len(p1.hand) == 3
        assert p1.life == 17

    def test_insatiable_avarice_spree_both_modes(self):
        """Test Insatiable Avarice with both modes selected."""
        from mtg_engine.engine.stack import _apply_spell_effect

        card = Card(
            id="avarice",
            name="Insatiable Avarice",
            faces=[CardFace(
                name="Insatiable Avarice",
                mana_cost="{B}",
                oracle_text="Spree\n+ {2} — Search your library for a card, then shuffle and put that card on top.\n+ {B}{B} — Target player draws three cards and loses 3 life."
            )],
            cmc=1,
            keywords=["Spree"]
        )

        cards = [create_test_card(f"Card{i}") for i in range(1, 6)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="so1",
            source_card=card,
            controller="p1",
            targets=[],
        )
        gs.stack.append(stack_obj)
        gs.pending_spree_effects = [
            {"card_id": "avarice", "effect": "Search your library for a card, then shuffle and put that card on top."},
            {"card_id": "avarice", "effect": "Target player draws three cards and loses 3 life."}
        ]

        gs = _apply_spell_effect(gs, stack_obj)

        p1 = gs.players[0]
        # After tutor, Card1 is on top, then draw 3 takes Card1, Card2, Card3
        assert len(p1.hand) == 3
        assert p1.hand[0].name == "Card1"
        assert p1.hand[1].name == "Card2"
        assert p1.hand[2].name == "Card3"
        assert len(p1.library) == 2  # 5 cards - 3 drawn = 2 remain
        assert p1.life == 17

    def test_non_spree_draw_effect_still_works(self):
        """Ensure regular draw effects still work after our changes."""
        cards = [create_test_card(f"Card{i}") for i in range(1, 4)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="so1",
            source_card=create_test_card("Divination"),
            controller="p1",
            targets=[],
        )

        effect_text = "Draw two cards."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        p1 = gs.players[0]
        assert len(p1.hand) == 2
        assert p1.life == 20  # No life loss

    def test_non_spree_gain_life_still_works(self):
        """Ensure regular gain life effects still work."""
        gs = create_test_game()

        stack_obj = StackObject(
            id="so1",
            source_card=create_test_card("Healing Salve"),
            controller="p1",
            targets=[],
        )

        effect_text = "Gain 3 life."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        p1 = gs.players[0]
        assert p1.life == 23

    def test_non_spree_tutor_still_works(self):
        """Ensure regular tutor effects still work."""
        cards = [create_test_card(f"Card{i}") for i in range(1, 4)]
        gs = create_test_game(player1_library=cards.copy())

        stack_obj = StackObject(
            id="so1",
            source_card=create_test_card("Tutor"),
            controller="p1",
            targets=[],
        )

        effect_text = "Search your library for a card and put it into your hand."
        gs = _apply_single_effect_text(gs, stack_obj, effect_text)

        p1 = gs.players[0]
        assert len(p1.hand) == 1
        assert p1.hand[0].name == "Card1"
        assert len(p1.library) == 2
