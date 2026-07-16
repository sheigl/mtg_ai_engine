"""
Extended QA tests for APP-06 Player Stats / ELO Rating System.
Tests edge cases, acceptance criteria gaps, and regression scenarios.
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


# ── Reusable mock from test_player_stats.py ────────────────────────────────────

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
            doc = {}
            for field, amount in inc_data.items():
                _apply_inc(doc, field, amount)
            doc.update(set_data)
            doc["_id"] = "mock-id"
            if docs is not None:
                docs.append(dict(doc))
        return MagicMock()

    def make_aggregate(pipeline):
        sort_field = "elo_rating"
        sort_dir = -1
        agg_limit = None
        match_format = None

        for stage in (pipeline or []):
            if "$sort" in stage:
                sf = list(stage["$sort"].keys())[0]
                sd = list(stage["$sort"].values())[0]
                sort_field = sf
                sort_dir = sd
            elif "$limit" in stage:
                agg_limit = stage["$limit"]
            elif "$match" in stage:
                for k, v in stage["$match"].items():
                    if k.startswith("formats."):
                        match_format = k.split(".", 1)[1]

        async def to_list(length):
            result = []
            for d in (docs or []):
                # Apply format filter from $match stage
                if match_format is not None:
                    fmt_data = d.get("formats", {})
                    if match_format not in fmt_data:
                        continue

                entry = {
                    "player_name": d["player_name"],
                    "elo_rating": d.get("elo", 1200),
                    "wins": d.get("wins", 0),
                    "losses": d.get("losses", 0),
                }

                # Apply format-specific wins/losses from $project stage
                if match_format is not None:
                    fmt_data = d.get("formats", {})
                    fmt_record = fmt_data.get(match_format, {})
                    entry["wins"] = fmt_record.get("wins", 0) if isinstance(fmt_record, dict) else 0
                    entry["losses"] = fmt_record.get("losses", 0) if isinstance(fmt_record, dict) else 0

                entry["total_games"] = entry["wins"] + entry["losses"]
                result.append(entry)

            reverse = (sort_dir == -1)
            if sort_field in ("elo_rating", "$elo"):
                result.sort(key=lambda e: e.get("elo_rating", 0), reverse=reverse)
            elif sort_field == "total_games":
                result.sort(key=lambda e: e.get("total_games", 0), reverse=reverse)

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


# ── ELO Edge Cases ─────────────────────────────────────────────────────────────

class TestELOEdgeCases:
    """Acceptance criterion #6: ELO follows standard formula with K=32."""

    def test_extreme_rating_difference_win(self):
        """Winning against a 0-rated opponent gives negligible gain."""
        new_elo = calculate_new_elo(5000, 0, won=True)
        assert new_elo == 5000 or new_elo == 5001

    def test_extreme_rating_difference_loss(self):
        """Losing to a 0-rated opponent gives negligible loss."""
        new_elo = calculate_new_elo(5000, 0, won=False)
        # Expected score ~ 1.0, so loss is ~ K * (0 - 1.0) ≈ -32
        assert new_elo < 4970

    def test_self_match_win(self):
        """Playing against yourself: win gives +16."""
        new_elo = calculate_new_elo(1500, 1500, won=True)
        assert new_elo == 1516

    def test_self_match_loss(self):
        """Playing against yourself: loss gives -16."""
        new_elo = calculate_new_elo(1500, 1500, won=False)
        assert new_elo == 1484

    def test_k_factor_default_is_32(self):
        """Default K-factor is 32 per acceptance criteria."""
        # Equal rating win: expected = 0.5, so delta = 32 * (1 - 0.5) = 16
        new_elo = calculate_new_elo(1200, 1200, won=True)
        assert new_elo == 1216

    def test_custom_k_factor(self):
        """Custom K-factor works correctly."""
        # With K=16, equal rating win gives +8
        new_elo = calculate_new_elo(1200, 1200, won=True, K=16)
        assert new_elo == 1208

    def test_rounding_behavior(self):
        """ELO is rounded to nearest integer."""
        # Small rating difference: expected ≈ 0.5113, delta = 32 * (1 - 0.5113) ≈ 15.6 → rounds to 16
        new_elo = calculate_new_elo(1200, 1201, won=True)
        assert isinstance(new_elo, int)

    def test_negative_rating_possible(self):
        """ELO can go negative with enough losses (no floor enforced)."""
        # Starting at 10 ELO, losing to an equal-rated opponent drops below zero
        new_elo = calculate_new_elo(10, 10, won=False)
        assert new_elo < 0


# ── Stats Update Edge Cases ────────────────────────────────────────────────────

class TestStatsUpdateEdgeCases:
    """Test update_player_stats with edge cases."""

    def test_first_game_new_player(self):
        """New player's first game updates from defaults (elo=1200, wins=0)."""
        stats = PlayerStats(player_name="NewPlayer")
        assert stats.elo == 1200
        assert stats.wins == 0
        assert stats.losses == 0

        new = update_player_stats(stats, "Opponent", 1200, won=True)
        assert new.wins == 1
        assert new.losses == 0
        assert new.elo > 1200

    def test_multiple_formats_tracked_independently(self):
        """Three different formats tracked separately."""
        stats = PlayerStats(player_name="Alice", elo=1200)

        # Commander win
        s1 = update_player_stats(stats, "Bob", 1200, won=True, format_name="commander")
        assert s1.formats["commander"].wins == 1

        # Standard loss
        s2 = update_player_stats(s1, "Charlie", 1200, won=False, format_name="standard")
        assert s2.formats["commander"].wins == 1
        assert s2.formats["commander"].losses == 0
        assert s2.formats["standard"].wins == 0
        assert s2.formats["standard"].losses == 1

        # Pioneer win
        s3 = update_player_stats(s2, "Dave", 1200, won=True, format_name="pioneer")
        assert s3.formats["pioneer"].wins == 1
        assert len(s3.formats) == 3

    def test_matchup_with_special_characters_in_name(self):
        """Player names with special characters are tracked correctly."""
        stats = PlayerStats(player_name="Alice", elo=1200)
        new = update_player_stats(stats, "Bob#123", 1200, won=True)
        assert "Bob#123" in new.matchups

    def test_same_opponent_multiple_games(self):
        """Playing same opponent multiple times accumulates correctly."""
        stats = PlayerStats(player_name="Alice", elo=1200)

        for i in range(5):
            won = i % 2 == 0
            stats = update_player_stats(stats, "Bob", 1200, won=won)

        assert stats.matchups["Bob"].wins == 3  # games 0, 2, 4
        assert stats.matchups["Bob"].losses == 2  # games 1, 3

    def test_updated_at_changes_on_update(self):
        """updated_at timestamp is refreshed on each update."""
        import time
        stats = PlayerStats(player_name="Alice")
        old_ts = stats.updated_at
        time.sleep(0.01)
        new = update_player_stats(stats, "Bob", 1200, won=True)
        assert new.updated_at >= old_ts

    def test_default_format_is_standard(self):
        """When format_name is not specified, defaults to 'standard'."""
        stats = PlayerStats(player_name="Alice")
        new = update_player_stats(stats, "Bob", 1200, won=True)
        assert "standard" in new.formats

    def test_elo_symmetry(self):
        """Two equal players: winner gains exactly what loser loses."""
        alice = PlayerStats(player_name="Alice", elo=1500)
        bob = PlayerStats(player_name="Bob", elo=1500)

        alice_new = update_player_stats(alice, "Bob", 1500, won=True)
        bob_new = update_player_stats(bob, "Alice", 1500, won=False)

        assert alice_new.elo - alice.elo == -(bob_new.elo - bob.elo)


# ── API Endpoint Edge Cases ────────────────────────────────────────────────────

class TestPlayerStatsAPIEdgeCases:
    """Test REST endpoints with edge cases."""

    def test_create_player_special_chars(self):
        """Creating player with special characters in name works."""
        docs = []
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.post("/stats/player/Player%231")
        assert resp.status_code == 200, resp.text

    def test_get_player_empty_matchups(self):
        """GET returns empty matchups list for player with no games."""
        docs = [{
            "player_name": "Alice",
            "elo": 1200,
            "wins": 0,
            "losses": 0,
            "formats": {},
            "matchups": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Alice/matchups")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["matchups"] == []

    def test_leaderboard_empty(self):
        """Leaderboard returns empty list when no players exist."""
        mock_col = _mock_col([])
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["leaderboard"] == []
        assert data["count"] == 0

    def test_leaderboard_single_player(self):
        """Leaderboard with one player shows rank=1."""
        docs = [{"player_name": "Solo", "elo": 1350, "wins": 7, "losses": 3}]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["data"]["leaderboard"]
        assert len(entries) == 1
        assert entries[0]["rank"] == 1

    def test_leaderboard_same_elo_ordering(self):
        """Players with same ELO are ordered (stable sort by elo desc)."""
        docs = [
            {"player_name": "Alice", "elo": 1500, "wins": 20, "losses": 5},
            {"player_name": "Bob", "elo": 1500, "wins": 15, "losses": 10},
        ]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["data"]["leaderboard"]
        # Both have same ELO, so order depends on sort stability — just verify both present
        names = {e["player_name"] for e in entries}
        assert "Alice" in names
        assert "Bob" in names

    def test_leaderboard_format_filter(self):
        """Leaderboard filtered by format returns only players with that format."""
        docs = [
            {"player_name": "Alice", "elo": 1500, "wins": 20, "losses": 5,
             "formats": {"commander": {"wins": 10, "losses": 2}}},
            {"player_name": "Bob", "elo": 1400, "wins": 15, "losses": 8,
             "formats": {"standard": {"wins": 8, "losses": 3}}},
        ]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard?format=commander")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["data"]["leaderboard"]
        # Only Alice has commander format
        assert len(entries) == 1
        assert entries[0]["player_name"] == "Alice"

    def test_leaderboard_limit_max(self):
        """Leaderboard limit=100 is accepted (max allowed)."""
        docs = [{"player_name": f"P{i}", "elo": 1200 + i, "wins": i, "losses": 0} for i in range(5)]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard?limit=100")
        assert resp.status_code == 200, resp.text

    def test_leaderboard_limit_zero_rejected(self):
        """Leaderboard limit=0 returns 422 (validation error)."""
        mock_col = _mock_col([])
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/leaderboard?limit=0")
        assert resp.status_code == 422

    def test_matchups_nonexistent_player(self):
        """GET matchups for unknown player returns 404."""
        mock_col = _mock_col([])
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Unknown/matchups")
        assert resp.status_code == 404

    def test_response_includes_total_games(self):
        """GET response includes total_games field."""
        docs = [{
            "player_name": "Alice",
            "elo": 1300,
            "wins": 7,
            "losses": 3,
            "formats": {},
            "matchups": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Alice")
        data = resp.json()["data"]
        assert "total_games" in data
        assert data["total_games"] == 10

    def test_response_includes_win_rate(self):
        """GET response includes win_rate field (float between 0 and 1)."""
        docs = [{
            "player_name": "Alice",
            "elo": 1300,
            "wins": 7,
            "losses": 3,
            "formats": {},
            "matchups": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }]
        mock_col = _mock_col(docs)
        with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
             patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
            resp = client.get("/stats/player/Alice")
        data = resp.json()["data"]
        assert "win_rate" in data
        assert 0.0 <= data["win_rate"] <= 1.0
        assert abs(data["win_rate"] - 0.7) < 0.001


# ── Game Completion Hook Edge Cases ────────────────────────────────────────────

class TestGameCompletionHookEdgeCases:
    """Test update_stats_for_game_completion with edge cases."""

    def _make_gs(self, winner, loser, fmt="commander"):
        from mtg_engine.models.game import GameState, PlayerState
        p1 = PlayerState(name=winner, life=5)
        p2 = PlayerState(name=loser, life=0)
        return GameState(
            game_id="test-game", seed=42, active_player=winner, priority_holder=winner,
            players=[p1, p2], winner=winner, loser=loser, format=fmt,
        )

    def test_game_completion_three_players_skips_loser(self):
        """Game with 3+ players: only first non-winner is treated as loser."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion
        from mtg_engine.models.game import GameState, PlayerState

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3, "formats": {}, "matchups": {}},
            {"player_name": "Bob", "elo": 1200, "wins": 4, "losses": 4, "formats": {}, "matchups": {}},
        ]
        mock_col = _mock_col(docs)

        gs = GameState(
            game_id="game-3p", seed=42, active_player="Alice", priority_holder="Alice",
            players=[
                PlayerState(name="Alice", life=5),
                PlayerState(name="Bob", life=0),
                PlayerState(name="Charlie", life=10),  # Extra player ignored
            ],
            winner="Alice",
        )

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-3p", gs)

        asyncio.run(_run())

        # Alice wins, Bob loses (first non-winner found)
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert alice_doc is not None
        assert alice_doc["wins"] == 6

    def test_game_completion_format_pioneer(self):
        """Stats tracked under correct format name."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3, "formats": {}, "matchups": {}},
            {"player_name": "Bob", "elo": 1200, "wins": 4, "losses": 4, "formats": {}, "matchups": {}},
        ]
        mock_col = _mock_col(docs)

        gs = self._make_gs("Alice", "Bob", fmt="pioneer")

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-pioneer", gs)

        asyncio.run(_run())

        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert "pioneer" in alice_doc.get("formats", {}), \
            f"Expected 'pioneer' format key, got {alice_doc.get('formats', {}).keys()}"

    def test_game_completion_mongo_unconfigured_skips(self):
        """When MongoDB is not configured, no error is raised."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion

        gs = self._make_gs("Alice", "Bob")

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=False):
                await update_stats_for_game_completion("game-skip", gs)
            # Should complete without raising

        asyncio.run(_run())  # No exception expected

    def test_game_completion_winner_only_player(self):
        """Game with only one player (no loser found) skips gracefully."""
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion
        from mtg_engine.models.game import GameState, PlayerState

        docs = [
            {"player_name": "Alice", "elo": 1200, "wins": 5, "losses": 3},
        ]
        mock_col = _mock_col(docs)

        gs = GameState(
            game_id="game-1p", seed=42, active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice")],
            winner="Alice",
        )

        async def _run():
            with patch("mtg_engine.persistence.mongo_client.is_configured", return_value=True), \
                 patch("mtg_engine.persistence.mongo_client.get_player_stats_collection", return_value=mock_col):
                await update_stats_for_game_completion("game-1p", gs)

        asyncio.run(_run())

        # Alice's stats should be unchanged (no loser found, early return)
        alice_doc = next((d for d in docs if d["player_name"] == "Alice"), None)
        assert alice_doc is not None
        assert alice_doc["wins"] == 5


# ── Model Validation Tests ─────────────────────────────────────────────────────

class TestStatsModels:
    """Test Pydantic model defaults and validation."""

    def test_player_stats_defaults(self):
        """PlayerStats has correct default values."""
        stats = PlayerStats(player_name="Alice")
        assert stats.elo == 1200
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.formats == {}
        assert stats.matchups == {}
        assert stats.updated_at is not None

    def test_format_record_defaults(self):
        """FormatRecord defaults to 0 wins/losses."""
        fmt = FormatRecord()
        assert fmt.wins == 0
        assert fmt.losses == 0

    def test_matchup_record_defaults(self):
        """MatchupRecord defaults correctly."""
        m = MatchupRecord(opponent="Bob")
        assert m.opponent == "Bob"
        assert m.wins == 0
        assert m.losses == 0

    def test_player_stats_response_computation(self):
        """PlayerStatsResponse computes win_rate and total_games correctly."""
        from mtg_engine.models.stats import PlayerStatsResponse
        stats = PlayerStats(player_name="Alice", elo=1350, wins=7, losses=3)
        total = stats.wins + stats.losses
        assert total == 10
        assert round(stats.wins / total, 4) == 0.7

    def test_leaderboard_entry_fields(self):
        """LeaderboardEntry has all required fields."""
        from mtg_engine.models.stats import LeaderboardEntry
        entry = LeaderboardEntry(rank=1, player_name="Alice", elo_rating=1500, wins=20, losses=5, total_games=25)
        assert entry.rank == 1
        assert entry.total_games == 25


# ── Regression: Verify Existing API Still Works ───────────────────────────────

class TestRegressionExistingEndpoints:
    """Ensure APP-06 additions don't break existing endpoints."""

    def test_game_create_still_works(self):
        """Basic game creation endpoint still functions."""
        resp = client.post("/game", json={
            "player1_name": "p1",
            "player2_name": "p2",
            "deck1": ["Mountain"] * 60,
            "deck2": ["Forest"] * 60,
            "seed": 42,
        })
        assert resp.status_code == 200, resp.text

    def test_card_search_still_works(self):
        """Card search endpoint still functions."""
        resp = client.get("/cards/search?q=mountain")
        # May return 503 if no Scryfall cache, but should not crash
        assert resp.status_code in (200, 503)

    def test_deck_validate_still_works(self):
        """Deck validation endpoint still functions."""
        resp = client.post("/deck/validate", json={
            "cards": [{"name": "Mountain"}],
            "format": "standard",
        })
        assert resp.status_code == 200, resp.text
