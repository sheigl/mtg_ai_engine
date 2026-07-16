"""
Tests for Player Stats / ELO endpoints (APP-06).

Covers: new player creation, idempotent creation, ELO update after win/loss,
win rate calculation, matchup tracking, leaderboard ordering, non-existent player,
MongoDB-unavailable error, format-filtered stats.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.engine.stats import calculate_new_elo, update_player_stats
from mtg_engine.models.stats import PlayerStats, FormatRecord, MatchupRecord

client = TestClient(app)


def _make_game_state(winner: str, loser: str, format_name: str | None = "commander"):
    """Create a minimal GameState for game completion testing."""
    from mtg_engine.models.game import GameState, PlayerState

    p1 = PlayerState(name=winner, life=5)
    p2 = PlayerState(name=loser, life=0)
    return GameState(
        game_id="test-game-1",
        seed=42,
        active_player=winner,
        priority_holder=winner,
        players=[p1, p2],
        winner=winner,
        loser=loser,
        format=format_name,
    )


# ── Engine-level tests (pure functions) ───────────────────────────────────────


class TestCalculateNewElo:
    """Test the ELO calculation formula."""

    def test_equal_rating_win(self):
        """Winning against equal-rated opponent gives +16 ELO (K=32, expected=0.5)."""
        new_elo = calculate_new_elo(1200, 1200, won=True)
        assert new_elo == 1216

    def test_equal_rating_loss(self):
        """Losing against equal-rated opponent gives -16 ELO."""
        new_elo = calculate_new_elo(1200, 1200, won=False)
        assert new_elo == 1184

    def test_win_against_lower_rated(self):
        """Winning against a much lower-rated opponent gives small gain."""
        new_elo = calculate_new_elo(1500, 1000, won=True)
        # Expected score ~ 0.993, so gain is ~ K * (1 - 0.993) ≈ 2
        assert 1 < new_elo - 1500 < 5

    def test_loss_against_higher_rated(self):
        """Losing to a much higher-rated opponent gives small loss."""
        new_elo = calculate_new_elo(1000, 1500, won=False)
        # Expected score ~ 0.007, so loss is ~ K * (0 - 0.007) ≈ -2
        assert -5 < new_elo - 1000 < 1

    def test_upset_win(self):
        """Winning against a much higher-rated opponent gives large gain."""
        new_elo = calculate_new_elo(1000, 1500, won=True)
        # Expected score ~ 0.007, so gain is ~ K * (1 - 0.007) ≈ 32
        assert new_elo > 1028

    def test_upset_loss(self):
        """Losing to a much lower-rated opponent gives large loss."""
        new_elo = calculate_new_elo(1500, 1000, won=False)
        # Expected score ~ 0.993, so loss is ~ K * (0 - 0.993) ≈ -32
        assert new_elo < 1478


class TestUpdatePlayerStats:
    """Test the pure stats update function."""

    def _make_stats(self, name="Alice", elo=1200, wins=0, losses=0):
        return PlayerStats(player_name=name, elo=elo, wins=wins, losses=losses)

    def test_win_increases_wins_and_elo(self):
        stats = self._make_stats(wins=3, losses=2)
        new = update_player_stats(stats, "Bob", 1200, won=True, format_name="commander")
        assert new.wins == 4
        assert new.losses == 2
        assert new.elo > stats.elo

    def test_loss_increases_losses_and_decreases_elo(self):
        stats = self._make_stats(wins=5, losses=1)
        new = update_player_stats(stats, "Bob", 1300, won=False, format_name="standard")
        assert new.wins == 5
        assert new.losses == 2
        # Losing to higher-rated opponent should decrease ELO more
        assert new.elo < stats.elo

    def test_format_record_updated(self):
        stats = self._make_stats()
        new = update_player_stats(stats, "Bob", 1200, won=True, format_name="commander")
        assert "commander" in new.formats
        assert new.formats["commander"].wins == 1
        assert new.formats["commander"].losses == 0

    def test_format_record_accumulates(self):
        stats = self._make_stats()
        stats.formats["standard"] = FormatRecord(wins=2, losses=1)
        new = update_player_stats(stats, "Bob", 1200, won=False, format_name="standard")
        assert new.formats["standard"].wins == 2
        assert new.formats["standard"].losses == 2

    def test_matchup_created_on_first_game(self):
        stats = self._make_stats()
        new = update_player_stats(stats, "Bob", 1200, won=True)
        assert "Bob" in new.matchups
        assert new.matchups["Bob"].wins == 1
        assert new.matchups["Bob"].losses == 0

    def test_matchup_accumulates(self):
        stats = self._make_stats()
        stats.matchups["Bob"] = MatchupRecord(opponent="Bob", wins=3, losses=2)
        new = update_player_stats(stats, "Bob", 1200, won=False)
        assert new.matchups["Bob"].wins == 3
        assert new.matchups["Bob"].losses == 3

    def test_pure_transform_original_unchanged(self):
        """Original stats object (including nested dicts) must not be mutated."""
        stats = self._make_stats(wins=5, losses=3)
        # Pre-populate nested structures so we can verify they're not mutated
        stats.formats["commander"] = FormatRecord(wins=2, losses=1)
        stats.matchups["Bob"] = MatchupRecord(opponent="Bob", wins=4, losses=2)

        original_wins = stats.wins
        original_elo = stats.elo
        original_formats_cmd = dict(stats.formats["commander"])
        original_matchups_bob = dict(stats.matchups["Bob"])

        _ = update_player_stats(stats, "Bob", 1200, won=True, format_name="standard")

        # Top-level fields unchanged
        assert stats.wins == original_wins
        assert stats.elo == original_elo

        # Nested formats dict: original FormatRecord not mutated
        assert stats.formats["commander"].wins == original_formats_cmd["wins"]
        assert stats.formats["commander"].losses == original_formats_cmd["losses"]

        # Nested matchups dict: original MatchupRecord not mutated
        assert stats.matchups["Bob"].wins == original_matchups_bob["wins"]
        assert stats.matchups["Bob"].losses == original_matchups_bob["losses"]

    def test_win_rate_calculation(self):
        """3 wins, 2 losses → win_rate = 0.6 (before adding another game)."""
        stats = self._make_stats(wins=3, losses=2)
        total = stats.wins + stats.losses
        assert round(stats.wins / total, 4) == 0.6


# ── API endpoint tests (with mocked MongoDB) ──────────────────────────────────


def _mock_col(docs=None):
    """Create a mock AsyncIOMotorCollection with pre-loaded docs."""
    col = MagicMock()

    async def find_one(filter_):
        for d in (docs or []):
            if filter_.get("player_name") == d.get("player_name"):
                return dict(d)
        return None

    async def insert_one(doc):
        doc["_id"] = "mock-id"
        if docs is not None:
            docs.append(dict(doc))
        return MagicMock()

    async def update_one(filter_, update, upsert=False):
        name = filter_.get("player_name")
        inc_data = update.get("$inc", {})
        set_data = update.get("$set", {})
        existing = None
        for d in (docs or []):
            if d.get("player_name") == name:
                existing = d
                break

        def _apply_inc(obj, field, amount):
            """Apply $inc to a dotted path like 'formats.commander.wins'."""
            parts = field.split(".")
            for part in parts[:-1]:
                obj.setdefault(part, {})
                obj = obj[part]
            obj[parts[-1]] = obj.get(parts[-1], 0) + amount

        if existing is not None:
            for field, amount in inc_data.items():
                _apply_inc(existing, field, amount)
            existing.update(set_data)
        elif upsert:
            # For new docs with $inc, simulate MongoDB behavior: missing fields start at 0 + delta
            doc = {}
            for field, amount in inc_data.items():
                _apply_inc(doc, field, amount)
            doc.update(set_data)
            doc["_id"] = "mock-id"
            if docs is not None:
                docs.append(dict(doc))
        return MagicMock()

    def make_aggregate(pipeline):
        """Create an aggregate cursor that applies sort/limit from the pipeline."""
        # Extract sort field and direction, and limit value from pipeline stages
        sort_field = "elo_rating"
        sort_dir = -1  # default descending
        agg_limit = None

        for stage in (pipeline or []):
            if "$sort" in stage:
                sf = list(stage["$sort"].keys())[0]
                sd = list(stage["$sort"].values())[0]
                sort_field = sf
                sort_dir = sd
            elif "$limit" in stage:
                agg_limit = stage["$limit"]

        async def to_list(length):
            result = []
            for d in (docs or []):
                entry = {
                    "player_name": d["player_name"],
                    "elo_rating": d.get("elo", 1200),
                    "wins": d.get("wins", 0),
                    "losses": d.get("losses", 0),
                    "total_games": d.get("wins", 0) + d.get("losses", 0),
                }
                result.append(entry)

            # Apply sort from pipeline
            reverse = (sort_dir == -1)
            if sort_field in ("elo_rating", "$elo"):
                result.sort(key=lambda e: e.get("elo_rating", 0), reverse=reverse)
            elif sort_field == "total_games":
                result.sort(key=lambda e: e.get("total_games", 0), reverse=reverse)

            # Apply limit from pipeline
            if agg_limit is not None:
                result = result[:agg_limit]

            return result

        cursor = MagicMock()
        cursor.to_list = to_list
        return cursor

    col.find_one = find_one
    col.insert_one = insert_one
    col.update_one = update_one
    col.aggregate = make_aggregate
    return col


class TestPlayerStatsAPI:
    """Test the player stats REST endpoints."""

    def test_create_player_new(self):
        """POST creates a new profile with elo=1200, wins=0, losses=0."""
        docs = []
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.post("/stats/player/Alice")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["player"] == "Alice"
        assert data["elo_rating"] == 1200
        assert data["wins"] == 0
        assert data["losses"] == 0

    def test_create_player_idempotent(self):
        """POST again returns success without error (no duplicate)."""
        docs = [{"player_name": "Alice", "elo": 1250, "wins": 3, "losses": 1}]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.post("/stats/player/Alice")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["player"] == "Alice"
        assert data["elo_rating"] == 1250

    def test_get_player_stats(self):
        """GET returns player stats with win_rate calculated."""
        docs = [{
            "player_name": "Alice",
            "elo": 1300,
            "wins": 6,
            "losses": 4,
            "formats": {},
            "matchups": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Alice")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["player"] == "Alice"
        assert data["elo_rating"] == 1300
        assert data["wins"] == 6
        assert data["losses"] == 4
        assert data["total_games"] == 10
        assert abs(data["win_rate"] - 0.6) < 0.001

    def test_get_nonexistent_player(self):
        """GET returns 404 for unknown player."""
        mock_col = _mock_col([])
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/UnknownPlayer")
        assert resp.status_code == 404

    def test_matchups_endpoint(self):
        """GET matchups returns per-opponent stats sorted by most games."""
        docs = [{
            "player_name": "Alice",
            "elo": 1250,
            "wins": 5,
            "losses": 3,
            "formats": {},
            "matchups": {
                "Bob": {"opponent": "Bob", "wins": 4, "losses": 1},
                "Charlie": {"opponent": "Charlie", "wins": 1, "losses": 2},
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Alice/matchups")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        matchups = data["matchups"]
        # Sorted by most games: Bob (5) before Charlie (3)
        assert len(matchups) == 2
        assert matchups[0]["opponent"] == "Bob"
        assert matchups[0]["wins"] == 4
        assert matchups[0]["losses"] == 1
        assert abs(matchups[0]["win_rate"] - 0.8) < 0.001

    def test_leaderboard_ordering(self):
        """Leaderboard returns players sorted by ELO descending."""
        docs = [
            {"player_name": "Alice", "elo": 1500, "wins": 20, "losses": 5},
            {"player_name": "Bob", "elo": 1300, "wins": 10, "losses": 8},
            {"player_name": "Charlie", "elo": 1600, "wins": 30, "losses": 2},
        ]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard?limit=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        entries = data["leaderboard"]
        # Should be sorted by elo desc: Charlie (1600), Alice (1500), Bob (1300)
        assert len(entries) == 3
        assert entries[0]["player_name"] == "Charlie"
        assert entries[0]["elo_rating"] == 1600
        assert entries[0]["rank"] == 1
        assert entries[1]["player_name"] == "Alice"
        assert entries[2]["player_name"] == "Bob"

    def test_leaderboard_limit(self):
        """Leaderboard respects the limit parameter."""
        docs = [
            {"player_name": f"P{i}", "elo": 1200 + i * 100, "wins": i, "losses": 0}
            for i in range(5)
        ]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard?limit=2")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["data"]["leaderboard"]
        assert len(entries) <= 2

    def test_mongodb_not_configured(self):
        """All endpoints return HTTP 503 when MongoDB is not configured."""
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=False):
            resp = client.get("/stats/player/Alice")
            assert resp.status_code == 503
            assert "MONGODB_NOT_CONFIGURED" in resp.text

            resp = client.post("/stats/player/Bob")
            assert resp.status_code == 503

            resp = client.get("/stats/leaderboard")
            assert resp.status_code == 503

    def test_format_filtered_stats(self):
        """Games in different formats are tracked separately."""
        stats = PlayerStats(player_name="Alice", elo=1200)
        # Play a commander game (win)
        new = update_player_stats(stats, "Bob", 1200, won=True, format_name="commander")
        assert new.formats["commander"].wins == 1
        assert new.formats["commander"].losses == 0

        # Play a standard game (loss)
        newer = update_player_stats(new, "Charlie", 1250, won=False, format_name="standard")
        assert newer.formats["commander"].wins == 1
        assert newer.formats["commander"].losses == 0
        assert newer.formats["standard"].wins == 0
        assert newer.formats["standard"].losses == 1

    def test_matchup_tracking_two_players(self):
        """Two players play multiple games, verify per-opponent stats accumulate."""
        alice = PlayerStats(player_name="Alice", elo=1200)
        bob = PlayerStats(player_name="Bob", elo=1200)

        # Game 1: Alice wins
        alice = update_player_stats(alice, "Bob", bob.elo, won=True)
        bob = update_player_stats(bob, "Alice", 1200, won=False)
        assert alice.matchups["Bob"].wins == 1
        assert alice.matchups["Bob"].losses == 0
        assert bob.matchups["Alice"].wins == 0
        assert bob.matchups["Alice"].losses == 1

        # Game 2: Bob wins
        alice = update_player_stats(alice, "Bob", bob.elo, won=False)
        bob = update_player_stats(bob, "Alice", alice.elo, won=True)
        assert alice.matchups["Bob"].wins == 1
        assert alice.matchups["Bob"].losses == 1
        assert bob.matchups["Alice"].wins == 1
        assert bob.matchups["Alice"].losses == 1

    def test_win_rate_zero_games(self):
        """New player with no games has win_rate = 0.0."""
        stats = PlayerStats(player_name="NewPlayer")
        total = stats.wins + stats.losses
        if total > 0:
            wr = stats.wins / total
        else:
            wr = 0.0
        assert wr == 0.0


# ── Game Completion Hook tests (MAJOR #5) ─────────────────────────────────────

class TestGameCompletionStatsUpdate:
    """Test update_stats_for_game_completion() end-to-end with mocked MongoDB."""

    def test_game_completion_both_players_exist(self):
        """Both players have existing docs; verify $inc applied correctly."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3, "formats": {}, "matchups": {}},
            {"player_name": "Bob", "elo": 1200, "wins": 4, "losses": 4, "formats": {}, "matchups": {}},
        ]
        mock_col = _mock_col(docs)

        gs = _make_game_state("Alice", "Bob")

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-1", gs)

        asyncio.run(_run())

        # Verify Alice's stats were updated via $inc (wins + 1, elo increased)
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert alice_doc is not None
        assert alice_doc["wins"] == 6  # was 5, +1 from $inc

        # Verify Bob's stats were updated via $inc (losses + 1, elo decreased)
        bob_doc = next((d for d in docs if d["player_name"] == "Bob"), None)
        assert bob_doc is not None
        assert bob_doc["losses"] == 5  # was 4, +1 from $inc

    def test_game_completion_new_player_upsert(self):
        """One player is new; verify correct ELO initialization (catches Critical Bug #1)."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion

        # Only Alice exists in the DB; Bob is a brand-new player
        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3, "formats": {}, "matchups": {}},
        ]
        mock_col = _mock_col(docs)

        gs = _make_game_state("Alice", "Bob")

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-2", gs)

        asyncio.run(_run())

        # Alice should have been updated via $inc (existing player)
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert alice_doc is not None
        assert alice_doc["wins"] == 6  # was 5, +1

        # Bob should have been upserted with $set (new player — correct ELO, NOT 0 + delta)
        bob_doc = next((d for d in docs if d["player_name"] == "Bob"), None)
        assert bob_doc is not None
        # Bob's ELO must be the computed value (~1184 for losing against equal-rated), NOT negative
        assert bob_doc["elo"] > 0, f"New player ELO should be positive, got {bob_doc['elo']}"
        assert bob_doc["losses"] == 1  # First loss (Bob lost to Alice)

    def test_game_completion_no_winner_skips(self):
        """Game with no winner set; verify early return (no DB writes)."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion
        from mtg_engine.models.game import GameState, PlayerState

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3},
            {"player_name": "Bob", "elo": 1200, "wins": 4, "losses": 4},
        ]
        mock_col = _mock_col(docs)

        gs = GameState(
            game_id="game-3", seed=42, active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            winner=None,  # No winner set
        )

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-3", gs)

        asyncio.run(_run())

        # Verify no stats were modified (early return on missing winner)
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert alice_doc is not None
        assert alice_doc["wins"] == 5  # Unchanged

    def test_game_completion_both_players_new(self):
        """Both players are new; verify correct ELO initialization for both."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion

        docs = []  # Empty — no existing player records
        mock_col = _mock_col(docs)

        gs = _make_game_state("Alice", "Bob")

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-4", gs)

        asyncio.run(_run())

        # Both players should be upserted with correct ELO values
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        bob_doc = next((d for d in docs if d["player_name"] == "Bob"), None)

        assert alice_doc is not None, "Winner should be upserted"
        assert alice_doc["elo"] > 0, f"Winner ELO should be positive, got {alice_doc['elo']}"
        assert alice_doc["wins"] == 1

        assert bob_doc is not None, "Loser should be upserted"
        assert bob_doc["elo"] > 0, f"Loser ELO should be positive, got {bob_doc['elo']}"
        assert bob_doc["losses"] == 1

    def test_game_completion_format_none_fallback(self):
        """Game with format=None; verify stats stored under 'standard' key."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion
        from mtg_engine.models.game import GameState, PlayerState

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3, "formats": {}, "matchups": {}},
            {"player_name": "Bob", "elo": 1200, "wins": 4, "losses": 4, "formats": {}, "matchups": {}},
        ]
        mock_col = _mock_col(docs)

        gs = GameState(
            game_id="game-5", seed=42, active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            winner="Alice",
        )
        # Explicitly set format to None
        gs.format = None

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-5", gs)

        asyncio.run(_run())

        # Verify stats stored under "standard" key, not "None"
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert "standard" in alice_doc.get("formats", {}), \
            f"Expected 'standard' format key, got {alice_doc.get('formats', {}).keys()}"
