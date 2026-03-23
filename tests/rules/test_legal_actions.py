"""
Unit tests for _compute_legal_actions in mtg_engine.api.routers.game.

Covers every action type the function can produce:
  pass, play_land, cast, activate, declare_attackers, put_trigger, cast_commander

Each section tests both inclusion (action IS offered when it should be) and
exclusion (action is NOT offered when rules forbid it).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import uuid
import pytest

from mtg_engine.models.game import (
    GameState, PlayerState, Card, Permanent, Phase, Step, ManaPool, PendingTrigger,
    StackObject,
)
from mtg_engine.api.routers.game import _compute_legal_actions


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_card(
    name: str,
    type_line: str = "Creature — Beast",
    mana_cost: str | None = None,
    oracle_text: str | None = None,
    power: str = "2",
    toughness: str = "2",
    keywords: list[str] | None = None,
) -> Card:
    return Card(
        id=str(uuid.uuid4()),
        name=name,
        type_line=type_line,
        mana_cost=mana_cost,
        oracle_text=oracle_text,
        power=power,
        toughness=toughness,
        keywords=keywords or [],
    )


def _make_permanent(card: Card, controller: str, tapped: bool = False, summoning_sick: bool = True) -> Permanent:
    return Permanent(
        id=str(uuid.uuid4()),
        card=card,
        controller=controller,
        tapped=tapped,
        summoning_sick=summoning_sick,
    )


def _make_game(
    phase: Phase = Phase.PRECOMBAT_MAIN,
    step: Step = Step.MAIN,
    active: str = "p1",
    priority: str = "p1",
    p1_hand: list[Card] | None = None,
    p2_hand: list[Card] | None = None,
    p1_pool: ManaPool | None = None,
    p2_pool: ManaPool | None = None,
    p1_lands_played: int = 0,
    game_format: str = "standard",
) -> GameState:
    p1 = PlayerState(
        name="p1",
        life=20,
        hand=p1_hand or [],
        mana_pool=p1_pool or ManaPool(),
        lands_played_this_turn=p1_lands_played,
    )
    p2 = PlayerState(
        name="p2",
        life=20,
        hand=p2_hand or [],
        mana_pool=p2_pool or ManaPool(),
    )
    return GameState(
        game_id="test",
        seed=1,
        active_player=active,
        priority_holder=priority,
        phase=phase,
        step=step,
        players=[p1, p2],
        format=game_format,
    )


def _action_types(gs: GameState) -> list[str]:
    return [a.action_type for a in _compute_legal_actions(gs)]


def _action_descriptions(gs: GameState) -> list[str]:
    return [a.description for a in _compute_legal_actions(gs)]


# ─── pass ──────────────────────────────────────────────────────────────────────

class TestPassAction:
    def test_pass_always_present_in_main(self):
        gs = _make_game()
        assert "pass" in _action_types(gs)

    def test_pass_present_in_every_phase(self):
        for phase, step in [
            (Phase.BEGINNING, Step.UNTAP),
            (Phase.BEGINNING, Step.UPKEEP),
            (Phase.BEGINNING, Step.DRAW),
            (Phase.PRECOMBAT_MAIN, Step.MAIN),
            (Phase.COMBAT, Step.DECLARE_ATTACKERS),
            (Phase.POSTCOMBAT_MAIN, Step.MAIN),
            (Phase.ENDING, Step.END),
            (Phase.ENDING, Step.CLEANUP),
        ]:
            gs = _make_game(phase=phase, step=step)
            assert "pass" in _action_types(gs), f"pass missing in {phase}/{step}"

    def test_pass_present_when_non_active_player_has_priority(self):
        gs = _make_game(active="p1", priority="p2")
        assert "pass" in _action_types(gs)


# ─── play_land ─────────────────────────────────────────────────────────────────

class TestPlayLand:
    def _forest(self) -> Card:
        return _make_card("Forest", type_line="Basic Land — Forest", mana_cost=None,
                          oracle_text="({T}: Add {G}.)")

    def test_play_land_offered_in_main_phase(self):
        forest = self._forest()
        gs = _make_game(p1_hand=[forest])
        assert "play_land" in _action_types(gs)

    def test_play_land_not_offered_in_upkeep(self):
        forest = self._forest()
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UPKEEP, p1_hand=[forest])
        assert "play_land" not in _action_types(gs)

    def test_play_land_not_offered_in_combat(self):
        forest = self._forest()
        gs = _make_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS, p1_hand=[forest])
        assert "play_land" not in _action_types(gs)

    def test_play_land_not_offered_after_land_already_played(self):
        forest = self._forest()
        gs = _make_game(p1_hand=[forest], p1_lands_played=1)
        assert "play_land" not in _action_types(gs)

    def test_play_land_not_offered_to_non_active_player(self):
        forest = self._forest()
        # p2 has priority but p1 is active
        gs = _make_game(active="p1", priority="p2", p2_hand=[forest])
        assert "play_land" not in _action_types(gs)

    def test_play_land_not_offered_with_stack_non_empty(self):
        forest = self._forest()
        gs = _make_game(p1_hand=[forest])
        bolt_card = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        stack_obj = StackObject(
            id=str(uuid.uuid4()),
            source_card=bolt_card,
            controller="p2",
        )
        gs.stack.append(stack_obj)
        assert "play_land" not in _action_types(gs)

    def test_play_land_description_includes_card_name(self):
        forest = self._forest()
        gs = _make_game(p1_hand=[forest])
        descs = _action_descriptions(gs)
        assert any("Forest" in d for d in descs)

    def test_multiple_lands_in_hand_only_one_play_per_turn(self):
        forests = [self._forest() for _ in range(3)]
        gs = _make_game(p1_hand=forests)
        actions = _compute_legal_actions(gs)
        play_land_actions = [a for a in actions if a.action_type == "play_land"]
        # All 3 forests offered (player picks which one), but each is a separate action
        assert len(play_land_actions) == 3

    def test_creature_in_hand_not_offered_as_play_land(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[bear])
        assert "play_land" not in _action_types(gs)


# ─── cast ──────────────────────────────────────────────────────────────────────

class TestCastSpell:
    def test_cast_creature_with_exact_mana(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=1, W=1)
        gs = _make_game(p1_hand=[bear], p1_pool=pool)
        assert "cast" in _action_types(gs)

    def test_cast_not_offered_without_mana(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[bear])  # empty pool
        assert "cast" not in _action_types(gs)

    def test_cast_not_offered_wrong_color(self):
        bolt = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        pool = ManaPool(G=1)  # green, not red
        gs = _make_game(p1_hand=[bolt], p1_pool=pool)
        assert "cast" not in _action_types(gs)

    def test_cast_instant_offered_during_combat(self):
        bolt = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        pool = ManaPool(R=1)
        gs = _make_game(
            phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
            p1_hand=[bolt], p1_pool=pool,
        )
        assert "cast" in _action_types(gs)

    def test_cast_sorcery_not_offered_during_combat(self):
        terror = _make_card("Fireball", type_line="Sorcery", mana_cost="{X}{R}")
        pool = ManaPool(R=3)
        gs = _make_game(
            phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
            p1_hand=[terror], p1_pool=pool,
        )
        assert "cast" not in _action_types(gs)

    def test_cast_sorcery_not_offered_to_non_active_player_in_main(self):
        sorcery = _make_card("Wrath of God", type_line="Sorcery", mana_cost="{2}{W}{W}")
        pool = ManaPool(W=4)
        # p2 has priority during p1's main phase
        gs = _make_game(active="p1", priority="p2", p2_hand=[sorcery], p2_pool=pool)
        assert "cast" not in _action_types(gs)

    def test_cast_instant_offered_to_non_active_player(self):
        counterspell = _make_card("Counterspell", type_line="Instant", mana_cost="{U}{U}")
        pool = ManaPool(U=2)
        gs = _make_game(active="p1", priority="p2", p2_hand=[counterspell], p2_pool=pool)
        assert "cast" in _action_types(gs)

    def test_cast_not_offered_with_split_second_on_stack(self):
        # A card with split second on the stack should block all casting
        split_card = _make_card("Sudden Shock", type_line="Instant",
                                mana_cost="{1}{R}", keywords=["split second"])
        stack_obj = StackObject(
            id=str(uuid.uuid4()),
            source_card=split_card,
            controller="p2",
        )
        bolt = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        pool = ManaPool(R=1)
        gs = _make_game(p1_hand=[bolt], p1_pool=pool)
        gs.stack.append(stack_obj)
        assert "cast" not in _action_types(gs)

    def test_cast_land_not_offered_as_cast(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest", mana_cost=None)
        pool = ManaPool(G=5)
        gs = _make_game(p1_hand=[forest], p1_pool=pool)
        cast_actions = [a for a in _compute_legal_actions(gs) if a.action_type == "cast"]
        assert not cast_actions

    def test_cast_action_includes_mana_options(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=2)
        gs = _make_game(p1_hand=[bear], p1_pool=pool)
        actions = _compute_legal_actions(gs)
        cast_action = next(a for a in actions if a.action_type == "cast")
        assert cast_action.mana_options
        assert cast_action.mana_options[0]["mana_cost"] == "{1}{G}"

    def test_cast_action_includes_card_id(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=2)
        gs = _make_game(p1_hand=[bear], p1_pool=pool)
        actions = _compute_legal_actions(gs)
        cast_action = next(a for a in actions if a.action_type == "cast")
        assert cast_action.card_id == bear.id

    def test_cast_enchantment_at_sorcery_speed(self):
        rancor = _make_card("Rancor", type_line="Enchantment — Aura", mana_cost="{G}")
        pool = ManaPool(G=1)
        gs = _make_game(p1_hand=[rancor], p1_pool=pool)
        assert "cast" in _action_types(gs)

    def test_cast_enchantment_not_offered_outside_main(self):
        rancor = _make_card("Rancor", type_line="Enchantment — Aura", mana_cost="{G}")
        pool = ManaPool(G=1)
        gs = _make_game(
            phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
            p1_hand=[rancor], p1_pool=pool,
        )
        assert "cast" not in _action_types(gs)

    def test_cast_artifact_at_sorcery_speed(self):
        sol_ring = _make_card("Sol Ring", type_line="Artifact", mana_cost="{1}")
        pool = ManaPool(W=1)
        gs = _make_game(p1_hand=[sol_ring], p1_pool=pool)
        assert "cast" in _action_types(gs)

    def test_cast_flash_creature_offered_outside_main(self):
        flash_bear = _make_card("Ambush Viper", type_line="Creature — Snake",
                                mana_cost="{1}{G}", keywords=["flash"])
        pool = ManaPool(G=2)
        gs = _make_game(
            phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
            p1_hand=[flash_bear], p1_pool=pool,
        )
        assert "cast" in _action_types(gs)


# ─── activate ──────────────────────────────────────────────────────────────────

class TestActivateAbility:
    def _add_permanent(self, gs: GameState, card: Card, controller: str,
                       tapped: bool = False, summoning_sick: bool = False) -> Permanent:
        perm = _make_permanent(card, controller, tapped=tapped, summoning_sick=summoning_sick)
        gs.battlefield.append(perm)
        return perm

    def test_forest_tap_offered_when_spell_castable(self):
        forest_card = _make_card("Forest", type_line="Basic Land — Forest",
                                 oracle_text="({T}: Add {G}.)")
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[bear])
        # Need G+1 generic; after tapping forest we have G:1 — still not enough for {1}{G}
        # but enough for {G} spell
        llanowar = _make_card("Llanowar Elves", type_line="Creature — Elf",
                              mana_cost="{G}")
        gs = _make_game(p1_hand=[llanowar])
        self._add_permanent(gs, forest_card, "p1")
        assert "activate" in _action_types(gs)

    def test_forest_tap_not_offered_when_no_spell_castable(self):
        forest_card = _make_card("Forest", type_line="Basic Land — Forest",
                                 oracle_text="({T}: Add {G}.)")
        # Hand has only a red spell — green mana can't cast it
        bolt = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        gs = _make_game(p1_hand=[bolt])
        self._add_permanent(gs, forest_card, "p1")
        assert "activate" not in _action_types(gs)

    def test_plains_tap_not_offered_with_only_green_spells(self):
        plains_card = _make_card("Plains", type_line="Basic Land — Plains",
                                 oracle_text="({T}: Add {W}.)")
        llanowar = _make_card("Llanowar Elves", type_line="Creature — Elf",
                              mana_cost="{G}")
        gs = _make_game(p1_hand=[llanowar])
        self._add_permanent(gs, plains_card, "p1")
        assert "activate" not in _action_types(gs)

    def test_all_five_basics_tap_offered_for_matching_spells(self):
        basics = [
            ("Plains",   "Basic Land — Plains",   "({T}: Add {W}.)", "{W}"),
            ("Island",   "Basic Land — Island",   "({T}: Add {U}.)", "{U}"),
            ("Swamp",    "Basic Land — Swamp",    "({T}: Add {B}.)", "{B}"),
            ("Mountain", "Basic Land — Mountain", "({T}: Add {R}.)", "{R}"),
            ("Forest",   "Basic Land — Forest",   "({T}: Add {G}.)", "{G}"),
        ]
        for land_name, type_line, oracle, spell_cost in basics:
            land_card = _make_card(land_name, type_line=type_line, oracle_text=oracle)
            spell = _make_card(f"Spell_{land_name}", type_line="Instant", mana_cost=spell_cost)
            gs = _make_game(p1_hand=[spell])
            self._add_permanent(gs, land_card, "p1")
            assert "activate" in _action_types(gs), \
                f"{land_name} tap should be offered when hand has {spell_cost} spell"

    def test_tapped_land_not_offered(self):
        forest_card = _make_card("Forest", type_line="Basic Land — Forest",
                                 oracle_text="({T}: Add {G}.)")
        llanowar = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[llanowar])
        perm = self._add_permanent(gs, forest_card, "p1", tapped=True)
        assert "activate" not in _action_types(gs)

    def test_opponent_permanent_not_offered(self):
        forest_card = _make_card("Forest", type_line="Basic Land — Forest",
                                 oracle_text="({T}: Add {G}.)")
        llanowar = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[llanowar])
        self._add_permanent(gs, forest_card, "p2")  # opponent's forest
        assert "activate" not in _action_types(gs)

    def test_llanowar_elves_tap_offered(self):
        elves_card = _make_card("Llanowar Elves", type_line="Creature — Elf Druid",
                                mana_cost="{G}", oracle_text="{T}: Add {G}.")
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        # Pool already has G:1; tapping elves gives G:2 → {1}{G} becomes payable
        pool = ManaPool(G=1)
        gs = _make_game(p1_hand=[bear], p1_pool=pool)
        self._add_permanent(gs, elves_card, "p1")
        assert "activate" in _action_types(gs)

    def test_non_mana_ability_always_offered_when_payable(self):
        # A non-mana activated ability (e.g. "{2}: Draw a card") should always show
        # regardless of castable spells
        looter = _make_card("Merfolk Looter", type_line="Creature — Merfolk",
                            mana_cost="{1}{U}", oracle_text="{T}: Draw a card, then discard a card.")
        pool = ManaPool()
        gs = _make_game(p1_hand=[], p1_pool=pool)
        self._add_permanent(gs, looter, "p1", summoning_sick=False)
        assert "activate" in _action_types(gs)

    def test_activate_action_has_correct_permanent_id(self):
        forest_card = _make_card("Forest", type_line="Basic Land — Forest",
                                 oracle_text="({T}: Add {G}.)")
        spell = _make_card("Spell", type_line="Instant", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell])
        perm = self._add_permanent(gs, forest_card, "p1")
        actions = _compute_legal_actions(gs)
        act = next(a for a in actions if a.action_type == "activate")
        assert act.permanent_id == perm.id

    def test_mana_ability_with_mana_cost_not_offered_if_cant_pay(self):
        # Ability costs {1} to activate and produces {G} — shouldn't show with empty pool
        card = _make_card("Mana Source", type_line="Artifact",
                          oracle_text="{1}, {T}: Add {G}.")
        spell = _make_card("Spell", type_line="Instant", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell], p1_pool=ManaPool())
        self._add_permanent(gs, card, "p1")
        assert "activate" not in _action_types(gs)

    def test_second_land_not_offered_when_spell_already_castable(self):
        # Pool already has G:1, spell costs {G} — tapping a second Forest is useless
        forest1 = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        forest2 = _make_card("Forest2", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        spell = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell], p1_pool=ManaPool(G=1))
        self._add_permanent(gs, forest1, "p1")
        self._add_permanent(gs, forest2, "p1")
        # With G:1 already in pool the spell is castable — no land taps should be offered
        assert "activate" not in _action_types(gs)

    def test_second_land_offered_for_two_mana_spell(self):
        # Spell costs {1}{G} — need 2 mana total; pool has G:1 so second tap is needed
        forest1 = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        forest2 = _make_card("Forest2", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        spell = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[spell], p1_pool=ManaPool(G=1))
        self._add_permanent(gs, forest1, "p1")
        self._add_permanent(gs, forest2, "p1")
        # G:1 can't pay {1}{G} — tapping a second Forest is progress, should be offered
        assert "activate" in _action_types(gs)

    def test_no_taps_offered_when_pool_already_covers_all_spells(self):
        # Pool has G:3, hand has {G} and {2}{G} spells — both castable, no taps needed
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        spell1 = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        spell2 = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[spell1, spell2], p1_pool=ManaPool(G=3))
        self._add_permanent(gs, forest, "p1")
        assert "activate" not in _action_types(gs)

    def test_tap_offered_when_it_unlocks_additional_spell(self):
        # Pool has G:1 (can cast {G} spell), tapping adds G:2 (now also casts {2}{G})
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        spell1 = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        spell2 = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[spell1, spell2], p1_pool=ManaPool(G=1))
        self._add_permanent(gs, forest, "p1")
        # G:1 can cast spell1 but not spell2; tapping Forest → G:2 enables spell2 too
        assert "activate" in _action_types(gs)

    # BUG-10: Summoning sickness blocks {T} on creatures (CR 302.6)

    def test_creature_with_summoning_sickness_tap_not_offered(self):
        # Llanowar Elves just entered — summoning sick, {T} blocked
        elves_card = _make_card("Llanowar Elves", type_line="Creature — Elf Druid",
                                oracle_text="{T}: Add {G}.")
        spell = _make_card("Llanowar Elves2", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell])
        self._add_permanent(gs, elves_card, "p1", summoning_sick=True)
        assert "activate" not in _action_types(gs)

    def test_land_with_summoning_sick_flag_tap_still_offered(self):
        # Lands are not creatures — CR 302.6 doesn't apply to them
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        spell = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell])
        self._add_permanent(gs, forest, "p1", summoning_sick=True)
        assert "activate" in _action_types(gs)

    def test_creature_without_summoning_sickness_tap_offered(self):
        # Same Elves but summoning sickness cleared (next turn) — tap should be offered
        elves_card = _make_card("Llanowar Elves", type_line="Creature — Elf Druid",
                                oracle_text="{T}: Add {G}.")
        spell = _make_card("Grizzly Bears", type_line="Creature — Bear", mana_cost="{1}{G}")
        gs = _make_game(p1_hand=[spell], p1_pool=ManaPool(G=1))
        self._add_permanent(gs, elves_card, "p1", summoning_sick=False)
        assert "activate" in _action_types(gs)

    def test_summoning_sick_creature_excluded_from_total_available_pool(self):
        # A summoning-sick Elf is the only mana source — total pool should be 0
        # so no tap actions are offered for the land either
        elves_card = _make_card("Llanowar Elves", type_line="Creature — Elf Druid",
                                oracle_text="{T}: Add {G}.")
        spell = _make_card("Llanowar Elves2", type_line="Creature — Elf", mana_cost="{G}")
        gs = _make_game(p1_hand=[spell])
        self._add_permanent(gs, elves_card, "p1", summoning_sick=True)
        types = _action_types(gs)
        assert "activate" not in types


# ─── declare_attackers ─────────────────────────────────────────────────────────

class TestDeclareAttackers:
    def _add_creature(self, gs: GameState, name: str, controller: str,
                      tapped: bool = False, summoning_sick: bool = False,
                      keywords: list[str] | None = None) -> Permanent:
        card = _make_card(name, keywords=keywords or [])
        perm = _make_permanent(card, controller, tapped=tapped, summoning_sick=summoning_sick)
        gs.battlefield.append(perm)
        return perm

    def _declare_attackers_game(self) -> GameState:
        return _make_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)

    def test_declare_attackers_offered_with_valid_attacker(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Bear", "p1", summoning_sick=False)
        assert "declare_attackers" in _action_types(gs)

    def test_declare_attackers_not_offered_with_no_creatures(self):
        gs = self._declare_attackers_game()
        assert "declare_attackers" not in _action_types(gs)

    def test_declare_attackers_not_offered_with_only_summoning_sick(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Bear", "p1", summoning_sick=True)
        assert "declare_attackers" not in _action_types(gs)

    def test_declare_attackers_not_offered_with_tapped_creature(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Bear", "p1", tapped=True, summoning_sick=False)
        assert "declare_attackers" not in _action_types(gs)

    def test_declare_attackers_not_offered_with_defender(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Wall of Wood", "p1", summoning_sick=False,
                           keywords=["defender"])
        assert "declare_attackers" not in _action_types(gs)

    def test_haste_creature_can_attack_when_summoning_sick(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Raging Goblin", "p1", summoning_sick=True,
                           keywords=["haste"])
        assert "declare_attackers" in _action_types(gs)

    def test_declare_attackers_not_offered_outside_declare_attackers_step(self):
        gs = _make_game(phase=Phase.COMBAT, step=Step.BEGINNING_OF_COMBAT)
        self._add_creature(gs, "Bear", "p1", summoning_sick=False)
        assert "declare_attackers" not in _action_types(gs)

    def test_declare_attackers_not_offered_to_non_active_player(self):
        gs = _make_game(
            phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
            active="p1", priority="p2",
        )
        # Add a creature controlled by p2
        card = _make_card("Bear")
        perm = _make_permanent(card, "p2", summoning_sick=False)
        gs.battlefield.append(perm)
        assert "declare_attackers" not in _action_types(gs)

    def test_declare_attackers_not_offered_for_opponent_creatures(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Bear", "p2", summoning_sick=False)  # opponent's creature
        assert "declare_attackers" not in _action_types(gs)

    def test_description_includes_creature_count(self):
        gs = self._declare_attackers_game()
        self._add_creature(gs, "Bear1", "p1", summoning_sick=False)
        self._add_creature(gs, "Bear2", "p1", summoning_sick=False)
        actions = _compute_legal_actions(gs)
        atk = next(a for a in actions if a.action_type == "declare_attackers")
        assert "2" in atk.description


# ─── put_trigger ───────────────────────────────────────────────────────────────

class TestPutTrigger:
    def test_put_trigger_offered_for_own_trigger(self):
        gs = _make_game()
        trigger = PendingTrigger(
            source_permanent_id="some-perm",
            controller="p1",
            trigger_type="dies",
            effect_description="Draw a card",
            source_card_name="Elvish Visionary",
        )
        gs.pending_triggers.append(trigger)
        assert "put_trigger" in _action_types(gs)

    def test_put_trigger_not_offered_for_opponents_trigger(self):
        gs = _make_game()
        trigger = PendingTrigger(
            source_permanent_id="some-perm",
            controller="p2",  # opponent owns it
            trigger_type="dies",
            effect_description="Draw a card",
            source_card_name="Elvish Visionary",
        )
        gs.pending_triggers.append(trigger)
        assert "put_trigger" not in _action_types(gs)

    def test_multiple_triggers_each_offered(self):
        gs = _make_game()
        for i in range(3):
            gs.pending_triggers.append(PendingTrigger(
                source_permanent_id=f"perm-{i}",
                controller="p1",
                trigger_type="enters",
                effect_description=f"Effect {i}",
                source_card_name="Card",
            ))
        actions = [a for a in _compute_legal_actions(gs) if a.action_type == "put_trigger"]
        assert len(actions) == 3


# ─── cast_commander ────────────────────────────────────────────────────────────

class TestCastCommander:
    def _commander_game(self, pool: ManaPool | None = None,
                        cast_count: int = 0) -> tuple[GameState, Card]:
        commander = _make_card("Llanowar Elves", type_line="Legendary Creature — Elf",
                               mana_cost="{G}")
        p1 = PlayerState(
            name="p1", life=40,
            mana_pool=pool or ManaPool(),
            commander_name="Llanowar Elves",
            commander_cast_count=cast_count,
            command_zone=[commander],
        )
        p2 = PlayerState(name="p2", life=40)
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[p1, p2],
            format="commander",
        )
        return gs, commander

    def test_cast_commander_offered_with_sufficient_mana(self):
        gs, _ = self._commander_game(pool=ManaPool(G=1))
        assert "cast_commander" in _action_types(gs)

    def test_cast_commander_not_offered_without_mana(self):
        gs, _ = self._commander_game(pool=ManaPool())
        assert "cast_commander" not in _action_types(gs)

    def test_commander_tax_increases_cost(self):
        # Cast once before → tax is {2} → total cost is {2}{G}
        gs, _ = self._commander_game(pool=ManaPool(G=1), cast_count=1)
        # G:1 alone can't pay {2}{G} (needs 3 total)
        assert "cast_commander" not in _action_types(gs)

    def test_commander_tax_payable_with_enough_mana(self):
        gs, _ = self._commander_game(pool=ManaPool(G=3), cast_count=1)
        # {2}{G} costs 3 total — G:3 covers it
        assert "cast_commander" in _action_types(gs)

    def test_commander_tax_doubles_each_cast(self):
        # Cast 3 times → tax is {6} → total is {6}{G}
        gs, _ = self._commander_game(pool=ManaPool(G=7), cast_count=3)
        assert "cast_commander" in _action_types(gs)

        gs2, _ = self._commander_game(pool=ManaPool(G=6), cast_count=3)
        assert "cast_commander" not in _action_types(gs2)

    def test_cast_commander_not_offered_in_standard_format(self):
        commander = _make_card("Llanowar Elves", type_line="Legendary Creature — Elf",
                               mana_cost="{G}")
        p1 = PlayerState(
            name="p1", life=20,
            mana_pool=ManaPool(G=1),
            command_zone=[commander],
        )
        p2 = PlayerState(name="p2", life=20)
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[p1, p2],
            format="standard",  # NOT commander
        )
        assert "cast_commander" not in _action_types(gs)

    def test_cast_commander_not_offered_outside_main_phase(self):
        gs, _ = self._commander_game(pool=ManaPool(G=1))
        gs.phase = Phase.COMBAT
        gs.step = Step.DECLARE_ATTACKERS
        assert "cast_commander" not in _action_types(gs)

    def test_cast_commander_description_includes_cost(self):
        gs, _ = self._commander_game(pool=ManaPool(G=1))
        actions = _compute_legal_actions(gs)
        cmd = next(a for a in actions if a.action_type == "cast_commander")
        assert "{G}" in cmd.description

    def test_cast_commander_description_includes_tax_when_nonzero(self):
        gs, _ = self._commander_game(pool=ManaPool(G=3), cast_count=1)
        actions = _compute_legal_actions(gs)
        cmd = next(a for a in actions if a.action_type == "cast_commander")
        assert "tax" in cmd.description.lower() or "{2}" in cmd.description


# ─── interaction / edge cases ─────────────────────────────────────────────────

class TestEdgeCases:
    def test_only_pass_when_hand_empty_and_no_permanents(self):
        gs = _make_game()
        actions = _compute_legal_actions(gs)
        assert actions == [next(a for a in actions if a.action_type == "pass")]
        assert len(actions) == 1

    def test_no_duplicate_action_types_for_single_card(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=2)
        gs = _make_game(p1_hand=[bear], p1_pool=pool)
        cast_actions = [a for a in _compute_legal_actions(gs) if a.action_type == "cast"]
        assert len(cast_actions) == 1

    def test_two_different_castable_spells_both_offered(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        elves = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        pool = ManaPool(G=3)
        gs = _make_game(p1_hand=[bear, elves], p1_pool=pool)
        cast_actions = [a for a in _compute_legal_actions(gs) if a.action_type == "cast"]
        assert len(cast_actions) == 2

    def test_empty_hand_no_play_land_or_cast(self):
        gs = _make_game(p1_hand=[])
        types = _action_types(gs)
        assert "play_land" not in types
        assert "cast" not in types

    def test_all_action_types_have_descriptions(self):
        # Build a rich game state and ensure every action has a non-empty description
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=3)
        gs = _make_game(p1_hand=[forest, bear], p1_pool=pool)
        # Add a creature to attack with
        attacker_card = _make_card("Attacker")
        attacker = _make_permanent(attacker_card, "p1", summoning_sick=False)
        gs.phase = Phase.COMBAT
        gs.step = Step.DECLARE_ATTACKERS
        gs.battlefield.append(attacker)

        for action in _compute_legal_actions(gs):
            assert action.description, f"Action {action.action_type} has no description"


# ─── commander format — all action types ──────────────────────────────────────

class TestCommanderFormat:
    """
    Verify that all action types work correctly inside a commander game state,
    not just cast_commander. The format field should not break standard actions.
    """

    def _cmd_game(
        self,
        phase: Phase = Phase.PRECOMBAT_MAIN,
        step: Step = Step.MAIN,
        p1_hand: list[Card] | None = None,
        p1_pool: ManaPool | None = None,
        p1_lands_played: int = 0,
    ) -> GameState:
        commander = _make_card("Omnath", type_line="Legendary Creature — Elemental",
                               mana_cost="{R}{G}")
        p1 = PlayerState(
            name="p1", life=40,
            hand=p1_hand or [],
            mana_pool=p1_pool or ManaPool(),
            lands_played_this_turn=p1_lands_played,
            commander_name="Omnath",
            commander_cast_count=0,
            command_zone=[commander],
        )
        p2 = PlayerState(name="p2", life=40)
        return GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=phase, step=step,
            players=[p1, p2],
            format="commander",
        )

    def test_pass_offered_in_commander(self):
        gs = self._cmd_game()
        assert "pass" in _action_types(gs)

    def test_play_land_offered_in_commander_main(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        gs = self._cmd_game(p1_hand=[forest])
        assert "play_land" in _action_types(gs)

    def test_play_land_blocked_after_land_drop_in_commander(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        gs = self._cmd_game(p1_hand=[forest], p1_lands_played=1)
        assert "play_land" not in _action_types(gs)

    def test_cast_spell_from_hand_in_commander(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(G=2)
        gs = self._cmd_game(p1_hand=[bear], p1_pool=pool)
        assert "cast" in _action_types(gs)

    def test_cast_spell_wrong_color_blocked_in_commander(self):
        bolt = _make_card("Lightning Bolt", type_line="Instant", mana_cost="{R}")
        pool = ManaPool(G=1)
        gs = self._cmd_game(p1_hand=[bolt], p1_pool=pool)
        assert "cast" not in _action_types(gs)

    def test_mana_land_tap_offered_when_useful_in_commander(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                            oracle_text="({T}: Add {G}.)")
        elves = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = self._cmd_game(p1_hand=[elves])
        perm = _make_permanent(forest, "p1")
        gs.battlefield.append(perm)
        assert "activate" in _action_types(gs)

    def test_mana_land_tap_suppressed_when_useless_in_commander(self):
        plains = _make_card("Plains", type_line="Basic Land — Plains",
                            oracle_text="({T}: Add {W}.)")
        # Only green spell in hand — white mana useless
        elves = _make_card("Llanowar Elves", type_line="Creature — Elf", mana_cost="{G}")
        gs = self._cmd_game(p1_hand=[elves])
        perm = _make_permanent(plains, "p1")
        gs.battlefield.append(perm)
        assert "activate" not in _action_types(gs)

    def test_declare_attackers_in_commander(self):
        gs = self._cmd_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)
        attacker = _make_permanent(_make_card("Bear"), "p1", summoning_sick=False)
        gs.battlefield.append(attacker)
        assert "declare_attackers" in _action_types(gs)

    def test_declare_attackers_blocked_for_sick_creature_in_commander(self):
        gs = self._cmd_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)
        attacker = _make_permanent(_make_card("Bear"), "p1", summoning_sick=True)
        gs.battlefield.append(attacker)
        assert "declare_attackers" not in _action_types(gs)

    def test_cast_commander_and_spell_both_offered_when_affordable(self):
        # Commander costs {R}{G} — pool has R:1, G:2
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        pool = ManaPool(R=1, G=2)
        gs = self._cmd_game(p1_hand=[bear], p1_pool=pool)
        types = _action_types(gs)
        assert "cast" in types
        assert "cast_commander" in types

    def test_trigger_offered_in_commander(self):
        gs = self._cmd_game()
        gs.pending_triggers.append(PendingTrigger(
            source_permanent_id="x",
            controller="p1",
            trigger_type="enters",
            effect_description="Gain 3 life",
            source_card_name="Omnath",
        ))
        assert "put_trigger" in _action_types(gs)

    def test_no_cast_commander_when_command_zone_empty(self):
        # Edge case: command zone emptied (e.g. exiled permanently)
        gs = self._cmd_game(p1_pool=ManaPool(R=1, G=1))
        gs.players[0].command_zone = []
        assert "cast_commander" not in _action_types(gs)


# ─── BUG-08: Untap step must not grant real actions ───────────────────────────

class TestUntapStep:
    """BUG-08: No priority is granted during the untap step (CR 502.4).
    _compute_legal_actions must return only [pass] when step == UNTAP."""

    def test_only_pass_during_untap(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UNTAP, active="p1", priority="p1")
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        types = _action_types(gs)
        assert types == ["pass"], f"Expected only ['pass'], got {types}"

    def test_no_activate_during_untap(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UNTAP)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        assert "activate" not in _action_types(gs)

    def test_no_play_land_during_untap(self):
        land = _make_card("Forest", type_line="Basic Land — Forest")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UNTAP)
        gs.players[0].hand.append(land)
        assert "play_land" not in _action_types(gs)

    def test_no_cast_during_untap(self):
        bear = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UNTAP)
        gs.players[0].hand.append(bear)
        gs.players[0].mana_pool = ManaPool(G=2)
        assert "cast" not in _action_types(gs)


# ─── BUG-09: Mana-tap timing awareness ───────────────────────────────────────

class TestManaTapTiming:
    """BUG-09: Mana taps should not be offered when all spells in hand are
    sorcery-speed and the current step doesn't allow sorcery-speed casting."""

    def test_no_tap_during_upkeep_with_sorcery_hand(self):
        # During upkeep, only instants can be cast — sorcery creatures should
        # NOT trigger mana-tap offers.
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        bear = _make_card("Grizzly Bears", type_line="Creature — Bear", mana_cost="{1}{G}")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UPKEEP)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        gs.players[0].hand.append(bear)
        assert "activate" not in _action_types(gs)

    def test_no_tap_during_draw_with_sorcery_hand(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        bear = _make_card("Grizzly Bears", type_line="Creature — Bear", mana_cost="{1}{G}")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.DRAW)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        gs.players[0].hand.append(bear)
        assert "activate" not in _action_types(gs)

    def test_tap_offered_during_upkeep_with_instant_in_hand(self):
        # Giant Growth has flash/instant rules (type_line="Instant") — tap should be offered.
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        growth = _make_card("Giant Growth", type_line="Instant", mana_cost="{G}")
        gs = _make_game(phase=Phase.BEGINNING, step=Step.UPKEEP)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        gs.players[0].hand.append(growth)
        assert "activate" in _action_types(gs)

    def test_tap_offered_during_main_with_sorcery_hand(self):
        # During main phase, sorcery-speed spells ARE castable — tap should be offered.
        # Use a {G} spell so one Forest can pay the full cost.
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        elf = _make_card("Llanowar Elves", type_line="Creature — Elf Druid", mana_cost="{G}")
        gs = _make_game(phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        gs.players[0].hand.append(elf)
        assert "activate" in _action_types(gs)

    def test_no_tap_during_combat_with_sorcery_hand(self):
        forest = _make_card("Forest", type_line="Basic Land — Forest",
                             oracle_text="({T}: Add {G}.)")
        bear = _make_card("Grizzly Bears", type_line="Creature — Bear", mana_cost="{1}{G}")
        gs = _make_game(phase=Phase.COMBAT, step=Step.BEGINNING_OF_COMBAT)
        gs.battlefield.append(_make_permanent(forest, "p1", tapped=False, summoning_sick=False))
        gs.players[0].hand.append(bear)
        assert "activate" not in _action_types(gs)


# ─── US6: Attack/block constraint enforcement ─────────────────────────────────

def test_propaganda_removes_attackers_when_no_mana():
    """Propaganda-style effect: creatures can't attack unless controller pays {2}. No mana → no attacker action."""
    propaganda = _make_card(
        "Propaganda", type_line="Enchantment",
        oracle_text="Creatures can't attack unless their controller pays {2}.",
    )
    bear = _make_card("Bear", type_line="Creature — Bear", mana_cost="{1}{G}")
    gs = _make_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)
    gs.battlefield.append(_make_permanent(propaganda, "p2", tapped=False, summoning_sick=False))
    gs.battlefield.append(_make_permanent(bear, "p1", tapped=False, summoning_sick=False))
    gs.players[0].mana_pool = ManaPool()  # no mana
    # No declare_attackers action should appear
    assert "declare_attackers" not in _action_types(gs)


def test_propaganda_allows_attack_when_mana_available():
    """Propaganda-style: with {2} available, attacker action IS offered."""
    propaganda = _make_card(
        "Propaganda", type_line="Enchantment",
        oracle_text="Creatures can't attack unless their controller pays {2}.",
    )
    bear = _make_card("Bear", type_line="Creature — Bear", mana_cost="{1}{G}")
    gs = _make_game(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)
    gs.battlefield.append(_make_permanent(propaganda, "p2", tapped=False, summoning_sick=False))
    gs.battlefield.append(_make_permanent(bear, "p1", tapped=False, summoning_sick=False))
    gs.players[0].mana_pool = ManaPool(G=2)  # 2 mana available
    assert "declare_attackers" in _action_types(gs)


def test_cant_block_creature_excluded_from_blockers():
    """'can't block' oracle text on a creature removes it from legal blocker targets."""
    cant_block_card = _make_card(
        "Fog Elemental", type_line="Creature — Elemental",
        oracle_text="Flying. When Fog Elemental attacks, sacrifice it at end of combat. Fog Elemental can't block.",
    )
    from mtg_engine.models.game import CombatState, AttackerInfo
    gs = _make_game(phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS)
    gs.priority_holder = "p2"
    gs.active_player = "p1"
    cant_block_perm = _make_permanent(cant_block_card, "p2", tapped=False, summoning_sick=False)
    gs.battlefield.append(cant_block_perm)
    # Set up an attacker for p1
    attacker_card = _make_card("Attacker", type_line="Creature — Beast")
    attacker_perm = _make_permanent(attacker_card, "p1", tapped=True, summoning_sick=False)
    gs.battlefield.append(attacker_perm)
    gs.combat = CombatState(attackers=[
        AttackerInfo(permanent_id=attacker_perm.id, defending_id="p2")
    ])

    # Re-derive constraints by calling compute_legal_actions
    from mtg_engine.engine.constraints import derive_combat_constraints
    atk_constraints, blk_constraints = derive_combat_constraints(gs)
    gs.block_constraints = blk_constraints

    actions = _compute_legal_actions(gs)
    blocker_actions = [a for a in actions if a.action_type == "declare_blockers"]
    assert blocker_actions, "Should have a declare_blockers action"
    # The cant-block creature should NOT appear in valid_targets
    if blocker_actions[0].valid_targets:
        assert cant_block_perm.id not in blocker_actions[0].valid_targets
