"""
WebSocket spectator endpoint for real-time game state streaming. APP-04.

Spectators connect via WS and receive:
  - initial_state on connect (full GameState dump)
  - transcript events as they happen (cast, resolve, damage, etc.)
  - game_end notification when the game finishes

Read-only — no game actions can be taken via WebSocket.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import get_export_store
from mtg_engine.export.transcript import TranscriptEntry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["spectate"])


# ── Constants ─────────────────────────────────────────────────────────────────

_SPECTATOR_QUEUE_MAX = 256       # Buffer for slow clients before dropping events
_IDLE_CHECK_INTERVAL_S = 1.0     # How often to check for game-end during idle periods


# ── Type aliases ──────────────────────────────────────────────────────────────

ListenerType = Callable[[TranscriptEntry], None]


# ── Spectator registry ────────────────────────────────────────────────────────

# Module-level registry: game_id → list of (ws, queue, listener) tuples
_spectators: dict[str, list[tuple[WebSocket, asyncio.Queue, ListenerType]]] = {}


def _get_spectators(game_id: str) -> list[tuple[WebSocket, asyncio.Queue, ListenerType]]:
    """Return the spectator list for a game, creating it if needed."""
    if game_id not in _spectators:
        _spectators[game_id] = []
    return _spectators[game_id]


# ── Transcript listener factory ───────────────────────────────────────────────

def _make_listener(queue: asyncio.Queue[dict[str, Any]]) -> ListenerType:
    """Create a listener callback that pushes transcript entries to the queue."""
    def _on_event(entry: TranscriptEntry) -> None:
        try:
            msg = {
                "type": entry.event_type,
                "data": entry.data,
                "timestamp": time.time(),
                "seq": entry.seq,
                "turn": entry.turn,
                "phase": entry.phase,
                "step": entry.step,
                "description": entry.description,
            }
            queue.put_nowait(msg)
        except asyncio.QueueFull:
            # Queue full — drop event silently to avoid crashing the engine
            logger.debug("Spectator queue full for game %s, dropping event", entry.event_type)
        except Exception:
            # Other unexpected error — don't crash the engine
            logger.debug("Spectator listener error pushing event", exc_info=True)

    return _on_event


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/game/{game_id}")
async def ws_game_spectate(websocket: WebSocket, game_id: str) -> None:
    """
    Spectator WebSocket endpoint. APP-04.

    - Sends initial_state on connect (full GameState dump).
    - Streams transcript events as they happen.
    - Sends game_end notification and closes with code 1000 when the game ends.
    - Rejects connections to non-existent or completed games (HTTP 4004).
    """
    # Validate game exists and is not over
    try:
        gs = get_manager().get(game_id)
    except KeyError:
        await websocket.close(code=4004, reason="Game not found")
        return

    if gs.is_game_over:
        await websocket.close(code=4004, reason="Game is already over")
        return

    await websocket.accept()
    logger.info("Spectator connected: game=%s", game_id)

    # Set up per-connection queue and listener
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_SPECTATOR_QUEUE_MAX)
    recorder = get_export_store(game_id).transcript
    listener = _make_listener(queue)
    recorder.register_listener(listener)

    # Register in spectator registry
    _get_spectators(game_id).append((websocket, queue, listener))

    try:
        # Send initial state on connect
        await websocket.send_json({
            "type": "initial_state",
            "data": gs.model_dump(mode="json"),
            "timestamp": time.time(),
        })

        # Event fan-out loop — single receive path, no competing heartbeat task
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=_IDLE_CHECK_INTERVAL_S)
                await websocket.send_json(msg)

                # Check game-over after each event
                if await _check_game_over_and_notify(websocket, game_id):
                    break

            except asyncio.TimeoutError:
                # No event yet — check if game was deleted or ended while idle
                try:
                    current_gs = get_manager().get(game_id)
                    if current_gs.is_game_over:
                        await _send_game_end(websocket, current_gs)
                        await websocket.close(code=1000)
                        return
                except KeyError:
                    # Game was deleted while idle — close connection
                    await _send_game_deleted(websocket)
                    await websocket.close(code=1000)
                    return

    except (WebSocketDisconnect, OSError, RuntimeError):
        pass  # Client disconnected abnormally — cleanup in finally
    finally:
        logger.info("Spectator disconnected: game=%s", game_id)
        _cleanup_connection(websocket, queue, listener, game_id)


async def _check_game_over_and_notify(ws: WebSocket, game_id: str) -> bool:
    """Check if the game has ended and notify spectator.

    Returns True if the game is over (caller should break out of event loop).
    """
    try:
        current_gs = get_manager().get(game_id)
        if current_gs.is_game_over:
            await _send_game_end(ws, current_gs)
            await ws.close(code=1000)
            return True
    except KeyError:
        # Game was deleted — notify and close
        await _send_game_deleted(ws)
        await ws.close(code=1000)
        return True
    except (WebSocketDisconnect, OSError, RuntimeError):
        pass  # Client already gone
    return False


async def _send_game_end(ws: WebSocket, gs: Any) -> None:
    """Send game_end notification with winner/loser info.

    NOTE: Currently optimized for the common 2-player case. For games with more
    than 2 players, iterates all players to find the highest life total as winner.
    """
    players = gs.players
    winner = None
    loser = None

    if len(players) == 2:
        p1, p2 = players[0], players[1]
        if p1.life > p2.life:
            winner, loser = p1.name, p2.name
        elif p2.life > p1.life:
            winner, loser = p2.name, p1.name
        else:
            winner = "draw"
    elif len(players) >= 3:
        # Multi-player: find player with highest life total as winner
        alive = [p for p in players if p.life > 0]
        if alive:
            winner = max(alive, key=lambda p: p.life).name
            loser = min(players, key=lambda p: p.life).name

    await ws.send_json({
        "type": "game_end",
        "data": {
            "winner": winner,
            "loser": loser,
            "reason": gs.game_over_reason or "unknown",
        },
        "timestamp": time.time(),
    })


async def _send_game_deleted(ws: WebSocket) -> None:
    """Send game_end notification for deleted games."""
    await ws.send_json({
        "type": "game_end",
        "data": {"winner": None, "loser": None, "reason": "game_deleted"},
        "timestamp": time.time(),
    })


def _cleanup_connection(
    ws: WebSocket, queue: asyncio.Queue, listener: ListenerType, game_id: str
) -> None:
    """Remove a spectator connection from the registry and unregister its listener."""
    try:
        recorder = get_export_store(game_id).transcript
        recorder.unregister_listener(listener)
    except Exception:
        pass

    # Remove from registry (find matching tuple by queue identity)
    spectators = _spectators.get(game_id)
    if spectators is not None:
        spectators[:] = [s for s in spectators if s[1] is not queue]
        if len(spectators) == 0:
            del _spectators[game_id]


# ── Utility: clear registry (for tests) ───────────────────────────────────────

def clear_spectator_registry() -> None:
    """Clear all spectator connections. Used in tests."""
    for game_id, conns in list(_spectators.items()):
        for ws, queue, listener in conns:
            try:
                recorder = get_export_store(game_id).transcript
                recorder.unregister_listener(listener)
            except Exception:
                pass
    _spectators.clear()
