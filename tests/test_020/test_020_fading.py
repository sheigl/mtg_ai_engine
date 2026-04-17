"""
User Story 26: Fading.

Acceptance Criteria:
1. Fading permanent enters battlefield with N time counters
2. One time counter removed at beginning of each upkeep
3. Permanent sacrificed when last counter is removed
4. Proliferate can extend lifetime by adding counters

CR References:
- CR 702.67: Fading
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, CardFace, Permanent, ManaPool
from mtg_engine.engine.turn_manager import begin_step
from mtg_engine.engine.zones import put_permanent_onto_battlefield


@pytest.fixture
def fading_card_game():
    """Create a game with a fading creature on the battlefield."""
    fading_creature = Card(
        name="Cloud of Faeries",
        mana_cost="{U}",
        type_line="Creature - Faerie",
        oracle_text="Flying, Fading 3",
        power="1",
        toughness="1",
        colors=["U"],
        card_layout="normal",
    )
    return GameState(
        game_id="test_fading",
        seed=42,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.BEGINNING,
        step=Step.UPKEEP,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.fixture
def fading_2_game():
    """Create a game with a fading creature that has 2 counters."""
    fading_creature = Card(
        name="Cloud of Faeries",
        mana_cost="{U}",
        type_line="Creature - Faerie",
        oracle_text="Flying, Fading 2",
        power="1",
        toughness="1",
        colors=["U"],
        card_layout="normal",
    )
    perm = Permanent(
        id="perm_fading_2",
        card=fading_creature,
        controller="player_1",
        tapped=False,
        counters={"fade": 2},
        turn_entered_battlefield=1,
        summoning_sick=False,
    )
    return GameState(
        game_id="test_fading_2",
        seed=43,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.BEGINNING,
        step=Step.UPKEEP,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[perm],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.fixture
def fading_1_game():
    """Create a game with a fading creature that has 1 counter — about to be sacrificed."""
    fading_creature = Card(
        name="Cloud of Faeries",
        mana_cost="{U}",
        type_line="Creature - Faerie",
        oracle_text="Flying, Fading 1",
        power="1",
        toughness="1",
        colors=["U"],
        card_layout="normal",
    )
    perm = Permanent(
        id="perm_fading_1",
        card=fading_creature,
        controller="player_1",
        tapped=False,
        counters={"fade": 1},
        turn_entered_battlefield=1,
        summoning_sick=False,
    )
    return GameState(
        game_id="test_fading_1",
        seed=44,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.BEGINNING,
        step=Step.UPKEEP,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[perm],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.fixture
def fading_3_game():
    """Create a game with a fading 3 creature — new on battlefield, 3 counters."""
    fading_creature = Card(
        name="Cloud of Faeries",
        mana_cost="{U}",
        type_line="Creature - Faerie",
        oracle_text="Flying, Fading 3",
        power="1",
        toughness="1",
        colors=["U"],
        card_layout="normal",
    )
    perm = Permanent(
        id="perm_fading_3",
        card=fading_creature,
        controller="player_1",
        tapped=False,
        counters={"fade": 3},
        turn_entered_battlefield=1,
        summoning_sick=False,
    )
    return GameState(
        game_id="test_fading_3",
        seed=45,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                hand=[],
                mana_pool=ManaPool(),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=2,
        phase=Phase.BEGINNING,
        step=Step.UPKEEP,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[perm],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.67")
class TestFadingEntry:
    """Test fading permanent enters with correct counter count."""

    def test_fading_3_enters_with_3_counters(self, fading_card_game):
        """Scenario 1: Fading 3 permanent enters battlefield with 3 fade counters."""
        gs = fading_card_game
        card = Card(
            name="Cloud of Faeries",
            mana_cost="{U}",
            type_line="Creature - Faerie",
            oracle_text="Flying, Fading 3",
            power="1",
            toughness="1",
            colors=["U"],
        )
        gs, perm = put_permanent_onto_battlefield(gs, card, "player_1", from_zone="hand")

        assert len(gs.battlefield) == 1
        assert perm.counters.get("fade", 0) == 3

    def test_fading_1_enters_with_1_counter(self):
        """Fading 1 permanent enters with 1 fade counter."""
        gs = GameState(
            game_id="test_fading_1_entry",
            seed=46,
            players=[
                PlayerState(name="p1", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
                PlayerState(name="p2", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
            ],
            turn=1, phase=Phase.BEGINNING, step=Step.UPKEEP,
            active_player="p1", priority_holder="p1", stack=[], battlefield=[],
            graveyards={"p1": [], "p2": []}, exile_zone={},
            pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
            format="standard",
        )
        card = Card(
            name="Bull Seer",
            mana_cost="{W}",
            type_line="Creature - Whale",
            oracle_text="Flying, Fading 1",
            power="1",
            toughness="2",
            colors=["W"],
        )
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")

        assert perm.counters.get("fade", 0) == 1

    def test_non_fading_enters_without_counters(self):
        """Non-fading permanent enters with no fade counters."""
        gs = GameState(
            game_id="test_no_fading",
            seed=47,
            players=[
                PlayerState(name="p1", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
                PlayerState(name="p2", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
            ],
            turn=1, phase=Phase.BEGINNING, step=Step.UPKEEP,
            active_player="p1", priority_holder="p1", stack=[], battlefield=[],
            graveyards={"p1": [], "p2": []}, exile_zone={},
            pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
            format="standard",
        )
        card = Card(
            name="Island",
            mana_cost="",
            type_line="Creature - Elf",
            oracle_text="Flying",
            power="1",
            toughness="1",
        )
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")

        assert perm.counters.get("fade", 0) == 0


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.67")
class TestFadingUpkeep:
    """Test fading upkeep processing (counter removal and sacrifice)."""

    def test_fading_2_removes_one_counter(self, fading_2_game):
        """Scenario: Fading 2 removes one counter at beginning of upkeep."""
        gs = fading_2_game
        gs = begin_step(gs)

        perm = gs.battlefield[0]
        assert perm.counters.get("fade", 0) == 1

    def test_fading_1_sacrificed_at_upkeep(self, fading_1_game):
        """Scenario: Fading 1 with one counter — removed to 0, then sacrificed."""
        gs = fading_1_game
        initial_count = len(gs.battlefield)
        gs = begin_step(gs)

        # Permanent should be gone (sacrificed)
        assert len(gs.battlefield) == initial_count - 1
        assert all(p.id != "perm_fading_1" for p in gs.battlefield)

    def test_fading_3_survives_until_last(self, fading_3_game):
        """Scenario: Fading 3 with 3 counters — removes one at upkeep."""
        gs = fading_3_game
        gs = begin_step(gs)

        perm = gs.battlefield[0]
        assert perm.counters.get("fade", 0) == 2

    def test_fading_repeated_upkeep_sacrifices(self):
        """Scenario: Fading 3 survives multiple upkeeps, then gets sacrificed."""
        fading_creature = Card(
            name="Cloud of Faeries",
            mana_cost="{U}",
            type_line="Creature - Faerie",
            oracle_text="Flying, Fading 3",
            power="1",
            toughness="1",
            colors=["U"],
        )

        # Upkeep 1: 3 counters → 2
        gs = GameState(
            game_id="test_fading_repeated",
            seed=48,
            players=[
                PlayerState(name="p1", life=20, hand=[], mana_pool=ManaPool(),
                            library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
                PlayerState(name="p2", life=20, hand=[], mana_pool=ManaPool(),
                            library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
            ],
            turn=2, phase=Phase.BEGINNING, step=Step.UPKEEP,
            active_player="p1", priority_holder="p1", stack=[], battlefield=[],
            graveyards={"p1": [], "p2": []}, exile_zone={},
            pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
            format="standard",
        )
        perm = Permanent(
            id="perm_fading_3_multi",
            card=fading_creature,
            controller="p1",
            tapped=False,
            counters={"fade": 3},
            turn_entered_battlefield=1,
            summoning_sick=False,
        )
        gs.battlefield.append(perm)

        gs = begin_step(gs)
        perm = gs.battlefield[0]
        assert perm.counters.get("fade", 0) == 2

        # Upkeep 2: 2 counters → 1
        gs.step = Step.UPKEEP
        gs = begin_step(gs)
        perm = gs.battlefield[0]
        assert perm.counters.get("fade", 0) == 1

        # Upkeep 3: 1 counter → 0, sacrificed
        gs = begin_step(gs)
        assert len(gs.battlefield) == 0

    def test_fading_opponent_permanent_not_affected(self):
        """Scenario: Opponent's fading permanent is not affected by this player's upkeep."""
        fading_creature = Card(
            name="Cloud of Faeries",
            mana_cost="{U}",
            type_line="Creature - Faerie",
            oracle_text="Flying, Fading 2",
            power="1",
            toughness="1",
            colors=["U"],
        )
        perm = Permanent(
            id="perm_fading_opp",
            card=fading_creature,
            controller="player_2",
            tapped=False,
            counters={"fade": 2},
            turn_entered_battlefield=1,
            summoning_sick=False,
        )
        gs = GameState(
            game_id="test_fading_opp",
            seed=49,
            players=[
                PlayerState(name="player_1", life=20, hand=[], mana_pool=ManaPool(),
                            library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
                PlayerState(name="player_2", life=20, hand=[], mana_pool=ManaPool(),
                            library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
            ],
            turn=2, phase=Phase.BEGINNING, step=Step.UPKEEP,
            active_player="player_1", priority_holder="player_1", stack=[], battlefield=[perm],
            graveyards={"player_1": [], "player_2": []}, exile_zone={},
            pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
            format="standard",
        )
        gs = begin_step(gs)

        # Opponent's fading permanent should still have 2 counters
        assert perm.counters.get("fade", 0) == 2
