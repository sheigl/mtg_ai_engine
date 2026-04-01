"""
Tests for Feature 019: Rules Engine Gap Closure.
Covers: Proliferate, Sagas, World Enchantment SBA, Unearth SBA,
Planeswalker Rules, Partner Commanders, Multiplayer Each Opponent.
"""
import pytest
from mtg_engine.models.game import (
    Card, GameState, Permanent, PlayerState, Phase, Step,
    ManaPool, StackObject, Emblem,
)
from mtg_engine.models.actions import CastRequest
from mtg_engine.engine.zones import (
    put_permanent_onto_battlefield,
    move_permanent_to_zone,
    get_player,
)
from mtg_engine.engine.sba import check_and_apply_sbas, _check_once
from mtg_engine.engine.stack import _trigger_proliferate, get_opponents
from mtg_engine.engine.triggers import check_phase_triggers
from mtg_engine.engine.replacement import apply_damage_event


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_game(format: str = "standard") -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
        format=format,
    )


def _make_card(
    name: str,
    type_line: str = "Creature",
    mana_cost: str = "{1}",
    oracle_text: str = "",
    power: str = "1",
    toughness: str = "1",
    keywords: list[str] | None = None,
) -> Card:
    return Card(
        name=name,
        type_line=type_line,
        mana_cost=mana_cost,
        oracle_text=oracle_text,
        power=power,
        toughness=toughness,
        keywords=keywords or [],
    )


def _add_perm(
    gs: GameState,
    name: str,
    controller: str,
    type_line: str = "Creature",
    oracle_text: str = "",
    keywords: list[str] | None = None,
    power: str = "1",
    toughness: str = "1",
    counters: dict | None = None,
) -> tuple[GameState, Permanent]:
    card = _make_card(name, type_line=type_line, oracle_text=oracle_text,
                      keywords=keywords, power=power, toughness=toughness)
    gs, perm = put_permanent_onto_battlefield(gs, card, controller)
    if counters:
        perm.counters.update(counters)
    return gs, perm


# ─── Phase 12: Proliferate (US13) ────────────────────────────────────────────

class TestProliferate:
    def test_proliferate_sets_pending_choice(self):
        gs = _make_game()
        gs, perm = _add_perm(gs, "Creature", "p1", counters={"+1/+1": 2})
        gs = _trigger_proliferate(gs, "p1")
        assert gs.pending_proliferate_choice is not None
        assert gs.pending_proliferate_choice["player"] == "p1"

    def test_proliferate_eligible_includes_counter_permanents(self):
        gs = _make_game()
        gs, perm = _add_perm(gs, "Creature", "p1", counters={"+1/+1": 1})
        gs, _ = _add_perm(gs, "NoCounts", "p2")
        gs = _trigger_proliferate(gs, "p1")
        eligible_ids = [e["id"] for e in gs.pending_proliferate_choice["eligible"]]
        assert perm.id in eligible_ids
        # Permanent with no counters should not be eligible
        no_count_perm = next(p for p in gs.battlefield if p.card.name == "NoCounts")
        assert no_count_perm.id not in eligible_ids

    def test_proliferate_eligible_includes_poisoned_player(self):
        gs = _make_game()
        p1 = get_player(gs, "p1")
        p1.poison_counters = 3
        gs = _trigger_proliferate(gs, "p1")
        eligible_ids = [e["id"] for e in gs.pending_proliferate_choice["eligible"]]
        assert "p1" in eligible_ids

    def test_get_opponents_returns_non_controller(self):
        gs = _make_game()
        opponents = get_opponents(gs, "p1")
        assert len(opponents) == 1
        assert opponents[0].name == "p2"

    def test_get_opponents_excludes_self(self):
        gs = _make_game()
        opponents = get_opponents(gs, "p2")
        assert all(o.name != "p2" for o in opponents)


# ─── Phase 13: Sagas (US14) ───────────────────────────────────────────────────

class TestSagas:
    def test_saga_etb_adds_lore_counter(self):
        gs = _make_game()
        saga_card = _make_card(
            "Urza's Saga",
            type_line="Enchantment — Saga",
            oracle_text="I — Add {C}.\nII — Search your library for a card.\nIII — Create a token.",
        )
        gs, perm = put_permanent_onto_battlefield(gs, saga_card, "p1")
        assert perm.counters.get("lore", 0) == 1

    def test_saga_etb_queues_chapter_I_trigger(self):
        gs = _make_game()
        saga_card = _make_card(
            "Test Saga",
            type_line="Enchantment — Saga",
            oracle_text="I — Draw a card.\nII — Gain 3 life.\nIII — Create a token.",
        )
        gs, _ = put_permanent_onto_battlefield(gs, saga_card, "p1")
        assert any(t.trigger_type == "saga_chapter" for t in gs.pending_triggers)

    def test_non_saga_does_not_get_lore_counter(self):
        gs = _make_game()
        card = _make_card("Grizzly Bears", type_line="Creature — Bear")
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert "lore" not in perm.counters


# ─── Phase 14: World Enchantment SBA (US15) ──────────────────────────────────

class TestWorldEnchantmentSBA:
    def test_two_worlds_keeps_newest(self):
        gs = _make_game()
        gs, w1 = _add_perm(gs, "World One", "p1", type_line="Enchantment World")
        import time
        time.sleep(0.01)
        gs, w2 = _add_perm(gs, "World Two", "p2", type_line="Enchantment World")
        # w2 has higher timestamp (newer)
        gs, events = _check_once(gs)
        world_events = [e for e in events if e.sba_type == "world_enchantment"]
        assert len(world_events) == 1
        # World One (older) should be removed
        surviving_world = next((p for p in gs.battlefield if "World" in p.card.type_line), None)
        assert surviving_world is not None
        assert surviving_world.card.name == "World Two"

    def test_single_world_no_sba(self):
        gs = _make_game()
        gs, _ = _add_perm(gs, "World One", "p1", type_line="Enchantment World")
        gs, events = _check_once(gs)
        world_events = [e for e in events if e.sba_type == "world_enchantment"]
        assert len(world_events) == 0


# ─── Phase 15: Unearth SBA (US16) ────────────────────────────────────────────

class TestUnearthSBA:
    def test_unearthed_permanent_exiled_at_end_step(self):
        gs = _make_game()
        gs.step = Step.END
        gs, perm = _add_perm(gs, "Unearthed Creature", "p1")
        perm.unearthed = True
        p1 = get_player(gs, "p1")
        gs, events = _check_once(gs)
        unearth_events = [e for e in events if e.sba_type == "unearth_exile"]
        assert len(unearth_events) == 1
        # Permanent should be exiled, not on battlefield
        assert not any(p.id == perm.id for p in gs.battlefield)
        assert any(c.name == "Unearthed Creature" for c in p1.exile)

    def test_unearthed_not_exiled_outside_end_step(self):
        gs = _make_game()
        gs.step = Step.MAIN
        gs, perm = _add_perm(gs, "Unearthed Creature", "p1")
        perm.unearthed = True
        gs, events = _check_once(gs)
        unearth_events = [e for e in events if e.sba_type == "unearth_exile"]
        assert len(unearth_events) == 0
        assert any(p.id == perm.id for p in gs.battlefield)

    def test_unearthed_redirected_to_exile_on_death(self):
        gs = _make_game()
        gs, perm = _add_perm(gs, "Unearthed Creature", "p1",
                             power="1", toughness="1")
        perm.unearthed = True
        p1 = get_player(gs, "p1")
        # Move to graveyard should redirect to exile
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        assert not any(c.name == "Unearthed Creature" for c in p1.graveyard)
        assert any(c.name == "Unearthed Creature" for c in p1.exile)

    def test_unearthed_exiled_on_bounce(self):
        """CR 702.83b: unearthed creatures are exiled even when bounced."""
        gs = _make_game()
        gs, perm = _add_perm(gs, "Unearthed Creature", "p1")
        perm.unearthed = True
        p1 = get_player(gs, "p1")
        gs = move_permanent_to_zone(gs, perm, "hand")
        # Unearthed replacement redirects to exile even when bounced
        assert not any(c.name == "Unearthed Creature" for c in p1.hand)
        assert any(c.name == "Unearthed Creature" for c in p1.exile)
        assert not any(p.id == perm.id for p in gs.battlefield)


# ─── Phase 16: Planeswalker Rules (US17) ──────────────────────────────────────

class TestPlaneswalkerRules:
    def test_loyalty_reset_at_untap(self):
        from mtg_engine.engine.turn_manager import begin_step
        gs = _make_game()
        gs, perm = _add_perm(gs, "Jace", "p1",
                             type_line="Legendary Planeswalker — Jace")
        perm.loyalty_activated_this_turn = True
        gs.step = Step.UNTAP
        gs = begin_step(gs)
        # loyalty_activated_this_turn should be reset
        perm_after = next(p for p in gs.battlefield if p.id == perm.id)
        assert perm_after.loyalty_activated_this_turn is False

    def test_emblem_model(self):
        gs = _make_game()
        emblem = Emblem(
            controller="p1",
            source_planeswalker="Jace, Wielder of Mysteries",
            abilities=["At the beginning of your upkeep, draw a card."],
        )
        gs.emblems.append(emblem)
        assert len(gs.emblems) == 1
        assert gs.emblems[0].controller == "p1"

    def test_emblem_phase_trigger_queued(self):
        gs = _make_game()
        gs.step = Step.UPKEEP
        emblem = Emblem(
            controller="p1",
            source_planeswalker="Test Planeswalker",
            abilities=["At the beginning of your upkeep, draw a card."],
        )
        gs.emblems.append(emblem)
        gs = check_phase_triggers(gs)
        assert any(
            t.controller == "p1" and t.trigger_type == "phase_change"
            for t in gs.pending_triggers
        )

    def test_damage_redirect_to_planeswalker(self):
        gs = _make_game()
        pw_card = _make_card("Jace", type_line="Legendary Planeswalker — Jace")
        gs, pw_perm = put_permanent_onto_battlefield(gs, pw_card, "p1")
        pw_perm.loyalty = 5
        # Apply damage redirected to planeswalker
        gs = apply_damage_event(
            gs, "source", [], "p1", 3,
            redirect_to_planeswalker_id=pw_perm.id
        )
        pw_after = next(p for p in gs.battlefield if p.id == pw_perm.id)
        assert pw_after.loyalty == 2  # 5 - 3

    def test_damage_to_player_still_works(self):
        gs = _make_game()
        p2 = get_player(gs, "p2")
        initial_life = p2.life
        gs = apply_damage_event(gs, "source", [], "p2", 3)
        p2_after = get_player(gs, "p2")
        assert p2_after.life == initial_life - 3


# ─── Phase 17: Partner Commanders (US19) ─────────────────────────────────────

class TestPartnerCommanders:
    def test_commander_cast_counts_per_card(self):
        p1 = PlayerState(name="p1", life=40, commander_cast_counts={})
        assert p1.commander_cast_counts == {}
        p1.commander_cast_counts["Tana, the Bloodsower"] = 1
        assert p1.commander_cast_counts["Tana, the Bloodsower"] == 1
        assert p1.commander_cast_counts.get("Reyhan, Last of the Abzan", 0) == 0

    def test_multiple_commanders_independent_taxes(self):
        p1 = PlayerState(
            name="p1", life=40,
            commander_cast_counts={"Commander A": 2, "Commander B": 0},
        )
        tax_a = 2 * p1.commander_cast_counts.get("Commander A", 0)
        tax_b = 2 * p1.commander_cast_counts.get("Commander B", 0)
        assert tax_a == 4
        assert tax_b == 0


# ─── Phase 18: Multiplayer Each Opponent (US20) ──────────────────────────────

class TestMultiplayerOpponents:
    def test_get_opponents_two_players(self):
        gs = _make_game()
        opps = get_opponents(gs, "p1")
        assert len(opps) == 1
        assert opps[0].name == "p2"

    def test_get_opponents_three_players(self):
        p1 = PlayerState(name="p1", life=20)
        p2 = PlayerState(name="p2", life=20)
        p3 = PlayerState(name="p3", life=20)
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[p1, p2, p3],
        )
        opps = get_opponents(gs, "p1")
        assert len(opps) == 2
        opp_names = {o.name for o in opps}
        assert "p2" in opp_names
        assert "p3" in opp_names
        assert "p1" not in opp_names

    def test_opponent_target_field_in_cast_request(self):
        req = CastRequest(card_id="abc", opponent_target="p2")
        assert req.opponent_target == "p2"

    def test_opponent_target_defaults_to_none(self):
        req = CastRequest(card_id="abc")
        assert req.opponent_target is None


# ─── Persist and Undying (already tested in zones) ───────────────────────────

class TestPersistUndying:
    def test_persist_returns_creature_with_minus_counter(self):
        gs = _make_game()
        card = _make_card("Persist Creature", keywords=["persist"], toughness="2")
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        p1 = get_player(gs, "p1")
        # Move to graveyard should trigger persist
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        # Should still be on battlefield (persist returned it)
        assert any(p.card.name == "Persist Creature" for p in gs.battlefield)
        assert not any(c.name == "Persist Creature" for c in p1.graveyard)
        # Should have -1/-1 counter
        returned = next(p for p in gs.battlefield if p.card.name == "Persist Creature")
        assert returned.counters.get("-1/-1", 0) == 1

    def test_persist_does_not_trigger_with_minus_counter(self):
        gs = _make_game()
        card = _make_card("Persist Creature", keywords=["persist"])
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        perm.counters["-1/-1"] = 1  # already has -1/-1 counter
        p1 = get_player(gs, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        # Should go to graveyard (no persist trigger)
        assert any(c.name == "Persist Creature" for c in p1.graveyard)
        assert not any(p.card.name == "Persist Creature" for p in gs.battlefield)

    def test_undying_returns_creature_with_plus_counter(self):
        gs = _make_game()
        card = _make_card("Undying Creature", keywords=["undying"])
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        p1 = get_player(gs, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        # Should still be on battlefield
        assert any(p.card.name == "Undying Creature" for p in gs.battlefield)
        assert not any(c.name == "Undying Creature" for c in p1.graveyard)
        returned = next(p for p in gs.battlefield if p.card.name == "Undying Creature")
        assert returned.counters.get("+1/+1", 0) == 1

    def test_undying_does_not_trigger_with_plus_counter(self):
        gs = _make_game()
        card = _make_card("Undying Creature", keywords=["undying"])
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        perm.counters["+1/+1"] = 1  # already has +1/+1 counter
        p1 = get_player(gs, "p1")
        gs = move_permanent_to_zone(gs, perm, "graveyard")
        assert any(c.name == "Undying Creature" for c in p1.graveyard)
        assert not any(p.card.name == "Undying Creature" for p in gs.battlefield)
