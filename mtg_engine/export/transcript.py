"""
Play-by-play transcript recorder. REQ-D04, REQ-D05, REQ-D06.
Records every engine event in sequence with natural-language descriptions.
"""
import uuid
from typing import Any
from pydantic import BaseModel, Field


class TranscriptEntry(BaseModel):
    """REQ-D05: each entry has seq, event_type, description, and structured data."""
    seq: int
    event_type: str   # cast|resolve|trigger|sba|zone_change|damage|phase_change|priority_grant|choice_made
    description: str  # human-readable natural language
    data: dict        # structured event data
    turn: int
    phase: str
    step: str


class TranscriptRecorder:
    """Per-game transcript store. REQ-D04: records every engine event."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self._entries: list[TranscriptEntry] = []
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _entry(
        self,
        event_type: str,
        description: str,
        data: dict,
        turn: int,
        phase: str,
        step: str,
    ) -> TranscriptEntry:
        e = TranscriptEntry(
            seq=self._next_seq(),
            event_type=event_type,
            description=description,
            data=data,
            turn=turn,
            phase=phase,
            step=step,
        )
        self._entries.append(e)
        return e

    # ── Event recording methods ──────────────────────────────────────────────

    def record_phase_change(self, turn: int, phase: str, step: str) -> None:
        self._entry(
            "phase_change",
            f"Turn {turn}: entering {phase} — {step}",
            {"turn": turn, "phase": phase, "step": step},
            turn, phase, step,
        )

    def record_priority_grant(self, player: str, turn: int, phase: str, step: str) -> None:
        self._entry(
            "priority_grant",
            f"{player} receives priority",
            {"player": player},
            turn, phase, step,
        )

    def record_cast(
        self, player: str, card_name: str, targets: list[str],
        turn: int, phase: str, step: str,
    ) -> None:
        target_str = f" targeting {', '.join(targets)}" if targets else ""
        self._entry(
            "cast",
            f"{player} casts {card_name}{target_str}",
            {"player": player, "card_name": card_name, "targets": targets},
            turn, phase, step,
        )

    def record_resolve(
        self, card_name: str, controller: str,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "resolve",
            f"{card_name} resolves (controller: {controller})",
            {"card_name": card_name, "controller": controller},
            turn, phase, step,
        )

    def record_trigger(
        self, source_card: str, controller: str, effect: str,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "trigger",
            f"Triggered ability from {source_card}: {effect}",
            {"source_card": source_card, "controller": controller, "effect": effect},
            turn, phase, step,
        )

    def record_sba(
        self, sba_type: str, description: str,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "sba",
            f"State-based action: {description}",
            {"sba_type": sba_type, "description": description},
            turn, phase, step,
        )

    def record_zone_change(
        self, card_name: str, from_zone: str, to_zone: str, player: str,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "zone_change",
            f"{card_name} moves from {from_zone} to {to_zone} ({player})",
            {"card_name": card_name, "from_zone": from_zone, "to_zone": to_zone, "player": player},
            turn, phase, step,
        )

    def record_damage(
        self, source: str, target: str, amount: int,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "damage",
            f"{source} deals {amount} damage to {target}",
            {"source": source, "target": target, "amount": amount},
            turn, phase, step,
        )

    def record_choice_made(
        self, player: str, choice_type: str, selection: Any,
        turn: int, phase: str, step: str,
    ) -> None:
        self._entry(
            "choice_made",
            f"{player} chooses: {selection} ({choice_type})",
            {"player": player, "choice_type": choice_type, "selection": str(selection)},
            turn, phase, step,
        )

    def get_all(self) -> list[TranscriptEntry]:
        return list(self._entries)

    def to_json(self) -> list[dict]:
        """Export all transcript entries as a list of dicts. REQ-D04."""
        return [e.model_dump() for e in self._entries]
