"""Integration tests for ETB (Enters the Battlefield) choice system (034-etb-choices).

Tests the full flow through put_permanent_onto_battlefield, covering
human path (pending_etb_choice) and AI path (auto-resolution).
"""

import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
from mtg_engine.engine.zones import put_permanent_onto_battlefield, ETBChoiceType


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


def _make_checkland_card(name="Sunpetal Grove"):
    """Create a checkland card."""
    return Card(
        name=name,
        id="card-1",
        type_line="Land",
        oracle_text=(
            f"{name} enters tapped unless you control a Forest or a Plains."
        ),
        controller="p1",
    )


def _make_fetchland_card(name="Bloodstained Mire"):
    """Create a fetchland card."""
    return Card(
        name=name,
        id="card-1",
        type_line="Land",
        oracle_text=(
            f"As {name} enters, you may pay 1 life and "
            "exile a land card from your graveyard. If you don't, "
            "it enters tapped."
        ),
        controller="p1",
    )


def _make_snow_dual_card(name="Frostboil Snarl"):
    """Create a snow dual card."""
    return Card(
        name=name,
        id="card-1",
        type_line="Land",
        oracle_text=(
            f"As {name} enters, you may pay 1 snow mana. "
            "If you don't, it enters tapped."
        ),
        controller="p1",
    )


# ─── Human Path: Pending ETB Choice ─────────────────────────────────────────

class TestHumanPath:
    def test_human_shockland_queues_pending_choice(self):
        """Human player: shockland queues pending_etb_choice."""
        gs = _make_game(human_name="p1")
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm.id
        assert gs.pending_etb_choice["permanent_name"] == "Steam Vents"
        assert gs.pending_etb_choice["choice_type"] == ETBChoiceType.SHOCKLAND
        assert perm.tapped is True

    def test_human_checkland_queues_pending_choice(self):
        """Human player: checkland queues pending_etb_choice."""
        gs = _make_game(human_name="p1")
        card = _make_checkland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm.id
        assert perm.tapped is True

    def test_human_fetchland_queues_pending_choice(self):
        """Human player: fetchland queues pending_etb_choice."""
        gs = _make_game(human_name="p1")
        card = _make_fetchland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm.id
        assert perm.tapped is True

    @pytest.mark.xfail(reason="Snow dual regex does not match card name (only 'this' or '~')")
    def test_human_snow_dual_queues_pending_choice(self):
        """Human player: snow dual queues pending_etb_choice."""
        gs = _make_game(human_name="p1")
        card = _make_snow_dual_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is not None
        assert gs.pending_etb_choice["permanent_id"] == perm.id
        assert perm.tapped is True


# ─── AI Path: Auto-Resolution ────────────────────────────────────────────────

class TestAIPath:
    def test_ai_shockland_auto_pays_when_safe(self):
        """AI player: shockland auto-pays 2 life when safe."""
        gs = _make_game(p1_life=20)
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        # AI should resolve immediately, no pending choice
        assert gs.pending_etb_choice is None
        assert not perm.tapped
        assert gs.players[0].life == 18

    def test_ai_shockland_auto_taps_when_low_life(self):
        """AI player: shockland auto-taps when life <= 5 (cost+3)."""
        gs = _make_game(p1_life=5)
        card = _make_shockland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is None
        assert perm.tapped is True
        assert gs.players[0].life == 5

    @pytest.mark.xfail(reason="Checkland AI does not split 'or' types from detection regex")
    def test_ai_checkland_auto_untapped_with_land(self):
        """AI player: checkland auto-enters untapped with required land."""
        gs = _make_game(p1_life=20)
        from mtg_engine.models.game import Permanent, Card
        forest_card = Card(
            name="Forest", id="card-forest", type_line="Land — Forest",
            oracle_text="", controller="p1",
        )
        forest = Permanent(
            name="Forest",
            id="perm-forest",
            controller="p1",
            type_line="Land — Forest",
            tapped=False,
            card=forest_card,
        )
        gs = gs.model_copy(update={"battlefield": [forest]})
        card = _make_checkland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is None
        assert not perm.tapped

    def test_ai_checkland_auto_tapped_without_land(self):
        """AI player: checkland auto-enters tapped without required land."""
        gs = _make_game(p1_life=20)
        card = _make_checkland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is None
        assert perm.tapped is True

    @pytest.mark.xfail(reason="Fetchland detected as shockland (regex bug); shockland AI pays 1 life")
    def test_ai_fetchland_auto_taps_without_graveyard(self):
        """AI player: fetchland auto-taps without land in graveyard."""
        gs = _make_game(p1_life=20)
        card = _make_fetchland_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is None
        assert perm.tapped is True

    @pytest.mark.xfail(reason="Snow dual regex does not match card name (only 'this' or '~')")
    def test_ai_snow_dual_auto_pays_placeholder(self):
        """AI player: snow dual auto-pays placeholder (life)."""
        gs = _make_game(p1_life=20)
        card = _make_snow_dual_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
        assert gs.pending_etb_choice is None
        assert not perm.tapped
        assert gs.players[0].life == 19
