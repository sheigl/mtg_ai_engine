"""
Snapshot recorder. REQ-D01, REQ-D02, REQ-D03.
A snapshot is recorded at every priority grant. The chosen action
is attached via finalize_snapshot() after the action is taken.
"""
import uuid
from typing import Any
from pydantic import BaseModel, Field
from mtg_engine.models.game import GameState


class Snapshot(BaseModel):
    """REQ-D03 schema."""
    game_id: str
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    turn: int
    phase: str
    step: str
    game_state: dict          # full serialized GameState
    legal_actions: list[dict]  # list of LegalAction dicts
    action_taken: dict | None = None
    action_taken_by: str | None = None


class SnapshotRecorder:
    """Per-game snapshot store. REQ-D01: one snapshot per priority grant."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self._snapshots: list[Snapshot] = []
        self._pending: Snapshot | None = None  # last unfinalized snapshot

    def record_snapshot(
        self,
        game_state: GameState,
        legal_actions: list[dict],
    ) -> Snapshot:
        """
        Record a snapshot at a priority grant point. REQ-D01.
        Finalizes any previous pending snapshot with action_taken=None
        (for cases where no action was recorded before next priority grant).
        """
        if self._pending is not None:
            self._snapshots.append(self._pending)

        snap = Snapshot(
            game_id=self.game_id,
            turn=game_state.turn,
            phase=game_state.phase.value,
            step=game_state.step.value,
            game_state=game_state.model_dump(),
            legal_actions=legal_actions,
        )
        self._pending = snap
        return snap

    def finalize_snapshot(
        self,
        action_taken: dict,
        action_taken_by: str,
    ) -> None:
        """
        Attach the chosen action to the last recorded snapshot. REQ-D02.
        Must be called after every player action, before the next priority grant.
        """
        if self._pending is not None:
            self._pending.action_taken = action_taken
            self._pending.action_taken_by = action_taken_by
            self._snapshots.append(self._pending)
            self._pending = None

    def flush(self) -> None:
        """Flush any remaining pending snapshot (e.g. at game end)."""
        if self._pending is not None:
            self._snapshots.append(self._pending)
            self._pending = None

    def get_all(self) -> list[Snapshot]:
        self.flush()
        return list(self._snapshots)

    def to_jsonl(self) -> str:
        """Export all snapshots as newline-delimited JSON. REQ-D03."""
        import json
        lines = [snap.model_dump_json() for snap in self.get_all()]
        return "\n".join(lines)
