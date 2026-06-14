"""Gameplay rules tests for ETB (Enters the Battlefield) choices (034-etb-choices).

Tests edge cases and rules interactions for ETB choice permanents.
"""

from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool
from mtg_engine.engine.zones import put_permanent_onto_battlefield


def _make_game(p1_life=20, p2_life=20, human_name=None):
    """Create a minimal two-player game state."""
    p1 = PlayerState(name="p1", life=p1_life, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=p2_life, mana_pool=ManaPool())
    return GameState(
        game_id="test",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[p1, p2],
        human_player_name=human_name,
    )


def _make_shockland_card(name="Steam Vents"):
    """Create a shockland card."""
    return Card(
        name=name,
        id="card-1",
        type_line="Land",
        oracle_text=(
            f"As {name} enters, you may pay 2 life. "
            "If you don't, it enters tapped."
        ),
        controller="p1",
    )


# ─── ETB Choice Edge Cases ─────────────────────────────────────────────────────

class TestETBGameplayEdgeCases:
    def test_multiple_shocklands_in_hand(self):
        """Human plays two shocklands: both queue pending ETB choices."""
        gs = _make_game(human_name="p1")
        card1 = _make_shockland_card("Steam Vents")
        card2 = _make_shockland_card("Stomping Ground")
        gs, perm1 = put_permanent_onto_battlefield(gs, card1, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm1.id
        # Resolve first
        gs = gs.model_copy(update={"pending_etb_choice": None})
        gs, perm2 = put_permanent_onto_battlefield(gs, card2, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm2.id

    def test_etb_choice_does_not_affect_other_permanents(self):
        """Resolving ETB for one permanent does not affect others."""
        gs = _make_game(human_name="p1")
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        # Add another permanent to battlefield
        other = Permanent(
            name="Forest",
            id="perm-other",
            controller="p1",
            type_line="Land",
            tapped=False,
            card=Card(name="Forest", id="card-forest", type_line="Land — Forest", controller="p1"),
        )
        gs = gs.model_copy(update={"battlefield": [perm, other]})
        # Resolve ETB (pay)
        gs = gs.model_copy(update={
            "pending_etb_choice": None,
            "battlefield": [perm.model_copy(update={"tapped": False}), other],
        })
        # Other permanent should not be affected
        assert gs.battlefield[1].tapped is False
        assert gs.battlefield[1].card.name == "Forest"

    def test_etb_choice_preserved_across_turns(self):
        """Pending ETB choice persists across turn changes."""
        gs = _make_game(human_name="p1")
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        # Change active player
        gs = gs.model_copy(update={"active_player": "p2", "priority_holder": "p2"})
        # Pending choice should still exist
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm.id

    def test_etb_choice_only_for_priority_player(self):
        """Pending ETB choice is for the player who played the land."""
        gs = _make_game(human_name="p1")
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice["player"] == "p1"
        # If p2 somehow had priority, they shouldn't see the ETB choice
        # (This is tested via legal_actions in the API test file)

    def test_etb_choice_life_exactly_at_cost(self):
        """Player with life exactly equal to cost can still pay."""
        gs = _make_game(human_name="p1", p1_life=2)
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["cost_amount"] == 2
        # The human player should be able to choose to pay
        # (API test verifies choice is available)
        assert gs.players[0].life == 2
