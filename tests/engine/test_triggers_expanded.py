"""
TRG-20: Integration tests for all 12 expanded trigger categories.
Tests the B1 trigger check functions added in Sprint 3.
"""
import pytest
import uuid

from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool
from mtg_engine.engine.triggers import (
    check_sacrifice_triggers,
    check_life_gain_lost_triggers,
    check_fight_triggers,
    check_proliferated_triggers,
    check_transformed_triggers,
    check_tutor_triggers,
    check_becomes_target_triggers,
    check_attach_triggers,
    check_day_night_change_triggers,
    check_completed_dungeon_triggers,
    check_mana_spent_triggers,
    check_mana_production_triggers,
)


def _make_gs() -> GameState:
    """Create a minimal 2-player game."""
    return GameState(
        game_id="t-triggers",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[
            PlayerState(name="p1", life=20, mana_pool=ManaPool()),
            PlayerState(name="p2", life=20, mana_pool=ManaPool()),
        ],
    )


def _card(name: str, oracle_text: str = "", type_line: str = "Creature — Human") -> Card:
    return Card(id=f"card-{uuid.uuid4().hex[:8]}", name=name, type_line=type_line, oracle_text=oracle_text)


def _perm(gs: GameState, card: Card, controller: str) -> tuple[GameState, Permanent]:
    """Add a card as a permanent to the battlefield."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    return put_permanent_onto_battlefield(gs, card, controller, from_zone="hand")


# ─── Test Classes ───────────────────────────────────────────────────────────────


class TestSacrificeTriggers:
    """Test check_sacrifice_triggers()."""

    def _sac_perm(self, controller: str = "p1") -> Permanent:
        """A sacrificed (off-battlefield) creature permanent."""
        return Permanent(
            id=f"perm-{uuid.uuid4().hex[:8]}",
            card=_card("Sacrificed Beast", oracle_text=""),
            controller=controller,
        )

    def test_triggers_on_sacrifice(self):
        gs = _make_gs()
        card = _card(
            "Zulaport Cutthroat",
            oracle_text="Whenever a creature you control is sacrificed, each opponent loses 1 life and you gain 1 life.",
        )
        gs, perm = _perm(gs, card, "p1")
        # A creature controlled by the watcher (p1) is sacrificed (off-battlefield)
        sac = self._sac_perm(controller="p1")
        before = len(gs.pending_triggers)
        gs = check_sacrifice_triggers(gs, [sac], "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "sacrifice"
        assert trig.source_permanent_id == perm.id
        assert trig.controller == "p1"

    def test_triggers_on_any_sacrifice(self):
        gs = _make_gs()
        card = _card(
            "Blood Artist",
            oracle_text="Whenever a player sacrifices a creature, each opponent loses 1 life and you gain 1 life.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        # Pattern 2 fires for any sacrificer (here the opponent, p2)
        gs = check_sacrifice_triggers(gs, [self._sac_perm(controller="p2")], "p2")
        assert len(gs.pending_triggers) == before + 1

    def test_no_trigger_without_match(self):
        gs = _make_gs()
        card = _card("Bear", oracle_text="2/2")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_sacrifice_triggers(gs, [self._sac_perm(controller="p1")], "p1")
        assert len(gs.pending_triggers) == before

    def test_optional_sacrifice_trigger(self):
        gs = _make_gs()
        card = _card(
            "Vengeful Regiment",
            oracle_text="Whenever a creature you control is sacrificed, you may return target creature card from your graveyard to the battlefield.",
        )
        gs, perm = _perm(gs, card, "p1")
        gs = check_sacrifice_triggers(gs, [self._sac_perm(controller="p1")], "p1")
        trig = next((t for t in gs.pending_triggers if t.source_permanent_id == perm.id), None)
        assert trig is not None
        assert trig.is_optional is True


class TestLifeGainLostTriggers:
    """Test check_life_gain_lost_triggers()."""

    def test_trigger_on_life_gain(self):
        gs = _make_gs()
        card = _card(
            "Alchemist's Vivary",
            oracle_text="Whenever you gain life, scry 2.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_life_gain_lost_triggers(gs, "p1", 3)
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "life_gain_lost"
        assert trig.source_permanent_id == perm.id

    def test_trigger_on_life_loss(self):
        gs = _make_gs()
        card = _card(
            "Spiteful PR",
            oracle_text="Whenever you lose life, each opponent loses 1 life.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_life_gain_lost_triggers(gs, "p1", -4)
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "life_gain_lost"

    def test_a_player_pattern_fires_for_any_player(self):
        """'Whenever a player loses life' fires for ANY player (not just controller)."""
        gs = _make_gs()
        card = _card("Blood Seeker", oracle_text="Whenever a player loses life, each opponent loses 1 life.")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_life_gain_lost_triggers(gs, "p2", -3)
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "life_gain_lost"

    def test_player_loses_life_trigger(self):
        gs = _make_gs()
        card = _card(
            "Kambal",
            oracle_text="Whenever a player gains life, each opponent loses 1 life.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_life_gain_lost_triggers(gs, "p2", 5)
        assert len(gs.pending_triggers) == before + 1


class TestFightTriggers:
    """Test check_fight_triggers()."""

    def test_trigger_on_self_fight(self):
        gs = _make_gs()
        card = _card(
            "Ulvenwald Tracker",
            oracle_text="Whenever this creature fights, it gets +10/+10 until end of turn.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_fight_triggers(gs, fighter_ids=[perm.id])
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "fight"
        assert trig.source_permanent_id == perm.id

    def test_fight_trigger_not_self_excluded(self):
        gs = _make_gs()
        card = _card(
            "Prey Upon",
            oracle_text="Whenever this creature fights, it deals damage equal to its power to target creature.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_fight_triggers(gs, fighter_ids=["other-perm-id"])
        assert len(gs.pending_triggers) == before

    def test_general_fight_trigger_fires_for_any(self):
        gs = _make_gs()
        card = _card(
            "Rampage",
            oracle_text="Whenever a creature you control fights, that creature gets +1/+1 until end of turn for each creature blocking it.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_fight_triggers(gs, fighter_ids=["any-other-id"])
        assert len(gs.pending_triggers) == before + 1
        assert gs.pending_triggers[-1].trigger_type == "fight"


class TestProliferatedTriggers:
    """Test check_proliferated_triggers()."""

    def test_trigger_on_proliferate(self):
        gs = _make_gs()
        card = _card(
            "Flux Channeler",
            oracle_text="Whenever you proliferate, draw a card.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_proliferated_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "proliferated"

    def test_pure_transform(self):
        """check_proliferated_triggers is the only pure-transform function in B1."""
        gs = _make_gs()
        card = _card("Flux Channeler", oracle_text="Whenever you proliferate, draw a card.")
        gs, _ = _perm(gs, card, "p1")
        old_id = id(gs)
        new_gs = check_proliferated_triggers(gs, "p1")
        assert id(new_gs) != old_id

    def test_no_proliferate_trigger_for_opponent(self):
        gs = _make_gs()
        card = _card("Teferi", oracle_text="Whenever you proliferate, each opponent exiles the top card of their library.")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_proliferated_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before


class TestTransformedTriggers:
    """Test check_transformed_triggers()."""

    def test_trigger_on_self_transform(self):
        gs = _make_gs()
        card = _card(
            "Jace, Vryn's Prodigy",
            oracle_text="Whenever this creature transforms, draw a card.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_transformed_triggers(gs, transformed_perm_ids=[perm.id])
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "transformed"
        assert trig.source_permanent_id == perm.id

    def test_transform_trigger_not_self_excluded(self):
        gs = _make_gs()
        card = _card(
            "Tovolar's Huntmaster",
            oracle_text="Whenever this creature transforms, create a 2/2 green Wolf creature token.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_transformed_triggers(gs, transformed_perm_ids=["other-id"])
        assert len(gs.pending_triggers) == before

    def test_general_transform_trigger(self):
        gs = _make_gs()
        card = _card(
            "Construct",
            oracle_text="Whenever a double-faced card you control transforms, put a +1/+1 counter on it.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_transformed_triggers(gs, transformed_perm_ids=["any-id"])
        assert len(gs.pending_triggers) == before + 1


class TestTutorTriggers:
    """Test check_tutor_triggers()."""

    def test_trigger_on_tutor(self):
        gs = _make_gs()
        card = _card(
            "Psychogenic Probe",
            oracle_text="Whenever you search your library, each opponent mills two cards.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_tutor_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "tutor"
        assert trig.source_permanent_id == perm.id

    def test_no_tutor_trigger_for_opponent(self):
        gs = _make_gs()
        card = _card("Leyline", oracle_text="Whenever you search your library, each opponent loses 1 life.")
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_tutor_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before

    def test_searched_library_trigger(self):
        gs = _make_gs()
        card = _card(
            "Thalia",
            oracle_text="Whenever a player searches their library, that player forfeits the search.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_tutor_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before + 1


class TestBecomesTargetTriggers:
    """Test check_becomes_target_triggers()."""

    def test_trigger_on_becomes_target(self):
        gs = _make_gs()
        card = _card(
            "Shiny Impetus",
            oracle_text="Whenever this creature becomes the target of a spell or ability, it gets +2/+2 until end of turn.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_becomes_target_triggers(gs, perm.id)
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "becomes_target"
        assert trig.source_permanent_id == perm.id

    def test_trigger_for_control(self):
        gs = _make_gs()
        card = _card(
            "Aura",
            oracle_text="Whenever an Aura you control becomes the target of a spell, destroy that Aura.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_becomes_target_triggers(gs, perm.id)
        assert len(gs.pending_triggers) == before + 1


class TestAttachTriggers:
    """Test check_attach_triggers()."""

    def test_trigger_on_unattach(self):
        gs = _make_gs()
        card = _card(
            "Eland",
            oracle_text="Whenever an Aura you control becomes unattached, you gain 3 life.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_attach_triggers(gs, aura_perm_id=perm.id, attach_event="unattach")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "attach"

    def test_trigger_becomes_attached(self):
        gs = _make_gs()
        card = _card(
            "Aura",
            oracle_text="Enchant creature. Whenever this becomes attached to another permanent, exile it at the beginning of the next end step.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_attach_triggers(gs, aura_perm_id=perm.id)
        assert len(gs.pending_triggers) == before + 1


class TestDayNightChangeTriggers:
    """Test check_day_night_change_triggers()."""

    def test_trigger_on_day_to_night(self):
        gs = _make_gs()
        card = _card(
            "Tovolar's Huntmaster",
            oracle_text="Whenever day becomes night, each player discards a card.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_day_night_change_triggers(gs)
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "day_night_change"

    def test_trigger_on_night_to_day(self):
        gs = _make_gs()
        card = _card(
            "Mare",
            oracle_text="Whenever night becomes day, each opponent sacrifices a creature.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_day_night_change_triggers(gs)
        assert len(gs.pending_triggers) == before + 1


class TestCompletedDungeonTriggers:
    """Test check_completed_dungeon_triggers()."""

    def test_trigger_on_dungeon_complete(self):
        gs = _make_gs()
        card = _card(
            "Hama Pashar",
            oracle_text="Whenever you complete a dungeon, create a 2/2 white Spirit creature token with flying.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_completed_dungeon_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "completed_dungeon"

    def test_no_trigger_for_opponent_dungeon(self):
        gs = _make_gs()
        card = _card(
            "Rival",
            oracle_text="Whenever you complete a dungeon, each opponent loses 2 life.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_completed_dungeon_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before


class TestManaSpentTriggers:
    """Test check_mana_spent_triggers()."""

    def test_trigger_on_mana_spent(self):
        gs = _make_gs()
        card = _card(
            "Karametra's Blessing",
            oracle_text="Whenever you spend mana, that mana produces one additional mana of the same type.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_mana_spent_triggers(gs, "p1")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "mana_spent"

    def test_no_mana_spent_trigger_for_opponent(self):
        gs = _make_gs()
        card = _card(
            "Obsidian",
            oracle_text="Whenever you spend mana, each opponent loses 1 life.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_mana_spent_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before


class TestManaProductionTriggers:
    """Test check_mana_production_triggers()."""

    def test_trigger_on_mana_production(self):
        gs = _make_gs()
        card = _card(
            "Heartbeat",
            oracle_text="Whenever you tap a land for mana, that land enters the battlefield tapped.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_mana_production_triggers(gs, perm.id, "p1", ["G"])
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "mana_production"

    def test_trigger_fires_for_any_land_tapped(self):
        gs = _make_gs()
        card = _card(
            "Keeper",
            oracle_text="Whenever a land produces mana, that land deals 1 damage to each creature player.",
        )
        gs, perm = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        gs = check_mana_production_triggers(gs, perm.id, "p1", ["U", "G"])
        assert len(gs.pending_triggers) == before + 1

    def test_trigger_for_opponent_mana(self):
        gs = _make_gs()
        card = _card(
            "Notion",
            oracle_text="Whenever a player spends mana, that player mills a card.",
        )
        gs, _ = _perm(gs, card, "p1")
        before = len(gs.pending_triggers)
        # "spends mana" is a MANA_SPENT trigger (MAJOR 5), not a production trigger
        gs = check_mana_spent_triggers(gs, "p2")
        assert len(gs.pending_triggers) == before + 1
        trig = gs.pending_triggers[-1]
        assert trig.trigger_type == "mana_spent"
