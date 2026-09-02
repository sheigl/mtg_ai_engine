"""
7-17 Integration: cycling API endpoint (US9).

``tests/ability/keywords/test_cycle.py`` exercises the ENGINE-level type-cycling
logic directly. This file closes the gap by driving the REAL HTTP route
``POST /game/{game_id}/cycle`` end-to-end via ``TestClient(app)`` and asserting
the observable integration effects: the cycled card is discarded to the
graveyard, exactly one card is drawn through the engine draw path (so the Draw
Trigger fires), a cycle trigger is queued, and mana was required.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.models.game import Card, Permanent, Phase, Step, ManaPool

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()
    yield
    mgr._games.clear()
    mgr._recorders.clear()


_CYCLING_CARD = Card(
    name="Test Cyclist",
    id="card-cyclist",
    mana_cost="{1}",
    type_line="Instant",
    oracle_text="Deal 3 damage to any target. Cycling {1}{R}",
    controller="p1",
)


def _cycle_watcher():
    """A permanent controlled by the cycler whose oracle contains 'whenever you
    cycle' so check_cycle_triggers queues a 'cycle' trigger when p1 cycles."""
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(
            name="Twinblade",
            mana_cost="{2}",
            type_line="Creature — Warrior",
            oracle_text="Whenever you cycle a card, draw a card.",
            power="2",
            toughness="2",
        ),
        controller="p1",
    )


def _add_cycle_watcher(game_id: str):
    """Attach the cycle-trigger watcher to p1's battlefield before cycling."""
    mgr = get_manager()
    gs = mgr._games[game_id]
    gs.battlefield.append(_cycle_watcher())
    mgr._games[game_id] = gs


def _create_cycle_game():
    """Create a game and put the cycling card into p1's hand with enough mana."""
    resp = client.post(
        "/game",
        json={
            "player1_name": "p1",
            "player2_name": "p2",
            "deck1": ["Forest"] * 60,
            "deck2": ["Island"] * 60,
            "seed": 7,
        },
    )
    assert resp.status_code == 200, resp.text
    game_id = resp.json()["data"]["game_id"]

    mgr = get_manager()
    gs = mgr._games[game_id]

    players = list(gs.players)
    p1 = players[0].model_copy(update={"hand": [_CYCLING_CARD], "mana_pool": ManaPool(R=1, C=2)})
    players[0] = p1
    gs = gs.model_copy(
        update={
            "players": players,
            "human_player_name": "p1",
            "phase": Phase.PRECOMBAT_MAIN,
            "step": Step.MAIN,
            "priority_holder": "p1",
            "active_player": "p1",
            "mulligan_phase_active": False,
        }
    )
    mgr._games[game_id] = gs

    library_before = len(gs.players[0].library)
    return game_id, library_before


class TestCycleEndpoint:
    def test_cycle_discards_and_draws(self):
        """POST /cycle discards the card to graveyard and draws one card."""
        game_id, library_before = _create_cycle_game()

        resp = client.post(f"/game/{game_id}/cycle", json={"card_id": "card-cyclist"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        p1 = next(p for p in gs.players if p.name == "p1")

        # Card left the hand...
        assert all(c.id != "card-cyclist" for c in p1.hand)
        # ...and landed in the graveyard.
        assert any(c.id == "card-cyclist" for c in p1.graveyard)
        # ...and exactly one card was drawn (library shrank by one).
        assert len(p1.library) == library_before - 1

    def test_cycle_queues_cycle_trigger(self):
        """POST /cycle queues a 'cycle' trigger via check_cycle_triggers."""
        game_id, _ = _create_cycle_game()
        _add_cycle_watcher(game_id)

        resp = client.post(f"/game/{game_id}/cycle", json={"card_id": "card-cyclist"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        trigger_types = [t.trigger_type for t in gs.pending_triggers]
        assert "cycle" in trigger_types, (
            f"Cycling endpoint did not queue a cycle trigger; got {trigger_types}"
        )

    def test_cycle_requires_mana(self):
        """POST /cycle with insufficient mana is rejected (INVALID_ACTION)."""
        game_id, _ = _create_cycle_game()

        mgr = get_manager()
        gs = mgr._games[game_id]
        players = list(gs.players)
        p1 = players[0].model_copy(update={"mana_pool": ManaPool()})  # empty pool
        players[0] = p1
        mgr._games[game_id] = gs.model_copy(update={"players": players})

        resp = client.post(f"/game/{game_id}/cycle", json={"card_id": "card-cyclist"})
        # INVALID_ACTION maps to HTTP 422 for this route (see _err default status).
        assert resp.status_code == 422, resp.text
        assert "INVALID_ACTION" in resp.text

    def test_type_cycling_not_accepted_as_regular(self):
        """A 'Type cycling {2}' card is NOT cycled via POST /cycle as regular
        cycling (CR 702.46b). The live route must reject it with INVALID_ACTION,
        because cycle.py's detector rejects type-cycling as regular cycling."""
        resp = client.post(
            "/game",
            json={
                "player1_name": "p1",
                "player2_name": "p2",
                "deck1": ["Forest"] * 60,
                "deck2": ["Island"] * 60,
                "seed": 9,
            },
        )
        assert resp.status_code == 200, resp.text
        game_id = resp.json()["data"]["game_id"]

        mgr = get_manager()
        gs = mgr._games[game_id]

        type_cycling_card = Card(
            name="Type Cycler",
            id="card-typecyc",
            mana_cost="{1}",
            type_line="Instant — Sorcery",
            oracle_text="Type cycling {2}",
            controller="p1",
        )
        players = list(gs.players)
        p1 = players[0].model_copy(update={"hand": [type_cycling_card], "mana_pool": ManaPool(C=5)})
        players[0] = p1
        gs = gs.model_copy(
            update={
                "players": players,
                "human_player_name": "p1",
                "phase": Phase.PRECOMBAT_MAIN,
                "step": Step.MAIN,
                "priority_holder": "p1",
                "active_player": "p1",
                "mulligan_phase_active": False,
            }
        )
        mgr._games[game_id] = gs

        resp = client.post(f"/game/{game_id}/cycle", json={"card_id": "card-typecyc"})
        # NOT accepted as regular cycling: the route must reject it (422 INVALID_ACTION).
        assert resp.status_code == 422, resp.text
        assert "INVALID_ACTION" in resp.text
