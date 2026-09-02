"""
KW-06: Toxic keyword — Integration tests.
CR 702.134: "Toxic N" means whenever this creature deals combat damage to a
player, that player gets N poison counters. CR 704.5c: a player with 10+
poison counters loses the game (checked via SBA).

Drives the REAL combat flow (declare_attackers → assign_combat_damage) and
the real non-combat damage path (stack._deal_damage) to verify:
- exactly-once firing per combat damage event (not per point of damage)
- non-combat damage does NOT trigger toxic
- pure transforms (original state unmutated; no-op paths return same object)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.ability.keywords.toxic import ToxicKeyword, apply_toxic
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, Phase, Step
from mtg_engine.models.actions import AttackDeclaration, BlockDeclaration
from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield
from mtg_engine.engine.combat import declare_attackers, declare_blockers, assign_combat_damage
from mtg_engine.engine.stack import _deal_damage
from mtg_engine.engine.sba import check_and_apply_sbas


def _library_card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


def _toxic_card(
    name: str = "Toxic Beast",
    power: int = 2,
    toughness: int = 2,
    toxic_value: int = 1,
) -> Card:
    """Create a creature card with Toxic N (like Venom Connoisseur — Toxic 1)."""
    return Card(
        name=name,
        type_line="Creature — Beast",
        power=str(power),
        toughness=str(toughness),
        oracle_text=(
            f"Toxic {toxic_value} "
            f"(Whenever this creature deals combat damage to a player, "
            f"that player gets {toxic_value} poison counters.)"
        ),
        keywords=["toxic"],
    )


def _plain_card(
    name: str = "Plain Beast",
    power: int = 3,
    toughness: int = 3,
) -> Card:
    """Create a creature card without Toxic."""
    return Card(
        name=name,
        type_line="Creature — Beast",
        power=str(power),
        toughness=str(toughness),
    )


def _make_game() -> GameState:
    return GameState(
        game_id="t-toxic",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[
            PlayerState(name="p1", life=20),
            PlayerState(name="p2", life=20),
        ],
    )


def _make_combat_game() -> GameState:
    """Create a game state ready for combat (declare attackers step)."""
    p1 = PlayerState(name="p1", life=20, library=[_library_card(f"A{i}") for i in range(30)])
    p2 = PlayerState(name="p2", life=20, library=[_library_card(f"B{i}") for i in range(30)])
    return GameState(
        game_id="t-toxic-combat",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_ATTACKERS,
        format="standard",
        players=[p1, p2],
    )


def _add_creature(gs: GameState, card: Card, controller: str):
    gs, perm = put_permanent_onto_battlefield(gs, card, controller)
    perm.summoning_sick = False
    return gs, perm


def _run_unblocked_attack(gs: GameState, attacker: Permanent, defending_id: str = "p2") -> GameState:
    """Full real combat flow: declare attackers → combat damage step → assign."""
    gs = declare_attackers(
        gs, [AttackDeclaration(attacker_id=attacker.id, defending_id=defending_id)]
    )
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    return gs


# ── Detection ────────────────────────────────────────────────────────────────

class TestDetection:
    def test_applies_true_with_keyword_or_oracle(self):
        gs = _make_game()
        perm = Permanent(card=_toxic_card(), controller="p1")
        assert ToxicKeyword().applies(gs, perm) is True
        # Oracle-only (no keywords list) is also detected
        oracle_only = _toxic_card()
        oracle_only.keywords = []
        perm2 = Permanent(card=oracle_only, controller="p1")
        assert ToxicKeyword().applies(gs, perm2) is True

    def test_applies_false_without_toxic(self):
        gs = _make_game()
        perm = Permanent(card=_plain_card(), controller="p1")
        assert ToxicKeyword().applies(gs, perm) is False


# ── Value parsing ────────────────────────────────────────────────────────────

class TestValueParsing:
    def test_get_toxic_value_parses_and_defaults(self):
        perm1 = Permanent(card=_toxic_card(toxic_value=1), controller="p1")
        perm2 = Permanent(card=_toxic_card(toxic_value=2), controller="p1")
        assert ToxicKeyword().get_toxic_value(perm1) == 1
        assert ToxicKeyword().get_toxic_value(perm2) == 2
        # No "Toxic N" in oracle text → falls back to the instance value
        plain_with_kw = _plain_card()
        plain_with_kw.keywords = ["toxic"]
        perm_default = Permanent(card=plain_with_kw, controller="p1")
        assert ToxicKeyword(value=3).get_toxic_value(perm_default) == 3

    def test_from_oracle(self):
        kw = ToxicKeyword.from_oracle("Toxic 2 (Whenever this creature deals combat "
                                      "damage to a player, that player gets 2 poison counters.)")
        assert kw is not None
        assert kw.value == 2
        assert ToxicKeyword.from_oracle("No keyword here.") is None


# ── Real combat flow ─────────────────────────────────────────────────────────

class TestCombatFlow:
    def test_combat_damage_to_player_gives_toxic_counters(self):
        """2/2 Toxic 1 attacks unblocked → damaged player gets exactly 1 counter."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(power=2, toughness=2, toxic_value=1), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 1
        # Normal life loss still applies alongside poison
        assert get_player(gs, "p2").life == 18

    def test_one_damage_gives_full_n_counters(self):
        """1/1 Toxic 2 deals only 1 damage → still gets the full 2 counters."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(power=1, toughness=1, toxic_value=2), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 2
        assert get_player(gs, "p2").life == 19

    def test_five_damage_gives_exactly_n_not_5n(self):
        """5/5 Toxic 2 deals 5 damage → exactly 2 counters (not 10)."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(power=5, toughness=5, toxic_value=2), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 2
        assert get_player(gs, "p2").life == 15

    def test_two_toxic_creatures_each_fire_once(self):
        """Two 1/1 Toxic 1 attackers → 2 counters total (one per assignment)."""
        gs = _make_combat_game()
        gs, a1 = _add_creature(gs, _toxic_card(name="Toxic A", power=1, toxic_value=1), "p1")
        gs, a2 = _add_creature(gs, _toxic_card(name="Toxic B", power=1, toxic_value=1), "p1")
        gs = declare_attackers(
            gs,
            [
                AttackDeclaration(attacker_id=a1.id, defending_id="p2"),
                AttackDeclaration(attacker_id=a2.id, defending_id="p2"),
            ],
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)
        assert get_player(gs, "p2").poison_counters == 2

    def test_non_toxic_source_gives_no_poison(self):
        """A normal creature's combat damage gives 0 poison counters."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _plain_card(power=3, toughness=3), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 0
        assert get_player(gs, "p2").life == 17

    def test_toxic_damage_to_creature_gives_no_poison(self):
        """Toxic only fires on damage dealt to a PLAYER — blocked damage gives 0."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(power=2, toughness=2, toxic_value=2), "p1")
        gs, blocker = _add_creature(gs, _plain_card(name="Bulwark", power=3, toughness=3), "p2")
        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")]
        )
        gs = declare_blockers(
            gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)]
        )
        gs = assign_combat_damage(gs)
        # Attacker dealt 2 damage to the blocker (not the player) → no poison
        assert get_player(gs, "p2").poison_counters == 0
        assert get_player(gs, "p2").life == 20


# ── Accumulation & loss ──────────────────────────────────────────────────────

class TestAccumulationAndLoss:
    def test_poison_counters_accumulate_across_turns(self):
        """Toxic 1 attacks on two consecutive turns → 2 counters total."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(power=1, toughness=1, toxic_value=1), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 1

        # Turn 2: untap and attack again
        attacker2 = next(p for p in gs.battlefield if p.id == attacker.id)
        attacker2.tapped = False
        gs.step = Step.DECLARE_ATTACKERS
        gs = _run_unblocked_attack(gs, attacker2, "p2")
        assert get_player(gs, "p2").poison_counters == 2
        assert get_player(gs, "p2").life == 18

    def test_loss_at_10_poison_counters_via_sba(self):
        """Player with 9 counters + Toxic 1 damage → 10 → SBA (CR 704.5c) marks loss."""
        gs = _make_combat_game()
        # p2 already has 9 poison counters from prior turns
        gs.players[1] = gs.players[1].model_copy(update={"poison_counters": 9})
        gs, attacker = _add_creature(gs, _toxic_card(power=1, toughness=1, toxic_value=1), "p1")
        gs = _run_unblocked_attack(gs, attacker, "p2")
        assert get_player(gs, "p2").poison_counters == 10

        # The EXISTING SBA check (engine/sba.py, CR 704.5c) handles the loss —
        # not re-implemented in toxic.py
        gs, events = check_and_apply_sbas(gs)
        assert get_player(gs, "p2").has_lost is True
        assert any(e.sba_type == "poison" for e in events)
        assert gs.is_game_over is True
        assert gs.winner == "p1"


# ── Non-combat damage ────────────────────────────────────────────────────────

class TestNonCombatDamage:
    def test_non_combat_damage_does_not_trigger_toxic(self):
        """Non-combat damage from a toxic source (real stack._deal_damage path)
        gives 0 poison counters — only combat damage triggers Toxic (CR 702.134a)."""
        gs = _make_combat_game()
        source = _toxic_card(power=2, toughness=2, toxic_value=2)
        gs = _deal_damage(gs, "p2", 2, source, "p1")
        assert get_player(gs, "p2").poison_counters == 0
        # The damage itself is applied (life loss)
        assert get_player(gs, "p2").life == 18


# ── Pure transform verification ──────────────────────────────────────────────

class TestPureTransform:
    def test_apply_toxic_pure_transform_original_unmutated(self):
        """apply_toxic returns a new GameState; the ORIGINAL player object is
        not mutated."""
        gs = _make_game()
        perm = Permanent(card=_toxic_card(toxic_value=2), controller="p1")
        original_p2 = gs.players[1]
        original_poison = original_p2.poison_counters

        new_gs = apply_toxic(gs, perm, "p2")

        assert new_gs is not gs
        assert get_player(new_gs, "p2").poison_counters == 2
        # Original state and player object untouched
        assert original_p2.poison_counters == original_poison == 0
        assert gs.players[1].poison_counters == 0

    def test_noop_paths_return_same_object(self):
        """No-op paths (unknown player, toxic value 0) return the SAME object."""
        gs = _make_game()
        perm = Permanent(card=_toxic_card(toxic_value=2), controller="p1")

        # Unknown player
        assert apply_toxic(gs, perm, "nonexistent") is gs
        # Class method, same no-op semantics
        assert ToxicKeyword().apply_toxic(gs, perm, "nonexistent") is gs

        # Toxic value 0 (no "Toxic N" in oracle → instance value used)
        plain_with_kw = _plain_card()
        plain_with_kw.keywords = ["toxic"]
        perm_zero = Permanent(card=plain_with_kw, controller="p1")
        assert ToxicKeyword(value=0).apply_toxic(gs, perm_zero, "p2") is gs

        # Main apply() remains a thin no-op (logic lives in apply_toxic,
        # called from the combat damage flow)
        assert ToxicKeyword().apply(gs, perm) is gs
