"""
Player Stats / ELO endpoints. Feature APP-06.
All endpoints require MongoDB; return HTTP 503 if not configured.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import WriteError, OperationFailure

from mtg_engine.engine.stats import update_player_stats
from mtg_engine.models.game import GameState
from mtg_engine.models.stats import (
    FormatRecord,
    LeaderboardEntry,
    MatchupRecord,
    MatchupResponse,
    PlayerStats,
    PlayerStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["player-stats"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _require_player_stats_collection():
    from mtg_engine.persistence.mongo_client import is_configured, get_player_stats_collection

    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    return get_player_stats_collection()


async def _get_or_create_player(col, player_name: str) -> PlayerStats:
    """Fetch existing stats or create a new profile (idempotent)."""
    doc = await col.find_one({"player_name": player_name})
    if doc is not None:
        return PlayerStats(**{k: v for k, v in doc.items() if k != "_id"})
    # Create new profile
    stats = PlayerStats(player_name=player_name)
    await col.insert_one(stats.model_dump())
    return stats


def _stats_to_response(stats: PlayerStats) -> PlayerStatsResponse:
    total = stats.wins + stats.losses
    win_rate = stats.wins / total if total > 0 else 0.0
    return PlayerStatsResponse(
        player=stats.player_name,
        wins=stats.wins,
        losses=stats.losses,
        win_rate=round(win_rate, 4),
        elo_rating=stats.elo,
        total_games=total,
        formats={k: v for k, v in stats.formats.items()},
        # TODO: recent_games is always empty — will be populated when game history store is implemented (APP-06 gap)
        recent_games=[],
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/stats/player/{player_name}")
async def get_player_stats(player_name: str) -> dict:
    """Return player stats and ELO rating."""
    col = _require_player_stats_collection()

    doc = await col.find_one({"player_name": player_name})
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Player not found", "error_code": "PLAYER_NOT_FOUND"},
        )

    stats = PlayerStats(**{k: v for k, v in doc.items() if k != "_id"})
    return {"data": _stats_to_response(stats).model_dump()}


@router.post("/stats/player/{player_name}")
async def create_player_stats(player_name: str) -> dict:
    """Create a new player profile (idempotent — no error if already exists)."""
    col = _require_player_stats_collection()

    stats = await _get_or_create_player(col, player_name)
    return {"data": _stats_to_response(stats).model_dump()}


@router.get("/stats/player/{player_name}/matchups")
async def get_player_matchups(player_name: str) -> dict:
    """Return per-opponent matchup stats sorted by most games played."""
    col = _require_player_stats_collection()

    doc = await col.find_one({"player_name": player_name})
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Player not found", "error_code": "PLAYER_NOT_FOUND"},
        )

    stats = PlayerStats(**{k: v for k, v in doc.items() if k != "_id"})

    # Build matchup responses sorted by total games (desc)
    matchups: list[MatchupResponse] = []
    for m in stats.matchups.values():
        total = m.wins + m.losses
        win_rate = m.wins / total if total > 0 else 0.0
        matchups.append(
            MatchupResponse(
                opponent=m.opponent,
                wins=m.wins,
                losses=m.losses,
                win_rate=round(win_rate, 4),
            )
        )

    matchups.sort(key=lambda x: x.wins + x.losses, reverse=True)
    return {"data": {"player": player_name, "matchups": [m.model_dump() for m in matchups]}}


@router.get("/stats/leaderboard")
async def get_leaderboard(
    format: Optional[str] = Query(None, alias="format"),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    """Return top players by ELO rating (optionally filtered by format)."""
    col = _require_player_stats_collection()

    if format is not None:
        # For format-specific leaderboard, use aggregation to compute per-format elo
        # Since we store global ELO but per-format records, we sort by total games in that format
        pipeline = [
            {"$match": {f"formats.{format}": {"$exists": True}}},
            {
                "$project": {
                    "player_name": 1,
                    "elo_rating": "$elo",
                    "wins": f"$formats.{format}.wins",
                    "losses": f"$formats.{format}.losses",
                }
            },
            {"$addFields": {"total_games": {"$add": ["$wins", "$losses"]}}},
            {"$sort": {"elo_rating": -1}},
            {"$limit": limit},
        ]
    else:
        pipeline = [
            {"$project": {
                "player_name": 1,
                "elo_rating": "$elo",
                "wins": 1,
                "losses": 1,
            }},
            {"$addFields": {"total_games": {"$add": ["$wins", "$losses"]}}},
            {"$sort": {"elo_rating": -1}},
            {"$limit": limit},
        ]

    cursor = col.aggregate(pipeline)
    docs = await cursor.to_list(length=limit)

    entries: list[LeaderboardEntry] = []
    for rank, doc in enumerate(docs, start=1):
        entries.append(
            LeaderboardEntry(
                rank=rank,
                player_name=doc["player_name"],
                elo_rating=doc["elo_rating"],
                wins=doc.get("wins", 0),
                losses=doc.get("losses", 0),
                total_games=doc.get("total_games", 0),
            )
        )

    return {"data": {"leaderboard": [e.model_dump() for e in entries], "count": len(entries)}}


# ── Game Completion Hook (called from game.py DELETE handler) ──────────────────


async def update_stats_for_game_completion(game_id: str, gs: GameState) -> None:
    """Update stats for both players after a completed game.

    Called asynchronously from the sync delete_game() handler via
    asyncio.run_coroutine_threadsafe().

    Args:
        game_id: The game ID (for logging).
        gs: The final GameState of the completed game.
    """
    from mtg_engine.persistence.mongo_client import is_configured, get_player_stats_collection

    if not is_configured():
        logger.debug("Skipping stats update — MongoDB not configured")
        return

    winner = gs.winner
    if not winner:
        logger.warning("Game %s completed but no winner set — skipping stats update", game_id)
        return

    # Find loser (the other player who is not the winner)
    loser: Optional[str] = None
    for p in gs.players:
        if p.name != winner:
            loser = p.name
            break

    if not loser:
        logger.warning("Game %s completed but only one player — skipping stats update", game_id)
        return

    col = get_player_stats_collection()
    # Fallback to "standard" if game has no format set (MINOR #6 fix)
    format_name = getattr(gs, "format", None) or "standard"

    # Fetch current stats for ELO calculation (need opponent's current ELO)
    winner_doc = await col.find_one({"player_name": winner})
    loser_doc = await col.find_one({"player_name": loser})

    if winner_doc:
        winner_stats = PlayerStats(**{k: v for k, v in winner_doc.items() if k != "_id"})
    else:
        winner_stats = PlayerStats(player_name=winner)

    if loser_doc:
        loser_stats = PlayerStats(**{k: v for k, v in loser_doc.items() if k != "_id"})
    else:
        loser_stats = PlayerStats(player_name=loser)

    # Compute ELO deltas (pure transforms — no mutation of fetched docs)
    new_winner_stats = update_player_stats(
        winner_stats, opponent_name=loser, opponent_elo=loser_stats.elo, won=True, format_name=format_name
    )
    new_loser_stats = update_player_stats(
        loser_stats, opponent_name=winner, opponent_elo=winner_stats.elo, won=False, format_name=format_name
    )

    # NOTE: Stale-delta race condition — ELO deltas are computed from data fetched above.
    # If another game completes between the find_one() calls and these update_one() calls,
    # the opponent's ELO may have changed, making our delta slightly stale. In production
    # with high game throughput, consider using a message queue for serial stat updates.
    winner_elo_delta = new_winner_stats.elo - winner_stats.elo
    loser_elo_delta = new_loser_stats.elo - loser_stats.elo

    # Determine which players need upsert vs atomic $inc (CRITICAL fix: $inc with upsert=True
    # initializes missing fields to 0, so a new player's ELO would be 0 + delta instead of
    # the correct computed value)
    winner_exists = winner_doc is not None
    loser_exists = loser_doc is not None

    winner_updated = False
    loser_updated = False

    try:
        if winner_exists:
            await col.update_one(
                {"player_name": winner},
                {
                    "$inc": {
                        "wins": 1,
                        "elo": winner_elo_delta,
                        f"formats.{format_name}.wins": 1,
                        f"matchups.{loser}.wins": 1,
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                },
            )
        else:
            await col.update_one(
                {"player_name": winner},
                {"$set": new_winner_stats.model_dump()},
                upsert=True,
            )
        winner_updated = True
    except (WriteError, OperationFailure):
        logger.warning("Winner update failed for game %s", game_id, exc_info=True)

    try:
        if loser_exists:
            await col.update_one(
                {"player_name": loser},
                {
                    "$inc": {
                        "losses": 1,
                        "elo": loser_elo_delta,
                        f"formats.{format_name}.losses": 1,
                        f"matchups.{winner}.losses": 1,
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                },
            )
        else:
            await col.update_one(
                {"player_name": loser},
                {"$set": new_loser_stats.model_dump()},
                upsert=True,
            )
        loser_updated = True
    except (WriteError, OperationFailure):
        logger.warning("Loser update failed for game %s", game_id, exc_info=True)

    # Retry only the ones that failed with full document replace
    if not winner_updated:
        logger.info("Retrying winner stats update with full replace for game %s", game_id)
        await col.update_one(
            {"player_name": winner},
            {"$set": new_winner_stats.model_dump()},
            upsert=True,
        )
    if not loser_updated:
        logger.info("Retrying loser stats update with full replace for game %s", game_id)
        await col.update_one(
            {"player_name": loser},
            {"$set": new_loser_stats.model_dump()},
            upsert=True,
        )

    logger.info(
        "Stats updated for game %s: %s (ELO %d→%d) vs %s (ELO %d→%d)",
        game_id,
        winner, winner_stats.elo, new_winner_stats.elo,
        loser, loser_stats.elo, new_loser_stats.elo,
    )
