"""
COM-01: Companion mechanic integration tests.
CR 702.148 — Full state transform verification and edge cases.
"""
import pytest

from mtg_engine.engine.companion import (
    has_companion, check_companion_restriction, activate_companion,
    get_companion_from_sideboard, can_activate_companion,
)
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool


def _companion_card(
    name: str = "Kaito Shizuki",
    restriction: str = "You own fewer than 40 cards",
) -> Card:
    return Card(
        id=f"id-{name}",
        name=name,
        type_line="Creature — Human Monk",
        oracle_text=restriction + "\nCompanion",
        keywords=["companion"],
        mana_cost="{1}{R}",
        power="2",
        toughness="2",
    )


def _make_gs(
    alice_sideboard: list[Card] | None = None,
    alice_hand_size: int = 0,
    alice_library_size: int = 30,
    alice_mana: dict[str, int] | None = None,
    bob_sideboard: list[Card] | None = None,
    bob_hand_size: int = 0,
    bob_library_size: int = 30,
    bob_mana: dict[str, int] | None = None,
) -> GameState:
    alice_mana_pool = ManaPool()
    if alice_mana:
        for color, amount in alice_mana.items():
            setattr(alice_mana_pool, color, amount)

    bob_mana_pool = ManaPool()
    if bob_mana:
        for color, amount in bob_mana.items():
            setattr(bob_mana_pool, color, amount)

    return GameState(
        game_id="test-companion-int",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(
                name="Alice",
                hand=[Card(id=f"ah-{i}", name=f"AliceHand{i}") for i in range(alice_hand_size)],
                library=[Card(id=f"al-{i}", name=f"AliceLib{i}") for i in range(alice_library_size)],
                sideboard=alice_sideboard or [],
                mana_pool=alice_mana_pool,
            ),
            PlayerState(
                name="Bob",
                hand=[Card(id=f"bh-{i}", name=f"BobHand{i}") for i in range(bob_hand_size)],
                library=[Card(id=f"bl-{i}", name=f"BobLib{i}") for i in range(bob_library_size)],
                sideboard=bob_sideboard or [],
                mana_pool=bob_mana_pool,
            ),
        ],
    )


class TestSuccessfulActivationTransform:
    """Full state transform verification on successful activation."""

    def test_companion_moves_from_sideboard_to_hand(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=3,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert card is not None
        assert len(new_gs.players[0].hand) == 4
        assert len(new_gs.players[0].sideboard) == 0
        assert companion in new_gs.players[0].hand

    def test_mana_deducted_correctly(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 7},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert new_gs.players[0].mana_pool.C == 4

    def test_companion_used_flag_set(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert new_gs.companion_used.get("Alice") is True
        # Bob's flag should not be set
        assert new_gs.companion_used.get("Bob") is None or new_gs.companion_used.get("Bob") is False

    def test_other_player_unchanged(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
            bob_hand_size=7,
            bob_library_size=25,
            bob_mana={"W": 4},
        )
        new_gs, card = activate_companion(gs, "Alice")

        # Bob's state should be completely unchanged
        assert len(new_gs.players[1].hand) == 7
        assert len(new_gs.players[1].library) == 25
        assert new_gs.players[1].mana_pool.W == 4


class TestImmutability:
    """Original GameState, PlayerState, ManaPool all unchanged after activation."""

    def test_original_game_state_unchanged(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 5},
        )
        original_alice = gs.players[0]

        new_gs, card = activate_companion(gs, "Alice")

        # Original GameState player still has companion in sideboard
        assert companion in original_alice.sideboard
        assert companion not in original_alice.hand
        assert not gs.companion_used.get("Alice")

    def test_original_player_state_unchanged(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 5},
        )
        original_alice = gs.players[0]
        original_hand_len = len(original_alice.hand)
        original_sideboard_len = len(original_alice.sideboard)

        new_gs, card = activate_companion(gs, "Alice")

        assert len(original_alice.hand) == original_hand_len
        assert len(original_alice.sideboard) == original_sideboard_len

    def test_original_mana_pool_unchanged(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 5},
        )
        original_c = gs.players[0].mana_pool.C

        new_gs, card = activate_companion(gs, "Alice")

        assert gs.players[0].mana_pool.C == original_c
        # New state should have deducted mana
        assert new_gs.players[0].mana_pool.C == 2


class TestOncePerGameRestriction:
    """Companion can only be activated once per game."""

    def test_second_activation_fails(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 6},
        )
        new_gs, card1 = activate_companion(gs, "Alice")
        assert card1 is not None

        gs2, card2 = activate_companion(new_gs, "Alice")
        assert card2 is None

    def test_second_activation_returns_same_state(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 6},
        )
        new_gs, card1 = activate_companion(gs, "Alice")

        # Second call on the same state returns it unchanged
        gs2, card2 = activate_companion(new_gs, "Alice")
        assert gs2 is new_gs


class TestMultiPlayerIndependent:
    """Each player's companion usage is tracked independently."""

    def test_both_players_can_activate(self):
        alice_comp = _companion_card(name="Kaito Shizuki")
        bob_comp = _companion_card(name="Ob Nixilis Reignited", restriction="You control no creatures")
        gs = _make_gs(
            alice_sideboard=[alice_comp],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
            bob_sideboard=[bob_comp],
            bob_hand_size=5,
            bob_library_size=30,
            bob_mana={"C": 3},
        )

        # Alice activates
        new_gs, card_a = activate_companion(gs, "Alice")
        assert card_a is not None
        assert card_a.name == "Kaito Shizuki"

        # Bob can still activate (independent tracking)
        gs2, card_b = activate_companion(new_gs, "Bob")
        assert card_b is not None
        assert card_b.name == "Ob Nixilis Reignited"

    def test_alice_used_does_not_block_bob(self):
        alice_comp = _companion_card(name="Kaito Shizuki")
        bob_comp = _companion_card(name="Ob Nixilis Reignited", restriction="You control no creatures")
        gs = _make_gs(
            alice_sideboard=[alice_comp],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 6},
            bob_sideboard=[bob_comp],
            bob_hand_size=5,
            bob_library_size=30,
            bob_mana={"C": 3},
        )

        # Alice activates twice (second fails)
        new_gs, _ = activate_companion(gs, "Alice")
        gs2, card_fail = activate_companion(new_gs, "Alice")
        assert card_fail is None

        # Bob can still activate
        gs3, card_b = activate_companion(gs2, "Bob")
        assert card_b is not None


class TestActivationFailureCases:
    """Various conditions that prevent activation."""

    def test_no_mana_at_all(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana=None,
        )
        new_gs, card = activate_companion(gs, "Alice")
        assert card is None

    def test_partial_mana_not_enough(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"W": 1},
        )
        new_gs, card = activate_companion(gs, "Alice")
        assert card is None

    def test_no_companion_in_sideboard(self):
        gs = _make_gs(
            alice_sideboard=[Card(id="x", name="Normal Card")],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")
        assert card is None

    def test_restriction_not_met(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=20,
            alice_library_size=30,  # 50 total >= 40 threshold
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")
        assert card is None

    def test_nonexistent_player(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Charlie")
        assert card is None

    def test_failure_returns_same_game_state(self):
        """When activation fails for any reason, same GameState object returned."""
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 2},  # Not enough mana
        )
        new_gs, card = activate_companion(gs, "Alice")
        assert card is None
        assert new_gs is gs


class TestManaDeductionStrategy:
    """Verify the colorless-first deduction strategy."""

    def test_prefers_colorless(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 2, "W": 2},
        )
        new_gs, card = activate_companion(gs, "Alice")

        # Should deduct C first (2), then W (1)
        assert new_gs.players[0].mana_pool.C == 0
        assert new_gs.players[0].mana_pool.W == 1

    def test_deducts_all_colors_if_needed(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 1, "W": 1, "U": 1},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert new_gs.players[0].mana_pool.C == 0
        assert new_gs.players[0].mana_pool.W == 0
        assert new_gs.players[0].mana_pool.U == 0

    def test_exact_mana(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert new_gs.players[0].mana_pool.C == 0


class TestSideboardWithMultipleCards:
    """Activation works correctly when sideboard has multiple cards."""

    def test_removes_only_companion(self):
        companion = _companion_card()
        other = Card(id="other", name="Other Card")
        gs = _make_gs(
            alice_sideboard=[other, companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert card is not None
        assert len(new_gs.players[0].sideboard) == 1
        assert other in new_gs.players[0].sideboard
        assert companion not in new_gs.players[0].sideboard

    def test_hand_grows_by_one(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert len(new_gs.players[0].hand) == 6


class TestGameIdPreserved:
    """New GameState preserves game_id and other metadata."""

    def test_game_id_preserved(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        new_gs, card = activate_companion(gs, "Alice")

        assert new_gs.game_id == gs.game_id
        assert new_gs.seed == gs.seed
        assert new_gs.turn == gs.turn
