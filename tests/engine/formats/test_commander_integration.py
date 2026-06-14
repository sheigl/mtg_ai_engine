"""CMD-01 Integration Tests — QA verification of zone replacement and combat damage.

These tests verify the complete flow of commander zone replacement (CR 903.9) 
and commander damage tracking (CR 903.10a), including edge cases not covered
by the unit tests.
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import move_permanent_to_zone, move_card_to_zone
from mtg_engine.engine.formats.commander import (
    check_commander_damage_loss,
    get_commander_tax,
    record_commander_cast,
    _is_commander,
    move_card_to_command_zone as cmd_move_to_command_zone,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_player(name: str, **kwargs) -> PlayerState:
    return PlayerState(
        name=name, life=20, mana_pool=ManaPool(),
        commander_names=kwargs.get("commander_names", []),
        commander_cast_counts=kwargs.get("commander_cast_counts", {}),
        commander_damage=kwargs.get("commander_damage", {}),
    )


def _make_game(human_player: str | None = None, **p1_kwargs) -> GameState:
    p1 = _make_player("p1", **p1_kwargs)
    p2 = _make_player("p2")
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2], format="commander",
        human_player_name=human_player,
    )


def _simulate_commander_zone_stay(gs: GameState) -> GameState:
    """Simulate the API handler for commander_zone_stay (game.py line 1813-1824).

    The card has already been removed from its source zone by the initial
    move_permanent_to_zone / move_card_to_zone call that queued this pending choice.
    We just need to place it in the intended destination directly.
    """
    cmd = gs.pending_commander_zone_choice
    if not cmd:
        return gs
    player_name = cmd.get("player", gs.priority_holder)
    card = cmd.get("card")
    intended = cmd.get("intended_destination", "graveyard")
    if card:
        player_obj = next((p for p in gs.players if p.name == player_name), None)
        if player_obj:
            dest_list = getattr(player_obj, intended, None)
            if dest_list is not None:
                dest_list.append(card)
    gs.pending_commander_zone_choice = None
    return gs


def _simulate_commander_zone_replace(gs: GameState) -> GameState:
    """Simulate the API handler for commander_zone_replace (game.py line 1801-1811)."""
    cmd = gs.pending_commander_zone_choice
    if not cmd:
        return gs
    player_name = cmd.get("player", gs.priority_holder)
    card = cmd.get("card")
    if card:
        gs = cmd_move_to_command_zone(gs, card, player_name)
    gs.pending_commander_zone_choice = None
    return gs


# ── Tests: Zone Replacement — AI Path (should work correctly) ────────────────

class TestZoneReplacementAIPath:
    """AI auto-redirects commander to command zone."""

    def test_ai_battlefield_to_graveyard(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])  # No human_player_name
        card = Card(name="Niv-Mizzet")
        perm = Permanent(id="perm-1", card=card, controller="p1")
        gs.battlefield.append(perm)

        result_gs = move_permanent_to_zone(gs, perm, "graveyard")
        p1 = next(p for p in result_gs.players if p.name == "p1")

        assert result_gs.pending_commander_zone_choice is None
        assert len(result_gs.battlefield) == 0
        assert len(p1.command_zone) == 1
        assert len(p1.graveyard) == 0

    def test_ai_battlefield_to_exile(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        perm = Permanent(id="perm-1", card=card, controller="p1")
        gs.battlefield.append(perm)

        result_gs = move_permanent_to_zone(gs, perm, "exile")
        p1 = next(p for p in result_gs.players if p.name == "p1")

        assert len(p1.command_zone) == 1
        assert len(p1.exile) == 0

    def test_ai_hand_to_exile(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        next(p for p in gs.players if p.name == "p1").hand.append(card)

        result_gs = move_card_to_zone(gs, card, "hand", "exile", "p1")
        p1 = next(p for p in result_gs.players if p.name == "p1")

        assert len(p1.command_zone) == 1
        assert len(p1.hand) == 0
        assert len(p1.exile) == 0


# ── Tests: Zone Replacement — Human Path (BUG: stay loses card) ──────────────

class TestZoneReplacementHumanPath:
    """Human player gets pending choice; replace works, stay has bug."""

    def test_human_battlefield_queues_choice(self):
        gs = _make_game(human_player="p1", commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        perm = Permanent(id="perm-1", card=card, controller="p1")
        gs.battlefield.append(perm)

        result_gs = move_permanent_to_zone(gs, perm, "graveyard")

        assert result_gs.pending_commander_zone_choice is not None
        assert result_gs.pending_commander_zone_choice["player"] == "p1"
        assert result_gs.pending_commander_zone_choice["intended_destination"] == "graveyard"
        assert len(result_gs.battlefield) == 0

    def test_human_replace_to_command_zone_works(self):
        gs = _make_game(human_player="p1", commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        perm = Permanent(id="perm-1", card=card, controller="p1")
        gs.battlefield.append(perm)

        result_gs = move_permanent_to_zone(gs, perm, "graveyard")
        final_gs = _simulate_commander_zone_replace(result_gs)
        p1 = next(p for p in final_gs.players if p.name == "p1")

        assert final_gs.pending_commander_zone_choice is None
        assert len(p1.command_zone) == 1
        assert len(p1.graveyard) == 0

    # ── BUG: commander_zone_stay loses the card ──────────────────────────────

    def test_human_battlefield_stay_loses_card(self):
        """BUG: When human chooses 'stay', card disappears from all zones.

        Root cause: move_permanent_to_zone removes permanent from battlefield,
        then queues pending choice. The API handler for commander_zone_stay
        calls move_card_to_zone(gs, card, "battlefield", intended, player_name),
        but the card is no longer on the battlefield and move_card_to_zone
        doesn't handle "battlefield" as a source zone.
        """
        gs = _make_game(human_player="p1", commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        perm = Permanent(id="perm-1", card=card, controller="p1")
        gs.battlefield.append(perm)

        result_gs = move_permanent_to_zone(gs, perm, "graveyard")
        final_gs = _simulate_commander_zone_stay(result_gs)
        p1 = next(p for p in final_gs.players if p.name == "p1")

        # BUG: Card should be in graveyard but is lost
        assert len(final_gs.battlefield) == 0
        # This assertion will FAIL — card is not in graveyard!
        assert len(p1.graveyard) == 1, (
            f"BUG: commander_zone_stay lost the card. "
            f"graveyard={len(p1.graveyard)}, command_zone={len(p1.command_zone)}"
        )

    def test_human_hand_to_exile_stay_loses_card(self):
        """BUG: Same issue for non-battlefield zones."""
        gs = _make_game(human_player="p1", commander_names=["Niv-Mizzet"])
        card = Card(name="Niv-Mizzet")
        next(p for p in gs.players if p.name == "p1").hand.append(card)

        result_gs = move_card_to_zone(gs, card, "hand", "exile", "p1")
        final_gs = _simulate_commander_zone_stay(result_gs)
        p1 = next(p for p in final_gs.players if p.name == "p1")

        # BUG: Card should be in exile but is lost
        assert len(p1.exile) == 1, (
            f"BUG: commander_zone_stay lost the card from hand->exile path. "
            f"exile={len(p1.exile)}, hand={len(p1.hand)}"
        )


# ── Tests: Commander Damage Edge Cases ───────────────────────────────────────

class TestCommanderDamageEdgeCases:
    """Verify damage tracking boundaries and partner independence."""

    def test_damage_at_20_no_loss(self):
        gs = _make_game(commander_names=["Niv-Mizzet"], commander_damage={"perm-1": 20})
        assert check_commander_damage_loss(gs) is None

    def test_damage_at_21_triggers_loss(self):
        gs = _make_game(commander_names=["Niv-Mizzet"], commander_damage={"perm-1": 21})
        assert check_commander_damage_loss(gs) == "p1"

    def test_damage_above_21_triggers_loss(self):
        gs = _make_game(commander_names=["Niv-Mizzet"], commander_damage={"perm-1": 50})
        assert check_commander_damage_loss(gs) == "p1"

    def test_partner_independent_damage_tracking(self):
        """Each partner tracks damage independently."""
        gs = _make_game(
            commander_names=["Gideon", "Ob"],
            commander_damage={"perm-gideon": 20, "perm-ob": 21},
        )
        assert check_commander_damage_loss(gs) == "p1"

    def test_both_partners_below_21_no_loss(self):
        gs = _make_game(
            commander_names=["Gideon", "Ob"],
            commander_damage={"perm-gideon": 20, "perm-ob": 20},
        )
        assert check_commander_damage_loss(gs) is None

    def test_non_commander_format_ignores_damage(self):
        p1 = _make_player("p1", commander_damage={"perm-1": 50})
        p2 = _make_player("p2")
        gs = GameState(
            game_id="test", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="standard",
        )
        assert check_commander_damage_loss(gs) is None


# ── Tests: Tax Edge Cases ────────────────────────────────────────────────────

class TestTaxEdgeCases:
    """Verify tax calculation at boundaries."""

    def test_zero_tax_first_cast(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])
        assert get_commander_tax(gs, "p1", "Niv-Mizzet") == 0

    def test_tax_progression_2_4_6(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])
        for i in range(1, 5):
            gs = record_commander_cast(gs, "p1", "Niv-Mizzet")
            expected = i * 2
            assert get_commander_tax(gs, "p1", "Niv-Mizzet") == expected

    def test_partner_independent_tax(self):
        gs = _make_game(commander_names=["Gideon", "Ob"])
        gs = record_commander_cast(gs, "p1", "Gideon")
        gs = record_commander_cast(gs, "p1", "Gideon")
        assert get_commander_tax(gs, "p1", "Gideon") == 4
        assert get_commander_tax(gs, "p1", "Ob") == 0

    def test_pure_transform_original_unchanged(self):
        gs = _make_game(commander_names=["Niv-Mizzet"])
        original_count = next(p for p in gs.players if p.name == "p1").commander_cast_counts.get(
            "Niv-Mizzet", 0
        )
        gs2 = record_commander_cast(gs, "p1", "Niv-Mizzet")
        assert next(p for p in gs.players if p.name == "p1").commander_cast_counts.get(
            "Niv-Mizzet", 0
        ) == original_count


# ── Tests: Identity Helpers ──────────────────────────────────────────────────

class TestIdentityHelpers:
    """Verify _is_commander and partner support."""

    def test_single_commander(self):
        p = _make_player("p1", commander_names=["Niv-Mizzet"])
        assert _is_commander("Niv-Mizzet", p) is True
        assert _is_commander("Other Card", p) is False

    def test_partner_both_recognized(self):
        p = _make_player("p1", commander_names=["Gideon", "Ob"])
        assert _is_commander("Gideon", p) is True
        assert _is_commander("Ob", p) is True
        assert _is_commander("Random", p) is False

    def test_empty_no_false_positives(self):
        p = _make_player("p1")
        assert _is_commander("Anything", p) is False
