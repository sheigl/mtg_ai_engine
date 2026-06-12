"""
User Story 23: Snow Mana.

Acceptance Criteria:
1. When a snow permanent produces mana, the mana is tracked as snow mana
2. {S} cost can be satisfied by any snow mana (any color with snow > 0)
3. Paying {S} decrements both the color field and snow_by_color
4. Non-snow mana does not count as snow mana

CR References:
- CR 107.4h: The S symbol in a mana cost represents snow mana
- CR 106.11: A snow permanent has the snow supertype
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, Permanent, ManaPool
from mtg_engine.engine.mana import (
    parse_mana_cost, can_pay_cost, pay_cost, add_mana
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def snow_land_card():
    """Snow land that produces {G} mana as snow mana."""
    return Card(
        name="Snow-Covered Forest",
        mana_cost="",
        type_line="Snow-Covered Land — Forest",
        oracle_text="T: Add {G}.",
        colors=["G"],
    )


@pytest.fixture
def normal_land_card():
    """Non-snow land that produces {G} mana normally."""
    return Card(
        name="Forest",
        mana_cost="",
        type_line="Land — Forest",
        oracle_text="T: Add {G}.",
        colors=["G"],
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.comprehensive_rules
@pytest.mark.cr("107.4h", "106.11")
class TestSnowManaProduction:
    """Test snow mana tracking when snow permanents produce mana."""

    def test_snow_land_produces_snow_mana(self, snow_land_card):
        """Snow land produces mana that is tracked as snow mana."""
        pool = ManaPool()
        # Simulate snow mana being added by resolve_mana_ability for snow permanent
        # The add_mana function needs to accept a snow flag
        pool = add_mana(pool, "G", 1, is_snow=True)

        assert pool.G == 1
        assert pool.snow == 1
        assert pool.snow_by_color.get("G", 0) == 1

    def test_normal_land_produces_non_snow_mana(self, normal_land_card):
        """Non-snow land produces mana that is NOT tracked as snow mana."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 1, is_snow=False)

        assert pool.G == 1
        assert pool.snow == 0
        assert pool.snow_by_color == {}

    def test_snow_mana_adds_to_color_field(self):
        """Snow mana is added to both the color field and snow tracking."""
        pool = ManaPool()
        pool = add_mana(pool, "R", 2, is_snow=True)

        assert pool.R == 2
        assert pool.snow == 2
        assert pool.snow_by_color["R"] == 2

    def test_mixed_snow_and_non_snow_mana(self):
        """Both snow and non-snow mana can coexist in the same pool."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 3, is_snow=True)
        pool = add_mana(pool, "R", 2, is_snow=False)

        assert pool.G == 3
        assert pool.R == 2
        assert pool.snow == 3  # only green is snow
        assert pool.snow_by_color["G"] == 3
        assert "R" not in pool.snow_by_color


@pytest.mark.comprehensive_rules
@pytest.mark.cr("107.4h")
class TestSnowCostPayment:
    """Test {S} cost parsing and payment validation."""

    def test_parse_s_cost(self):
        """{S} is parsed correctly into the cost dict."""
        cost = parse_mana_cost("{S}")
        assert cost["S"] == 1

    def test_parse_multiple_s_cost(self):
        """Multiple {S} symbols are parsed correctly."""
        cost = parse_mana_cost("{S}{S}{S}")
        assert cost["S"] == 3

    def test_parse_mixed_s_and_color_cost(self):
        """{S} can be mixed with other mana symbols."""
        cost = parse_mana_cost("{1}{S}{G}")
        assert cost["S"] == 1
        assert cost["G"] == 1
        assert cost["generic"] == 1

    def test_can_pay_s_with_snow_mana(self):
        """{S} cost can be paid with snow mana from snow_by_color."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 1, is_snow=True)

        assert can_pay_cost(pool, "{S}") is True

    def test_can_pay_s_with_no_snow_mana(self):
        """{S} cost cannot be paid with non-snow mana alone."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 1, is_snow=False)

        assert can_pay_cost(pool, "{S}") is False

    def test_validate_s_payment(self):
        """{S} payment validates against snow_by_color and decrements both."""
        pool = ManaPool()
        pool = add_mana(pool, "R", 2, is_snow=True)

        payment = {"R": 1}  # Pay with 1 red snow mana
        result = can_pay_cost(pool, "{S}", payment)
        assert result is True

    def test_pay_s_decrements_both_counters(self):
        """Paying {S} decrements both the color field and snow_by_color."""
        pool = ManaPool()
        pool = add_mana(pool, "U", 2, is_snow=True)

        payment = {"U": 1}
        new_pool = pay_cost(pool, "{S}", payment)

        assert new_pool.U == 1
        assert new_pool.snow == 1
        assert new_pool.snow_by_color["U"] == 1

    def test_pay_s_from_mixed_snow(self):
        """{S} can be paid with any color snow mana, not just the attacker's color."""
        pool = ManaPool()
        pool = add_mana(pool, "B", 1, is_snow=True)
        pool = add_mana(pool, "W", 1, is_snow=True)

        # Pay {S} using black snow mana
        payment = {"B": 1}
        new_pool = pay_cost(pool, "{S}", payment)

        assert new_pool.B == 0
        assert new_pool.W == 1
        assert new_pool.snow == 1
        assert new_pool.snow_by_color.get("B", 0) == 0
        assert new_pool.snow_by_color["W"] == 1

    def test_pay_multiple_s(self):
        """Multiple {S} costs require multiple snow mana."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 2, is_snow=True)
        pool = add_mana(pool, "R", 1, is_snow=True)

        payment = {"G": 2, "R": 1}
        new_pool = pay_cost(pool, "{S}{S}{S}", payment)

        assert new_pool.G == 0
        assert new_pool.R == 0
        assert new_pool.snow == 0
        assert new_pool.snow_by_color == {}

    def test_cannot_pay_s_without_enough_snow(self):
        """{S} cost fails when there isn't enough snow mana."""
        pool = ManaPool()
        pool = add_mana(pool, "G", 1, is_snow=True)

        payment = {"G": 2}  # Try to pay with 2 snow mana but only have 1
        result = can_pay_cost(pool, "{S}{S}", payment)
        assert result is False


@pytest.mark.comprehensive_rules
@pytest.mark.cr("107.4h", "106.11")
class TestSnowManaIntegration:
    """Integration tests for snow mana through resolve_mana_ability."""

    def _make_game_state(self, player_name="Player1"):
        """Create a minimal GameState for testing."""
        return GameState(
            game_id="test_game",
            seed=12345,
            players=[
                PlayerState(
                    name=player_name,
                    life=20,
                    max_hand_size=7,
                    mana_pool=ManaPool(),
                    library=[],
                    hand=[],
                    graveyard=[],
                    exile=[],
                    command_zone=[],
                    deck=[],
                )
            ],
            turn=1,
            phase=Phase.PRECOMBAT_MAIN,
            step=Step.MAIN,
            active_player=player_name,
            priority_holder=player_name,
            stack=[],
            battlefield=[],
            graveyards={},
            exile_zone={},
            pending_triggers=[],
            pending_choices=[],
            is_game_over=False,
            winner=None,
            format="standard",
        )

    def test_resolve_mana_ability_snow_produces_snow_mana(self):
        """resolve_mana_ability on a snow permanent tracks mana as snow."""
        from mtg_engine.engine.mana import resolve_mana_ability

        snow_card = Card(
            name="Snow-Covered Forest",
            mana_cost="",
            type_line="Snow-Covered Land — Forest",
            oracle_text="T: Add {G}.",
            colors=["G"],
            supertypes=["Snow"],
        )
        snow_perm = Permanent(
            card=snow_card,
            controller="Player1",
            tapped=False,
        )

        gs = self._make_game_state()
        gs.battlefield = [snow_perm]

        gs = resolve_mana_ability(gs, snow_perm.id, "T: Add {G}.")

        assert gs.players[0].mana_pool.G == 1
        assert gs.players[0].mana_pool.snow == 1
        assert gs.players[0].mana_pool.snow_by_color.get("G", 0) == 1

    def test_resolve_mana_ability_non_snow_produces_non_snow(self):
        """resolve_mana_ability on a non-snow permanent does NOT track as snow."""
        from mtg_engine.engine.mana import resolve_mana_ability

        normal_card = Card(
            name="Forest",
            mana_cost="",
            type_line="Land — Forest",
            oracle_text="T: Add {G}.",
            colors=["G"],
            supertypes=[],
        )
        normal_perm = Permanent(
            card=normal_card,
            controller="Player1",
            tapped=False,
        )

        gs = self._make_game_state()
        gs.battlefield = [normal_perm]

        gs = resolve_mana_ability(gs, normal_perm.id, "T: Add {G}.")

        assert gs.players[0].mana_pool.G == 1
        assert gs.players[0].mana_pool.snow == 0
        assert gs.players[0].mana_pool.snow_by_color == {}

    def test_snow_mana_can_pay_s_cost_after_resolve(self):
        """Snow mana from resolve_mana_ability can satisfy {S} cost."""
        from mtg_engine.engine.mana import resolve_mana_ability

        snow_card = Card(
            name="Snow-Covered Forest",
            mana_cost="",
            type_line="Snow-Covered Land — Forest",
            oracle_text="T: Add {G}.",
            colors=["G"],
            supertypes=["Snow"],
        )
        snow_perm = Permanent(
            card=snow_card,
            controller="Player1",
            tapped=False,
        )

        gs = self._make_game_state()
        gs.battlefield = [snow_perm]

        gs = resolve_mana_ability(gs, snow_perm.id, "T: Add {G}.")

        pool = gs.players[0].mana_pool
        assert can_pay_cost(pool, "{S}") is True
        assert can_pay_cost(pool, "{2}{S}") is False
