"""
Ward-on-abilities (CR 702.145a) — API-level tests via the REAL /activate endpoint.

Ward fires whenever a permanent becomes the target of a spell **or ability**.
This file closes the ability half of the contract through the real HTTP surface:

* an AI opponent activating a targeting ability (regen) at a ward permanent it
  CAN pay for → ward cost paid, the effect applies (AI proceeds),
* an AI opponent activating a targeting ability it CANNOT pay for → the ability
  is countered: the effect does NOT apply (no regen shield), while the
  activation cost (tap + mana) is still consumed,
* a human activating a targeting ability at an opponent's ward permanent →
  ``pending_ward_payment`` is queued with ``targeting_type="ability"`` plus the
  deferred activation, and the effect is NOT applied yet; legal actions offer
  ``ward_pay``/``ward_counter`` (NO pass),
* human ``ward_pay`` (affordable) → ward cost paid AND the deferred effect
  applies; pending cleared,
* human ``ward_pay`` (unaffordable) → 422 INSUFFICIENT_MANA, pending KEPT,
* human ``ward_counter`` → pending cleared, effect never applied, no stack
  change,
* self-targeting (CR 702.145b) → no Ward trigger, effect applies normally,
* non-ward targets and non-ward activations (mana ability) → unchanged
  behavior (regression guard for the extracted effect helper).
"""
import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.models.game import Card, ManaPool, Phase, Step

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()
    yield
    mgr._games.clear()
    mgr._recorders.clear()


def _ward_card() -> Card:
    """An opponent-style ward permanent (Ward {2}, the story's example cost)."""
    return Card(
        name="Silver Scourge",
        mana_cost="{1}{G}",
        type_line="Legendary Creature — Elemental Wolf",
        power="2",
        toughness="2",
        keywords=["ward"],
        oracle_text="Ward {2}",
    )


def _plain_creature_card() -> Card:
    return Card(
        name="Test Bear",
        mana_cost="{1}{G}",
        type_line="Creature — Bear",
        power="2",
        toughness="2",
    )


def _regen_source_card(cost: str = "{T}") -> Card:
    """A creature with a tap-activated 'Regenerate target creature.' ability."""
    return Card(
        name="Regen Shaman",
        mana_cost="{1}{G}",
        type_line="Creature — Human Shaman",
        power="2",
        toughness="2",
        oracle_text=f"{cost}: Regenerate target creature.",
    )


def _regen_self_card() -> Card:
    """A ward creature that can regenerate itself (CR 702.145b self-target)."""
    return Card(
        name="Ward Regenerist",
        mana_cost="{1}{G}",
        type_line="Creature — Elemental",
        power="2",
        toughness="2",
        keywords=["ward"],
        oracle_text="Ward {2}\n{T}: Regenerate this permanent.",
    )


def _mana_source_card() -> Card:
    return Card(
        name="Mana Tapir",
        mana_cost="{1}{G}",
        type_line="Creature — Tapir",
        power="1",
        toughness="1",
        oracle_text="{T}: Add {G} to your mana pool.",
    )


def _create_game(
    human: str | None,
    activator: str = "p1",
    ward_controller: str | None = None,
    activator_pool: ManaPool | None = None,
    source_card: Card | None = None,
    target_card: Card | None = None,
    target_controller: str | None = None,
) -> tuple[str, str, str | None]:
    """Create a main-phase game with the source creature under ``activator``'s
    control and (optionally) a ward/plain target on the battlefield.

    ``ward_controller=None`` means no second creature is placed (target_card is
    ignored). Returns (game_id, source_perm_id, target_perm_id | None).
    """
    resp = client.post(
        "/game",
        json={
            "player1_name": "p1",
            "player2_name": "p2",
            "deck1": ["Forest"] * 60,
            "deck2": ["Forest"] * 60,
            "seed": 11,
        },
    )
    assert resp.status_code == 200, resp.text
    game_id = resp.json()["data"]["game_id"]

    mgr = get_manager()
    gs = mgr._games[game_id]

    players = list(gs.players)
    if activator_pool is not None:
        idx = 0 if activator == "p1" else 1
        players[idx] = players[idx].model_copy(update={"mana_pool": activator_pool})

    gs = gs.model_copy(
        update={
            "players": players,
            "human_player_name": human,
            "phase": Phase.PRECOMBAT_MAIN,
            "step": Step.MAIN,
            "priority_holder": activator,
            "active_player": activator,
            "mulligan_phase_active": False,
        }
    )

    src = source_card if source_card is not None else _regen_source_card()
    gs, src_perm = put_permanent_onto_battlefield(gs, src, activator, from_zone="hand")

    target_id = None
    if ward_controller is not None:
        tgt = target_card if target_card is not None else _ward_card()
        controller = target_controller or ward_controller
        gs, tgt_perm = put_permanent_onto_battlefield(gs, tgt, controller, from_zone="hand")
        target_id = tgt_perm.id

    mgr._games[game_id] = gs
    return game_id, src_perm.id, target_id


def _activate(game_id: str, perm_id: str, targets: list[str], mana_payment: dict | None = None):
    return client.post(
        f"/game/{game_id}/activate",
        json={
            "permanent_id": perm_id,
            "ability_index": 0,
            "targets": targets,
            "mana_payment": mana_payment or {},
        },
    )


def _gs(game_id: str):
    return get_manager()._games[game_id]


# ─── AI targeter: Ward auto-resolves by affordability ────────────────────────


def test_ai_activate_paid_ward_effect_applies():
    """AI can afford Ward {2}: pays it and the regen effect applies."""
    game_id, src_id, ward_id = _create_game(
        human="p1",
        activator="p2",
        ward_controller="p1",
        source_card=_regen_source_card(cost="{T}{1}"),
        activator_pool=ManaPool(C=3),  # {T}{1} activation + Ward {2}
    )
    resp = _activate(game_id, src_id, [ward_id], mana_payment={"C": 1})
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None  # auto-resolved, nothing pending
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 1  # effect applied
    src = next(p for p in gs.battlefield if p.id == src_id)
    assert src.tapped  # activation cost consumed
    p2 = next(p for p in gs.players if p.name == "p2")
    assert p2.mana_pool.C == 0  # {1} activation + {2} ward


def test_ai_activate_unaffordable_ward_counters_effect():
    """AI cannot afford Ward {2}: the ability is countered — NO regen shield —
    but the activation cost (tap + mana) is still consumed."""
    game_id, src_id, ward_id = _create_game(
        human="p1",
        activator="p2",
        ward_controller="p1",
        source_card=_regen_source_card(cost="{T}{1}"),
        activator_pool=ManaPool(C=1),  # pays {T}{1} activation, cannot pay Ward {2}
    )
    resp = _activate(game_id, src_id, [ward_id], mana_payment={"C": 1})
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None  # resolved (countered), not queued
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 0  # effect NOT applied
    src = next(p for p in gs.battlefield if p.id == src_id)
    assert src.tapped  # tap cost consumed even though countered
    p2 = next(p for p in gs.players if p.name == "p2")
    assert p2.mana_pool.C == 0  # {1} activation cost consumed
    # Nothing went on the stack (inline ability) — and nothing to clean up.
    assert gs.stack == []


def test_ai_activate_colored_ward_paid():
    """AI pays a colored ward cost ({G}) from its pool when affordable."""
    ward = Card(
        name="Green Warden",
        type_line="Creature — Elemental",
        power="2",
        toughness="2",
        keywords=["ward"],
        oracle_text="Ward {G}",
    )
    game_id, src_id, ward_id = _create_game(
        human="p1",
        activator="p2",
        ward_controller="p1",
        activator_pool=ManaPool(G=1),
        target_card=ward,
    )
    resp = _activate(game_id, src_id, [ward_id])
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None
    ward_perm = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward_perm.regen_shields == 1  # paid Ward {G} → effect applies
    p2 = next(p for p in gs.players if p.name == "p2")
    assert p2.mana_pool.G == 0


# ─── Human targeter: Ward defers until ward_pay / ward_counter ───────────────


def test_human_activate_queues_ability_ward_pending():
    """A human activating a targeting ability at an opponent's ward permanent
    queues pending_ward_payment tagged targeting_type='ability' with the
    deferred activation — and the effect is NOT applied yet."""
    game_id, src_id, ward_id = _create_game(
        human="p1",
        activator="p1",
        ward_controller="p2",
        activator_pool=ManaPool(C=2),
    )
    resp = _activate(game_id, src_id, [ward_id])
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    pending = gs.pending_ward_payment
    assert pending is not None
    # Existing keys (spell-path compatibility).
    assert pending["player"] == "p1"
    assert pending["ward_cost"] == "{2}"
    assert pending["targeting_spell_id"] == ""  # no StackObject for inline abilities
    assert pending["target_permanent_id"] == ward_id
    # Ability-case keys.
    assert pending["targeting_type"] == "ability"
    assert pending["permanent_id"] == src_id
    assert pending["ability_index"] == 0
    assert pending["targets"] == [ward_id]
    assert pending["mana_payment"] == {}
    assert pending["ability_text"] == "Regenerate target creature."
    # Effect NOT applied while the decision is outstanding.
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 0
    # Activation cost already consumed.
    src = next(p for p in gs.battlefield if p.id == src_id)
    assert src.tapped
    assert gs.stack == []


def test_human_activate_ward_legal_actions_no_pass():
    """While the ability ward is pending, legal actions offer ward_pay and
    ward_counter — NO pass (Ward is mandatory, CR 702.145a)."""
    game_id, src_id, ward_id = _create_game(
        human="p1", activator="p1", ward_controller="p2", activator_pool=ManaPool(C=2),
    )
    _activate(game_id, src_id, [ward_id])

    la = client.get(f"/game/{game_id}/legal-actions")
    assert la.status_code == 200, la.text
    actions = la.json()["data"]["legal_actions"]
    names = [a.get("card_name") for a in actions]
    assert "ward_pay" in names
    assert "ward_counter" in names
    assert not any(a.get("action_type") == "pass" for a in actions)


def test_human_ward_pay_reapplies_deferred_effect():
    """ward_pay (affordable): ward cost deducted AND the deferred regen effect
    applies; pending cleared."""
    game_id, src_id, ward_id = _create_game(
        human="p1", activator="p1", ward_controller="p2", activator_pool=ManaPool(C=2),
    )
    _activate(game_id, src_id, [ward_id])

    resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_pay"})
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 1  # deferred effect applied
    p1 = next(p for p in gs.players if p.name == "p1")
    assert p1.mana_pool.C == 0  # Ward {2} paid
    assert gs.stack == []


def test_human_ward_pay_unaffordable_keeps_pending():
    """ward_pay with insufficient mana: 422 INSUFFICIENT_MANA and the pending
    ability ward is KEPT (the player must then pick ward_counter)."""
    game_id, src_id, ward_id = _create_game(
        human="p1", activator="p1", ward_controller="p2", activator_pool=ManaPool(C=1),
    )
    _activate(game_id, src_id, [ward_id])

    resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_pay"})
    assert resp.status_code == 422, resp.text
    assert "INSUFFICIENT_MANA" in resp.text

    gs = _gs(game_id)
    pending = gs.pending_ward_payment
    assert pending is not None  # KEPT — decision still outstanding
    assert pending["targeting_type"] == "ability"
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 0  # effect still not applied
    p1 = next(p for p in gs.players if p.name == "p1")
    assert p1.mana_pool.C == 1  # nothing deducted


def test_human_ward_counter_no_effect_no_stack_change():
    """ward_counter: pending cleared, effect never applied, no stack change."""
    game_id, src_id, ward_id = _create_game(
        human="p1", activator="p1", ward_controller="p2", activator_pool=ManaPool(C=2),
    )
    _activate(game_id, src_id, [ward_id])

    resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_counter"})
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None
    ward = next(p for p in gs.battlefield if p.id == ward_id)
    assert ward.regen_shields == 0  # effect NOT applied
    assert gs.stack == []  # inline ability — nothing to remove


# ─── Negative tests (Q1): no trigger where Ward must not fire ────────────────


def test_self_targeting_ward_no_trigger():
    """CR 702.145b: a player regenerating their OWN ward creature never
    triggers Ward — no pending, effect applies normally."""
    src = _regen_self_card()
    game_id, src_id, _ = _create_game(
        human="p1", activator="p1", ward_controller=None,
        source_card=src, activator_pool=ManaPool(C=2),
    )
    resp = _activate(game_id, src_id, [])
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None  # self-targeting: no Ward trigger
    src_perm = next(p for p in gs.battlefield if p.id == src_id)
    assert src_perm.regen_shields == 1  # effect applies normally
    assert src_perm.tapped


def test_non_ward_target_no_trigger():
    """Targeting a creature WITHOUT Ward never queues a ward — normal regen."""
    game_id, src_id, bear_id = _create_game(
        human="p1",
        activator="p1",
        ward_controller="p2",
        target_card=_plain_creature_card(),
        activator_pool=ManaPool(C=2),
    )
    resp = _activate(game_id, src_id, [bear_id])
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None
    bear = next(p for p in gs.battlefield if p.id == bear_id)
    assert bear.regen_shields == 1


def test_mana_ability_activation_regression():
    """Regression: a mana ability activation still resolves immediately
    (extracted effect helper preserves non-ward behavior)."""
    game_id, src_id, _ = _create_game(
        human="p1",
        activator="p1",
        ward_controller=None,
        source_card=_mana_source_card(),
        activator_pool=ManaPool(G=0),
    )
    resp = _activate(game_id, src_id, [])
    assert resp.status_code == 200, resp.text

    gs = _gs(game_id)
    assert gs.pending_ward_payment is None
    p1 = next(p for p in gs.players if p.name == "p1")
    assert p1.mana_pool.G == 1  # {G} added
    src = next(p for p in gs.battlefield if p.id == src_id)
    assert src.tapped
