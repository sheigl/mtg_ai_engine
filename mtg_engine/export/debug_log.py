"""
Per-game debug log recorder. Feature 011-observer-ai-commentary.
Mirrors the listener pattern from mtg_engine/export/transcript.py.
"""
from typing import Callable

from mtg_engine.models.debug import DebugEntry


class DebugLogRecorder:
    """Stores debug entries for a single game in insertion order."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self._entries: list[DebugEntry] = []
        self._index: dict[str, DebugEntry] = {}
        self._listeners: list[Callable[[DebugEntry], None]] = []

    def register_listener(self, fn: Callable[[DebugEntry], None]) -> None:
        """Register a callback invoked on every append or patch."""
        self._listeners.append(fn)

    def unregister_listener(self, fn: Callable[[DebugEntry], None]) -> None:
        """Remove a previously registered listener."""
        try:
            self._listeners.remove(fn)
        except ValueError:
            pass

    def _notify(self, entry: DebugEntry) -> None:
        for fn in self._listeners:
            try:
                fn(entry)
            except Exception:
                pass

    def append_entry(self, entry: DebugEntry) -> None:
        """Add a new entry; notifies listeners."""
        self._entries.append(entry)
        self._index[entry.entry_id] = entry
        self._notify(entry)

    def patch_entry(self, entry_id: str, chunk: str, is_complete: bool) -> DebugEntry | None:
        """Append a chunk to an existing entry's response; notifies listeners. Returns None if not found."""
        entry = self._index.get(entry_id)
        if entry is None:
            return None
        entry.response += chunk
        entry.is_complete = is_complete
        self._notify(entry)
        return entry

    def get_all(self) -> list[DebugEntry]:
        """Return all entries (copy)."""
        return list(self._entries)
