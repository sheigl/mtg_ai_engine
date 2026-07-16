"""
B1: Missing Trigger Categories (Sprint 3)
Tests for newly added trigger check functions in triggers.py.
"""
import pytest
from mtg_engine.models.game import GameState, Permanent, Card, Phase, Step
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
)


def _make_gs(
    battlefield: list[Permanent] | None = None,
    active_player: str = "Alice",
):
    from mtg_engine.models.game import PlayerState

    return GameState(
        game_id="test-triggers",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[
            PlayerState(name="Alice", life_total=20),
            PlayerState(name="Bob", life_total=20),
        ],
        battlefield=battlefield or [],
    )


def _perm(card_name: str, oracle_text: str, controller: str = "Alice") -> Permanent:
    import uuid
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name=card_name, type_line="Creature — Human", oracle_text=oracle_text),
        controller=controller,
    )


# ─── Sacrifice Triggers ──────────────────────────────────────────────

class TestSacrificeTriggers:
    def test_sacrifice_creature_trigger(self):
        gs = _make_gs()
        perm = _perm("Zulaport Cutthroat", "Whenever a creature you control is sacrificed, that creature's controller loses 1 life and you gain 1 life.")
        gs.battlefield.append(perm)
        gs = check_sacrifice_triggers(gs, [perm.id], "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "sacrifice"]) >= 1

    def test_sacrifice_you_trigger(self):
        gs = _make_gs()
        perm = _perm("Cabal Covenant", "Whenever you sacrifice a creature, put a +1/+1 counter on this creature.")
        gs.battlefield.append(perm)
        gs = check_sacrifice_triggers(gs, [perm.id], "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "sacrifice"]) >= 1

    def test_no_match_non_matching_oracle(self):
        gs = _make_gs()
        perm = _perm("Basic Island", "{T}: Add {U}.")
        gs.battlefield.append(perm)
        gs = check_sacrifice_triggers(gs, [perm.id], "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "sacrifice"]) == 0


# ─── Life Gain/Lost Triggers ────────────────────────────────────────

class TestLifeGainLostTriggers:
    def test_life_gained_trigger(self):
        gs = _make_gs()
        perm = _perm("Karametra's Blessing", "Whenever you gain life, put a +1/+1 counter on this creature.")
        gs.battlefield.append(perm)
        gs = check_life_gain_lost_triggers(gs, "Alice", 3)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "life_gain_lost"]) >= 1

    def test_life_lost_trigger(self):
        gs = _make_gs()
        perm = _perm("Geth's Grimoire", "Whenever you lose life, draw a card.")
        gs.battlefield.append(perm)
        gs = check_life_gain_lost_triggers(gs, "Alice", -2)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "life_gain_lost"]) >= 1

    def test_player_gains_life_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a player gains life, you gain 1 life.")
        gs.battlefield.append(perm)
        gs = check_life_gain_lost_triggers(gs, "Bob", 5)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "life_gain_lost"]) >= 1


# ─── Fight Triggers ────────────────────────────────────────────────

class TestFightTriggers:
    def test_this_fights_trigger(self):
        gs = _make_gs()
        perm = _perm("Ulvenwald Tracker", "{T}: This creature fights target creature.")
        perm2 = _perm("Sword of the Paruns", "Whenever this creature fights, put a +1/+1 counter on it.")
        gs.battlefield.extend([perm, perm2])
        gs = check_fight_triggers(gs, [perm.id, perm2.id])
        assert len([t for t in gs.pending_triggers if t.trigger_type == "fight"]) >= 1

    def test_creature_you_control_fights(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a creature you control fights, draw a card.")
        fighter = _perm("Warhorse", "")
        gs.battlefield.extend([perm, fighter])
        gs = check_fight_triggers(gs, [fighter.id])
        assert len([t for t in gs.pending_triggers if t.trigger_type == "fight"]) >= 1

    def test_non_participant_no_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever this creature fights, draw a card.")
        fighter = _perm("Warhorse", "")
        gs.battlefield.extend([perm, fighter])
        gs = check_fight_triggers(gs, [fighter.id])
        assert len([t for t in gs.pending_triggers if t.trigger_type == "fight" and t.source_permanent_id == perm.id]) == 0


# ─── Proliferated Triggers ────────────────────────────────────────

class TestProliferatedTriggers:
    def test_you_proliferate_trigger(self):
        gs = _make_gs()
        perm = _perm("Flux Channeler", "Whenever you proliferate, draw a card.")
        gs.battlefield.append(perm)
        gs = check_proliferated_triggers(gs, "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "proliferated"]) >= 1

    def test_player_proliferates_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a player proliferates, that player draws a card.")
        gs.battlefield.append(perm)
        gs = check_proliferated_triggers(gs, "Bob")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "proliferated"]) >= 1


# ─── Transformed Triggers ────────────────────────────────────────

class TestTransformedTriggers:
    def test_this_transforms_trigger(self):
        gs = _make_gs()
        perm = _perm("Jace, Vryn's Prodigy", "Whenever this transforms, draw a card.")
        gs.battlefield.append(perm)
        gs = check_transformed_triggers(gs, [perm.id])
        assert len([t for t in gs.pending_triggers if t.trigger_type == "transformed"]) >= 1

    def test_dfc_transforms_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a double-faced card you control transforms, draw a card.")
        dfc = _perm("Tovolar's Huntmaster", "")
        gs.battlefield.extend([perm, dfc])
        gs = check_transformed_triggers(gs, [dfc.id])
        assert len([t for t in gs.pending_triggers if t.trigger_type == "transformed"]) >= 1


# ─── Tutor Triggers ──────────────────────────────────────────────

class TestTutorTriggers:
    def test_search_library_trigger(self):
        gs = _make_gs()
        perm = _perm("Psychogenic Probe", "Whenever you search your library, draw a card.")
        gs.battlefield.append(perm)
        gs = check_tutor_triggers(gs, "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "tutor"]) >= 1

    def test_player_searches_library_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a player searches their library, you gain 1 life.")
        gs.battlefield.append(perm)
        gs = check_tutor_triggers(gs, "Bob")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "tutor"]) >= 1


# ─── Becomes Target Triggers ──────────────────────────────────────

class TestBecomesTargetTriggers:
    def test_becomes_target_spell_or_ability(self):
        gs = _make_gs()
        perm = _perm("Shiny Impetus", "Whenever this creature becomes the target of a spell or ability, put a +1/+1 counter on it.")
        gs.battlefield.append(perm)
        gs = check_becomes_target_triggers(gs, perm.id)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "becomes_target"]) >= 1

    def test_creature_you_control_becomes_target(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a creature you control becomes the target of a spell, draw a card.")
        gs.battlefield.append(perm)
        gs = check_becomes_target_triggers(gs, "some-target-id")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "becomes_target"]) >= 1


# ─── Attach Triggers ──────────────────────────────────────────────

class TestAttachTriggers:
    def test_attached_to_another_permanent(self):
        gs = _make_gs()
        perm = _perm("Some Aura", "Whenever this becomes attached to another permanent, draw a card.")
        gs.battlefield.append(perm)
        gs = check_attach_triggers(gs, perm.id)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "attach"]) >= 1

    def test_aura_unattached(self):
        gs = _make_gs()
        perm = _perm("Sun Titan", "Whenever an aura you control becomes unattached, return target exile card to battlefield.")
        gs.battlefield.append(perm)
        gs = check_attach_triggers(gs, "some-aura-id")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "attach"]) >= 1


# ─── Day/Night Change Triggers ──────────────────────────────────────

class TestDayNightChangeTriggers:
    def test_day_becomes_night(self):
        gs = _make_gs()
        perm = _perm("Tovolar's Huntmaster", "Whenever day becomes night, transform this creature.")
        gs.battlefield.append(perm)
        gs = check_day_night_change_triggers(gs)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "day_night_change"]) >= 1

    def test_night_becomes_day(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever night becomes day, draw a card.")
        gs.battlefield.append(perm)
        gs = check_day_night_change_triggers(gs)
        assert len([t for t in gs.pending_triggers if t.trigger_type == "day_night_change"]) >= 1


# ─── Completed Dungeon Triggers ──────────────────────────────────────

class TestCompletedDungeonTriggers:
    def test_complete_dungeon_trigger(self):
        gs = _make_gs()
        perm = _perm("Hama Pashar, the Teetering", "Whenever you complete a dungeon, draw two cards.")
        gs.battlefield.append(perm)
        gs = check_completed_dungeon_triggers(gs, "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "completed_dungeon"]) >= 1

    def test_player_completes_dungeon(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a player completes a dungeon, that player draws a card.")
        gs.battlefield.append(perm)
        gs = check_completed_dungeon_triggers(gs, "Bob")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "completed_dungeon"]) >= 1


# ─── Mana Spent Triggers ──────────────────────────────────────

class TestManaSpentTriggers:
    def test_spend_mana_trigger(self):
        gs = _make_gs()
        perm = _perm("Karametra's Blessing", "Whenever you spend mana, put a +1/+1 counter on this creature.")
        gs.battlefield.append(perm)
        gs = check_mana_spent_triggers(gs, "Alice")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "mana_spent"]) >= 1

    def test_player_spends_mana_trigger(self):
        gs = _make_gs()
        perm = _perm("Some Card", "Whenever a player spends mana, you gain 1 life.")
        gs.battlefield.append(perm)
        gs = check_mana_spent_triggers(gs, "Bob")
        assert len([t for t in gs.pending_triggers if t.trigger_type == "mana_spent"]) >= 1
