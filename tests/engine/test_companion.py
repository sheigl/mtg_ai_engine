"""
COM-01: Companion mechanic tests.
CR 702.148
"""
import pytest

from mtg_engine.engine.companion import (
    has_companion, check_companion_restriction, activate_companion,
    get_companion_from_sideboard, can_activate_companion,
)
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool


def _companion_card(name: str = "Kaito Shizuki", restriction: str = "You own fewer than 40 cards") -> Card:
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
) -> GameState:
    mana_pool = ManaPool()
    if alice_mana:
        for color, amount in alice_mana.items():
            setattr(mana_pool, color, amount)

    return GameState(
        game_id="test-companion",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(
                name="Alice",
                hand=[Card(id=f"hand-{i}", name=f"Hand{i}") for i in range(alice_hand_size)],
                library=[Card(id=f"lib-{i}", name=f"Lib{i}") for i in range(alice_library_size)],
                sideboard=alice_sideboard or [],
                mana_pool=mana_pool,
            ),
            PlayerState(name="Bob"),
        ],
    )


class TestHasCompanion:
    def test_card_with_companion_keyword(self):
        card = _companion_card()
        assert has_companion(card) is True

    def test_card_without_companion_keyword(self):
        card = Card(id="x", name="Normal Card", keywords=["flying"])
        assert has_companion(card) is False

    def test_no_keywords(self):
        card = Card(id="x", name="Normal Card")
        assert has_companion(card) is False


class TestCompanionRestriction:
    def test_fewer_than_40_satisfied(self):
        gs = _make_gs(alice_hand_size=5, alice_library_size=30)
        card = _companion_card()
        assert check_companion_restriction(gs, "Alice", card) is True

    def test_fewer_than_40_not_satisfied(self):
        gs = _make_gs(alice_hand_size=10, alice_library_size=35)
        card = _companion_card()
        assert check_companion_restriction(gs, "Alice", card) is False

    def test_no_known_restriction_always_true(self):
        card = Card(id="x", name="Card", keywords=["companion"], oracle_text="Companion")
        gs = _make_gs(alice_hand_size=100, alice_library_size=100)
        assert check_companion_restriction(gs, "Alice", card) is True


class TestActivateCompanion:
    def test_successful_activation(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        result = activate_companion(gs, "Alice")
        assert result is not None
        assert result.name == "Kaito Shizuki"
        assert companion in gs.players[0].hand
        assert companion not in gs.players[0].sideboard

    def test_once_per_game_restriction(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 6},
        )
        activate_companion(gs, "Alice")
        result = activate_companion(gs, "Alice")
        assert result is None

    def test_not_enough_mana(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 2},
        )
        result = activate_companion(gs, "Alice")
        assert result is None

    def test_no_companion_in_sideboard(self):
        gs = _make_gs(
            alice_sideboard=[],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        result = activate_companion(gs, "Alice")
        assert result is None

    def test_restriction_not_met(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=20,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        result = activate_companion(gs, "Alice")
        assert result is None

    def test_deducts_mana(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 5},
        )
        activate_companion(gs, "Alice")
        assert gs.players[0].mana_pool.C == 2

    def test_deducts_mixed_colors(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"W": 1, "U": 2},
        )
        activate_companion(gs, "Alice")
        assert gs.players[0].mana_pool.W == 0
        assert gs.players[0].mana_pool.U == 0


class TestGetCompanionFromSideboard:
    def test_finds_companion(self):
        companion = _companion_card()
        gs = _make_gs(alice_sideboard=[companion])
        result = get_companion_from_sideboard(gs, "Alice")
        assert result is not None
        assert result.name == "Kaito Shizuki"

    def test_no_companion(self):
        gs = _make_gs(alice_sideboard=[Card(id="x", name="Normal Card")])
        result = get_companion_from_sideboard(gs, "Alice")
        assert result is None


class TestCanActivateCompanion:
    def test_can_activate_when_all_conditions_met(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        assert can_activate_companion(gs, "Alice") is True

    def test_cannot_activate_after_use(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 6},
        )
        activate_companion(gs, "Alice")
        assert can_activate_companion(gs, "Alice") is False

    def test_cannot_activate_not_enough_mana(self):
        companion = _companion_card()
        gs = _make_gs(
            alice_sideboard=[companion],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 2},
        )
        assert can_activate_companion(gs, "Alice") is False

    def test_cannot_activate_no_companion(self):
        gs = _make_gs(
            alice_sideboard=[],
            alice_hand_size=5,
            alice_library_size=30,
            alice_mana={"C": 3},
        )
        assert can_activate_companion(gs, "Alice") is False
