"""
Trigger hygiene: Toxic keyword reminder must NOT queue a spurious no-op
combat_damage PendingTrigger.

Root cause: the fallback block in ``check_damage_triggers``
(mtg_engine/engine/triggers.py) regex-scans the card's FULL oracle text for
"whenever this creature deals combat damage". A Toxic card's oracle text is a
keyword reminder:

    "Toxic 2 (whenever this creature deals combat damage to a player,
     that player gets 2 poison counters.)"

The reminder text (inside parentheses) matched the regex and queued a spurious
no-op ``combat_damage`` PendingTrigger. Toxic is already handled by the
dedicated ``apply_toxic()`` in combat/core.py, so the trigger was pure noise.

Fix: the fallback now iterates all regex matches and queues at most ONE
trigger per permanent — and only for a match that is NOT inside a
parenthetical (real self-referential triggers are top-level text).

These tests drive the REAL combat flow (declare_attackers →
assign_combat_damage) and the real ``check_damage_triggers`` function.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.engine.combat import declare_attackers, declare_blockers, assign_combat_damage
from mtg_engine.engine.triggers import check_damage_triggers, _is_inside_parenthetical
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.models.actions import AttackDeclaration, BlockDeclaration, DamageAssignment
from mtg_engine.models.game import Card, GameState, PlayerState, Phase, Step


TOXIC_ORACLE = (
    "Toxic 1 (whenever this creature deals combat damage to a player, "
    "that player gets 1 poison counters.)"
)
OPHIDIAN_ORACLE = (
    "Whenever this creature deals combat damage to a player, you may draw a card."
)
COMBINED_ORACLE = (
    "Toxic 1 (whenever this creature deals combat damage to a player, "
    "that player gets 1 poison counters.) "
    "Whenever this creature deals combat damage to a player, draw a card."
)


def _make_combat_game() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="t-toxic-hygiene",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_ATTACKERS,
        players=[p1, p2],
    )


def _toxic_card(power: int = 2, toughness: int = 2) -> Card:
    return Card(
        name="Venom Connoisseur",
        type_line="Creature — Cat",
        power=str(power),
        toughness=str(toughness),
        oracle_text=TOXIC_ORACLE,
        keywords=["toxic"],
    )


def _add_creature(gs: GameState, card: Card, controller: str):
    gs, perm = put_permanent_onto_battlefield(gs, card, controller)
    perm.summoning_sick = False
    return gs, perm


def _run_unblocked_attack(gs: GameState, attacker, defending_id: str = "p2") -> GameState:
    """Full real combat flow: declare attackers → combat damage step → assign."""
    gs = declare_attackers(
        gs, [AttackDeclaration(attacker_id=attacker.id, defending_id=defending_id)]
    )
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    return gs


def _combat_damage_triggers(gs: GameState) -> list:
    return [t for t in gs.pending_triggers if t.trigger_type == "combat_damage"]


# ── Negative: the fix ────────────────────────────────────────────────────────

class TestToxicNoSpuriousTrigger:
    def test_toxic_hit_queues_no_combat_damage_trigger(self):
        """Q1 negative: a Toxic hit queues NO combat_damage trigger (and no
        spurious trigger of any type from the keyword reminder text)."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(), "p1")
        gs = _run_unblocked_attack(gs, attacker)

        assert _combat_damage_triggers(gs) == [], (
            f"Spurious combat_damage trigger still queued: "
            f"{[(t.trigger_type, t.source_card_name) for t in gs.pending_triggers]}"
        )
        # No spurious trigger of ANY type from the reminder text either.
        assert gs.pending_triggers == [], (
            f"Expected no pending triggers at all, got "
            f"{[(t.trigger_type, t.source_card_name) for t in gs.pending_triggers]}"
        )

    def test_toxic_hit_still_applies_poison_counter(self):
        """Regression (orthogonal): the real apply_toxic() path still adds the
        poison counter even though no trigger is queued."""
        gs = _make_combat_game()
        gs, attacker = _add_creature(gs, _toxic_card(), "p1")
        gs = _run_unblocked_attack(gs, attacker)

        assert gs.players[1].poison_counters == 1
        assert gs.players[0].poison_counters == 0


# ── Positive: real self-referential triggers still fire ─────────────────────

class TestRealTriggerStillQueued:
    def test_real_self_referential_trigger_queues_exactly_one(self):
        """Q1 positive: a real (non-parenthetical) 'whenever this creature
        deals combat damage' trigger still queues exactly ONE combat_damage
        trigger. Mirrors tests/rules/test_combat.py::test_combat_damage_trigger_queued."""
        gs = _make_combat_game()
        card = Card(
            name="Ophidian",
            type_line="Creature — Snake",
            power="1",
            toughness="1",
            oracle_text=OPHIDIAN_ORACLE,
        )
        gs, attacker = _add_creature(gs, card, "p1")
        gs = _run_unblocked_attack(gs, attacker)

        triggers = _combat_damage_triggers(gs)
        assert len(triggers) == 1
        assert triggers[0].source_permanent_id == attacker.id
        assert triggers[0].source_card_name == "Ophidian"

    def test_combined_reminder_and_real_trigger_queues_exactly_one(self):
        """A card with BOTH a Toxic reminder (in parentheses) AND a real
        top-level self-referential trigger queues exactly ONE combat_damage
        trigger — the real one, not two."""
        gs = _make_combat_game()
        card = Card(
            name="Toxic Ophidian",
            type_line="Creature — Snake",
            power="1",
            toughness="1",
            oracle_text=COMBINED_ORACLE,
            keywords=["toxic"],
        )
        gs, attacker = _add_creature(gs, card, "p1")
        gs = _run_unblocked_attack(gs, attacker)

        triggers = _combat_damage_triggers(gs)
        assert len(triggers) == 1
        assert triggers[0].source_permanent_id == attacker.id
        # Toxic still applies via its dedicated path.
        assert gs.players[1].poison_counters == 1

    def test_real_trigger_not_queued_for_zero_damage(self):
        """Real trigger does NOT queue when the creature deals 0 damage
        (blocked by an equal-or-higher-toughness blocker, no trample).
        Mirrors tests/rules/test_combat.py::test_combat_damage_trigger_not_queued_for_zero_damage."""
        gs = _make_combat_game()
        card = Card(
            name="Ophidian",
            type_line="Creature — Snake",
            power="1",
            toughness="1",
            oracle_text="Whenever this creature deals combat damage to a player, draw a card.",
        )
        gs, attacker = _add_creature(gs, card, "p1")
        wall = Card(name="Wall", type_line="Creature — Wall", power="0", toughness="3")
        gs, blocker = _add_creature(gs, wall, "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        assert _combat_damage_triggers(gs) == []  # blocked: player took no damage


# ── Direct function-level checks ─────────────────────────────────────────────

class TestCheckDamageTriggersDirect:
    def _game_with(self, card: Card):
        gs = _make_combat_game()
        gs, perm = _add_creature(gs, card, "p1")
        return gs, perm

    def test_direct_toxic_assignment_queues_nothing(self):
        """Driving check_damage_triggers directly with a Toxic attacker that
        dealt 2 damage to a player queues no combat_damage trigger."""
        gs, perm = self._game_with(_toxic_card(power=2, toughness=2))
        assignment = DamageAssignment(source_id=perm.id, target_id="p2", damage=2)
        gs = check_damage_triggers(gs, [assignment])
        assert _combat_damage_triggers(gs) == []

    def test_direct_real_trigger_assignment_queues_one(self):
        """Driving check_damage_triggers directly with a real self-referential
        trigger queues exactly one combat_damage trigger."""
        card = Card(
            name="Ophidian",
            type_line="Creature — Snake",
            power="1",
            toughness="1",
            oracle_text=OPHIDIAN_ORACLE,
        )
        gs, perm = self._game_with(card)
        assignment = DamageAssignment(source_id=perm.id, target_id="p2", damage=1)
        gs = check_damage_triggers(gs, [assignment])
        triggers = _combat_damage_triggers(gs)
        assert len(triggers) == 1
        assert triggers[0].source_permanent_id == perm.id

    def test_direct_zero_damage_assignment_queues_nothing(self):
        """Zero damage to a player never queues the trigger, even for a real
        self-referential trigger card."""
        card = Card(
            name="Ophidian",
            type_line="Creature — Snake",
            power="1",
            toughness="1",
            oracle_text=OPHIDIAN_ORACLE,
        )
        gs, perm = self._game_with(card)
        assignment = DamageAssignment(source_id=perm.id, target_id="p2", damage=0)
        gs = check_damage_triggers(gs, [assignment])
        assert _combat_damage_triggers(gs) == []


# ── _is_inside_parenthetical helper ──────────────────────────────────────────

class TestIsInsideParenthetical:
    def test_depth_zero_at_start(self):
        text = "Toxic 2 (whenever this creature deals combat damage to a player, that player gets 2 poison counters.)"
        assert _is_inside_parenthetical(text, 0) is False

    def test_depth_positive_inside_parens(self):
        text = "Toxic 2 (whenever this creature deals combat damage to a player, that player gets 2 poison counters.)"
        inside = text.index("whenever")
        assert _is_inside_parenthetical(text, inside) is True

    def test_depth_back_to_zero_after_closed_paren(self):
        text = "Toxic 2 (whenever this creature deals combat damage to a player, that player gets 2 poison counters.) After the close."
        closed_at = text.index(")")
        assert _is_inside_parenthetical(text, closed_at + 1) is False

    def test_nested_parens(self):
        text = "a ((inner)) b"
        # indices: 0='a' 1=' ' 2='(' 3='(' 4..8='inner' 9=')' 10=')' 11=' '
        assert _is_inside_parenthetical(text, 3) is True   # between ( and (
        assert _is_inside_parenthetical(text, 4) is True   # inside inner
        assert _is_inside_parenthetical(text, 11) is False  # after ))
