"""Data structures for the AI CLI client."""
from dataclasses import dataclass, field


@dataclass
class PlayerConfig:
    """One AI player, parsed from a --player CLI flag."""
    name: str
    base_url: str
    model: str


@dataclass
class GameConfig:
    """Top-level game configuration assembled from CLI arguments."""
    players: list[PlayerConfig]
    engine_url: str = "http://localhost:8000"
    deck1: list[str] = field(default_factory=list)
    deck2: list[str] = field(default_factory=list)
    verbose: bool = False
    max_turns: int = 200
    format: str = "standard"
    commander1: str | None = None
    commander2: str | None = None


@dataclass
class TurnRecord:
    """Captures a single AI decision for console logging."""
    turn_number: int
    player_name: str
    phase: str
    step: str
    legal_actions: list[dict]
    chosen_index: int
    reasoning: str
    action_description: str
    fallback_used: bool = False


@dataclass
class GameSummary:
    """Result produced at game end."""
    game_id: str
    winner: str | None
    total_turns: int
    total_decisions: int
    termination_reason: str
    commander_damage: dict = field(default_factory=dict)
