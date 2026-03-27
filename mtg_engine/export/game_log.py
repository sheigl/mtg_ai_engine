"""
Human-readable game log builder.

Combines TranscriptEntry events and Snapshot board states into a structured,
turn-by-turn text log. Returned from GET /export/{game_id}/game-log.
"""
from __future__ import annotations


# ── Phase ordering ────────────────────────────────────────────────────────────

_PHASE_ORDER = {
    "beginning": 0,
    "precombat_main": 1,
    "combat": 2,
    "postcombat_main": 3,
    "ending": 4,
}

_STEP_ORDER = {
    "untap": 0,
    "upkeep": 1,
    "draw": 2,
    "main": 3,
    "beginning_of_combat": 4,
    "declare_attackers": 5,
    "declare_blockers": 6,
    "first_strike_damage": 7,
    "combat_damage": 8,
    "end_of_combat": 9,
    "end": 10,
    "cleanup": 11,
}

# Event types that are too noisy to print in the log
_SKIP_EVENTS = {"phase_change", "priority_grant"}


def _phase_step_key(phase: str, step: str) -> tuple[int, int]:
    return (_PHASE_ORDER.get(phase, 99), _STEP_ORDER.get(step, 99))


# ── Board state formatting ─────────────────────────────────────────────────────

def _fmt_permanent(perm: dict) -> str:
    """Format a single permanent as 'Name [mods]'."""
    card = perm.get("card", {})
    name = card.get("name", "?")
    parts: list[str] = []
    if perm.get("tapped"):
        parts.append("tapped")
    counters: dict = perm.get("counters") or {}
    for kind, count in counters.items():
        if count:
            parts.append(f"{count} {kind} counter{'s' if count != 1 else ''}")
    damage = perm.get("damage_marked", 0)
    if damage:
        parts.append(f"{damage} damage")
    if parts:
        return f"{name} ({', '.join(parts)})"
    return name


def _fmt_board(gs: dict) -> list[str]:
    """Return lines describing every player's board state."""
    lines: list[str] = []
    players: list[dict] = gs.get("players", [])
    battlefield: list[dict] = gs.get("battlefield", [])

    for player in players:
        name = player.get("name", "?")
        life = player.get("life", 0)
        hand: list = player.get("hand", [])
        mana_pool: dict = player.get("mana_pool", {})
        command_zone: list = player.get("command_zone", [])

        my_perms = [p for p in battlefield if p.get("controller") == name]
        lands = [
            _fmt_permanent(p) for p in my_perms
            if "land" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        nonlands = [
            _fmt_permanent(p) for p in my_perms
            if "land" not in (p.get("card", {}).get("type_line") or "").lower()
        ]

        lines.append(f"  {name}  |  Life: {life}  |  Hand: {len(hand)} card{'s' if len(hand) != 1 else ''}")

        if lands:
            lines.append(f"    Lands    : {', '.join(lands)}")
        else:
            lines.append("    Lands    : (none)")

        if nonlands:
            lines.append(f"    Battlefield: {', '.join(nonlands)}")

        # Show floating mana if any
        pool_str = _fmt_mana_pool(mana_pool)
        if pool_str:
            lines.append(f"    Mana pool: {pool_str}")

        # Commander zone
        if command_zone:
            cmd_names = [c.get("name", "?") for c in command_zone]
            lines.append(f"    Command zone: {', '.join(cmd_names)}")

    return lines


def _fmt_mana_pool(pool: dict) -> str:
    symbols = []
    for sym in ("W", "U", "B", "R", "G", "C"):
        n = pool.get(sym, 0)
        if n:
            symbols.extend([f"{{{sym}}}"] * n)
    return "".join(symbols)


# ── Phase label ───────────────────────────────────────────────────────────────

_PHASE_LABEL = {
    "beginning": "Beginning",
    "precombat_main": "Pre-Combat Main",
    "combat": "Combat",
    "postcombat_main": "Post-Combat Main",
    "ending": "Ending",
}

_STEP_LABEL = {
    "untap": "Untap",
    "upkeep": "Upkeep",
    "draw": "Draw",
    "main": "Main",
    "beginning_of_combat": "Beginning of Combat",
    "declare_attackers": "Declare Attackers",
    "declare_blockers": "Declare Blockers",
    "first_strike_damage": "First Strike Damage",
    "combat_damage": "Combat Damage",
    "end_of_combat": "End of Combat",
    "end": "End",
    "cleanup": "Cleanup",
}


def _fmt_phase_header(phase: str, step: str) -> str:
    p = _PHASE_LABEL.get(phase, phase.upper())
    s = _STEP_LABEL.get(step, step)
    return f"  -- {p} / {s} " + "-" * max(0, 46 - len(p) - len(s))


# ── Main builder ──────────────────────────────────────────────────────────────

def build_game_log(
    transcript: list[dict],
    snapshots: list[dict],
    game_id: str = "",
) -> str:
    """
    Build a human-readable turn-by-turn game log.

    Args:
        transcript: list of TranscriptEntry dicts (from TranscriptRecorder.to_json())
        snapshots:  list of Snapshot dicts (from SnapshotRecorder.get_all())
        game_id:    game identifier shown in the header
    """
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append("+" + "=" * 60 + "+")
    title = f"  GAME LOG  --  {game_id}" if game_id else "  GAME LOG"
    lines.append("|" + title.ljust(60) + "|")
    lines.append("+" + "=" * 60 + "+")
    lines.append("")

    # ── Build ID → card name lookup from all snapshots ────────────────────────
    # Collect every permanent/card ID we ever see so target UUIDs can be resolved.
    _id_to_name: dict[str, str] = {}
    for snap in snapshots:
        gs_s = snap.get("game_state", {})
        for perm in gs_s.get("battlefield", []):
            pid = perm.get("id") or perm.get("permanent_id", "")
            name = (perm.get("card") or {}).get("name", "")
            if pid and name:
                _id_to_name[pid] = name
        for player in gs_s.get("players", []):
            for card in player.get("hand", []) + player.get("graveyard", []):
                cid = card.get("id", "")
                name = card.get("name", "")
                if cid and name:
                    _id_to_name[cid] = name

    def _resolve_targets(desc: str) -> str:
        """Replace any UUID-looking tokens in desc with the card name if known."""
        import re as _re
        uuid_pat = _re.compile(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            _re.IGNORECASE,
        )
        def _replace(m: "_re.Match[str]") -> str:
            return _id_to_name.get(m.group(0), m.group(0))
        return uuid_pat.sub(_replace, desc)

    # ── Build snapshot indices ────────────────────────────────────────────────
    # first snapshot per turn (for turn-start board state)
    first_snap_by_turn: dict[int, dict] = {}
    # first snapshot per (turn, phase) — for phase-start board state
    first_snap_by_turn_phase: dict[tuple[int, str], dict] = {}
    for snap in snapshots:
        t = snap.get("turn", 0)
        p = snap.get("phase", "")
        if t not in first_snap_by_turn:
            first_snap_by_turn[t] = snap
        if (t, p) not in first_snap_by_turn_phase:
            first_snap_by_turn_phase[(t, p)] = snap

    # ── Sort transcript by seq ────────────────────────────────────────────────
    entries = sorted(transcript, key=lambda e: e.get("seq", 0))

    # ── Group by turn ─────────────────────────────────────────────────────────
    by_turn: dict[int, list[dict]] = {}
    for e in entries:
        by_turn.setdefault(e.get("turn", 0), []).append(e)

    for turn_num in sorted(by_turn):
        turn_entries = by_turn[turn_num]

        # Determine active player
        snap = first_snap_by_turn.get(turn_num, {})
        turn_gs: dict = snap.get("game_state", {})
        active_player: str = turn_gs.get("active_player", "")
        if not active_player:
            for e in turn_entries:
                if e.get("event_type") == "phase_change":
                    active_player = e.get("data", {}).get("active_player", "")
                    if active_player:
                        break

        # ── Turn header ───────────────────────────────────────────────────────
        turn_label = f"  TURN {turn_num}"
        if active_player:
            turn_label += f"  (Active player: {active_player})"
        lines.append("=" * 62)
        lines.append(turn_label)
        lines.append("=" * 62)
        lines.append("")

        # ── Group entries by (phase, step) ────────────────────────────────────
        by_phase: dict[tuple[str, str], list[dict]] = {}
        for e in turn_entries:
            key = (e.get("phase", ""), e.get("step", ""))
            by_phase.setdefault(key, []).append(e)

        # Track the last phase we printed a board state for (avoid duplicates
        # when multiple steps share the same phase).
        last_board_phase: str | None = None

        # Sort by phase/step order
        for phase_step in sorted(by_phase, key=lambda ps: _phase_step_key(*ps)):
            phase, step = phase_step
            phase_entries = by_phase[phase_step]

            # Collect printable actions (skip noisy system events)
            action_lines: list[str] = []
            for e in phase_entries:
                if e.get("event_type") in _SKIP_EVENTS:
                    continue
                desc = e.get("description", "")
                desc = _resolve_targets(desc)
                # Remove double-period that occurs when ability text ends with "."
                desc = desc.replace("..", ".")
                action_lines.append(f"    {desc}")

            if not action_lines:
                continue  # skip phases with no visible actions

            lines.append(_fmt_phase_header(phase, step))

            # Show board state once at the start of each new phase
            if phase != last_board_phase:
                phase_snap = first_snap_by_turn_phase.get((turn_num, phase), {})
                phase_gs = phase_snap.get("game_state", {})
                if phase_gs:
                    lines.extend(_fmt_board(phase_gs))
                last_board_phase = phase

            lines.extend(action_lines)
            lines.append("")

        lines.append("")

    return "\n".join(lines)
