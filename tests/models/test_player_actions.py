"""
PLA-01: Player Actions model tests.
"""
from mtg_engine.models.player_actions import (
    PlayerActionType, PlayerAction, ActionValidationResult, PlayerActionLog,
)


class TestPlayerActionType:
    def test_cast_spell_type(self):
        assert PlayerActionType.CAST_SPELL == "cast_spell"

    def test_play_land_type(self):
        assert PlayerActionType.PLAY_LAND == "play_land"

    def test_pass_priority_type(self):
        assert PlayerActionType.PASS_PRIORITY == "pass_priority"

    def test_all_types_unique(self):
        values = [t.value for t in PlayerActionType]
        assert len(values) == len(set(values))


class TestPlayerAction:
    def test_minimal_action(self):
        action = PlayerAction(
            action_type=PlayerActionType.PASS_PRIORITY,
            player_name="Alice",
        )
        assert action.action_type == PlayerActionType.PASS_PRIORITY
        assert action.player_name == "Alice"
        assert action.targets == []
        assert action.payload == {}

    def test_cast_spell_action(self):
        action = PlayerAction(
            action_type=PlayerActionType.CAST_SPELL,
            player_name="Alice",
            card_id="card-1",
            targets=["opponent-1"],
            payload={"mana_payment": {"R": 1}},
            description="Cast Lightning Bolt",
        )
        assert action.card_id == "card-1"
        assert "opponent-1" in action.targets
        assert action.payload["mana_payment"] == {"R": 1}

    def test_attack_action(self):
        action = PlayerAction(
            action_type=PlayerActionType.DECLARE_ATTACKERS,
            player_name="Bob",
            permanent_id="perm-1",
            targets=["Alice"],
        )
        assert action.permanent_id == "perm-1"

    def test_mulligan_action(self):
        action = PlayerAction(
            action_type=PlayerActionType.MULLIGAN,
            player_name="Alice",
            payload={"keep": False},
        )
        assert action.payload["keep"] is False

    def test_has_game_id(self):
        action = PlayerAction(
            action_type=PlayerActionType.PASS_PRIORITY,
            player_name="Alice",
            game_id="game-123",
        )
        assert action.game_id == "game-123"


class TestActionValidationResult:
    def test_legal_action(self):
        result = ActionValidationResult(is_legal=True)
        assert result.is_legal is True
        assert result.reason == ""

    def test_illegal_action(self):
        result = ActionValidationResult(
            is_legal=False,
            reason="Not enough mana",
        )
        assert result.is_legal is False
        assert result.reason == "Not enough mana"

    def test_with_action(self):
        action = PlayerAction(
            action_type=PlayerActionType.CAST_SPELL,
            player_name="Alice",
        )
        result = ActionValidationResult(is_legal=True, action=action)
        assert result.action is not None
        assert result.action.action_type == PlayerActionType.CAST_SPELL


class TestPlayerActionLog:
    def test_minimal_log(self):
        action = PlayerAction(
            action_type=PlayerActionType.PLAY_LAND,
            player_name="Alice",
        )
        log = PlayerActionLog(
            action=action,
            turn=1,
            phase="precombat_main",
            step="main",
        )
        assert log.turn == 1
        assert log.phase == "precombat_main"
        assert log.legal is True

    def test_log_with_timestamp(self):
        action = PlayerAction(
            action_type=PlayerActionType.PASS_PRIORITY,
            player_name="Bob",
        )
        import time
        log = PlayerActionLog(
            action=action,
            turn=3,
            phase="combat",
            step="declare_attackers",
            timestamp=time.time(),
        )
        assert log.timestamp > 0
