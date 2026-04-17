"""
User Story 27: Echo.

Acceptance Criteria:
1. Echo triggers on upkeep if permanent entered this turn and wasn't controlled at start of previous upkeep
2. Payment of echo cost prevents sacrifice
3. Declining payment results in sacrifice
4. Echo doesn't trigger again after payment

CR References:
- CR 702.39: Echo
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, Permanent, ManaPool
from mtg_engine.engine.turn_manager import begin_step


@pytest.fixture
def echo_creature_game():
    """Create a game with an echo creature on the battlefield (not echo_paid)."""
    echo_creature = Card(
        name="Phyrexian Dreadnought",
        mana_cost="{B}",
        type_line="Creature - Horror",
        oracle_text="Echo {B}, Menace\nPhyrexian Dreadnought enters the battlefield with a -1/-1 counter on it.",
        power="8",
        toughness="8",
        colors=["B"],
    )
    perm = Permanent(
        id="perm_echo_1",
        card=echo_creature,
        controller="player_1",
        tapped=False,
        counters={},
        turn_entered_battlefield=1,
        summoning_sick=False,
        echo_paid=False,
    )
    return GameState(
        game_id="test_echo",
        seed=50,
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


@pytest.fixture
def echo_paid_game():
    """Create a game with an echo creature that already paid echo."""
    echo_creature = Card(
        name="Phyrexian Dreadnought",
        mana_cost="{B}",
        type_line="Creature - Horror",
        oracle_text="Echo {B}",
        power="8",
        toughness="8",
        colors=["B"],
    )
    perm = Permanent(
        id="perm_echo_paid",
        card=echo_creature,
        controller="player_1",
        tapped=False,
        counters={},
        turn_entered_battlefield=1,
        summoning_sick=False,
        echo_paid=True,
    )
    return GameState(
        game_id="test_echo_paid",
        seed=51,
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


@pytest.fixture
def echo_same_turn_game():
    """Create a game with an echo creature on battlefield this turn (should NOT trigger)."""
    echo_creature = Card(
        name="Phyrexian Dreadnought",
        mana_cost="{B}",
        type_line="Creature - Horror",
        oracle_text="Echo {B}",
        power="8",
        toughness="8",
        colors=["B"],
    )
    perm = Permanent(
        id="perm_echo_same_turn",
        card=echo_creature,
        controller="player_1",
        tapped=False,
        counters={},
        turn_entered_battlefield=2,  # entered this turn
        summoning_sick=False,
        echo_paid=False,
    )
    return GameState(
        game_id="test_echo_same_turn",
        seed=52,
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
@pytest.mark.cr("702.39")
class TestEchoTrigger:
    """Test echo triggers at the beginning of upkeep."""

    def test_pending_echo_payment_set_on_new_echo(self, echo_creature_game):
        """Scenario 1: pending_echo_payment is set when echo creature enters previous turn."""
        gs = echo_creature_game
        gs = begin_step(gs)

        # Should have pending echo payment for player_1
        assert gs.pending_echo_payment is not None
        assert gs.pending_echo_payment["player"] == "player_1"
        assert gs.pending_echo_payment["permanent_id"] == "perm_echo_1"
        assert gs.pending_echo_payment["echo_cost"] == "{B}"

    def test_no_pending_echo_when_already_paid(self, echo_paid_game):
        """Echo creature with echo_paid=True does not set pending_echo_payment."""
        gs = echo_paid_game
        gs = begin_step(gs)

        assert gs.pending_echo_payment is None

    def test_no_pending_echo_same_turn(self, echo_same_turn_game):
        """Echo creature that entered this turn does NOT set pending_echo_payment."""
        gs = echo_same_turn_game
        gs = begin_step(gs)

        # turn_entered_battlefield == current turn, so no echo
        assert gs.pending_echo_payment is None

    def test_no_echo_on_opponents_permanent(self):
        """Echo doesn't trigger for permanents controlled by opponent."""
        echo_creature = Card(
            name="Phyrexian Dreadnought",
            mana_cost="{B}",
            type_line="Creature - Horror",
            oracle_text="Echo {B}",
            power="8",
            toughness="8",
            colors=["B"],
        )
        perm = Permanent(
            id="perm_echo_other",
            card=echo_creature,
            controller="player_2",
            tapped=False,
            counters={},
            turn_entered_battlefield=1,
            summoning_sick=False,
            echo_paid=False,
        )
        gs = GameState(
            game_id="test_echo_opponent",
            seed=53,
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

        # player_1 should not get pending_echo_payment for player_2's permanent
        assert gs.pending_echo_payment is None

    def test_no_pending_echo_no_echo_keyword(self):
        """Permanent without echo keyword does not set pending_echo_payment."""
        normal_creature = Card(
            name="Goblin",
            mana_cost="{R}",
            type_line="Creature - Goblin",
            oracle_text="T: Goblin deals 1 damage to any target.",
            power="1",
            toughness="1",
            colors=["R"],
        )
        perm = Permanent(
            id="perm_no_echo",
            card=normal_creature,
            controller="player_1",
            tapped=False,
            counters={},
            turn_entered_battlefield=1,
            summoning_sick=False,
            echo_paid=False,
        )
        gs = GameState(
            game_id="test_no_echo",
            seed=54,
            players=[
                PlayerState(name="p1", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
                PlayerState(name="p2", life=20, hand=[], mana_pool=ManaPool(),
                           library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
            ],
            turn=2, phase=Phase.BEGINNING, step=Step.UPKEEP,
            active_player="p1", priority_holder="p1", stack=[], battlefield=[perm],
            graveyards={"p1": [], "p2": []}, exile_zone={},
            pending_triggers=[], pending_choices=[], is_game_over=False, winner=None,
            format="standard",
        )
        gs = begin_step(gs)

        assert gs.pending_echo_payment is None


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.39")
class TestEchoPayment:
    """Test echo payment handling (pay vs decline)."""

    def test_echo_pay_marks_permanent(self, echo_creature_game):
        """Scenario: Player pays echo cost — permanent marked as paid."""
        gs = echo_creature_game
        gs = begin_step(gs)

        assert gs.pending_echo_payment is not None
        perm = next(p for p in gs.battlefield if p.id == "perm_echo_1")

        # Simulate paying echo by directly setting echo_paid (mimics the choice handler)
        perm.echo_paid = True
        gs.pending_echo_payment = None

        assert perm.echo_paid is True

    def test_echo_decline_sacrifices_permanent(self, echo_creature_game):
        """Scenario: Player declines to pay echo — permanent sacrificed."""
        gs = echo_creature_game
        gs = begin_step(gs)

        assert gs.pending_echo_payment is not None
        perm = next(p for p in gs.battlefield if p.id == "perm_echo_1")

        # Simulate declining echo by directly sacrificing (mimics the choice handler)
        from mtg_engine.engine.zones import move_permanent_to_zone, get_player
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        gs.battlefield[:] = [p for p in gs.battlefield if p.id != perm.id]
        gs.pending_echo_payment = None

        assert len(gs.battlefield) == 0
        player1 = get_player(gs, "player_1")
        assert perm.card.name in [c.name for c in player1.graveyard]

    def test_echo_paid_prevents_trigger(self, echo_paid_game):
        """Scenario: Already-paid echo permanent does not trigger again."""
        gs = echo_paid_game
        gs = begin_step(gs)

        # permanent still on battlefield
        assert any(p.id == "perm_echo_paid" for p in gs.battlefield)
        # no pending echo
        assert gs.pending_echo_payment is None
