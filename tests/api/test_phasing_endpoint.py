"""API e2e tests for Phasing legal-action exclusion and cast rejection (CR 702.26).

Covers the two code-review findings that were missing:

* ``GET /legal-actions`` must never offer a phased-out permanent as a spell target,
  attacker, or blocker. While phased out a permanent is treated as though it does
  not exist (US15 / CR 702.26a), so the legal-action enumeration in
  ``mtg_engine/api/routers/game.py`` must skip it everywhere.
* ``POST /cast`` against a phased-out permanent is rejected at runtime with a
  ``ValueError`` before the spell is built on the stack (US15).

Each test phases out a creature by driving the *real* untap-step hook in
``turn_manager.begin_step()`` (CR 702.26 ordering: phase-in at start of untap,
phase-out at end), then asserts the exclusion through the live HTTP endpoints via
``TestClient(app)`` — not by calling engine internals directly.
"""
import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.engine.turn_manager import begin_step
from mtg_engine.models.game import Card, ManaPool, Phase, Permanent, Step
from mtg_engine.ability.keywords.phasing import is_phased_out

client = TestClient(app)


# ─── Fixtures / helpers ──────────────────────────────────────────────────────

def _clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()


@pytest.fixture(autouse=True)
def clear_games_fixture():
    """Reset the in-memory game manager before and after every test."""
    _clear_games()
    yield
    _clear_games()


def _make_game():
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Forest"] * 60,
        "deck2": ["Forest"] * 60,
        "seed": 7,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["game_id"]


def _phasing_perm(name="Dread Statuary", controller="p1"):
    """A permanent carrying the Phasing keyword (CR 702.26)."""
    card = Card(
        name=name,
        type_line="Artifact Creature — Golem",
        oracle_text="3/3. Phasing.\nWhenever this phases in, draw a card.",
        mana_cost="{4}",
        power="3",
        toughness="3",
    )
    return Permanent(card=card, controller=controller)


def _plain_perm(name="Bear", power="2", toughness="2", controller="p1"):
    card = Card(
        name=name, type_line="Creature — Bear", mana_cost="{1}",
        power=power, toughness=toughness,
    )
    return Permanent(card=card, controller=controller)


GIANT_GROWTH = Card(
    name="Giant Growth",
    type_line="Sorcery",
    oracle_text="Target creature gets +3/+3 until end of turn.",
    mana_cost="{R}",
)

LIGHTNING_BOLT = Card(
    name="Lightning Bolt",
    type_line="Instant",
    oracle_text="Deal 3 damage to any target.",
    mana_cost="{R}",
)


def _place_permanents(game_id, *perms):
    """Overwrite the battlefield directly (mirrors engine test helpers)."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    gs.battlefield = list(perms)
    mgr._games[game_id] = gs


def _hand_and_mana(game_id, cards=None, mana=None):
    """Set p1's hand and/or mana pool (both live on PlayerState)."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    updates = {}
    new_p1 = gs.players[0]
    if cards is not None:
        new_p1 = new_p1.model_copy(update={"hand": list(cards)})
    if mana is not None:
        new_p1 = new_p1.model_copy(update={"mana_pool": mana})
    players = list(gs.players)
    players[0] = new_p1
    updates["players"] = players
    mgr._games[game_id] = gs.model_copy(update=updates)


def _phase_out_via_untap(game_id):
    """Phase out p1's phasing permanents by running the untap-step hook."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    gs = gs.model_copy(
        update={"step": Step.UNTAP, "active_player": "p1", "priority_holder": "p1"}
    )
    mgr._games[game_id] = gs
    # begin_step(UNTAP): phase-in (none) -> untap p1's creatures -> phase-out.
    gs = begin_step(gs)
    mgr._games[game_id] = gs


def _advance_to(game_id, step=Step.MAIN, phase=Phase.PRECOMBAT_MAIN, active="p1", holder="p1"):
    """Move the game into a queryable step/phase (read-only legal-actions)."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    mgr._games[game_id] = gs.model_copy(
        update={"step": step, "phase": phase, "active_player": active,
                "priority_holder": holder, "mulligan_phase_active": False}
    )


def _legal_actions(game_id):
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["legal_actions"]


# ─── Issue 1: spell-target exclusion ─────────────────────────────────────────

def test_phased_out_excluded_from_spell_targets():
    """A phased-out creature is not offered as a spell target (CR 702.26a)."""
    game_id = _make_game()
    bear = _plain_perm("Bear")
    phasing = _phasing_perm("Dread Statuary")

    _place_permanents(game_id, bear, phasing)
    _hand_and_mana(game_id, cards=[GIANT_GROWTH], mana=ManaPool(R=1))
    _phase_out_via_untap(game_id)  # untap hook phases out the Golem only

    assert is_phased_out(get_manager()._games[game_id], phasing.id) is True
    _advance_to(game_id, step=Step.MAIN, phase=Phase.PRECOMBAT_MAIN)

    actions = _legal_actions(game_id)
    pump = next(
        a for a in actions
        if a.get("card_name") == "Giant Growth"
    )
    valid_targets = pump.get("valid_targets", [])
    # The untapped Bear is targetable; the phased-out Golem is not.
    assert bear.id in valid_targets
    assert phasing.id not in valid_targets


# ─── Issue 1: attacker exclusion ─────────────────────────────────────────────

def test_phased_out_cannot_be_declared_attacker():
    """A phased-out creature cannot be offered as an attacker (CR 702.26a)."""
    game_id = _make_game()
    bear = _plain_perm("Bear")
    phasing = _phasing_perm("Dread Statuary")

    # Both must be able to attack normally (no summoning sickness) except the
    # phased-out one, which is excluded by phase-out.
    bear.summoning_sick = False
    phasing.summoning_sick = False
    _place_permanents(game_id, bear, phasing)
    _phase_out_via_untap(game_id)

    assert is_phased_out(get_manager()._games[game_id], phasing.id) is True
    _advance_to(
        game_id, step=Step.DECLARE_ATTACKERS, phase=Phase.COMBAT, active="p1", holder="p1"
    )

    actions = _legal_actions(game_id)
    atk = next((a for a in actions if a.get("action_type") == "declare_attackers"), None)
    assert atk is not None  # the Bear should still be able to attack
    valid_targets = atk.get("valid_targets", [])
    assert bear.id in valid_targets
    assert phasing.id not in valid_targets


# ─── Issue 1: blocker exclusion ──────────────────────────────────────────────

def test_phased_out_cannot_be_declared_blocker():
    """A phased-out creature cannot be offered as a blocker (CR 702.26a)."""
    from mtg_engine.models.game import CombatState, AttackerInfo

    game_id = _make_game()
    # p1 controls an attacker; p2 controls one plain + one phased-out blocker.
    attacker = _plain_perm("Goblin", controller="p1")
    good_blocker = _plain_perm("Bear", controller="p2")
    bad_blocker = _phasing_perm("Dread Statuary", controller="p2")

    attacker.summoning_sick = False
    good_blocker.summoning_sick = False
    bad_blocker.summoning_sick = False
    _place_permanents(game_id, attacker, good_blocker, bad_blocker)

    # Phase out p2's Golem: run the untap hook while p2 is the active player.
    mgr = get_manager()
    gs = mgr._games[game_id]
    gs = gs.model_copy(
        update={"step": Step.UNTAP, "active_player": "p2", "priority_holder": "p2"}
    )
    mgr._games[game_id] = gs
    gs = begin_step(gs)  # p2 phases out its Golem at end of untap
    mgr._games[game_id] = gs

    assert is_phased_out(get_manager()._games[game_id], bad_blocker.id) is True

    # Combat has an attacker so declare-blockers can run; p2 is the defender.
    combat = CombatState(attackers=[AttackerInfo(permanent_id=attacker.id, defending_id="p2")])
    mgr._games[game_id] = mgr._games[game_id].model_copy(update={"combat": combat})
    _advance_to(game_id, step=Step.DECLARE_BLOCKERS, phase=Phase.COMBAT, active="p1", holder="p2")

    actions = _legal_actions(game_id)
    blk = next(
        a for a in actions if a.get("action_type") == "declare_blockers"
    )
    assert blk is not None  # the plain Bear should still be able to block
    valid_targets = blk.get("valid_targets", [])
    assert good_blocker.id in valid_targets
    assert bad_blocker.id not in valid_targets


# ─── Issue 2: cast rejection at runtime ──────────────────────────────────────

def test_cast_against_phased_out_target_is_rejected():
    """POST /cast targeting a phased-out permanent raises (HTTP 422)."""
    game_id = _make_game()
    phasing = _phasing_perm("Dread Statuary")

    _place_permanents(game_id, phasing)
    _hand_and_mana(game_id, cards=[LIGHTNING_BOLT], mana=ManaPool(R=1))
    _phase_out_via_untap(game_id)

    assert is_phased_out(get_manager()._games[game_id], phasing.id) is True
    _advance_to(game_id, step=Step.MAIN, phase=Phase.PRECOMBAT_MAIN)

    resp = client.post(
        f"/game/{game_id}/cast",
        json={
            "card_id": LIGHTNING_BOLT.id,
            "targets": [phasing.id],
            "mana_payment": {"R": 1},
        },
    )
    # The cast is rejected before the spell reaches the stack.
    assert resp.status_code == 422, resp.text
    assert "phased" in resp.text.lower()
    assert not any(s.source_card.name == "Lightning Bolt" for s in
                   get_manager()._games[game_id].stack)


def test_cast_against_live_target_succeeds():
    """Regression: casting at a non-phased-out creature still succeeds."""
    game_id = _make_game()
    bear = _plain_perm("Bear")

    _place_permanents(game_id, bear)
    _hand_and_mana(game_id, cards=[LIGHTNING_BOLT], mana=ManaPool(R=1))
    # No phase-out this turn — the Bear stays in play.
    _advance_to(game_id, step=Step.MAIN, phase=Phase.PRECOMBAT_MAIN)

    resp = client.post(
        f"/game/{game_id}/cast",
        json={
            "card_id": LIGHTNING_BOLT.id,
            "targets": [bear.id],
            "mana_payment": {"R": 1},
        },
    )
    assert resp.status_code == 200, resp.text
    assert any(s.source_card.name == "Lightning Bolt" for s in
               get_manager()._games[game_id].stack)
