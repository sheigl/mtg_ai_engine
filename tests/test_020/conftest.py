"""Fixtures for comprehensive rules tests."""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step


@pytest.fixture
def game_with_two_players():
    """Create a basic two-player game state."""
    gs = GameState(
        game_id="test_game",
        seed=12345,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                max_hand_size=7,
                library=[],
                hand=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                max_hand_size=7,
                library=[],
                hand=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.ENDING,
        step=Step.CLEANUP,
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
    return gs
