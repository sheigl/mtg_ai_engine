"""
Player stats and ELO rating models. Feature APP-06.
Pydantic v2 models for MongoDB storage and API responses.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FormatRecord(BaseModel):
    """Per-format win/loss record."""
    wins: int = 0
    losses: int = 0


class MatchupRecord(BaseModel):
    """Per-opponent win/loss record."""
    opponent: str = ""
    wins: int = 0
    losses: int = 0


class PlayerStats(BaseModel):
    """Stored player stats document (matches MongoDB schema)."""
    player_name: str
    elo: int = 1200
    wins: int = 0
    losses: int = 0
    formats: dict[str, FormatRecord] = Field(default_factory=dict)
    matchups: dict[str, MatchupRecord] = Field(default_factory=dict)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ── API Response Models ───────────────────────────────────────────────────────


class RecentGameEntry(BaseModel):
    """A single recent game result."""
    game_id: str
    opponent: str
    result: str  # "win" or "loss"
    date: datetime


class PlayerStatsResponse(BaseModel):
    """GET /stats/player/{player_name} response payload."""
    player: str
    wins: int
    losses: int
    win_rate: float  # 0.0–1.0
    elo_rating: int
    total_games: int
    formats: dict[str, FormatRecord] = Field(default_factory=dict)
    recent_games: list[RecentGameEntry] = Field(default_factory=list)


class MatchupResponse(BaseModel):
    """Per-opponent matchup entry."""
    opponent: str
    wins: int
    losses: int
    win_rate: float


class LeaderboardEntry(BaseModel):
    """Leaderboard row."""
    rank: int
    player_name: str
    elo_rating: int
    wins: int
    losses: int
    total_games: int
