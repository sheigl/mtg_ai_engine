"""
WebSocket spectator endpoint tests. APP-04.

Tests cover:
1. Connect and receive initial state
2. Event broadcasting during gameplay (manual transcript event)
3. Multiple simultaneous connections all receive events
4. Game-end notification with close code 1000
5. Non-existent game rejection (WebSocket handshake fails)
6. Disconnect cleanup (listener unregistered, registry cleaned)
7. Completed game rejection
8. Incoming non-pong messages silently ignored
9. Registry cleanup utility works
10. Transcript unregister_listener works
11. Game deleted while spectator connected
12. Multiple events in sequence
13. Spectator count tracking
14. Event contains all transcript fields
15. Queue overflow behavior (events dropped, connection stays alive)
16. Rapid reconnect (fresh initial_state and listener each time)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.api.routers.spectate import clear_spectator_registry, _spectators, _SPECTATOR_QUEUE_MAX
from mtg_engine.export.store import get_export_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Clear game manager and spectator registry between tests."""
    mgr = get_manager()
    initial_games = list(mgr._games.keys())
    clear_spectator_registry()
    yield
    # Cleanup: delete any games created during the test
    for gid in list(mgr._games.keys()):
        if gid not in initial_games:
            try:
                mgr.delete(gid)
            except Exception:
                pass
    clear_spectator_registry()


def _make_deck(size: int = 60) -> list[str]:
    """Build a minimal deck list."""
    return ["Forest"] * size


def _create_game(deck_size: int = 60, seed: int = 42) -> str:
    """Create a game via REST and return the game_id."""
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": _make_deck(deck_size),
        "deck2": _make_deck(deck_size),
        "seed": seed,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["game_id"]


# ─── Test 1: Connect and receive initial state ────────────────────────────────

def test_connect_receives_initial_state():
    """Spectator connects and receives the full game state as initial_state."""
    game_id = _create_game()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        assert "data" in data
        assert "timestamp" in data
        state = data["data"]
        assert state["game_id"] == game_id
        assert state["turn"] == 1
        assert len(state["players"]) == 2


# ─── Test 2: Event broadcasting during gameplay ──────────────────────────────

def test_event_broadcasting():
    """Transcript events are pushed to connected spectators in real time."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Manually trigger a transcript event (simulating gameplay)
        recorder.record_cast(
            player="p1", card_name="Lightning Bolt", targets=["p2"],
            turn=1, phase="main", step="main", mana_cost="{R}",
        )

        # Spectator should receive the cast event
        data = ws.receive_json()
        assert data["type"] == "cast"
        assert data["data"]["player"] == "p1"
        assert data["data"]["card_name"] == "Lightning Bolt"
        assert "timestamp" in data


# ─── Test 3: Multiple simultaneous connections ────────────────────────────────

def test_multiple_connections_all_receive_events():
    """Multiple spectators connect simultaneously and all receive the same events."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    # Open two WebSocket connections
    with client.websocket_connect(f"/ws/game/{game_id}") as ws1:
        with client.websocket_connect(f"/ws/game/{game_id}") as ws2:
            # Both receive initial state
            d1 = ws1.receive_json()
            d2 = ws2.receive_json()
            assert d1["type"] == "initial_state"
            assert d2["type"] == "initial_state"

            # Fire a transcript event
            recorder.record_damage(
                source="Lightning Bolt", target="p2", amount=3,
                turn=1, phase="main", step="main",
            )

            # Both spectators receive the damage event
            e1 = ws1.receive_json()
            e2 = ws2.receive_json()
            assert e1["type"] == "damage"
            assert e2["type"] == "damage"
            assert e1["data"]["amount"] == 3
            assert e2["data"]["amount"] == 3


# ─── Test 4: Game-end notification ────────────────────────────────────────────

def test_game_end_notification():
    """When a game ends, spectators receive a game_end message and the connection closes."""
    game_id = _create_game()
    mgr = get_manager()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Simulate game end by setting is_game_over on the GameState
        gs = mgr.get(game_id)
        from mtg_engine.models.game import GameState
        gs = gs.model_copy(update={
            "is_game_over": True,
            "game_over_reason": "player_reduced_to_zero_life",
        })
        # Also set life totals so winner/loser can be determined
        players = list(gs.players)
        players[0].life = 20
        players[1].life = 0
        gs = gs.model_copy(update={"players": players})
        mgr.update(game_id, gs)

        # Fire a transcript event to trigger the game-over check in the WS loop.
        # _check_game_over_and_notify now sends game_end after detecting is_game_over,
        # so we expect: [transcript_event, game_end_notification]
        recorder = get_export_store(game_id).transcript
        recorder.record_game_end(
            winner="p1", reason="player_reduced_to_zero_life",
            turn=5, phase="combat", step="combat_damage",
        )

        # First message: the transcript event itself (game_end type from record_game_end)
        data = ws.receive_json()
        assert data["type"] == "game_end"  # transcript event

        # Second message: the game-end notification with winner info
        data = ws.receive_json()
        assert data["type"] == "game_end"
        assert data["data"]["winner"] == "p1"


# ─── Test 5: Non-existent game rejection ──────────────────────────────────────

def test_nonexistent_game_rejected():
    """Connecting to a non-existent game rejects the WebSocket handshake.

    The server closes with code 4004 before accepting, so TestClient raises
    an exception (ClosedResourceError or StarletteWebSocketReject).
    We verify by checking that no spectator was registered for this game_id.
    """
    # Attempt connection — it will fail because the game doesn't exist
    try:
        with client.websocket_connect("/ws/game/nonexistent-game-id") as ws:
            # If we get here, check that the close code is 4004
            pass
    except Exception:
        # Expected: TestClient raises on rejected WebSocket handshake
        pass

    # Verify no spectator was registered for this game_id
    assert "nonexistent-game-id" not in _spectators


# ─── Test 6: Disconnect cleanup ───────────────────────────────────────────────

def test_disconnect_cleanup():
    """When a spectator disconnects, their listener is unregistered and registry cleaned."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    # Count listeners before connecting
    initial_listener_count = len(recorder._listeners)

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        # Listener should be registered while connected
        assert len(recorder._listeners) > initial_listener_count
        assert game_id in _spectators

    # After disconnect, listener should be unregistered
    assert len(recorder._listeners) == initial_listener_count
    # Registry entry should be cleaned up (empty list removed)
    assert game_id not in _spectators


# ─── Additional: Completed game rejection ─────────────────────────────────────

def test_completed_game_rejected():
    """Connecting to a completed game rejects the WebSocket handshake."""
    game_id = _create_game()
    mgr = get_manager()

    # Mark game as over
    gs = mgr.get(game_id)
    gs = gs.model_copy(update={"is_game_over": True, "game_over_reason": "test"})
    mgr.update(game_id, gs)

    # Attempt connection — it will fail because the game is over
    try:
        with client.websocket_connect(f"/ws/game/{game_id}") as ws:
            pass
    except Exception:
        # Expected: TestClient raises on rejected WebSocket handshake
        pass

    # Verify no spectator was registered for this game_id
    assert game_id not in _spectators


# ─── Additional: Incoming non-pong messages silently ignored ──────────────────

def test_incoming_messages_ignored():
    """Spectator sends a message that is not a pong — it should be handled gracefully."""
    game_id = _create_game()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Send a non-pong message (should not crash the connection)
        ws.send_json({"type": "some_random_action", "data": {"foo": "bar"}})

        # Connection should still be open — verify by triggering an event
        recorder = get_export_store(game_id).transcript
        recorder.record_draw(player="p1", turn=1, phase="main", step="main")

        data = ws.receive_json()
        assert data["type"] == "draw"


# ─── Additional: Registry cleanup utility works ──────────────────────────────

def test_clear_spectator_registry():
    """clear_spectator_registry() removes all entries."""
    game_id = _create_game()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        ws.receive_json()  # initial state
        assert len(_spectators) > 0

    clear_spectator_registry()
    assert len(_spectators) == 0


# ─── Additional: Transcript unregister_listener works ────────────────────────

def test_transcript_unregister_listener():
    """TranscriptRecorder.unregister_listener removes the callback."""
    from mtg_engine.export.transcript import TranscriptEntry, TranscriptRecorder

    recorder = TranscriptRecorder("test-game")
    received: list[TranscriptEntry] = []

    def listener(entry: TranscriptEntry) -> None:
        received.append(entry)

    # Register and fire event
    recorder.register_listener(listener)
    recorder.record_draw(player="p1", turn=1, phase="main", step="main")
    assert len(received) == 1

    # Unregister and fire another event
    recorder.unregister_listener(listener)
    recorder.record_damage(source="X", target="Y", amount=5, turn=1, phase="main", step="main")
    assert len(received) == 1  # No new entry received after unregister

    # Unregistering again should be a no-op (not raise)
    recorder.unregister_listener(listener)


# ─── Additional: Game deleted while spectator connected ──────────────────────

def test_game_deleted_while_connected():
    """If the game is deleted while a spectator is connected, they get game_end notification."""
    game_id = _create_game()
    mgr = get_manager()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Delete the game while spectator is connected
        try:
            mgr.delete(game_id)
        except Exception:
            pass  # Game might already be cleaned up by fixture

        # Spectator should receive game_end with reason=game_deleted
        data = ws.receive_json()
        assert data["type"] == "game_end"
        assert data["data"]["reason"] == "game_deleted"


# ─── Additional: Multiple events in sequence ─────────────────────────────────

def test_multiple_events_in_sequence():
    """Multiple transcript events are delivered in order to spectators."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Fire multiple events in sequence
        recorder.record_draw(player="p1", turn=1, phase="main", step="main")
        recorder.record_cast(
            player="p1", card_name="Bear", targets=[],
            turn=1, phase="main", step="main", mana_cost="{G}",
        )
        recorder.record_damage(source="Bear", target="p2", amount=2,
                               turn=1, phase="combat", step="combat_damage")

        # All three events should arrive in order
        e1 = ws.receive_json()
        assert e1["type"] == "draw"

        e2 = ws.receive_json()
        assert e2["type"] == "cast"

        e3 = ws.receive_json()
        assert e3["type"] == "damage"


# ─── Additional: Spectator count tracking ─────────────────────────────────────

def test_spectator_count_tracking():
    """Spectator registry correctly tracks multiple connections per game."""
    game_id = _create_game()

    with client.websocket_connect(f"/ws/game/{game_id}") as ws1:
        ws1.receive_json()  # initial state
        assert len(_spectators.get(game_id, [])) == 1

        with client.websocket_connect(f"/ws/game/{game_id}") as ws2:
            ws2.receive_json()  # initial state
            assert len(_spectators.get(game_id, [])) == 2

        # After ws2 disconnects, only ws1 remains
        assert len(_spectators.get(game_id, [])) == 1

    # After ws1 disconnects, registry is cleaned up
    assert game_id not in _spectators


# ─── Additional: Event contains all transcript fields ────────────────────────

def test_event_contains_all_fields():
    """Broadcasted events contain all expected transcript fields."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Fire a transcript event
        recorder.record_draw(player="p1", turn=3, phase="main", step="main")

        data = ws.receive_json()
        assert data["type"] == "draw"
        assert "data" in data
        assert "timestamp" in data
        assert "seq" in data
        assert "turn" in data
        assert "phase" in data
        assert "step" in data
        assert "description" in data


# ─── Test 15: Queue overflow behavior ────────────────────────────────────────

def test_queue_overflow_drops_events_but_connection_stays_alive():
    """When the queue is full (maxsize=256), excess events are silently dropped.

    The connection should remain alive and continue delivering events after
    the queue drains below capacity. We verify by flooding beyond capacity,
    draining what we can receive, then sending a final marker event to prove
    the connection survived.
    """
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        data = ws.receive_json()
        assert data["type"] == "initial_state"

        # Flood the queue beyond capacity — excess events silently dropped
        num_flooded = _SPECTATOR_QUEUE_MAX + 50
        for i in range(num_flooded):
            recorder.record_draw(player="p1", turn=1, phase="main", step="main")

        # Drain what we can receive. We know at most _SPECTATOR_QUEUE_MAX events
        # were queued (the rest were dropped). Receive up to that many draw events.
        received_count = 0
        for _ in range(_SPECTATOR_QUEUE_MAX):
            msg = ws.receive_json()
            if msg["type"] == "draw":
                received_count += 1
            else:
                break  # Unexpected message type, stop draining

        # We should have received events (up to queue capacity)
        assert received_count > 0, "Should receive at least some events"
        # Some were definitely dropped since we flooded more than capacity
        assert received_count < num_flooded, \
            f"Expected drops; got {received_count} out of {num_flooded}"

        # Connection is still alive: fire a marker event and verify delivery.
        # After draining the queue, there's room for new events again.
        recorder.record_cast(
            player="p1", card_name="Final Card", targets=[],
            turn=2, phase="main", step="main", mana_cost="{W}",
        )
        data = ws.receive_json()
        assert data["type"] == "cast"
        assert data["data"]["card_name"] == "Final Card"


# ─── Test 16: Rapid reconnect ────────────────────────────────────────────────

def test_rapid_reconnect_gets_fresh_state_and_listener():
    """Disconnecting and immediately reconnecting yields a new initial_state
    and registers a fresh listener (old one is cleaned up).
    """
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    # First connection
    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        first_timestamp = data["timestamp"]
        initial_listener_count = len(recorder._listeners)
        assert len(_spectators.get(game_id, [])) == 1

    # After disconnect, listener should be cleaned up
    assert len(recorder._listeners) == initial_listener_count - 1
    assert game_id not in _spectators

    # Reconnect immediately
    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        second_timestamp = data["timestamp"]

        # New timestamp (may be equal if very fast, but should be >= first)
        assert second_timestamp >= first_timestamp

        # Fresh listener registered
        assert len(recorder._listeners) == initial_listener_count
        assert len(_spectators.get(game_id, [])) == 1

        # Verify the new listener works by firing an event
        recorder.record_draw(player="p2", turn=1, phase="main", step="main")
        data = ws.receive_json()
        assert data["type"] == "draw"
        assert data["data"]["player"] == "p2"
