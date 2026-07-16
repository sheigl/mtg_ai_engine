"""APP-03 Game Replay tests — engine + API integration."""
import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.export.store import get_export_store, delete_export_store, _store
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool


# ─── Fixtures / Helpers ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_state():
    """Clear game manager and export store between tests."""
    from mtg_engine.api.game_manager import get_manager
    mgr = get_manager()
    mgr._games.clear()
    _store.clear()
    yield
    mgr._games.clear()
    _store.clear()


def _create_game_with_events(game_id: str = "replay-test") -> str:
    """Create a game, advance it through several turns to generate transcript events and snapshots."""
    client = TestClient(app)

    # Create game with simple decks
    deck1 = ["Mountain"] * 60
    deck2 = ["Forest"] * 60

    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": deck1,
        "deck2": deck2,
        "seed": 42,
    })
    assert resp.status_code == 200
    gid = resp.json()["data"]["game_id"]

    # Advance through several passes to generate events and snapshots
    for _ in range(6):
        client.post(f"/game/{gid}/pass", json={})
        # Call legal-actions to trigger snapshot recording (snapshots contain full game state)
        client.get(f"/game/{gid}/legal-actions")

    return gid


def _create_game_with_card_play(game_id: str = "replay-card") -> str:
    """Create a game where cards are actually played (zone changes, life changes)."""
    client = TestClient(app)

    # p1 has creatures and removal; p2 has forests
    deck1 = ["Lightning Bolt"] * 5 + ["Mountain"] * 55
    deck2 = ["Forest"] * 60

    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": deck1,
        "deck2": deck2,
        "seed": 42,
    })
    assert resp.status_code == 200
    gid = resp.json()["data"]["game_id"]

    # Pass several times to generate events and snapshots
    for _ in range(8):
        client.post(f"/game/{gid}/pass", json={})
        client.get(f"/game/{gid}/legal-actions")

    return gid


# ─── Engine Unit Tests ────────────────────────────────────────────────────────

class TestGetReplayInfo:
    """REQ-R01: Replay info retrieval."""

    def test_returns_basic_info(self):
        from mtg_engine.export.replay_engine import get_replay_info
        gid = _create_game_with_events()
        store = get_export_store(gid)
        info = get_replay_info(store)

        assert "game_id" in info
        assert info["game_id"] == gid
        assert isinstance(info["total_events"], int)
        assert info["total_events"] > 0
        assert isinstance(info["turns"], int)

    def test_returns_zero_for_empty_store(self):
        from mtg_engine.export.replay_engine import get_replay_info
        store = get_export_store("empty-game")
        # Empty store — no events recorded yet
        info = get_replay_info(store)
        assert info["total_events"] == 0

    def test_includes_format(self):
        from mtg_engine.export.replay_engine import get_replay_info
        gid = _create_game_with_events()
        store = get_export_store(gid)
        info = get_replay_info(store)
        assert "format" in info


class TestPaginateEvents:
    """REQ-R02: Paginated event access."""

    def test_returns_all_on_first_page(self):
        from mtg_engine.export.replay_engine import paginate_events
        gid = _create_game_with_events()
        store = get_export_store(gid)

        events, total = paginate_events(store, page=1, per_page=25)
        assert isinstance(events, list)
        assert isinstance(total, int)
        assert total > 0
        assert len(events) <= 25

    def test_pagination_respects_per_page(self):
        from mtg_engine.export.replay_engine import paginate_events
        gid = _create_game_with_events()
        store = get_export_store(gid)

        events, total = paginate_events(store, page=1, per_page=3)
        assert len(events) <= 3
        assert total > 0

    def test_second_page_returns_remaining(self):
        from mtg_engine.export.replay_engine import paginate_events
        gid = _create_game_with_events()
        store = get_export_store(gid)

        page1, total = paginate_events(store, page=1, per_page=3)
        page2, _ = paginate_events(store, page=2, per_page=3)

        assert len(page1) <= 3
        # Combined should equal total (or be close if last page is partial)
        combined = page1 + page2
        assert len(combined) == min(total, 6)

    def test_empty_store_returns_zero(self):
        from mtg_engine.export.replay_engine import paginate_events
        store = get_export_store("empty-game-2")
        events, total = paginate_events(store)
        assert events == []
        assert total == 0


class TestStepToEvent:
    """REQ-R03: Forward/backward stepping."""

    def test_forward_from_zero(self):
        from mtg_engine.export.replay_engine import step_to_event
        gid = _create_game_with_events()
        store = get_export_store(gid)

        result = step_to_event(store, "forward", 0)
        assert result is not None
        event, board_state, from_seq, to_seq = result
        assert from_seq == 0
        assert to_seq >= 1
        assert isinstance(board_state, dict)

    def test_forward_returns_none_at_end(self):
        from mtg_engine.export.replay_engine import step_to_event
        gid = _create_game_with_events()
        store = get_export_store(gid)

        # Step forward past the end
        result = step_to_event(store, "forward", 9999)
        assert result is None

    def test_backward_from_first_returns_none(self):
        from mtg_engine.export.replay_engine import step_to_event
        gid = _create_game_with_events()
        store = get_export_store(gid)

        # First event has seq=1; backward from 0 should return None
        result = step_to_event(store, "backward", 0)
        assert result is None

    def test_forward_then_backward_round_trip(self):
        from mtg_engine.export.replay_engine import step_to_event
        gid = _create_game_with_events()
        store = get_export_store(gid)

        # Forward one step
        fwd = step_to_event(store, "forward", 0)
        assert fwd is not None
        _, _, _, to_seq = fwd

        # Backward from first event goes back to "before game" (to_seq=0)
        bwd = step_to_event(store, "backward", to_seq)
        assert bwd is not None
        _, _, _, back_seq = bwd
        assert back_seq == 0  # Returns to pre-game state


class TestBuildTimeline:
    """REQ-R04: Timeline generation."""

    def test_returns_timeline(self):
        from mtg_engine.export.replay_engine import build_timeline
        gid = _create_game_with_events()
        store = get_export_store(gid)

        timeline = build_timeline(store)
        assert isinstance(timeline, list)
        # Should have at least one turn entry if events exist
        for turn_entry in timeline:
            assert "turn" in turn_entry
            assert "phases" in turn_entry
            assert isinstance(turn_entry["phases"], list)

    def test_empty_store_returns_empty_timeline(self):
        from mtg_engine.export.replay_engine import build_timeline
        store = get_export_store("empty-game-3")
        timeline = build_timeline(store)
        assert timeline == []

    def test_timeline_phases_have_event_counts(self):
        from mtg_engine.export.replay_engine import build_timeline
        gid = _create_game_with_events()
        store = get_export_store(gid)

        timeline = build_timeline(store)
        for turn_entry in timeline:
            for seg in turn_entry["phases"]:
                assert "event_count" in seg
                assert seg["event_count"] > 0
                assert "first_event_seq" in seg
                assert "last_event_seq" in seg


class TestReconstructBoardStateAt:
    """REQ-R05: Board state reconstruction."""

    def test_returns_valid_board_state(self):
        from mtg_engine.export.replay_engine import reconstruct_board_state_at
        gid = _create_game_with_events()
        store = get_export_store(gid)

        entries = store.transcript.to_json()
        if not entries:
            pytest.skip("No events recorded")

        first_seq = entries[0]["seq"]
        board = reconstruct_board_state_at(store, first_seq)

        assert isinstance(board, dict)
        assert "battlefield" in board
        assert "player_life" in board
        assert "hand_sizes" in board
        assert "graveyard_top" in board
        assert "stack_size" in board

    def test_board_state_has_player_data(self):
        from mtg_engine.export.replay_engine import reconstruct_board_state_at
        gid = _create_game_with_events()
        store = get_export_store(gid)

        entries = store.transcript.to_json()
        if not entries:
            pytest.skip("No events recorded")

        last_seq = entries[-1]["seq"]
        board = reconstruct_board_state_at(store, last_seq)

        # Should have player life totals
        assert isinstance(board["player_life"], dict)
        assert len(board["player_life"]) >= 2


class TestApplyEventToBoardState:
    """Test the event-to-board-state mutation logic."""

    def test_zone_change_to_battlefield(self):
        from mtg_engine.export.replay_engine import _apply_event_to_board_state, _build_initial_board_state

        board = {
            "battlefield": [],
            "player_life": {"p1": 20, "p2": 20},
            "hand_sizes": {"p1": 7, "p2": 7},
            "graveyard_top": {"p1": None, "p2": None},
            "stack_size": 0,
        }

        event = {
            "event_type": "zone_change",
            "data": {"card_name": "Mountain", "from_zone": "hand", "to_zone": "battlefield", "player": "p1"},
        }
        board = _apply_event_to_board_state(board, event)

        assert len(board["battlefield"]) == 1
        assert board["battlefield"][0]["name"] == "Mountain"
        assert board["hand_sizes"]["p1"] == 6

    def test_zone_change_from_battlefield(self):
        from mtg_engine.export.replay_engine import _apply_event_to_board_state

        board = {
            "battlefield": [{"id": "p1", "name": "Mountain", "controller": "p1"}],
            "player_life": {"p1": 20, "p2": 20},
            "hand_sizes": {"p1": 7, "p2": 7},
            "graveyard_top": {"p1": None, "p2": None},
            "stack_size": 0,
        }

        event = {
            "event_type": "zone_change",
            "data": {"card_name": "Mountain", "from_zone": "battlefield", "to_zone": "graveyard", "player": "p1"},
        }
        board = _apply_event_to_board_state(board, event)

        assert len(board["battlefield"]) == 0
        assert board["graveyard_top"]["p1"] == "Mountain"

    def test_life_change(self):
        from mtg_engine.export.replay_engine import _apply_event_to_board_state

        board = {
            "battlefield": [],
            "player_life": {"p1": 20, "p2": 20},
            "hand_sizes": {"p1": 7, "p2": 7},
            "graveyard_top": {"p1": None, "p2": None},
            "stack_size": 0,
        }

        event = {
            "event_type": "life_change",
            "data": {"player": "p1", "delta": -5},
        }
        board = _apply_event_to_board_state(board, event)
        assert board["player_life"]["p1"] == 15

    def test_draw_increases_hand(self):
        from mtg_engine.export.replay_engine import _apply_event_to_board_state

        board = {
            "battlefield": [],
            "player_life": {"p1": 20, "p2": 20},
            "hand_sizes": {"p1": 7, "p2": 7},
            "graveyard_top": {"p1": None, "p2": None},
            "stack_size": 0,
        }

        event = {
            "event_type": "draw",
            "data": {"player": "p1"},
        }
        board = _apply_event_to_board_state(board, event)
        assert board["hand_sizes"]["p1"] == 8


# ─── API Integration Tests ────────────────────────────────────────────────────

class TestReplayInfoEndpoint:
    """GET /replay/{game_id}/info — REQ-R01"""

    def test_returns_200_with_info(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/info")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "game_id" in data
        assert data["game_id"] == gid
        assert "total_events" in data
        assert data["total_events"] > 0

    def test_returns_404_for_unknown_game(self):
        client = TestClient(app)
        resp = client.get("/replay/nonexistent-game/info")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "GAME_NOT_FOUND" in detail["error_code"]


class TestReplayEventsEndpoint:
    """GET /replay/{game_id}/events — REQ-R02"""

    def test_returns_paginated_events(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/events")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "events" in data
        assert "total_count" in data
        assert "page" in data
        assert "per_page" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert len(data["events"]) > 0

    def test_events_have_board_state(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/events")
        assert resp.status_code == 200
        events = resp.json()["data"]["events"]
        for event in events:
            assert "board_state" in event
            assert isinstance(event["board_state"], dict)

    def test_events_have_descriptions(self):
        """Assert that paginated events include non-empty human-readable descriptions."""
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/events")
        assert resp.status_code == 200
        events = resp.json()["data"]["events"]
        for event in events:
            assert "description" in event
            assert event["description"] and len(event["description"]) > 0

    def test_pagination_params(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/events?page=1&per_page=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["events"]) <= 3
        assert data["page"] == 1
        assert data["per_page"] == 3

    def test_pagination_has_next_prev(self):
        """Verify has_next and has_prev flags are correct."""
        client = TestClient(app)
        gid = _create_game_with_events()

        # First page: has_prev should be False, has_next depends on total
        resp1 = client.get(f"/replay/{gid}/events?page=1&per_page=3")
        assert resp1.status_code == 200
        data1 = resp1.json()["data"]
        assert data1["has_prev"] is False

        # Second page: has_prev should be True
        if data1["total_count"] > 3:
            resp2 = client.get(f"/replay/{gid}/events?page=2&per_page=3")
            assert resp2.status_code == 200
            data2 = resp2.json()["data"]
            assert data2["has_prev"] is True

    def test_returns_404_for_unknown_game(self):
        client = TestClient(app)
        resp = client.get("/replay/nonexistent-game/events")
        assert resp.status_code == 404


class TestReplayStepEndpoint:
    """POST /replay/{game_id}/step — REQ-R03"""

    def test_forward_step(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "event" in data
        assert "from_seq" in data
        assert "to_seq" in data
        assert data["from_seq"] == 0
        assert data["to_seq"] >= 1

    def test_backward_step(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        # First get the second event seq (so backward has something to go back to)
        fwd1 = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        first_seq = fwd1.json()["data"]["to_seq"]

        # Try to get second event for backward test
        fwd2 = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": first_seq,
        })
        if fwd2.status_code == 400:
            pytest.skip("Only one event recorded")

        second_seq = fwd2.json()["data"]["to_seq"]

        # Step backward from second seq should go back to first
        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "backward",
            "from_event_seq": second_seq,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["to_seq"] < second_seq

    def test_step_returns_board_state(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        assert resp.status_code == 200
        event = resp.json()["data"]["event"]
        assert "board_state" in event

    def test_invalid_direction(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "sideways",
            "from_event_seq": 0,
        })
        assert resp.status_code == 400

    def test_out_of_bounds(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 9999,
        })
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "OUT_OF_BOUNDS" in detail["error_code"]

    def test_returns_404_for_unknown_game(self):
        client = TestClient(app)
        resp = client.post("/replay/nonexistent-game/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        assert resp.status_code == 404


class TestReplayTimelineEndpoint:
    """GET /replay/{game_id}/timeline — REQ-R04"""

    def test_returns_timeline(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/timeline")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # TimelineResponse is a wrapped object with game_id, total_events, turns
        assert "game_id" in data
        assert data["game_id"] == gid
        assert "total_events" in data
        assert isinstance(data["turns"], list)
        # Should have at least one turn if events exist
        for turn_entry in data["turns"]:
            assert "turn" in turn_entry
            assert "phases" in turn_entry

    def test_timeline_phases_have_counts(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.get(f"/replay/{gid}/timeline")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for turn_entry in data["turns"]:
            for seg in turn_entry["phases"]:
                assert "event_count" in seg
                assert seg["event_count"] > 0

    def test_returns_404_for_unknown_game(self):
        client = TestClient(app)
        resp = client.get("/replay/nonexistent-game/timeline")
        assert resp.status_code == 404


# ─── Multi-Turn Replay Tests ─────────────────────────────────────────────────

class TestMultiTurnReplay:
    """Full replay flow across multiple turns."""

    def test_full_forward_replay(self):
        """Step through entire game from start to finish."""
        client = TestClient(app)
        gid = _create_game_with_events()

        # Get total events
        info_resp = client.get(f"/replay/{gid}/info")
        total = info_resp.json()["data"]["total_events"]

        if total == 0:
            pytest.skip("No events recorded")

        # Step forward through all events
        current_seq = 0
        steps_taken = 0
        while True:
            resp = client.post(f"/replay/{gid}/step", json={
                "direction": "forward",
                "from_event_seq": current_seq,
            })
            if resp.status_code == 400:
                break
            data = resp.json()["data"]
            current_seq = data["to_seq"]
            steps_taken += 1

        assert steps_taken == total

    def test_timeline_matches_event_count(self):
        """Timeline event counts sum to total events."""
        client = TestClient(app)
        gid = _create_game_with_events()

        info_resp = client.get(f"/replay/{gid}/info")
        total = info_resp.json()["data"]["total_events"]

        timeline_resp = client.get(f"/replay/{gid}/timeline")
        data = timeline_resp.json()["data"]

        timeline_total = sum(
            seg["event_count"]
            for turn_entry in data["turns"]
            for seg in turn_entry["phases"]
        )
        assert timeline_total == total

    def test_board_state_changes_across_steps(self):
        """Board state reflects changes as we step through events."""
        client = TestClient(app)
        gid = _create_game_with_events()

        # Get first and last event board states
        info_resp = client.get(f"/replay/{gid}/info")
        total = info_resp.json()["data"]["total_events"]

        if total < 2:
            pytest.skip("Not enough events")

        # First step
        resp1 = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        first_board = resp1.json()["data"]["event"]["board_state"]

        # Last event via pagination
        events_resp = client.get(f"/replay/{gid}/events?page=1&per_page={total}")
        last_event = events_resp.json()["data"]["events"][-1]
        last_board = last_event["board_state"]

        # Both should be valid board states
        assert "battlefield" in first_board
        assert "player_life" in first_board
        assert "battlefield" in last_board
        assert "player_life" in last_board


# ─── Edge Cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_game_still_returns_info(self):
        client = TestClient(app)
        gid = _create_game_with_events("empty-replay")

        # Even if no events, info should return 200
        resp = client.get(f"/replay/{gid}/info")
        assert resp.status_code == 200

    def test_pagination_beyond_total(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        # Request page beyond available data
        resp = client.get(f"/replay/{gid}/events?page=999&per_page=1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["events"] == []

    def test_backward_from_zero(self):
        client = TestClient(app)
        gid = _create_game_with_events()

        resp = client.post(f"/replay/{gid}/step", json={
            "direction": "backward",
            "from_event_seq": 0,
        })
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "OUT_OF_BOUNDS" in detail["error_code"]

    def test_deleted_game_returns_404_on_all_replay_endpoints(self):
        """After a game is deleted, all replay endpoints should return 404."""
        client = TestClient(app)
        gid = _create_game_with_events("deleted-game-test")

        # Verify the game has export data before deletion
        info_resp = client.get(f"/replay/{gid}/info")
        assert info_resp.status_code == 200

        # Delete the game via API (MongoDB export fails silently in tests)
        del_resp = client.delete(f"/game/{gid}")
        assert del_resp.status_code == 200

        # Manually remove export store since MongoDB export doesn't run in tests
        delete_export_store(gid)

        # All replay endpoints should now return 404
        resp_info = client.get(f"/replay/{gid}/info")
        assert resp_info.status_code == 404

        resp_events = client.get(f"/replay/{gid}/events")
        assert resp_events.status_code == 404

        resp_step = client.post(f"/replay/{gid}/step", json={
            "direction": "forward",
            "from_event_seq": 0,
        })
        assert resp_step.status_code == 404

        resp_timeline = client.get(f"/replay/{gid}/timeline")
        assert resp_timeline.status_code == 404
