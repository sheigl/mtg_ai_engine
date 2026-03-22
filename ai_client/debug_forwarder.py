"""
HTTP helper that forwards AI prompt/response debug entries to the engine.
Feature 011-observer-ai-commentary.
"""
import logging
import time
import uuid

import httpx

logger = logging.getLogger(__name__)


class DebugForwarder:
    """
    Posts debug entries and streaming patches to the engine's debug log API.

    Usage:
        forwarder = DebugForwarder(engine_url, game_id)
        entry_id = forwarder.post_entry({...})
        forwarder.patch_entry(entry_id, chunk, is_complete=False)
        forwarder.patch_entry(entry_id, "", is_complete=True)
    """

    def __init__(self, engine_url: str, game_id: str) -> None:
        self._base = engine_url.rstrip("/")
        self._game_id = game_id
        self._client = httpx.Client(timeout=10.0)

    def post_entry(self, entry: dict) -> str:
        """
        POST a new DebugEntry to the engine. Returns the entry_id.
        Silently swallows errors so debug failures never crash the game.
        """
        try:
            resp = self._client.post(
                f"{self._base}/game/{self._game_id}/debug/entry",
                json=entry,
                timeout=5.0,
            )
            resp.raise_for_status()
            return entry["entry_id"]
        except Exception as exc:
            logger.debug("DebugForwarder.post_entry failed: %s", exc)
            return entry.get("entry_id", "")

    def patch_entry(self, entry_id: str, chunk: str, is_complete: bool) -> None:
        """
        PATCH an in-progress entry with a new response chunk.
        Silently swallows errors.
        """
        try:
            resp = self._client.patch(
                f"{self._base}/game/{self._game_id}/debug/entry/{entry_id}",
                json={"response_chunk": chunk, "is_complete": is_complete},
                timeout=5.0,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.debug("DebugForwarder.patch_entry failed: %s", exc)

    def new_entry_id(self) -> str:
        """Generate a fresh UUID for use as entry_id."""
        return str(uuid.uuid4())

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
