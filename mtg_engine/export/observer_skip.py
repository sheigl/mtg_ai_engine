"""
Shared registry for observer skip events.
Allows the debug HTTP endpoint to signal a running observer thread to stop early.
Both ai_client/game_loop.py and mtg_engine/api/routers/debug.py import from here —
they run in the same Python process so the module-level dict is shared.
"""
import threading

_events: dict[str, threading.Event] = {}
_lock = threading.Lock()


def register(entry_id: str) -> threading.Event:
    """Create and store a stop event for the given entry. Returns the event."""
    event = threading.Event()
    with _lock:
        _events[entry_id] = event
    return event


def trigger_skip(entry_id: str) -> bool:
    """Set the stop event for entry_id. Returns True if the entry was found."""
    with _lock:
        event = _events.get(entry_id)
    if event:
        event.set()
        return True
    return False


def unregister(entry_id: str) -> None:
    """Remove the stop event once the observer thread is done."""
    with _lock:
        _events.pop(entry_id, None)
