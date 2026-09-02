"""API e2e tests for the Fortify keyword (CR 702.54a).

Covers: play-land with a Fortification (it's a land), legal actions
(play_land + activate with valid_targets), and /activate Fortify success,
dry_run, and 422 failure paths (invalid target, wrong timing, unaffordable).

Real card fixtures: Darksteel Garrison ("Fortify {3}") and C.A.M.P.
("Fortify {2}{G}").
"""
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.models.game import Card, ManaPool, Phase, Step

client = TestClient(app)

GARRISON_ORACLE = (
    "Fortify {3} ({3}: Attach to target land you control. "
    "Fortify only as a sorcery. This card enters unattached and stays on the "
    "battlefield if the land leaves.)"
)
CAMP_ORACLE = (
    "Fortify {2}{G} ({2}{G}: Attach to target land you control. "
    "Fortify only as a sorcery. C.A.M.P. can't be attacked. As long as C.A.M.P. "
    "is attached, it doesn't have base abilities or rules text.)"
)


def _garrison_card(name="Darksteel Garrison") -> Card:
    return Card(name=name, type_line="Artifact Creature — Fortification", oracle_text=GARRISON_ORACLE)


def _forest_card(name="Test Forest") -> Card:
    return Card(name=name, type_line="Basic Land — Forest")


def _clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()


@pytest.fixture(autouse=True)
def clear_games_fixture():
    _clear_games()
    yield
    _clear_games()


def _create_fortify_game(hand_cards=None, pool=None, step=Step.MAIN, phase=Phase.PRECOMBAT_MAIN):
    """Create a game in p1's main phase with the given cards in p1's hand.

    Returns (game_id, card_ids_in_hand).
    """
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Forest"] * 60,
        "deck2": ["Forest"] * 60,
        "seed": 42,
    })
    assert resp.status_code == 200
    game_id = resp.json()["data"]["game_id"]

    mgr = get_manager()
    gs = mgr._games[game_id]
    hand = hand_cards if hand_cards is not None else [_garrison_card(), _forest_card()]
    p1 = gs.players[0].model_copy(update={
        "hand": hand,
        "mana_pool": pool if pool is not None else ManaPool(C=3),
    })
    players = [p1, gs.players[1]]
    gs = gs.model_copy(update={
        "players": players,
        "human_player_name": "p1",
        "step": step,
        "phase": phase,
        "active_player": "p1",
        "priority_holder": "p1",
        "mulligan_phase_active": False,
    })
    mgr._games[game_id] = gs
    return game_id, [c.id for c in hand]


def _put_on_battlefield(game_id, card, controller="p1"):
    """Put a card onto the battlefield directly; returns the permanent id."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    gs, perm = put_permanent_onto_battlefield(gs, card, controller, from_zone="hand")
    mgr._games[game_id] = gs
    return perm.id


def _get_gs(game_id):
    return get_manager()._games[game_id]


# ─── Play land ───────────────────────────────────────────────────────────────

def test_fortification_can_be_played_as_land():
    """A Fortification is a land (CR 301.7) — playable as a land drop."""
    game_id, card_ids = _create_fortify_game()
    resp = client.post(f"/game/{game_id}/play-land", json={"card_id": card_ids[0]})
    assert resp.status_code == 200
    gs = _get_gs(game_id)
    battlefield_names = [p.card.name for p in gs.battlefield]
    assert "Darksteel Garrison" in battlefield_names
    p1 = gs.players[0]
    assert p1.lands_played_this_turn == 1


def test_legal_actions_include_play_land_for_fortification():
    game_id, card_ids = _create_fortify_game()
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200
    actions = resp.json()["data"]["legal_actions"]
    play_land = [a for a in actions if a.get("action_type") == "play_land"]
    names = {a.get("card_name") for a in play_land}
    assert "Darksteel Garrison" in names
    assert "Test Forest" in names


def test_one_land_per_turn_includes_fortification():
    """Playing a Fortification consumes the one-land-per-turn rule."""
    game_id, card_ids = _create_fortify_game()
    resp = client.post(f"/game/{game_id}/play-land", json={"card_id": card_ids[0]})
    assert resp.status_code == 200
    # Now try to play the Forest — must be rejected
    resp2 = client.post(f"/game/{game_id}/play-land", json={"card_id": card_ids[1]})
    assert resp2.status_code == 422


# ─── Legal actions: activate with valid_targets ──────────────────────────────

def test_legal_actions_include_fortify_activate_with_targets():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200
    actions = resp.json()["data"]["legal_actions"]
    fortify = [
        a for a in actions
        if a.get("action_type") == "activate" and a.get("permanent_id") == garrison_id
    ]
    assert len(fortify) == 1
    assert fortify[0]["valid_targets"] == [forest_id]
    assert "Fortify" in fortify[0]["description"]


def test_legal_actions_fortify_with_no_valid_target_absent():
    """No Fortify action is offered when there is no valid target land."""
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    _put_on_battlefield(game_id, Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2"))
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200
    actions = resp.json()["data"]["legal_actions"]
    fortify = [
        a for a in actions
        if a.get("action_type") == "activate" and a.get("permanent_id") == garrison_id
    ]
    assert fortify == []


def test_legal_actions_fortify_absent_when_unaffordable():
    """Fortify action is not offered when the cost can't be paid."""
    game_id, _ = _create_fortify_game(hand_cards=[], pool=ManaPool())
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    _put_on_battlefield(game_id, _forest_card())
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200
    actions = resp.json()["data"]["legal_actions"]
    fortify = [
        a for a in actions
        if a.get("action_type") == "activate" and a.get("permanent_id") == garrison_id
    ]
    assert fortify == []


def test_legal_actions_fortify_absent_wrong_timing():
    """Fortify (sorcery-speed) is not offered outside the main phase."""
    game_id, _ = _create_fortify_game(hand_cards=[], step=Step.COMBAT_DAMAGE, phase=Phase.COMBAT)
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    _put_on_battlefield(game_id, _forest_card())
    resp = client.get(f"/game/{game_id}/legal-actions")
    assert resp.status_code == 200
    actions = resp.json()["data"]["legal_actions"]
    fortify = [
        a for a in actions
        if a.get("action_type") == "activate" and a.get("permanent_id") == garrison_id
    ]
    assert fortify == []


# ─── /activate success ───────────────────────────────────────────────────────

def test_activate_fortify_success():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [forest_id],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 200
    gs = _get_gs(game_id)
    garrison = next(p for p in gs.battlefield if p.id == garrison_id)
    forest = next(p for p in gs.battlefield if p.id == forest_id)
    assert garrison.attached_to == forest_id
    assert garrison_id in forest.attachments
    p1 = gs.players[0]
    assert p1.mana_pool.C == 0


def test_activate_fortify_colored_cost():
    """C.A.M.P.: Fortify {2}{G} paid from a colored pool."""
    game_id, _ = _create_fortify_game(hand_cards=[], pool=ManaPool(G=1, C=2))
    camp_id = _put_on_battlefield(game_id, Card(name="C.A.M.P.", type_line="Artifact Creature — Fortification", oracle_text=CAMP_ORACLE))
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": camp_id,
        "ability_index": 0,
        "targets": [forest_id],
        "mana_payment": {"G": 1, "C": 2},
    })
    assert resp.status_code == 200
    gs = _get_gs(game_id)
    camp = next(p for p in gs.battlefield if p.id == camp_id)
    assert camp.attached_to == forest_id
    p1 = gs.players[0]
    assert p1.mana_pool.G == 0
    assert p1.mana_pool.C == 0


def test_activate_fortify_dry_run_does_not_change_state():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [forest_id],
        "mana_payment": {"C": 3},
        "dry_run": True,
    })
    assert resp.status_code == 200
    gs = _get_gs(game_id)
    garrison = next(p for p in gs.battlefield if p.id == garrison_id)
    assert garrison.attached_to is None
    assert gs.players[0].mana_pool.C == 3  # unchanged


# ─── /activate 422 failure paths ─────────────────────────────────────────────

def test_activate_fortify_invalid_target_not_land():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    bear_id = _put_on_battlefield(game_id, Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2"))
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [bear_id],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 422
    gs = _get_gs(game_id)
    garrison = next(p for p in gs.battlefield if p.id == garrison_id)
    assert garrison.attached_to is None  # state unchanged


def test_activate_fortify_invalid_target_opponents_land():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    enemy_forest_id = _put_on_battlefield(game_id, _forest_card(name="Enemy Forest"), controller="p2")
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [enemy_forest_id],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 422


def test_activate_fortify_invalid_target_self():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [garrison_id],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 422


def test_activate_fortify_missing_target():
    game_id, _ = _create_fortify_game(hand_cards=[])
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 422


def test_activate_fortify_wrong_timing():
    """Fortify only as a sorcery — rejected during the combat damage step."""
    game_id, _ = _create_fortify_game(
        hand_cards=[], step=Step.COMBAT_DAMAGE, phase=Phase.COMBAT,
    )
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [forest_id],
        "mana_payment": {"C": 3},
    })
    assert resp.status_code == 422
    gs = _get_gs(game_id)
    garrison = next(p for p in gs.battlefield if p.id == garrison_id)
    assert garrison.attached_to is None


def test_activate_fortify_unaffordable():
    """Empty pool + empty payment → 422, state unchanged."""
    game_id, _ = _create_fortify_game(hand_cards=[], pool=ManaPool())
    garrison_id = _put_on_battlefield(game_id, _garrison_card())
    forest_id = _put_on_battlefield(game_id, _forest_card())
    resp = client.post(f"/game/{game_id}/activate", json={
        "permanent_id": garrison_id,
        "ability_index": 0,
        "targets": [forest_id],
        "mana_payment": {},
    })
    assert resp.status_code == 422
    gs = _get_gs(game_id)
    garrison = next(p for p in gs.battlefield if p.id == garrison_id)
    assert garrison.attached_to is None
