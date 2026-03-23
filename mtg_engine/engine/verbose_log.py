"""
Play-by-play verbose logger for the MTG engine.
VerboseLogger receives TranscriptEntry events and emits human-readable output.
Feature: 007-play-by-play-log
"""
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mtg_engine.export.transcript import TranscriptEntry

_verbose_logger = logging.getLogger("mtg_engine.verbose")
_verbose_logger.setLevel(logging.INFO)

# ── Global zone-change listener (registered once at first game creation) ───────
_listener_registered: bool = False


def ensure_zone_listener_registered() -> None:
    """Register the global zone-change listener exactly once."""
    global _listener_registered
    if _listener_registered:
        return
    from mtg_engine.engine.zones import register_zone_change_listener
    register_zone_change_listener(_on_zone_change)
    _listener_registered = True


def _on_zone_change(event: dict, gs: Any) -> None:
    """Global zone-change listener. Routes events to the per-game recorder."""
    try:
        from mtg_engine.api.game_manager import get_manager
        recorder = get_manager().get_recorder(gs.game_id)
    except (KeyError, Exception):
        return
    try:
        from_zone = event.get("from_zone", "")
        to_zone = event.get("to_zone", "")
        is_token = event.get("is_token", False)
        player = event.get("player", "unknown")

        if event.get("is_draw"):
            recorder.record_draw(player, gs.turn, gs.phase.value, gs.step.value)
        elif (from_zone == "battlefield" or to_zone == "battlefield") and not is_token:
            card_name = event.get("card_name") or "Unknown"
            recorder.record_zone_change(
                card_name, from_zone, to_zone, player,
                gs.turn, gs.phase.value, gs.step.value,
            )
    except Exception:
        pass  # Never let logging errors crash the game


# ── VerboseLogger ─────────────────────────────────────────────────────────────

class VerboseLogger:
    """Per-game verbose logger. Subscribes to TranscriptEntry events and emits formatted text."""

    def __init__(self, game_id: str, enabled: bool = False) -> None:
        self._game_id = game_id
        self._enabled = enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def on_event(self, entry: "TranscriptEntry") -> None:
        if not self._enabled:
            return
        try:
            line = self._format(entry)
            if line is not None:
                print(line, flush=True)
                _verbose_logger.info("%s", line)
        except Exception:
            pass  # Never let formatting errors crash the game

    def _format(self, entry: "TranscriptEntry") -> str | None:  # noqa: PLR0911
        et = entry.event_type
        d = entry.data

        # Suppressed: priority passes are not logged (edge-case spec)
        if et == "priority_grant":
            return None

        if et == "cast":
            target_str = f" targeting {', '.join(d['targets'])}" if d.get("targets") else ""
            return f"  {d['player']} casts {d['card_name']}{target_str}."

        if et == "activate":
            target_str = f" targeting {', '.join(d['targets'])}" if d.get("targets") else ""
            return f"  {d['player']} activates ability of {d['perm_name']}{target_str}."

        if et == "resolve":
            return f"  {d['card_name']} resolves (controller: {d['controller']})."

        if et == "attack":
            return f"  {d['player']} attacks with {d['card_name']} \u2192 {d['defending_id']}."

        if et == "block":
            return f"  {d['blocker_controller']} blocks {d['attacker_name']} with {d['blocker_name']}."

        if et == "trigger":
            return f"  Triggered: {d['source_card']} \u2014 {d['effect']}."

        if et == "sba":
            return f"  [SBA] {d['description']}"

        if et == "zone_change":
            from_zone = d.get("from_zone", "unknown")
            to_zone = d.get("to_zone", "unknown")
            card_name = d.get("card_name", "Unknown")
            player = d.get("player", "unknown")
            if to_zone == "battlefield":
                return f"  {card_name} enters the battlefield under {player}'s control."
            return f"  {card_name} moves {from_zone} \u2192 {to_zone} ({player})."

        if et == "damage":
            return f"  {d['source']} deals {d['amount']} damage to {d['target']}."

        if et == "life_change":
            delta = d.get("delta", 0)
            prefix = "gains" if delta > 0 else "takes"
            amount = abs(delta)
            player = d.get("player", "unknown")
            source = d.get("source", "unknown")
            new_total = d.get("new_total", "?")
            return f"  {player} {prefix} {amount} life from {source}. ({player} life: {new_total})"

        if et == "draw":
            return f"  {d['player']} draws a card."

        if et == "phase_change":
            turn = d.get("turn", entry.turn)
            step = d.get("step", entry.step)
            phase = d.get("phase", entry.phase)
            active_player = d.get("active_player", "")

            if step == "untap":
                player_label = f" \u2014 {active_player}" if active_player else ""
                header = f"\u2550\u2550\u2550 Turn {turn}{player_label} "
                header = header.ljust(60, "\u2550")
                return header

            phase_display = phase.replace("_", " ").title()
            step_display = step.replace("_", " ").title()
            return f"  [{phase_display} / {step_display}]"

        if et == "game_end":
            winner = d.get("winner", "Unknown")
            reason = d.get("reason", "unknown")
            banner = f"\u2550\u2550 GAME OVER \u2014 {winner} wins ({reason}) "
            banner = banner.ljust(60, "\u2550")
            return banner

        if et == "choice_made":
            return f"  {d['player']} chooses: {d['selection']} ({d['choice_type']})."

        # Fallback for unknown event types
        return f"  [{et}] {entry.description}"
