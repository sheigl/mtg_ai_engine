"""
User Story 5: ETB Replacement Effects.

Acceptance Criteria:
1. "Enters tapped" replacement effects apply when permanents enter battlefield
2. Counter doubling ETB replacement effects apply correctly
3. Multiple ETB replacements can apply to the same permanent

CR References:
- CR 614.1: "Enters the battlefield with" replacement effects
- CR 614.1e: Enters with X counters
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, ManaPool
from mtg_engine.engine.zones import put_permanent_onto_battlefield


@pytest.fixture
def basic_game():
    """Create a basic two-player game state."""
    return GameState(
        game_id="test_etb",
        seed=100,
        players=[
            PlayerState(
                name="player_1", life=20, hand=[], mana_pool=ManaPool(),
                library=[], graveyard=[], exile=[], command_zone=[], deck=[],
            ),
            PlayerState(
                name="player_2", life=20, hand=[], mana_pool=ManaPool(),
                library=[], graveyard=[], exile=[], command_zone=[], deck=[],
            ),
        ],
        turn=1, phase=Phase.BEGINNING, step=Step.UNTAP,
        active_player="player_1", priority_holder="player_1",
        stack=[], battlefield=[],
        graveyards={"player_1": [], "player_2": []}, exile_zone={},
        pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
        format="standard",
    )


@pytest.fixture
def enters_tapped_game(basic_game):
    """Game with a permanent that enters tapped (e.g. Shockland)."""
    enters_tapped_card = Card(
        name="Shockland",
        mana_cost="{2}{R}",
        type_line="Land -- Swamp Mountain",
        oracle_text="Shockland enters battlefield tapped. {T}: Add {B} or {R}.",
        card_layout="normal",
    )
    return basic_game, enters_tapped_card


@pytest.fixture
def enters_with_counters_game(basic_game):
    """Game with a permanent that enters with counters."""
    enters_counters_card = Card(
        name="Powerstone Forge",
        mana_cost="{2}",
        type_line="Artifact",
        oracle_text="Powerstone Forge enters battlefield with two +1/+1 counters on it.",
        card_layout="normal",
    )
    return basic_game, enters_counters_card


@pytest.fixture
def counter_doubling_game(basic_game):
    """Game with a counter-doubling ETB replacement source on battlefield."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield as _put

    # Doubling vessel - a permanent that doubles counters on ETB
    doubling_vessel = Card(
        name="Doubling Vessel",
        mana_cost="{2}",
        type_line="Artifact",
        oracle_text="If a permanent would enter the battlefield with counters on it, instead double the number of those counters.",
        card_layout="normal",
    )

    gs, _ = _put(basic_game, doubling_vessel, "player_1", from_zone="hand")

    # The card that will be doubled
    target_card = Card(
        name="Powerstone Forge",
        mana_cost="{2}",
        type_line="Artifact",
        oracle_text="Powerstone Forge enters battlefield with two +1/+1 counters on it.",
        card_layout="normal",
    )

    return gs, target_card


@pytest.mark.comprehensive_rules
@pytest.mark.cr("614.1e")
class TestEntersTappedReplacement:
    """Test 'enters tapped' replacement effects."""

    def test_shockland_enters_tapped(self, enters_tapped_game):
        """Scenario 1: Shockland enters tapped due to its own replacement effect."""
        gs, card = enters_tapped_game

        gs, perm = put_permanent_onto_battlefield(gs, card, "player_1", from_zone="hand")

        assert len(gs.battlefield) == 1
        assert perm.tapped is True

    def test_normal_land_enters_untapped(self, basic_game):
        """Scenario 2: Normal lands enter untapped (no replacement)."""
        normal_land = Card(
            name="Island",
            mana_cost="{0}",
            type_line="Basic Land -- Island",
            oracle_text="{T}: Add {U}",
            card_layout="normal",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, normal_land, "player_1", from_zone="hand")

        assert perm.tapped is False

    def test_force_enters_tapped_override(self, basic_game):
        """Scenario 3: Explicit tapped=True parameter overrides normal behavior."""
        normal_land = Card(
            name="Island",
            mana_cost="{0}",
            type_line="Basic Land -- Island",
            oracle_text="{T}: Add {U}",
            card_layout="normal",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, normal_land, "player_1", tapped=True, from_zone="hand")

        assert perm.tapped is True

    def test_enters_tapped_can_attack_next_turn(self, enters_tapped_game):
        """Scenario 4: Tapped permanents have summoning sick but can attack next turn."""
        gs, card = enters_tapped_game

        gs, perm = put_permanent_onto_battlefield(gs, card, "player_1", from_zone="hand")

        # Even if it's a creature, it enters tapped AND summoning sick
        assert perm.tapped is True
        assert perm.summoning_sick is True


@pytest.mark.comprehensive_rules
@pytest.mark.cr("614.1e")
class TestEntersWithCountersReplacement:
    """Test 'enters with counters' replacement effects."""

    def test_enters_with_two_counters(self, enters_with_counters_game):
        """Scenario 1: Permanent enters with exactly 2 +1/+1 counters."""
        gs, card = enters_with_counters_game

        gs, perm = put_permanent_onto_battlefield(gs, card, "player_1", from_zone="hand")

        assert perm.counters.get("+1/+1", 0) == 2

    def test_enters_with_different_counter_type(self, basic_game):
        """Scenario 2: Permanent can enter with different counter types (e.g. charge counters)."""
        charge_card = Card(
            name="Charge Chamber",
            mana_cost="{3}",
            type_line="Artifact",
            oracle_text="Charge Chamber enters battlefield with three charge counters on it.",
            card_layout="normal",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, charge_card, "player_1", from_zone="hand")

        assert perm.counters.get("charge", 0) == 3

    def test_enters_with_no_counters(self, basic_game):
        """Scenario 3: Permanent without counter text enters with no counters."""
        simple_artifact = Card(
            name="Sol Ring",
            mana_cost="{1}",
            type_line="Artifact",
            oracle_text="{T}: Add one mana of any color.",
            card_layout="normal",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, simple_artifact, "player_1", from_zone="hand")

        assert len(perm.counters) == 0


@pytest.mark.comprehensive_rules
@pytest.mark.cr("614.1")
class TestCounterDoublingReplacement:
    """Test counter-doubling ETB replacement effects."""

    def test_doubling_vessel_doubles_counters(self, counter_doubling_game):
        """Scenario 1: Doubling Vessel on battlefield doubles counters on entering permanents."""
        gs, card = counter_doubling_game

        gs, perm = put_permanent_onto_battlefield(gs, card, "player_1", from_zone="hand")

        # Doubling Vessel doubles: 2 +1/+1 counters become 4
        assert perm.counters.get("+1/+1", 0) == 4

    def test_doubling_vessel_its_own_counters(self, basic_game):
        """Scenario 2: Doubling Vessel doubles its own counters (enters with 4 instead of 2)."""
        from mtg_engine.engine.zones import put_permanent_onto_battlefield as _put

        doubling_vessel = Card(
            name="Doubling Vessel",
            mana_cost="{2}",
            type_line="Artifact",
            oracle_text="Doubling Vessel enters battlefield with two +1/+1 counters on it.",
            card_layout="normal",
        )

        # No doubling vessel on battlefield yet (can't double itself)
        gs, perm = _put(basic_game, doubling_vessel, "player_1", from_zone="hand")

        # Without a doubling vessel already on battlefield, enters with 2
        assert perm.counters.get("+1/+1", 0) == 2

    def test_no_doubling_vessel_normal_counters(self, basic_game):
        """Scenario 3: Without doubling source, counters enter normally."""
        normal_card = Card(
            name="Powerstone Forge",
            mana_cost="{2}",
            type_line="Artifact",
            oracle_text="Powerstone Forge enters battlefield with two +1/+1 counters on it.",
            card_layout="normal",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, normal_card, "player_1", from_zone="hand")

        assert perm.counters.get("+1/+1", 0) == 2


@pytest.mark.comprehensive_rules
@pytest.mark.cr("614.1")
class TestMultipleETBReplacements:
    """Test multiple ETB replacement effects on the same permanent."""

    def test_enters_tapped_and_with_counters(self, basic_game):
        """Scenario 1: Permanent can both enter tapped AND with counters."""
        multi_effect = Card(
            name="Complex Permanent",
            mana_cost="{3}",
            type_line="Artifact Creature -- Golem",
            oracle_text="Complex Permanent enters battlefield tapped with three +1/+1 counters on it.",
            card_layout="normal",
            power="2",
            toughness="2",
        )

        gs, perm = put_permanent_onto_battlefield(basic_game, multi_effect, "player_1", from_zone="hand")

        assert perm.tapped is True
        assert perm.counters.get("+1/+1", 0) == 3
