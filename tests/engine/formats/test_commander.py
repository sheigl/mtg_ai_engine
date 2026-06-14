"""CMD-01: Commander format rules tests."""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
from mtg_engine.engine.formats.commander import (
    _is_commander,
    _get_commander_names,
    get_commander_tax,
    record_commander_cast,
    check_commander_damage_loss,
    add_commander_to_command_zone,
    move_card_to_command_zone,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_player(name: str, **kwargs) -> PlayerState:
    return PlayerState(
        name=name,
        life=20,
        mana_pool=ManaPool(),
        commander_names=kwargs.get("commander_names", []),
        commander_cast_counts=kwargs.get("commander_cast_counts", {}),
        commander_damage=kwargs.get("commander_damage", {}),
    )


def _make_game(
    commanders: list[str] | None = None,
    format_: str = "commander",
) -> GameState:
    p1 = _make_player("p1", commander_names=commanders or [])
    p2 = _make_player("p2")
    return GameState(
        game_id="test",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[p1, p2],
        format=format_,
    )


def _make_card(name: str = "Test Card") -> Card:
    return Card(name=name)


# ── Tests: _is_commander / _get_commander_names ───────────────────────────────

@pytest.mark.cr("903.8")
class TestIsCommander:

    def test_single_commander_match(self):
        player = _make_player("p1", commander_names=["Niv-Mizzet"])
        assert _is_commander("Niv-Mizzet", player) is True
        assert _is_commander("Some Other Card", player) is False

    def test_partner_both_are_commanders(self):
        player = _make_player(
            "p1",
            commander_names=["Gideon of the Trials", "Ob Nixilis"],
        )
        assert _is_commander("Gideon of the Trials", player) is True
        assert _is_commander("Ob Nixilis", player) is True
        assert _is_commander("Random Card", player) is False

    def test_empty_commanders(self):
        player = _make_player("p1")
        assert _get_commander_names(player) == []
        assert _is_commander("Anything", player) is False


# ── Tests: Commander Tax (CR 903.8) ───────────────────────────────────────────

@pytest.mark.cr("903.8")
class TestCommanderTax:

    def test_tax_zero_on_first_cast(self):
        gs = _make_game(commanders=["Niv-Mizzet"])
        assert get_commander_tax(gs, "p1", "Niv-Mizzet") == 0

    def test_tax_increases_after_each_cast(self):
        gs = _make_game(commanders=["Niv-Mizzet"])
        gs = record_commander_cast(gs, "p1", "Niv-Mizzet")
        assert get_commander_tax(gs, "p1", "Niv-Mizzet") == 2

        gs = record_commander_cast(gs, "p1", "Niv-Mizzet")
        assert get_commander_tax(gs, "p1", "Niv-Mizzet") == 4

    def test_partner_independent_tax(self):
        gs = _make_game(commanders=["Gideon of the Trials", "Ob Nixilis"])
        gs = record_commander_cast(gs, "p1", "Gideon of the Trials")
        assert get_commander_tax(gs, "p1", "Gideon of the Trials") == 2
        assert get_commander_tax(gs, "p1", "Ob Nixilis") == 0

    def test_record_is_pure_transform(self):
        gs = _make_game(commanders=["Niv-Mizzet"])
        p1_before = next(p for p in gs.players if p.name == "p1")
        assert p1_before.commander_cast_counts.get("Niv-Mizzet", 0) == 0

        gs2 = record_commander_cast(gs, "p1", "Niv-Mizzet")
        # Original state unchanged
        assert next(p for p in gs.players if p.name == "p1").commander_cast_counts.get(
            "Niv-Mizzet", 0
        ) == 0
        # New state updated
        assert next(p for p in gs2.players if p.name == "p1").commander_cast_counts[
            "Niv-Mizzet"
        ] == 1


# ── Tests: Commander Damage Loss (CR 903.10a) ────────────────────────────────

@pytest.mark.cr("903.10")
class TestCommanderDamageLoss:

    def test_no_loss_below_21(self):
        p1 = _make_player(
            "p1", commander_damage={"perm-1": 20}
        )
        gs = GameState(
            game_id="test", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, _make_player("p2")], format="commander",
        )
        assert check_commander_damage_loss(gs) is None

    def test_loss_at_21(self):
        p1 = _make_player(
            "p1", commander_damage={"perm-1": 21}
        )
        gs = GameState(
            game_id="test", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, _make_player("p2")], format="commander",
        )
        assert check_commander_damage_loss(gs) == "p1"

    def test_partner_independent_damage(self):
        p1 = _make_player(
            "p1", commander_damage={"perm-gideon": 20, "perm-ob": 21}
        )
        gs = GameState(
            game_id="test", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, _make_player("p2")], format="commander",
        )
        assert check_commander_damage_loss(gs) == "p1"

    def test_no_check_for_non_commander_format(self):
        p1 = _make_player(
            "p1", commander_damage={"perm-1": 50}
        )
        gs = GameState(
            game_id="test", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, _make_player("p2")], format="standard",
        )
        assert check_commander_damage_loss(gs) is None


# ── Tests: Command Zone (CR 903.9) ───────────────────────────────────────────

@pytest.mark.cr("903.9")
class TestCommandZone:

    def test_add_to_command_zone(self):
        gs = _make_game(commanders=[])
        card = _make_card("Niv-Mizzet")
        gs2 = add_commander_to_command_zone(gs, "p1", card)
        p1 = next(p for p in gs2.players if p.name == "p1")
        assert len(p1.command_zone) == 1
        assert "Niv-Mizzet" in p1.commander_names

    def test_add_is_pure_transform(self):
        gs = _make_game(commanders=[])
        card = _make_card("Niv-Mizzet")
        original_len = len(next(p for p in gs.players if p.name == "p1").command_zone)
        gs2 = add_commander_to_command_zone(gs, "p1", card)
        assert len(next(p for p in gs.players if p.name == "p1").command_zone) == original_len
        assert len(next(p for p in gs2.players if p.name == "p1").command_zone) == 1

    def test_move_to_command_zone(self):
        gs = _make_game(commanders=["Niv-Mizzet"])
        card = _make_card("Niv-Mizzet")
        gs2 = move_card_to_command_zone(gs, card, "p1")
        p1 = next(p for p in gs2.players if p.name == "p1")
        assert len(p1.command_zone) == 1
