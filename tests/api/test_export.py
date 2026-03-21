"""Tests for Phase 6 export functionality."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    get_manager()._games.clear()
    export_store.clear()
    yield
    get_manager()._games.clear()
    export_store.clear()


def _create_game(seed: int = 1) -> str:
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Forest"] * 60,
        "deck2": ["Forest"] * 60,
        "seed": seed,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["game_id"]


# ─── TASK-20: Snapshots ───────────────────────────────────────────────────────

def test_snapshot_recorder_basic():
    from mtg_engine.export.snapshots import SnapshotRecorder
    from mtg_engine.models.game import GameState, PlayerState, Phase, Step
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    gs = GameState(game_id="g1", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    recorder = SnapshotRecorder("g1")
    snap = recorder.record_snapshot(gs, [{"action_type": "pass"}])
    assert snap.game_id == "g1"
    assert snap.turn == 1
    recorder.finalize_snapshot({"action_type": "pass"}, "p1")
    all_snaps = recorder.get_all()
    assert len(all_snaps) == 1
    assert all_snaps[0].action_taken == {"action_type": "pass"}


def test_snapshot_jsonl_format():
    from mtg_engine.export.snapshots import SnapshotRecorder
    from mtg_engine.models.game import GameState, PlayerState
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    gs = GameState(game_id="g1", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    recorder = SnapshotRecorder("g1")
    recorder.record_snapshot(gs, [])
    recorder.finalize_snapshot({"action_type": "pass"}, "p1")
    jsonl = recorder.to_jsonl()
    import json
    line = json.loads(jsonl.strip().split("\n")[0])
    assert line["game_id"] == "g1"
    assert "game_state" in line


# ─── TASK-21: Transcript ─────────────────────────────────────────────────────

def test_transcript_recorder_events():
    from mtg_engine.export.transcript import TranscriptRecorder
    tr = TranscriptRecorder("g1")
    tr.record_phase_change(1, "beginning", "untap")
    tr.record_priority_grant("p1", 1, "beginning", "untap")
    tr.record_cast("p1", "Lightning Bolt", ["p2"], 1, "precombat_main", "main")
    entries = tr.get_all()
    assert len(entries) == 3
    types = [e.event_type for e in entries]
    assert "phase_change" in types
    assert "priority_grant" in types
    assert "cast" in types


def test_transcript_seq_ordering():
    from mtg_engine.export.transcript import TranscriptRecorder
    tr = TranscriptRecorder("g1")
    for i in range(5):
        tr.record_priority_grant("p1", 1, "beginning", "upkeep")
    entries = tr.get_all()
    seqs = [e.seq for e in entries]
    assert seqs == sorted(seqs)
    assert seqs[0] == 1


def test_transcript_natural_language():
    from mtg_engine.export.transcript import TranscriptRecorder
    tr = TranscriptRecorder("g1")
    tr.record_zone_change("Grizzly Bears", "battlefield", "graveyard", "p1", 2, "combat", "combat_damage")
    entry = tr.get_all()[0]
    assert "Grizzly Bears" in entry.description
    assert "battlefield" in entry.description
    assert "graveyard" in entry.description


def test_transcript_sba_event():
    from mtg_engine.export.transcript import TranscriptRecorder
    tr = TranscriptRecorder("g1")
    tr.record_sba("lethal_damage", "Grizzly Bears has lethal damage", 1, "combat", "combat_damage")
    entry = tr.get_all()[0]
    assert entry.event_type == "sba"
    assert "Grizzly Bears" in entry.description


# ─── TASK-22: Rules Q&A ───────────────────────────────────────────────────────

def test_qa_at_least_20_templates():
    from mtg_engine.export.rules_qa import TEMPLATES
    assert len(TEMPLATES) >= 20


def test_qa_lethal_damage():
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_sba("lethal_damage", 1, creature_name="Grizzly Bears", damage_marked=3, toughness=2)
    pairs = rec.get_all()
    assert len(pairs) == 1
    assert "Grizzly Bears" in pairs[0].question
    assert "704.5g" in pairs[0].rules_cited


def test_qa_deathtouch():
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_damage("Deadly Recluse", ["deathtouch"], "Serra Angel", 1, 1)
    pairs = rec.get_all()
    assert any("deathtouch" in p.answer.lower() or "702.2" in str(p.rules_cited) for p in pairs)


def test_qa_trample():
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_trample("Scaled Behemoth", "Llanowar Elves", 6, 1, 5, 1)
    pairs = rec.get_all()
    assert len(pairs) == 1
    assert "Scaled Behemoth" in pairs[0].question
    assert "702.19b" in pairs[0].rules_cited


def test_qa_lifelink():
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_damage("Serra Angel", ["lifelink"], "p2", 4, 1)
    pairs = rec.get_all()
    assert any("lifelink" in p.answer.lower() for p in pairs)


def test_qa_schema_matches_req_d08():
    """All Q&A pairs must have required fields per REQ-D08."""
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_sba("legend_rule", 2, card_name="Jace, the Mind Sculptor")
    pair = rec.get_all()[0]
    assert hasattr(pair, "question") and pair.question
    assert hasattr(pair, "answer") and pair.answer
    assert hasattr(pair, "game_id")
    assert hasattr(pair, "turn")
    assert hasattr(pair, "trigger_event")
    assert hasattr(pair, "cards_involved")
    assert hasattr(pair, "rules_cited") and pair.rules_cited


def test_qa_uses_real_card_names():
    """REQ-D09: Q&A questions use real card names from context."""
    from mtg_engine.export.rules_qa import RulesQARecorder
    rec = RulesQARecorder("g1")
    rec.on_sba("lethal_damage", 1, creature_name="Tarmogoyf", damage_marked=5, toughness=4)
    pair = rec.get_all()[0]
    assert "Tarmogoyf" in pair.question


# ─── TASK-23: Export endpoints ────────────────────────────────────────────────

def test_export_snapshots_endpoint():
    game_id = _create_game()
    resp = client.get(f"/export/{game_id}/snapshots")
    assert resp.status_code == 200
    # Empty JSONL is fine initially


def test_export_transcript_endpoint():
    game_id = _create_game()
    resp = client.get(f"/export/{game_id}/transcript")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_export_rules_qa_endpoint():
    game_id = _create_game()
    resp = client.get(f"/export/{game_id}/rules-qa")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_export_outcome_endpoint():
    game_id = _create_game()
    resp = client.get(f"/export/{game_id}/outcome")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "game_id" in data
    assert "total_turns" in data
    assert "player_1_final_life" in data
    assert "player_2_final_life" in data


def test_delete_game_does_not_crash_without_mongodb():
    """DELETE should succeed even if MongoDB is unavailable. REQ-P04."""
    game_id = _create_game()
    resp = client.delete(f"/game/{game_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "deleted"


def test_snapshot_action_taken_attached():
    """finalize_snapshot attaches action correctly."""
    from mtg_engine.export.snapshots import SnapshotRecorder
    from mtg_engine.models.game import GameState, PlayerState
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    gs = GameState(game_id="g2", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    rec = SnapshotRecorder("g2")
    rec.record_snapshot(gs, [{"action_type": "pass"}])
    rec.finalize_snapshot({"action_type": "pass", "description": "Pass priority"}, "p1")
    snaps = rec.get_all()
    assert snaps[0].action_taken is not None
    assert snaps[0].action_taken_by == "p1"
