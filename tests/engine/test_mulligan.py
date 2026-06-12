"""
MLG-01: Mulligan system tests.
Tests all mulligan variants: London, Vancouver, Paris, Original.
"""
from mtg_engine.engine.mulligan import (
    MulliganType, apply_mulligan, get_mulligan_type, set_mulligan_type,
)
from mtg_engine.models.game import GameState, PlayerState
from mtg_engine.card_data.card_factory import create_card


def _make_gs(*, variant: str = "london") -> GameState:
    cards = [create_card(f"Card{i}") for i in range(60)]
    player = PlayerState(name="Alice", hand=cards[:7], library=cards[7:])
    gs = GameState(
        game_id="test-mull",
        seed=42,
        active_player="Alice",
        priority_holder="Alice",
        players=[player],
        mulligan_phase_active=True,
        mulligan_variant=variant,
    )
    return gs


class TestMulliganType:
    def test_london_default(self):
        gs = _make_gs()
        assert get_mulligan_type(gs) == MulliganType.LONDON

    def test_set_variant(self):
        gs = _make_gs()
        set_mulligan_type(gs, MulliganType.VANCOUVER)
        assert get_mulligan_type(gs) == MulliganType.VANCOUVER

    def test_all_variants(self):
        for v in MulliganType:
            gs = _make_gs(variant=v.value)
            assert get_mulligan_type(gs) == v


class TestLondonMulligan:
    def test_keep_hand(self):
        gs = _make_gs()
        hand_before = list(gs.players[0].hand)
        apply_mulligan(gs, "Alice", keep=True)
        assert gs.players[0].hand == hand_before
        assert gs.mulligan_phase_active is False

    def test_mulligan_once(self):
        gs = _make_gs()
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 6
        assert gs.hands_mulliganed["Alice"] == 1

    def test_mulligan_twice(self):
        gs = _make_gs()
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 6
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 5
        assert gs.hands_mulliganed["Alice"] == 2

    def test_cannot_mulligan_below_1(self):
        gs = _make_gs()
        # Mulligan to 1 card
        for _ in range(6):
            apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 1
        # Should auto-keep at 1 card
        gs.players_kept = []  # reset for test
        apply_mulligan(gs, "Alice", keep=False)
        assert gs.players[0].name in gs.players_kept

    def test_keep_ends_mulligan_phase(self):
        gs = _make_gs()
        assert gs.mulligan_phase_active is True
        apply_mulligan(gs, "Alice", keep=True)
        assert gs.mulligan_phase_active is False

    def test_mulligan_keeps_phase_active(self):
        gs = _make_gs()
        apply_mulligan(gs, "Alice", keep=False)
        assert gs.mulligan_phase_active is True


class TestVancouverMulligan:
    def test_scry_on_keep_fewer(self):
        gs = _make_gs(variant="vancouver")
        # Mulligan to 6
        apply_mulligan(gs, "Alice", keep=False)
        gs.players_kept.clear()
        # Keep at 6 cards → should get scry 1
        apply_mulligan(gs, "Alice", keep=True)
        assert gs.pending_scry_choice is not None
        assert gs.pending_scry_choice["player"] == "Alice"
        assert gs.pending_scry_choice["count"] == 1

    def test_no_scry_on_keep_7(self):
        gs = _make_gs(variant="vancouver")
        apply_mulligan(gs, "Alice", keep=True)
        # Kept at 7 → no scry
        assert gs.pending_scry_choice is None

    def test_keep_after_mulligan_triggers_scry(self):
        gs = _make_gs(variant="vancouver")
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 6
        gs.players_kept.clear()
        apply_mulligan(gs, "Alice", keep=True)
        assert gs.pending_scry_choice is not None


class TestParisMulligan:
    def test_paris_mulligan(self):
        gs = _make_gs(variant="paris")
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 6

    def test_paris_keep(self):
        gs = _make_gs(variant="paris")
        apply_mulligan(gs, "Alice", keep=True)
        assert len(gs.players[0].hand) == 7


class TestOriginalPartialParis:
    def test_first_mulligan_reshuffles(self):
        gs = _make_gs(variant="original")
        hand_before = list(gs.players[0].hand)
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 7  # partial paris keeps same count
        # Hand should be different after reshuffle
        assert gs.players[0].hand != hand_before

    def test_second_mulligan_reduces(self):
        gs = _make_gs(variant="original")
        # First mulligan: partial (draw 7 new)
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 7
        # Second mulligan: standard (reduce by 1)
        gs.players_kept.clear()
        apply_mulligan(gs, "Alice", keep=False)
        assert len(gs.players[0].hand) == 6


class TestMulliganValidation:
    def test_raises_if_not_mulligan_phase(self):
        gs = _make_gs()
        gs.mulligan_phase_active = False
        import pytest
        with pytest.raises(ValueError, match="Not in mulligan phase"):
            apply_mulligan(gs, "Alice", keep=False)

    def test_raises_if_already_kept(self):
        gs = _make_gs()
        gs.players_kept.append("Alice")  # simulate already kept
        gs.mulligan_phase_active = True  # ensure phase still active for this check
        import pytest
        with pytest.raises(ValueError, match="already kept"):
            apply_mulligan(gs, "Alice", keep=False)

    def test_raises_for_unknown_player(self):
        gs = _make_gs()
        import pytest
        with pytest.raises(ValueError, match="not found"):
            apply_mulligan(gs, "Unknown", keep=False)


class TestTwoPlayerMulligan:
    def test_both_players_must_keep(self):
        gs = GameState(
            game_id="test-2p",
            seed=42,
            active_player="Alice",
            priority_holder="Alice",
            players=[
                PlayerState(name="Alice", hand=[create_card(f"A{i}") for i in range(7)],
                            library=[create_card(f"Alib{i}") for i in range(53)]),
                PlayerState(name="Bob", hand=[create_card(f"B{i}") for i in range(7)],
                            library=[create_card(f"Blib{i}") for i in range(53)]),
            ],
            mulligan_phase_active=True,
        )
        assert gs.mulligan_phase_active is True
        # Alice keeps
        apply_mulligan(gs, "Alice", keep=True)
        assert gs.mulligan_phase_active is True  # Bob hasn't decided yet
        # Bob keeps
        apply_mulligan(gs, "Bob", keep=True)
        assert gs.mulligan_phase_active is False  # All kept
