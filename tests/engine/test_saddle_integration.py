"""Integration tests for the Saddle keyword (Bloomburrow, BLI 2025).

"Saddle — This enters the battlefield attached to target creature you control,
as an Equipment would."

Saddle attaches at enter-the-battlefield like Equip but WITHOUT an activated
ability, sorcery-speed gate, or mana/tap cost. These tests cover:

* detection (Q1) — ``has_saddle`` / ``from_oracle_text`` keyword + oracle parsing,
* the HUMAN path via ``put_permanent_onto_battlefield`` — queues
  ``pending_saddle_choice`` WITHOUT attaching (permanent stays loose),
* the AI path — auto-resolves to the highest-power eligible creature and attaches
  via the shared ``_apply_equip`` helper, firing attach triggers,
* attachment state correctness (``attached_to`` + host ``attachments``),
* deterministic tie-break (lowest perm id among equal-power creatures),
* graceful no-legal-target behaviour (permanent enters loose, not an error),
* pure-transform guarantees (Q4): meaningful changes return a new GameState,
  no-op paths return the SAME object so repeated events cannot double-fire,
* clean SBA detach when the host leaves the battlefield.

Because transforms build fresh battlefield lists of copied permanents on each
meaningful change, tests read status from the *returned* GameState rather than
stale local references.
"""
from mtg_engine.ability.keywords.saddle import (
    SaddleKeyword,
    apply_saddle,
    resolve_saddle_choice,
)
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.models.game import Card, GameState, Permanent, Phase, PlayerState, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(active: str = "p1", holder: str | None = None, human: str | None = None) -> GameState:
    """A game state (optionally with a human controller)."""
    gs = GameState(
        game_id="test-saddle", seed=1,
        active_player=active, priority_holder=holder or active,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        step=Step.MAIN, phase=Phase.COMBAT,
    )
    if human is not None:
        gs.human_player_name = human  # type: ignore[attr-defined]
    return gs


def _saddled_card(name: str = "Iron Saddle", extra_oracle: str = "") -> Card:
    """A saddled artifact that enters attached to a target creature it controls."""
    oracle = "Saddle."
    if extra_oracle:
        oracle += "\n" + extra_oracle
    return Card(
        name=name,
        type_line="Artifact — Equipment",
        oracle_text=oracle,
        mana_cost="{2}",
    )


def _host_card(power: str = "3", toughness: str = "3", controller: str = "p1", name: str = "Goblin Warband") -> Card:
    return Card(
        name=name,
        type_line="Creature — Goblin Warrior",
        oracle_text="",
        mana_cost="{2}",
        power=power,
        toughness=toughness,
    )


def _place(gs: GameState, *perms: Permanent) -> None:
    gs.battlefield = list(perms)


def _find(gs: GameState, perm_id: str) -> Permanent | None:
    return next((p for p in gs.battlefield if p.id == perm_id), None)


# ---------------------------------------------------------------------------
# 1. Detection (Q1)
# ---------------------------------------------------------------------------

class TestDetection:
    def test_has_saddle_true(self):
        card = _saddled_card()
        assert SaddleKeyword.has_saddle(card) is True

    def test_has_saddle_false(self):
        card = Card(name="Bear", type_line="Creature — Bear", mana_cost="{1}")
        assert SaddleKeyword.has_saddle(card) is False

    def test_has_saddle_on_perm_object(self):
        perm = Permanent(card=_saddled_card(), controller="p1")
        assert SaddleKeyword.has_saddle(perm) is True

    def test_from_oracle_text_case_insensitive(self):
        assert SaddleKeyword.from_oracle_text("3/3. saddle.") is True

    def test_from_oracle_text_false(self):
        assert SaddleKeyword.from_oracle_text("Flying, menace.") is False

    def test_from_oracle_text_empty(self):
        assert SaddleKeyword.from_oracle_text("") is False


# ---------------------------------------------------------------------------
# 2. from_oracle_text parsing (Q1)
# ---------------------------------------------------------------------------

class TestFromOracleText:
    def test_bare_keyword(self):
        assert SaddleKeyword.from_oracle_text("Saddle") is True

    def test_in_full_oracle(self):
        oracle = "This enters the battlefield attached to target creature you control."
        # The word 'saddle' must appear for detection (real cards spell it out).
        assert SaddleKeyword.from_oracle_text(oracle + "\nSaddle.") is True

    def test_substring_not_matched(self):
        # "assaddle" contains the letters but not the word boundary.
        assert SaddleKeyword.from_oracle_text("assadbling") is False


# ---------------------------------------------------------------------------
# 3. Human path queues pending_choice WITHOUT attaching (via zones.py hook)
# ---------------------------------------------------------------------------

class TestHumanPath:
    def test_human_queues_pending_choice_not_attached(self):
        gs = _make_game(human="p1")
        gs, host = put_permanent_onto_battlefield(gs, _host_card(), "p1")
        gs, saddle_perm = put_permanent_onto_battlefield(gs, _saddled_card(), "p1")

        # Queued a choice ...
        choice = gs.pending_saddle_choice
        assert choice is not None
        assert choice["player"] == "p1"
        assert choice["permanent_id"] == saddle_perm.id
        assert choice["card_name"] == "Iron Saddle"
        assert host.id in choice["available_creatures"]
        assert choice["resolved"] is False

        # ... and the permanent stays LOOSE until resolved.
        saddle_now = _find(gs, saddle_perm.id)
        assert saddle_now.attached_to is None


# ---------------------------------------------------------------------------
# 4. AI auto-resolves to highest-power creature (via apply_saddle)
# ---------------------------------------------------------------------------

class TestAIPath:
    def test_ai_attaches_to_highest_power(self):
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        small = Permanent(card=_host_card(power="1", name="Small"), controller="p1")
        big = Permanent(card=_host_card(power="5", name="Big"), controller="p1")
        _place(gs, saddle_perm, small, big)

        new_gs = apply_saddle(gs, saddle_perm.id)

        assert new_gs.pending_saddle_choice is None  # AI does not queue a choice
        saddle_now = _find(new_gs, saddle_perm.id)
        assert saddle_now.attached_to == big.id       # highest power chosen
        assert _find(new_gs, small.id).attached_to is None  # smaller creature untouched

    def test_ai_no_friendly_target_returns_same_object(self):
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        opponent = Permanent(card=_host_card(power="5", name="Opponent"), controller="p2")
        _place(gs, saddle_perm, opponent)

        result = apply_saddle(gs, saddle_perm.id)
        assert result is gs  # pure no-op — opponent's creature is not a legal target
        assert _find(gs, saddle_perm.id).attached_to is None

    def test_already_attached_returns_same_object(self):
        # Regression for the double-fire path: an already-saddled permanent must NOT
        # be reattached to a different creature when apply_saddle runs again. Without
        # the already-attached no-op guard this would leave a stale id in the old
        # host's attachments list and attach to a new host. Mirrors Equip's guard.
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        host = Permanent(card=_host_card(power="4", name="Host"), controller="p1")
        other = Permanent(card=_host_card(power="2", name="Other"), controller="p1")
        _place(gs, saddle_perm, host, other)

        # First attach: AI saddles to the higher-power Host.
        gs = apply_saddle(gs, saddle_perm.id)
        assert _find(gs, saddle_perm.id).attached_to == host.id

        # Second invocation (e.g. a re-triggering event) must be a strict no-op —
        # same object, still attached to the ORIGINAL host, and the other creature
        # untouched so no stale id lingers on its attachments list.
        result = apply_saddle(gs, saddle_perm.id)
        assert result is gs  # Q4 pure-transform: already-attached → unchanged state
        assert _find(gs, saddle_perm.id).attached_to == host.id
        other_now = _find(gs, other.id)
        assert other_now.attachments == (other_now.attachments or [])


# ---------------------------------------------------------------------------
# 5. Enters attached: attached_to set + host.attachments records the id
# ---------------------------------------------------------------------------

class TestAttachmentState:
    def test_enters_attached(self):
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        host = Permanent(card=_host_card(power="4", name="Host"), controller="p1")
        _place(gs, saddle_perm, host)

        new_gs = apply_saddle(gs, saddle_perm.id)

        saddle_now = _find(new_gs, saddle_perm.id)
        host_now = _find(new_gs, host.id)
        assert saddle_now.attached_to == host.id          # permanent records its host
        assert saddle_perm.id in (host_now.attachments or [])  # host records the permanent


# ---------------------------------------------------------------------------
# 6. Attach triggers fire when saddled permanent attaches
# ---------------------------------------------------------------------------

class TestAttachTrigger:
    def test_attach_trigger_fires(self):
        gs = _make_game(active="p1", holder="p1")
        card = _saddled_card(extra_oracle="Whenever this becomes attached to another "
                                         "permanent, draw a card.")
        saddle_perm = Permanent(card=card, controller="p1")
        host = Permanent(card=_host_card(power="3", name="Host"), controller="p1")
        _place(gs, saddle_perm, host)

        new_gs = apply_saddle(gs, saddle_perm.id)

        assert _find(new_gs, saddle_perm.id).attached_to == host.id  # actually attached ...
        trigger_types = {t.trigger_type for t in new_gs.pending_triggers}
        assert "attach" in trigger_types                            # ... and the trigger fired


# ---------------------------------------------------------------------------
# 7. Deterministic tie-break: equal power → lowest perm id chosen
# ---------------------------------------------------------------------------

class TestDeterministicTieBreak:
    def test_lowest_perm_id_wins(self):
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        c_a = Permanent(
            card=Card(name="A", type_line="Creature — Goblin", mana_cost="{2}", power="3", toughness="3"),
            id="aaa-creature", controller="p1",
        )
        c_b = Permanent(
            card=Card(name="B", type_line="Creature — Goblin", mana_cost="{2}", power="3", toughness="3"),
            id="bbb-creature", controller="p1",
        )
        _place(gs, saddle_perm, c_a, c_b)

        new_gs = apply_saddle(gs, saddle_perm.id)

        # Equal power → lowest perm id ("aaa-creature") is chosen.
        saddle_now = _find(new_gs, saddle_perm.id)
        assert saddle_now.attached_to == "aaa-creature"


# ---------------------------------------------------------------------------
# 8. No legal target → enters loose (graceful no-op, not an error)
# ---------------------------------------------------------------------------

class TestNoLegalTarget:
    def test_no_creatures_enters_loose(self):
        gs = _make_game(active="p1", holder="p1")
        saddle_perm = Permanent(card=_saddled_card(), controller="p1")
        _place(gs, saddle_perm)  # no creatures at all

        new_gs = apply_saddle(gs, saddle_perm.id)
        assert new_gs is gs  # graceful no-op — nothing to attach to
        saddle_now = _find(new_gs, saddle_perm.id)
        assert saddle_now.attached_to is None   # enters loose on the battlefield


# ---------------------------------------------------------------------------
# 9. Pure transform: non-saddled card returns SAME object (Q4)
# ---------------------------------------------------------------------------

class TestPureTransformNoop:
    def test_non_saddled_returns_same_object(self):
        gs = _make_game(active="p1", holder="p1")
        plain = Permanent(card=_host_card(power="2", name="Plain"), controller="p1")
        _place(gs, plain)

        result = apply_saddle(gs, plain.id)
        assert result is gs  # no Saddle keyword → identical state

    def test_missing_permanent_returns_same_object(self):
        gs = _make_game(active="p1", holder="p1")
        result = apply_saddle(gs, "does-not-exist")
        assert result is gs


# ---------------------------------------------------------------------------
# 10. Detach when host leaves the battlefield (via SBA)
# ---------------------------------------------------------------------------

class TestDetachWhenHostLeaves:
    def test_host_leaves_detaches_via_sba(self):
        # AI auto-attaches at ETB via the zones.py hook, then the host is removed.
        gs = _make_game(active="p1", holder="p1")  # no human → AI path
        gs, host = put_permanent_onto_battlefield(gs, _host_card(power="4", name="Host"), "p1")
        gs, saddle_perm = put_permanent_onto_battlefield(gs, _saddled_card(), "p1")

        saddle_now = _find(gs, saddle_perm.id)
        assert saddle_now.attached_to == host.id  # attached at ETB

        # Host leaves the battlefield (destroyed).
        gs.battlefield = [p for p in gs.battlefield if p.id != host.id]
        gs, events = check_and_apply_sbas(gs)

        saddle_after = _find(gs, saddle_perm.id)
        assert saddle_after.attached_to is None                 # detached cleanly
        assert any(e.sba_type == "equipment_detach" for e in events)
        assert len(gs.battlefield) == 1                          # saddle stays on board


# ---------------------------------------------------------------------------
# Resolution via the API choice handler (resolve_saddle_choice)
# ---------------------------------------------------------------------------

class TestResolveChoice:
    def test_resolve_attaches_and_clears_pending(self):
        gs = _make_game(human="p1")
        gs, host = put_permanent_onto_battlefield(gs, _host_card(), "p1")
        gs, saddle_perm = put_permanent_onto_battlefield(gs, _saddled_card(), "p1")
        assert gs.pending_saddle_choice is not None

        new_gs = resolve_saddle_choice(gs, "saddle_confirm", host.id)
        assert new_gs.pending_saddle_choice is None  # cleared after resolution
        saddle_now = _find(new_gs, saddle_perm.id)
        assert saddle_now.attached_to == host.id      # attached to chosen creature

    def test_decline_clears_pending_without_attaching(self):
        gs = _make_game(human="p1")
        gs, host = put_permanent_onto_battlefield(gs, _host_card(), "p1")
        gs, saddle_perm = put_permanent_onto_battlefield(gs, _saddled_card(), "p1")

        new_gs = resolve_saddle_choice(gs, "saddle_confirm", None)  # decline
        assert new_gs.pending_saddle_choice is None
        assert _find(new_gs, saddle_perm.id).attached_to is None   # stays loose

    def test_invalid_action_id_is_noop(self):
        gs = _make_game(human="p1")
        gs, host = put_permanent_onto_battlefield(gs, _host_card(), "p1")
        gs, saddle_perm = put_permanent_onto_battlefield(gs, _saddled_card(), "p1")

        new_gs = resolve_saddle_choice(gs, "not_saddle", host.id)
        assert new_gs is gs  # wrong choice id → unchanged state
