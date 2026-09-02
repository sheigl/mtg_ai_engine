"""Integration tests for the Equip keyword (CR 702.5, story 7-5b).

Equip {cost} means "{cost}: Attach this Equipment to target creature you control.
Activate this ability only any time you could cast a sorcery." These tests exercise:

* detection + cost/bonus parsing (Q1),
* the HUMAN path — ``Equip.apply`` queues ``pending_equip_choice`` WITHOUT attaching,
* the AI path — auto-resolves to the highest-power eligible creature and attaches,
  reflecting the Equipment's static +N/+N as combat P/T bonuses,
* attach-trigger firing (reused ``_apply_equip`` helper),
* the sorcery-speed timing gate (CR 702.5) and CR 702.6b (already-attached source),
* pure-transform guarantees (Q4): meaningful changes return a new GameState built
  with ``model_copy``; every no-op path returns the SAME object so repeated events
  cannot double-fire.

Because transforms build a fresh ``battlefield`` list of copied permanents, tests read
creature/equipment status from the *returned* GameState rather than stale locals.
"""
from mtg_engine.ability.keywords.equip import (
    Equip,
    apply_equip,
    resolve_equip_choice,
    parse_equip_bonus,
    clear_equip_bonus,
)
from mtg_engine.engine.combat.core import _effective_power, _effective_toughness
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, StackObject, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(active: str = "p1", holder: str | None = None, human: str | None = None) -> GameState:
    """A game at sorcery speed (controller's main phase, empty stack)."""
    gs = GameState(
        game_id="test-equip", seed=1,
        active_player=active, priority_holder=holder or active,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        step=Step.MAIN,
    )
    if human is not None:
        gs.human_player_name = human  # type: ignore[attr-defined]
    return gs


def _equipment(
    name: str = "Sword of Fire and Ice",
    power: str = "2",
    toughness: str = "2",
    cost: str = "{2}",
    controller: str = "p1",
    attached_to: str | None = None,
    extra_oracle: str = "",
) -> Permanent:
    """A realistic Equipment (+N/+N and an Equip {cost} clause)."""
    oracle = f"Equipped creature gets +{power}/+{toughness}."
    if extra_oracle:
        oracle += "\n" + extra_oracle
    oracle += f"\nEquip {cost}"
    card = Card(
        name=name,
        type_line="Artifact — Equipment",
        oracle_text=oracle,
        mana_cost=cost or "{1}",
    )
    return Permanent(card=card, controller=controller, attached_to=attached_to)


def _creature(power: str, toughness: str = "2", controller: str = "p1", name: str = "Goblin Soldier") -> Permanent:
    card = Card(
        name=name,
        type_line="Creature — Goblin",
        oracle_text="",
        mana_cost="{1}",
        power=power,
        toughness=toughness,
    )
    return Permanent(card=card, controller=controller)


def _place(gs: GameState, *perms: Permanent) -> None:
    gs.battlefield = list(perms)


def _equip_perm(gs: GameState) -> Permanent:
    return next(p for p in gs.battlefield if p.card.type_line.startswith("Artifact — Equipment"))


# ---------------------------------------------------------------------------
# Detection / parsing (Q1)
# ---------------------------------------------------------------------------

class TestDetection:
    def test_from_oracle_text_true(self):
        assert Equip.from_oracle_text("Equip {2}") is True

    def test_from_oracle_text_case_insensitive(self):
        assert Equip.from_oracle_text("equip — {1}{R}") is True

    def test_from_oracle_text_false(self):
        assert Equip.from_oracle_text("Flying, reach.") is False

    def test_from_oracle_text_empty(self):
        assert Equip.from_oracle_text("") is False

    def test_has_equip(self):
        assert Equip.has_equip(["equip"]) is True
        assert Equip.has_equip(["flying"]) is False

    def test_applies_on_real_equipment(self):
        gs = _make_game()
        perm = _equipment()
        assert Equip().applies(gs, perm) is True

    def test_parse_equip_cost(self):
        assert Equip.parse_equip_cost("Equip {2}") == "{2}"
        assert Equip.parse_equip_cost("Sword. Equip {1}{R}.") == "{1}{R}"
        assert Equip.parse_equip_cost("No keyword here.") is None

    def test_parse_equip_bonus_variants(self):
        assert parse_equip_bonus("Equipped creature gets +2/+2.") == (2, 2)
        assert parse_equip_bonus("+3/+1 to the equipped creature") == (3, 1)
        assert parse_equip_bonus("Protection only. No bonus.") == (0, 0)

    def test_parse_equip_bonus_negative(self):
        # A hypothetical -1/-1 equipment still parses (asymmetric bonuses supported).
        assert parse_equip_bonus("Equipped creature gets -1/-1.") == (-1, -1)


# ---------------------------------------------------------------------------
# Human path: queue choice WITHOUT attaching (Q4 no-attach)
# ---------------------------------------------------------------------------

class TestHumanPath:
    def test_human_queues_choice_without_attaching(self):
        gs = _make_game(human="p1")
        equip = _equipment()
        creature = _creature("3")
        _place(gs, equip, creature)

        new_gs = apply_equip(gs, equip)

        choice = new_gs.pending_equip_choice
        assert choice is not None
        assert choice["player"] == "p1"
        assert choice["permanent_id"] == equip.id
        assert choice["card_name"] == "Sword of Fire and Ice"
        assert choice["equipment_cost"] == "{2}"
        assert choice["resolved"] is False
        assert creature.id in choice["available_creatures"]

        # Nothing attached yet — the equipment must remain unattached.
        assert equip.attached_to is None
        assert creature.id not in equip.attachments
        assert new_gs.pending_equip_choice is not None

    def test_available_excludes_opponent_and_noncreatures(self):
        gs = _make_game(human="p1")
        equip = _equipment()
        friendly = _creature("2", controller="p1")
        opponent = _creature("5", controller="p2")
        land = Permanent(
            card=Card(name="Forest", type_line="Land — Forest", mana_cost="{G}"),
            controller="p1",
        )
        _place(gs, equip, friendly, opponent, land)

        new_gs = apply_equip(gs, equip)
        available = new_gs.pending_equip_choice["available_creatures"]

        assert friendly.id in available
        assert opponent.id not in available  # opponent's creature
        assert land.id not in available      # not a creature


# ---------------------------------------------------------------------------
# AI path: auto-resolve to highest-power creature (Q5 natural context)
# ---------------------------------------------------------------------------

class TestAIPath:
    def test_ai_attaches_to_highest_power_creature(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        small = _creature("1", name="Small Goblin")
        big = _creature("5", name="Big Goblin")
        _place(gs, equip, small, big)

        new_gs = apply_equip(gs, equip)

        assert new_gs.pending_equip_choice is None  # AI does not queue a choice
        target = next(p for p in new_gs.battlefield if p.card.name == "Big Goblin")
        attached = _equip_perm(new_gs)
        assert attached.attached_to == target.id    # highest power chosen
        assert equip.id in target.attachments       # creature records its equipment
        assert small.attached_to is None            # smaller creature untouched

    def test_equip_bonus_reflected_in_combat_pt(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment(power="2", toughness="2")
        creature = _creature("2", toughness="2")
        _place(gs, equip, creature)

        new_gs = apply_equip(gs, equip)
        target = next(p for p in new_gs.battlefield if p.id == creature.id)

        # Base 2/2 + equipment bonus +2/+2 => effective combat P/T 4/4.
        assert _effective_power(target) == 4
        assert _effective_toughness(target) == 4
        assert target.power_bonus == 2
        assert target.toughness_bonus == 2

    def test_ai_no_eligible_target_returns_same_object(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        # Only an opponent's creature on the board.
        opponent = _creature("5", controller="p2")
        _place(gs, equip, opponent)

        result = apply_equip(gs, equip)
        assert result is gs  # pure no-op — nothing to attach to

    def test_ai_no_creatures_returns_same_object(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        _place(gs, equip)
        assert apply_equip(gs, equip) is gs


# ---------------------------------------------------------------------------
# Attach-trigger firing (Q5 real entry point via reused _apply_equip)
# ---------------------------------------------------------------------------

class TestAttachTrigger:
    def test_ai_equip_fires_attach_trigger(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment(
            extra_oracle="Whenever this becomes attached to another permanent, draw a card.",
        )
        creature = _creature("3")
        _place(gs, equip, creature)

        new_gs = apply_equip(gs, equip)

        by_id = {p.id: p for p in new_gs.battlefield}
        assert by_id[equip.id].attached_to == creature.id  # actually attached ...
        trigger_types = {t.trigger_type for t in new_gs.pending_triggers}
        assert "attach" in trigger_types                   # ... and the trigger fired


# ---------------------------------------------------------------------------
# Sorcery-speed timing guard (AC: sorcery-speed only)
# ---------------------------------------------------------------------------

class TestTimingGuard:
    def test_not_active_player_main_phase_is_noop(self):
        gs = _make_game(active="p2", holder="p1")  # not p1's main phase
        equip = _equipment(controller="p1")
        creature = _creature("3", controller="p1")
        _place(gs, equip, creature)

        result = apply_equip(gs, equip)
        assert result is gs
        assert equip.attached_to is None

    def test_stack_not_empty_is_noop(self):
        gs = _make_game(active="p1", holder="p1")
        gs.stack = [StackObject(source_card=Card(name="Lightning Bolt", type_line="Instant"), controller="p2")]
        equip = _equipment()
        creature = _creature("3")
        _place(gs, equip, creature)

        result = apply_equip(gs, equip)
        assert result is gs
        assert equip.attached_to is None

    def test_non_main_phase_is_noop(self):
        gs = _make_game(active="p1", holder="p1")
        gs.step = Step.DECLARE_ATTACKERS  # not a main phase
        equip = _equipment()
        creature = _creature("3")
        _place(gs, equip, creature)

        result = apply_equip(gs, equip)
        assert result is gs
        assert equip.attached_to is None


# ---------------------------------------------------------------------------
# Negative / guard paths (Q1 + Q4 exactly-once)
# ---------------------------------------------------------------------------

class TestGuardPaths:
    def test_already_attached_source_is_noop(self):
        # CR 702.6b: an Equipment already attached cannot be re-activated.
        gs = _make_game(active="p1", holder="p1")
        creature = _creature("3")
        equip = _equipment(attached_to=creature.id)
        _place(gs, equip, creature)

        result = apply_equip(gs, equip)
        assert result is gs

    def test_wrong_controller_is_noop(self):
        gs = _make_game(active="p2", holder="p2")  # p2 holds priority
        equip = _equipment(controller="p1")         # but p1 controls the Equipment
        creature = _creature("3", controller="p1")
        _place(gs, equip, creature)

        result = apply_equip(gs, equip)
        assert result is gs

    def test_equipment_not_on_battlefield_is_noop(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        creature = _creature("3")
        _place(gs, creature)  # equipment intentionally absent

        assert apply_equip(gs, equip) is gs

    def test_non_equipment_card_is_noop(self):
        gs = _make_game(active="p1", holder="p1")
        plain = Permanent(
            card=Card(name="Iron Skiff", type_line="Artifact — Vehicle", oracle_text="", mana_cost="{2}"),
            controller="p1",
        )
        creature = _creature("3")
        _place(gs, plain, creature)

        result = apply_equip(gs, plain)
        assert result is gs
        assert plain.attached_to is None  # nothing attached

    def test_repeated_apply_does_not_double_attach(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        creature = _creature("3")
        _place(gs, equip, creature)

        gs = apply_equip(gs, equip)          # AI attaches to the only creature
        current_equip = _equip_perm(gs)
        second = apply_equip(gs, current_equip)  # already attached -> no-op (702.6b)

        assert second is gs
        assert current_equip.attached_to == creature.id
        # Bonus applied exactly once.
        target = next(p for p in gs.battlefield if p.id == creature.id)
        assert target.power_bonus == 2


# ---------------------------------------------------------------------------
# Pure-transform guarantees (Q4)
# ---------------------------------------------------------------------------

class TestPureTransform:
    def test_ai_returns_new_object_and_leaves_original_unchanged(self):
        gs = _make_game(active="p1", holder="p1")
        equip = _equipment()
        creature = _creature("2")
        _place(gs, equip, creature)

        new_gs = apply_equip(gs, equip)

        assert new_gs is not gs  # meaningful change -> new object
        orig_equip = next(p for p in gs.battlefield if p.id == equip.id)
        assert orig_equip.attached_to is None          # original battlefield untouched
        orig_creature = next(p for p in gs.battlefield if p.id == creature.id)
        assert orig_creature.power_bonus == 0

    def test_human_queues_pending_via_model_copy(self):
        gs = _make_game(human="p1")
        equip = _equipment()
        creature = _creature("3")
        _place(gs, equip, creature)

        new_gs = apply_equip(gs, equip)

        assert new_gs is not gs  # queued choice -> new object (model_copy update)
        assert new_gs.pending_equip_choice["permanent_id"] == equip.id


# ---------------------------------------------------------------------------
# Human choice resolution
# ---------------------------------------------------------------------------

class TestResolveChoice:
    def _queued(self, powers: list[str]) -> GameState:
        gs = _make_game(human="p1")
        equip = _equipment()
        creatures = [_creature(p) for p in powers]
        _place(gs, equip, *creatures)
        return apply_equip(gs, equip)  # returned state carries the pending choice

    def test_resolve_attaches_and_clears_pending(self):
        gs = self._queued(["2", "4"])
        target_id = next(p.id for p in gs.battlefield if p.card.power == "4")

        new_gs = resolve_equip_choice(gs, "p1", target_id)

        assert new_gs.pending_equip_choice is None
        equip = _equip_perm(new_gs)
        target = next(p for p in new_gs.battlefield if p.id == target_id)
        assert equip.attached_to == target_id
        assert equip.id in target.attachments   # creature records its equipment
        # Bonus reflected on the chosen creature.
        target = next(p for p in new_gs.battlefield if p.id == target_id)
        assert _effective_power(target) == 6  # base 4 + 2/+2

    def test_resolve_decline_clears_pending_without_attaching(self):
        gs = self._queued(["3"])
        equip = _equip_perm(gs)

        new_gs = resolve_equip_choice(gs, "p1", None)  # no target -> decline

        assert new_gs.pending_equip_choice is None
        assert equip.attached_to is None

    def test_resolve_invalid_target_clears_pending(self):
        gs = self._queued(["3"])
        unknown_id = "does-not-exist"

        new_gs = resolve_equip_choice(gs, "p1", unknown_id)

        assert new_gs.pending_equip_choice is None
        assert _equip_perm(new_gs).attached_to is None

    def test_resolve_wrong_player_is_noop(self):
        gs = self._queued(["3"])
        result = resolve_equip_choice(gs, "p2")  # not the choosing player
        assert result is gs


# ---------------------------------------------------------------------------
# clear_equip_bonus helper (unattach revert)
# ---------------------------------------------------------------------------

class TestClearEquipBonus:
    def test_clear_resets_bonus(self):
        creature = _creature("2")
        creature.power_bonus = 2
        creature.toughness_bonus = 2
        cleared = clear_equip_bonus(creature)
        assert cleared.power_bonus == 0
        assert cleared.toughness_bonus == 0

    def test_clear_on_no_bonus_returns_same_object(self):
        creature = _creature("2")
        assert clear_equip_bonus(creature) is creature
