"""
Tests for VerboseLogger and play-by-play log integration.
Feature: 007-play-by-play-log
"""
import logging
import pytest

from mtg_engine.export.transcript import TranscriptEntry, TranscriptRecorder
from mtg_engine.engine.verbose_log import VerboseLogger


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_entry(**kwargs) -> TranscriptEntry:
    defaults = dict(
        seq=1, event_type="cast", description="test",
        data={}, turn=1, phase="precombat_main", step="main",
    )
    defaults.update(kwargs)
    return TranscriptEntry(**defaults)


# ── T020a: on_event is no-op when disabled ────────────────────────────────────

def test_on_event_disabled_produces_no_output(caplog):
    vlogger = VerboseLogger("test-game-1", enabled=False)
    entry = _make_entry(
        event_type="cast",
        description="Alice casts Lightning Bolt.",
        data={"player": "Alice", "card_name": "Lightning Bolt", "targets": ["Bob"]},
    )
    with caplog.at_level(logging.INFO, logger="mtg_engine.verbose"):
        vlogger.on_event(entry)
    assert caplog.text == "", "Disabled logger should produce no output"


def test_on_event_enabled_produces_output(caplog):
    vlogger = VerboseLogger("test-game-2", enabled=True)
    entry = _make_entry(
        event_type="cast",
        description="Alice casts Lightning Bolt.",
        data={"player": "Alice", "card_name": "Lightning Bolt", "targets": []},
    )
    with caplog.at_level(logging.INFO, logger="mtg_engine.verbose"):
        vlogger.on_event(entry)
    assert "casts Lightning Bolt" in caplog.text


# ── T020b: _format returns expected strings ───────────────────────────────────

def test_format_cast_no_targets():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="cast",
        data={"player": "Alice", "card_name": "Grizzly Bears", "targets": []},
    )
    result = vlogger._format(entry)
    assert result == "  Alice casts Grizzly Bears."


def test_format_cast_with_targets():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="cast",
        data={"player": "Alice", "card_name": "Lightning Bolt", "targets": ["Bob"]},
    )
    result = vlogger._format(entry)
    assert "targeting Bob" in result


def test_format_attack():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="attack",
        data={"player": "Alice", "card_name": "Grizzly Bears", "defending_id": "Bob"},
    )
    result = vlogger._format(entry)
    assert "Alice" in result and "Grizzly Bears" in result and "Bob" in result


def test_format_block():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="block",
        data={"blocker_controller": "Bob", "blocker_name": "Hill Giant", "attacker_name": "Grizzly Bears"},
    )
    result = vlogger._format(entry)
    assert "Bob" in result and "Hill Giant" in result and "Grizzly Bears" in result


def test_format_life_change_damage():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="life_change",
        data={"player": "Bob", "delta": -3, "source": "Lightning Bolt", "new_total": 17},
    )
    result = vlogger._format(entry)
    assert "Bob" in result and "3" in result and "17" in result
    assert "takes" in result


def test_format_life_change_gain():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="life_change",
        data={"player": "Alice", "delta": 5, "source": "lifelink", "new_total": 25},
    )
    result = vlogger._format(entry)
    assert "gains" in result and "5" in result and "25" in result


def test_format_draw():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(event_type="draw", data={"player": "Alice"})
    result = vlogger._format(entry)
    assert result == "  Alice draws a card."


def test_format_zone_change_enter_battlefield():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="zone_change",
        data={"card_name": "Forest", "from_zone": "unknown", "to_zone": "battlefield", "player": "Alice"},
    )
    result = vlogger._format(entry)
    assert "enters the battlefield" in result and "Alice" in result


def test_format_zone_change_leave_battlefield():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="zone_change",
        data={"card_name": "Grizzly Bears", "from_zone": "battlefield", "to_zone": "graveyard", "player": "Alice"},
    )
    result = vlogger._format(entry)
    assert "Grizzly Bears" in result and "battlefield" in result and "graveyard" in result


def test_format_phase_change_new_turn():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="phase_change",
        data={"turn": 3, "phase": "beginning", "step": "untap", "active_player": "Bob"},
        turn=3, phase="beginning", step="untap",
    )
    result = vlogger._format(entry)
    assert result is not None
    assert "Turn 3" in result
    assert "Bob" in result


def test_format_phase_change_step():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="phase_change",
        data={"turn": 1, "phase": "combat", "step": "declare_attackers", "active_player": "Alice"},
        turn=1, phase="combat", step="declare_attackers",
    )
    result = vlogger._format(entry)
    assert result is not None
    assert "Combat" in result and "Declare" in result


def test_format_game_end():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(
        event_type="game_end",
        data={"winner": "Alice", "reason": "life_total_zero"},
    )
    result = vlogger._format(entry)
    assert "GAME OVER" in result and "Alice" in result and "life_total_zero" in result


# ── T020c: priority_grant suppressed ─────────────────────────────────────────

def test_format_priority_grant_suppressed():
    vlogger = VerboseLogger("g", enabled=True)
    entry = _make_entry(event_type="priority_grant", data={"player": "Alice"})
    result = vlogger._format(entry)
    assert result is None, "priority_grant should be suppressed (return None)"


# ── T020d: enable/disable toggles ────────────────────────────────────────────

def test_enable_disable_toggle():
    vlogger = VerboseLogger("g", enabled=False)
    assert not vlogger.is_enabled
    vlogger.enable()
    assert vlogger.is_enabled
    vlogger.disable()
    assert not vlogger.is_enabled


# ── T021: TranscriptRecorder listener mechanism ───────────────────────────────

def test_recorder_notifies_listener():
    recorder = TranscriptRecorder("test-listener-game")
    received: list[TranscriptEntry] = []
    recorder.register_listener(received.append)

    recorder.record_cast("Alice", "Lightning Bolt", ["Bob"], 1, "precombat_main", "main")
    assert len(received) == 1
    assert received[0].event_type == "cast"
    assert received[0].data["card_name"] == "Lightning Bolt"


def test_recorder_multiple_listeners():
    recorder = TranscriptRecorder("test-multi-listener")
    log1: list = []
    log2: list = []
    recorder.register_listener(log1.append)
    recorder.register_listener(log2.append)

    recorder.record_draw("Alice", 1, "beginning", "draw")
    assert len(log1) == 1 and len(log2) == 1


def test_recorder_listener_exception_does_not_crash():
    """A broken listener must not crash the game."""
    recorder = TranscriptRecorder("test-broken-listener")

    def bad_listener(entry):
        raise RuntimeError("listener exploded")

    recorder.register_listener(bad_listener)
    # Should not raise
    recorder.record_draw("Alice", 1, "beginning", "draw")
    assert len(recorder.get_all()) == 1


# ── T021 integration: verbose=False game produces no log output ───────────────

def test_verbose_false_produces_no_log_output(caplog):
    """When verbose is disabled, no lines appear in the mtg_engine.verbose logger."""
    recorder = TranscriptRecorder("silent-game")
    vlogger = VerboseLogger("silent-game", enabled=False)
    recorder.register_listener(vlogger.on_event)

    with caplog.at_level(logging.INFO, logger="mtg_engine.verbose"):
        recorder.record_cast("Alice", "Forest", [], 1, "precombat_main", "main")
        recorder.record_attack("Alice", "Grizzly Bears", "Bob", 1, "combat", "declare_attackers")
        recorder.record_phase_change(2, "beginning", "untap", "Bob")
        recorder.record_game_end("Alice", "life_total_zero", 2, "beginning", "untap")

    assert caplog.text == "", "verbose=False must produce zero log output"


def test_verbose_true_produces_log_output(caplog):
    """When verbose is enabled, events appear in the mtg_engine.verbose logger."""
    recorder = TranscriptRecorder("loud-game")
    vlogger = VerboseLogger("loud-game", enabled=True)
    recorder.register_listener(vlogger.on_event)

    with caplog.at_level(logging.INFO, logger="mtg_engine.verbose"):
        recorder.record_cast("Alice", "Lightning Bolt", ["Bob"], 1, "precombat_main", "main")

    assert "Lightning Bolt" in caplog.text


# ── New recorder methods ──────────────────────────────────────────────────────

def test_record_life_change():
    recorder = TranscriptRecorder("lc-game")
    recorder.record_life_change("Bob", -3, "Lightning Bolt", 17, 1, "precombat_main", "main")
    entries = recorder.get_all()
    assert entries[0].event_type == "life_change"
    assert entries[0].data["delta"] == -3
    assert entries[0].data["new_total"] == 17


def test_record_life_change_zero_delta_skipped():
    recorder = TranscriptRecorder("lc-zero-game")
    recorder.record_life_change("Bob", 0, "nothing", 20, 1, "precombat_main", "main")
    assert len(recorder.get_all()) == 0


def test_record_draw():
    recorder = TranscriptRecorder("draw-game")
    recorder.record_draw("Alice", 1, "beginning", "draw")
    entries = recorder.get_all()
    assert entries[0].event_type == "draw"
    assert entries[0].data["player"] == "Alice"


def test_record_game_end():
    recorder = TranscriptRecorder("end-game")
    recorder.record_game_end("Alice", "life_total_zero", 5, "combat", "combat_damage")
    entries = recorder.get_all()
    assert entries[0].event_type == "game_end"
    assert entries[0].data["winner"] == "Alice"
    assert entries[0].data["reason"] == "life_total_zero"
