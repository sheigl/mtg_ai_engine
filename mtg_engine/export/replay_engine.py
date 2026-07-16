"""
Game replay engine. APP-03.

Pure functions for reconstructing board state from export store data
(transcript + snapshots), generating timelines, and paginating events.
No FastAPI dependencies — operates on GameExportStore objects directly.
"""
from __future__ import annotations

import logging
from typing import Any

from mtg_engine.export.store import GameExportStore, _store as export_store_registry

logger = logging.getLogger(__name__)


def game_has_export_data(game_id: str) -> bool:
    """Check if a game has any recorded export data without auto-creating a store."""
    return game_id in export_store_registry


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_transcript_entries(store: GameExportStore) -> list[dict]:
    """Return all transcript entries as dicts."""
    return store.transcript.to_json()


def _get_snapshots(store: GameExportStore) -> list[dict]:
    """Return all snapshots as dicts (flushes pending)."""
    return [s.model_dump() for s in store.snapshots.get_all()]


def _find_snapshot_anchor(snapshots: list[dict], target_turn: int) -> dict | None:
    """
    Find the best snapshot to use as a board-state reconstruction anchor.

    Snapshots are recorded at priority grants and contain full GameState dumps.
    We pick the most recent snapshot whose turn is <= target_turn, so that we
    only need to replay events AFTER the snapshot point (avoiding double-apply).

    Returns None if no suitable snapshot exists.
    """
    if not snapshots:
        return None

    # Find the latest snapshot at or before the target turn
    best = None
    for snap in reversed(snapshots):
        gs_data = snap.get("game_state", {})
        snap_turn = gs_data.get("turn", 0)
        if snap_turn <= target_turn:
            best = snap
            break

    return best


def _extract_board_state_from_snapshot(snapshot_gs: dict) -> dict:
    """Extract board state summary from a serialized GameState dict."""
    battlefield = []
    for perm in snapshot_gs.get("battlefield", []):
        card = perm.get("card", {})
        battlefield.append({
            "id": perm.get("id"),
            "name": card.get("name", ""),
            "controller": perm.get("controller", ""),
            "power": card.get("power") or perm.get("power_bonus", 0),
            "toughness": card.get("toughness"),
            "tapped": perm.get("tapped", False),
            "counters": perm.get("counters", {}),
            "damage_marked": perm.get("damage_marked", 0),
        })

    player_life: dict[str, int] = {}
    hand_sizes: dict[str, int] = {}
    graveyard_top: dict[str, str | None] = {}

    for p in snapshot_gs.get("players", []):
        pname = p["name"]
        player_life[pname] = p.get("life", 20)
        hand_sizes[pname] = len(p.get("hand", []))
        # Graveyard: index 0 is top (most recent)
        grave = p.get("graveyard", [])
        graveyard_top[pname] = grave[0]["name"] if grave else None

    return {
        "battlefield": battlefield,
        "player_life": player_life,
        "hand_sizes": hand_sizes,
        "graveyard_top": graveyard_top,
        "stack_size": len(snapshot_gs.get("stack", [])),
    }


def _apply_event_to_board_state(board: dict, event: dict) -> dict:
    """Apply a single transcript event to a reconstructed board state."""
    etype = event.get("event_type", "")
    data = event.get("data", {})

    if etype == "zone_change":
        card_name = data.get("card_name", "")
        from_zone = data.get("from_zone", "")
        to_zone = data.get("to_zone", "")
        player = data.get("player", "")

        if to_zone == "battlefield" and from_zone != "battlefield":
            # Card enters battlefield — we don't have full card details, add minimal entry
            board["battlefield"].append({
                "id": f"reconstructed_{card_name}_{len(board['battlefield'])}",
                "name": card_name,
                "controller": player,
                "power": None,
                "toughness": None,
                "tapped": False,
                "counters": {},
                "damage_marked": 0,
            })

        if from_zone == "battlefield" and to_zone != "battlefield":
            # Card leaves battlefield — remove matching permanent
            board["battlefield"] = [
                p for p in board["battlefield"]
                if not (p.get("name") == card_name and p.get("controller") == player)
            ]

        # Update graveyard top
        if to_zone == "graveyard" and player:
            board["graveyard_top"][player] = card_name

        # Adjust hand sizes for zone transitions involving hand
        if from_zone == "hand" and player in board.get("hand_sizes", {}):
            board["hand_sizes"][player] = max(0, board["hand_sizes"].get(player, 0) - 1)
        elif to_zone == "hand" and player in board.get("hand_sizes", {}):
            board["hand_sizes"][player] = board["hand_sizes"].get(player, 0) + 1

    elif etype == "life_change":
        player = data.get("player", "")
        delta = data.get("delta", 0)
        if player in board.get("player_life", {}):
            board["player_life"][player] += delta

    elif etype == "damage":
        target = data.get("target", "")
        amount = data.get("amount", 0)
        # If target is a player, reduce life (life_change events handle this too, but be safe)
        if target in board.get("player_life", {}):
            board["player_life"][target] -= amount

    elif etype == "draw":
        player = data.get("player", "")
        if player in board.get("hand_sizes", {}):
            board["hand_sizes"][player] = board["hand_sizes"].get(player, 0) + 1

    elif etype == "cast":
        # Spell goes on stack
        board["stack_size"] += 1

    elif etype == "resolve":
        # Spell resolves and leaves stack
        board["stack_size"] = max(0, board.get("stack_size", 0) - 1)

    return board


def _build_initial_board_state(entries: list[dict], snapshots: list[dict] | None = None) -> dict:
    """Build a minimal initial board state from transcript entries (fallback when no snapshots)."""
    players = set()

    # Check snapshots first — most reliable source of full game state
    if snapshots:
        for snap in snapshots:
            gs_data = snap.get("game_state", {})
            for p in gs_data.get("players", []):
                pname = p.get("name")
                if pname:
                    players.add(pname)

    # Extract from event data fields that contain player info
    for e in entries:
        data = e.get("data", {})
        for field in ("player", "active_player"):
            val = data.get(field)
            if val and isinstance(val, str):
                players.add(val)

    # Infer missing players from naming patterns (e.g., p1 → also expect p2).
    # KNOWN LIMITATION: this heuristic is fragile — it only works for the common
    # "p1"/"p2" naming convention and will produce incorrect results for other
    # player name schemes. It exists as a fallback when no snapshot data is
    # available to provide authoritative player names.
    inferred = set()
    for p in list(players):
        if p.endswith("1"):
            inferred.add(p[:-1] + "2")
        elif p.endswith("2"):
            inferred.add(p[:-1] + "1")
    players.update(inferred)

    if not players:
        players = {"p1", "p2"}  # default fallback for standard 2-player game

    player_list = sorted(players)
    return {
        "battlefield": [],
        "player_life": {p: 20 for p in player_list},
        "hand_sizes": {p: 7 for p in player_list},
        "graveyard_top": {p: None for p in player_list},
        "stack_size": 0,
    }


# ─── Public API ──────────────────────────────────────────────────────────────

def get_replay_info(store: GameExportStore) -> dict:
    """Return replay metadata: game_id, total_events, turns, winner, loser, format."""
    entries = _get_transcript_entries(store)
    snapshots = _get_snapshots(store)

    total_events = len(entries)
    max_turn = 0
    winner: str | None = None
    loser: str | None = None
    game_format: str | None = "standard"

    # Extract info from transcript events
    for e in entries:
        turn = e.get("turn", 0)
        if turn > max_turn:
            max_turn = turn
        data = e.get("data", {})
        if e.get("event_type") == "game_end":
            winner = data.get("winner")

    # Extract format and more details from latest snapshot
    if snapshots:
        last_snap = snapshots[-1]
        gs_data = last_snap.get("game_state", {})
        game_format = gs_data.get("format", "standard")
        max_turn = max(max_turn, gs_data.get("turn", 0))

        # Determine winner/loser from game state
        if gs_data.get("winner"):
            winner = gs_data["winner"]
        players = gs_data.get("players", [])
        if len(players) == 2:
            p1_lost = players[0].get("has_lost", False)
            p2_lost = players[1].get("has_lost", False)
            if p1_lost and not p2_lost:
                loser = players[0]["name"]
                winner = players[1]["name"]
            elif p2_lost and not p1_lost:
                loser = players[1]["name"]
                winner = players[0]["name"]

    return {
        "game_id": store.game_id,
        "total_events": total_events,
        "turns": max_turn,
        "winner": winner,
        "loser": loser,
        "format": game_format,
    }


def paginate_events(
    store: GameExportStore, page: int = 1, per_page: int = 25
) -> tuple[list[dict], int]:
    """Return (events_page, total_count) for paginated transcript access."""
    entries = _get_transcript_entries(store)
    total = len(entries)

    start = (page - 1) * per_page
    end = start + per_page
    page_entries = entries[start:end]

    return page_entries, total


def step_to_event(
    store: GameExportStore, direction: str, from_seq: int
) -> tuple[dict, dict, int, int] | None:
    """
    Step forward/backward one event.

    Returns (event_dict, board_state_dict, from_seq, to_seq) or None if out of bounds.
    """
    entries = _get_transcript_entries(store)
    total = len(entries)

    if direction == "forward":
        # from_seq=0 means before game starts; next event is seq 1 (index 0)
        target_index = from_seq  # 0-based index: from_seq 0 -> index 0, from_seq 1 -> index 1
        if target_index >= total:
            return None
        to_seq = entries[target_index]["seq"]
    elif direction == "backward":
        # from_seq is the seq number of current event; go back one
        if from_seq <= 0:
            return None
        # Find index of event with seq == from_seq, then step back
        target_index = -1
        for i, e in enumerate(entries):
            if e["seq"] == from_seq:
                target_index = i
                break
        if target_index < 0:
            return None
        # If we're at the first event (index 0), backward goes to "before game" state
        if target_index == 0:
            # Return the first event with from_seq=from_seq, to_seq=0
            event = entries[0]
            board_state = reconstruct_board_state_at(store, from_seq)
            return event, board_state, from_seq, 0
        target_index -= 1
        to_seq = entries[target_index]["seq"]
    else:
        return None

    event = entries[target_index]
    board_state = reconstruct_board_state_at(store, to_seq)

    return event, board_state, from_seq, to_seq


def build_timeline(store: GameExportStore) -> list[dict]:
    """Return condensed timeline grouped by turn/phase with event counts."""
    entries = _get_transcript_entries(store)

    if not entries:
        return []

    # Group by (turn, phase, step)
    groups: dict[tuple[int, str, str], list[dict]] = {}
    for e in entries:
        key = (e.get("turn", 0), e.get("phase", ""), e.get("step", ""))
        if key not in groups:
            groups[key] = []
        groups[key].append(e)

    # Build timeline structure
    turns_map: dict[int, list[dict]] = {}
    for (turn, phase, step), events in sorted(groups.items()):
        if turn not in turns_map:
            turns_map[turn] = []

        seqs = [e["seq"] for e in events]
        segment = {
            "phase": phase,
            "step": step if step else None,
            "event_count": len(events),
            "first_event_seq": min(seqs),
            "last_event_seq": max(seqs),
        }

        # Merge with existing segment for same turn/phase/step
        merged = False
        for existing in turns_map[turn]:
            if existing["phase"] == phase and existing.get("step") == (step if step else None):
                existing["event_count"] += len(events)
                existing["first_event_seq"] = min(existing["first_event_seq"], min(seqs))
                existing["last_event_seq"] = max(existing["last_event_seq"], max(seqs))
                merged = True
                break

        if not merged:
            turns_map[turn].append(segment)

    # Convert to sorted list
    result = []
    for turn_num in sorted(turns_map.keys()):
        phases = sorted(turns_map[turn_num], key=lambda s: (s["first_event_seq"]))
        result.append({
            "turn": turn_num,
            "phases": phases,
        })

    return result


def reconstruct_board_state_at(store: GameExportStore, target_seq: int) -> dict:
    """
    Reconstruct board state at the given event sequence number.

    Uses snapshot anchors + incremental replay from transcript events.
    When a suitable snapshot exists (at or before the target turn), it serves
    as the base state and only events AFTER the snapshot point are replayed,
    avoiding double-application of events already reflected in the snapshot.
    """
    entries = _get_transcript_entries(store)
    snapshots = _get_snapshots(store)

    # Find the target event index
    target_index = -1
    for i, e in enumerate(entries):
        if e["seq"] == target_seq:
            target_index = i
            break

    if target_index < 0:
        # Event not found — return initial state
        return _build_initial_board_state(entries, snapshots)

    target_event = entries[target_index]
    target_turn = target_event.get("turn", 0)

    # Strategy: find nearest snapshot anchor and replay from there
    if snapshots:
        anchor = _find_snapshot_anchor(snapshots, target_turn)
        if anchor is not None:
            gs_data = anchor.get("game_state", {})
            snap_turn = gs_data.get("turn", 0)

            # Use the snapshot as base state — it already reflects all events
            # up to its recording point. Only replay events that occurred AFTER
            # the snapshot was taken (i.e., from the first event of the target
            # turn onward, up to and including the target).
            board = _extract_board_state_from_snapshot(gs_data)

            if snap_turn < target_turn:
                # Snapshot is from an earlier turn — replay events starting from
                # the first event of the target turn through the target index.
                start_index = _find_first_event_of_turn(entries, target_turn)
            else:
                # Snapshot is from the same turn as the target — replay only
                # events after the snapshot's phase/step point up to target.
                # For simplicity, replay all events in this turn through target.
                start_index = _find_first_event_of_turn(entries, target_turn)

            for i in range(start_index, target_index + 1):
                board = _apply_event_to_board_state(board, entries[i])

            return board

    # Fallback: build from initial state and replay all events up to target
    board = _build_initial_board_state(entries, snapshots)
    for i in range(target_index + 1):
        board = _apply_event_to_board_state(board, entries[i])

    return board


def _find_first_event_of_turn(entries: list[dict], turn: int) -> int:
    """Find the index of the first event belonging to the given turn."""
    for i, e in enumerate(entries):
        if e.get("turn", 0) == turn:
            return i
    # Turn not found — default to start of entries
    return 0
