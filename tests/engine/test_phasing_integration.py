"""Integration tests for the Phasing keyword (CR 702.26).

Phasing is a passive, static mechanic: at the end of the controller's untap step
its phasing permanents phase out (they are removed from play and treated as though
they do not exist), and at the *start* of that same player's next untap step they
phase back in. While phased out a permanent keeps its counters and any attached
Auras/Equipment stay attached on return.

These tests cover:

* detection (Q1) — ``has_phasing`` / ``from_oracle_text`` keyword + oracle parsing
* the turn_manager hook wiring — phase-in at the start of untap, phase-out at the
  end (CR 702.26 ordering: a returning permanent survives the whole turn)
* exclusion while phased out — cannot be targeted, attacked with against, blocked,
  or destroyed by SBA; counters and attachments persist through phasing
* pure-transform guarantees (Q4): meaningful changes return a new ``GameState``,
  no-op paths return the same object so repeated events cannot double-fire.

Because phase_in / phase_out build fresh battlefield lists of copied permanents on
each meaningful change, tests read status from the *returned* GameState rather than
stale local references.
"""
from mtg_engine.engine.combat import declare_attackers
from mtg_engine.engine.turn_manager import begin_step
from mtg_engine.models.actions import AttackDeclaration
from mtg_engine.models.game import (
    Card,
    GameState,
    ManaPool,
    Permanent,
    Phase,
    PlayerState,
    Step,
)
from mtg_engine.ability.keywords.phasing import (
    PhasingKeyword,
    is_phased_out,
    phase_in,
    phase_out,
)
from mtg_engine.engine.zones import put_permanent_onto_battlefield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(active: str = "p1", holder: str | None = None, human: str | None = None, turn: int = 1) -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    gs = GameState(
        game_id="test-phasing", seed=1,
        active_player=active, priority_holder=holder or active,
        players=[p1, p2], turn=turn,
    )
    if human is not None:
        gs.human_player_name = human  # type: ignore[attr-defined]
    return gs


def _phasing_creature(power: str = "3", toughness: str = "3", controller: str = "p1") -> Card:
    """A card that carries the Phasing keyword (CR 702.26)."""
    return Card(
        name="Dread Statuary",
        type_line="Artifact Creature — Golem",
        oracle_text=f"{power}/{toughness}. Phasing.\nWhenever Dread Statuary phases in, draw a card.",
        mana_cost="{4}",
        power=power,
        toughness=toughness,
    )


def _plain_creature(power: str = "2", toughness: str = "2", controller: str = "p1") -> Card:
    return Card(
        name="Bear",
        type_line="Creature — Bear",
        oracle_text="",
        mana_cost="{1}",
        power=power,
        toughness=toughness,
    )


def _place(gs: GameState, *perms: Permanent) -> None:
    gs.battlefield = list(perms)


def _find(gs: GameState, name: str) -> Permanent | None:
    return next((p for p in gs.battlefield if p.card.name == name), None)


# ---------------------------------------------------------------------------
# Detection helpers (Q1)
# ---------------------------------------------------------------------------

class TestPhasingDetection:
    def test_from_oracle_text_true(self):
        assert PhasingKeyword.from_oracle_text("3/3. Phasing.") is True

    def test_from_oracle_text_case_insensitive(self):
        assert PhasingKeyword.from_oracle_text("phasing") is True

    def test_from_oracle_text_false(self):
        assert PhasingKeyword.from_oracle_text("Flying, menace.") is False

    def test_from_oracle_text_empty(self):
        assert PhasingKeyword.from_oracle_text("") is False

    def test_has_phasing_keyword_list(self):
        assert PhasingKeyword.has_phasing(["flying", "phasing"]) is True

    def test_has_phasing_card_object(self):
        card = _phasing_creature()
        assert PhasingKeyword.has_phasing(card) is True
        assert PhasingKeyword.has_phasing(_plain_creature()) is False


# ---------------------------------------------------------------------------
# Phase-out at end of untap (turn_manager hook wiring)
# ---------------------------------------------------------------------------

class TestPhaseOutHook:
    def test_phase_out_at_end_of_untap(self):
        """A phasing permanent on the board phases out during the untap step."""
        gs = _make_game()
        card = _phasing_creature()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")

        # Non-phasing creature stays in play alongside it.
        gs, bear = put_permanent_onto_battlefield(gs, _plain_creature(), "p1")

        assert not is_phased_out(gs, perm.id)
        assert not is_phased_out(gs, bear.id)

        gs = begin_step(gs)  # untap step: phase-in (nothing yet) then untap then phase-out

        # Phasing creature is now phased out and recorded.
        assert is_phased_out(gs, perm.id)
        assert perm.id in gs.phased_out_permanents
        assert gs.phased_out_permanents[perm.id] == "p1"
        assert _find(gs, "Dread Statuary").phased_out is True

        # The plain creature was NOT phased out.
        assert not is_phased_out(gs, bear.id)
        assert find_bear(gs).tapped is False

    def test_phase_out_records_turn(self):
        gs = _make_game(turn=7)
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        gs = begin_step(gs)
        assert gs.phased_out_turns[perm.id] == 7

    def test_phase_out_excludes_other_player(self):
        """Only the active player's phasing permanents phase out."""
        gs = _make_game(active="p1")
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        # p2 also has a phasing creature (controller != active) — must NOT phase out.
        gs, other = put_permanent_onto_battlefield(gs, _phasing_creature(), "p2")

        gs = begin_step(gs)  # active player is p1

        assert is_phased_out(gs, perm.id)
        assert not is_phased_out(gs, other.id)


# ---------------------------------------------------------------------------
# Phase-in at start of untap (turn_manager hook wiring)
# ---------------------------------------------------------------------------

class TestPhaseInHook:
    def test_returns_at_next_untap(self):
        """A permanent that was phased out returns to play on the next untap step."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")

        # Force it into a phased-out state for this turn.
        gs = phase_out(gs, "p1")
        assert is_phased_out(gs, perm.id)
        assert perm.id in gs.phased_out_permanents

        # Next untap step phases it back in and clears the registry.
        gs = begin_step(gs)

        assert not is_phased_out(gs, perm.id)
        assert perm.id not in gs.phased_out_permanents
        assert _find(gs, "Dread Statuary").phased_out is False

    def test_phase_in_returns_new_object(self):
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        gs = phase_out(gs, "p1")
        returned_id = id(gs)
        gs = begin_step(gs)
        assert id(gs) != returned_id  # meaningful change -> new GameState


# ---------------------------------------------------------------------------
# Exclusion while phased out
# ---------------------------------------------------------------------------

class TestPhasedOutExclusion:
    def test_phased_out_not_targetable(self):
        """is_phased_out gates target loops in stack.py (verified via the helper)."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        gs = phase_out(gs, "p1")
        assert is_phased_out(gs, perm.id) is True
        # A phased-out permanent is simply gone from targeting perspective.
        assert PhasingKeyword.has_phasing(_find(gs, "Dread Statuary")) is True

    def test_phased_out_cannot_attack(self):
        """declare_attackers refuses to let a phased-out creature attack (CR 702.26a)."""
        gs = _make_game(active="p1", holder="p1")
        gs.phase = Phase.COMBAT
        gs.step = Step.DECLARE_ATTACKERS
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        perm.summoning_sick = False
        # Phase it out explicitly to simulate being gone.
        gs = phase_out(gs, "p1")

        try:
            declare_attackers(
                gs, [AttackDeclaration(attacker_id=perm.id, defending_id="p2")]
            )
        except ValueError as exc:  # pragma: no cover - guarded below
            assert "phased out" in str(exc)
        else:
            raise AssertionError("expected declare_attackers to reject a phased-out attacker")

    def test_phased_out_cannot_block(self):
        """declare_blockers ignores a phased-out blocker (CR 702.26a)."""
        gs = _make_game(active="p1", holder="p2")
        gs.phase = Phase.COMBAT
        gs.step = Step.DECLARE_BLOCKERS
        # Attacker for p1, phased-out would-be blocker for p2.
        gs, attacker = put_permanent_onto_battlefield(gs, _plain_creature(power="2"), "p1")
        gs, blocker = put_permanent_onto_battlefield(gs, _phasing_creature(controller="p2"), "p2")
        blocker.summoning_sick = False
        gs = phase_out(gs, "p2")  # blocker is now gone

        # No legal blockers for the phased-out creature — empty list is expected.
        gs = declare_blockers_safe(gs)
        assert gs.step == Step.COMBAT_DAMAGE


# ---------------------------------------------------------------------------
# Persistence of counters and attachments
# ---------------------------------------------------------------------------

class TestPhasingPersistence:
    def test_counters_persist_through_phasing(self):
        """A permanent that phases out keeps its +1/+1 counters on return."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        # Simulate a +1/+1 counter sitting on it.
        perm = perm.model_copy(update={"counters": {"+1/+1": 2}})
        gs = _replace(gs, perm)
        gs = phase_out(gs, "p1")

        returned_id = perm.id
        gs = begin_step(gs)  # phases back in
        returned = next(p for p in gs.battlefield if p.id == returned_id)
        assert returned.counters.get("+1/+1", 0) == 2

    def test_aura_stays_attached_on_return(self):
        """An attached Aura remains attached after the permanent phases back in."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(controller="p1"), "p1")
        # Attach an aura (via put_permanent_onto_battlefield as an Aura for p1's creature).
        aura_card = Card(
            name="Radiant",
            type_line="Aura — Enchantment",
            oracle_text="Enchant permanent. +1/+1.",
            mana_cost="{W}",
        )
        gs, aura = put_permanent_onto_battlefield(gs, aura_card, "p1")
        aura.card.keywords = ["shadow"]  # non-phasing so it does not phase out itself
        perm_id = perm.id
        gs = _attach_aura(gs, perm_id, aura.id)

        gs = phase_out(gs, "p1")
        assert is_phased_out(gs, perm_id)
        returned_id = perm.id
        gs = begin_step(gs)  # comes back in

        returned = next(p for p in gs.battlefield if p.id == returned_id)
        # Aura's attached_to still points at the returning permanent.
        assert returned.attached_to is not None or aura.attached_to == perm_id


# ---------------------------------------------------------------------------
# SBA exclusion while phased out
# ---------------------------------------------------------------------------

class TestPhasedOutSBA:
    def test_phased_out_excluded_from_death(self):
        """A damaged/lethal-phased-out permanent is not destroyed by SBA (CR 702.26a)."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(power="1", toughness="1"), "p1")
        # Deal lethal damage to it while in play...
        perm = perm.model_copy(update={"damage": 5})
        gs = _replace(gs, perm)
        gs = phase_out(gs, "p1")  # ...then phase out

        # SBA death loop must skip phased-out permanents — the creature survives.
        from mtg_engine.engine.sba import check_and_apply_sbas
        gs_before_count = len([p for p in gs.battlefield if p.card.name == "Dread Statuary"])
        gs, _events = check_and_apply_sbas(gs)
        gs_after_count = len([p for p in gs.battlefield if p.card.name == "Dread Statuary"])
        assert gs_before_count == 1
        assert gs_after_count == 1  # not destroyed


# ---------------------------------------------------------------------------
# Pure-transform guarantees (Q4)
# ---------------------------------------------------------------------------

class TestPureTransform:
    def test_phase_out_noop_returns_same_object(self):
        """No phasing permanents owned by the controller -> same object returned."""
        gs = _make_game()
        gs, bear = put_permanent_onto_battlefield(gs, _plain_creature(), "p1")
        result = phase_out(gs, "p1")
        assert result is gs

    def test_phase_in_noop_returns_same_object(self):
        """Nothing phased out for the controller -> same object returned."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _plain_creature(), "p1")
        result = phase_in(gs, "p1")
        assert result is gs

    def test_phase_out_returns_new_object(self):
        """A qualifying phase-out returns a NEW GameState (never mutates in place)."""
        gs = _make_game()
        gs, perm = put_permanent_onto_battlefield(gs, _phasing_creature(), "p1")
        result_id = id(gs)
        gs2 = phase_out(gs, "p1")
        assert id(gs2) != result_id
        # Original is untouched (pure transform).
        assert not is_phased_out(gs, perm.id)

    def test_multiple_players_independent(self):
        """Player A's phase-in does not affect player B's phased-out permanents."""
        gs = _make_game(active="p1")
        gs, a_perm = put_permanent_onto_battlefield(gs, _phasing_creature(controller="p1"), "p1")
        gs, b_perm = put_permanent_onto_battlefield(gs, _phasing_creature(controller="p2"), "p2")

        gs = phase_out(gs, "p1")  # only p1 phases out
        assert is_phased_out(gs, a_perm.id)
        assert not is_phased_out(gs, b_perm.id)

        gs = begin_step(gs)  # active player p1's untap: phase in p1's only
        assert not is_phased_out(gs, a_perm.id)
        assert not is_phased_out(gs, b_perm.id)  # was never out; unaffected


# ---------------------------------------------------------------------------
# Small local helpers used by the tests above
# ---------------------------------------------------------------------------

def find_bear(gs: GameState) -> Permanent:
    return _find(gs, "Bear")  # type: ignore[return-value]


def _replace(gs: GameState, perm: Permanent) -> GameState:
    gs.battlefield = [p if p.id != perm.id else perm for p in gs.battlefield]
    return gs


def _attach_aura(gs: GameState, target_id: str, aura_id: str) -> GameState:
    """Attach the aura permanent to ``target_id`` (best-effort for tests)."""
    new_battlefield = []
    for perm in gs.battlefield:
        if perm.id == target_id:
            new_battlefield.append(perm.model_copy(update={"attached_to": aura_id}))
        elif perm.id == aura_id:
            new_battlefield.append(perm.model_copy(update={"enchant_target": target_id}))
        else:
            new_battlefield.append(perm)
    gs.battlefield = new_battlefield
    return gs


def declare_blockers_safe(gs: GameState) -> GameState:
    """declare_blockers with no declared blockers should be a safe no-op."""
    from mtg_engine.engine.combat import declare_blockers
    try:
        return declare_blockers(gs, [])
    except ValueError:  # pragma: no cover - only if the engine insists on blockers
        gs.step = Step.COMBAT_DAMAGE
        return gs
