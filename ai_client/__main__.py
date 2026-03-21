"""Entry point: python -m ai_client [OPTIONS]"""
import argparse
import sys

from .ai_player import AIPlayer
from .client import EngineClient
from .game_loop import GameLoop
from .models import GameConfig, PlayerConfig
from .prompts import DEFAULT_DECK


def parse_player_flag(value: str) -> PlayerConfig:
    """
    Parse a --player flag value of the form 'name,url,model'.
    Raises argparse.ArgumentTypeError on invalid input.
    """
    parts = value.split(",", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"--player must be in format 'NAME,URL,MODEL', got: {value!r}"
        )
    name, url, model = (p.strip() for p in parts)
    if not name:
        raise argparse.ArgumentTypeError(f"Player name cannot be empty in: {value!r}")
    if not url:
        raise argparse.ArgumentTypeError(f"Player URL cannot be empty in: {value!r}")
    if not model:
        raise argparse.ArgumentTypeError(f"Player model cannot be empty in: {value!r}")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise argparse.ArgumentTypeError(
            f"Player URL must start with http:// or https://, got: {url!r}"
        )
    return PlayerConfig(name=name, base_url=url, model=model)


def parse_deck_flag(value: str) -> list[str]:
    """Split a --deck1/--deck2 value on commas and strip whitespace."""
    return [card.strip() for card in value.split(",") if card.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ai_client",
        description="Run an AI vs AI MTG game via the engine REST API.",
    )
    parser.add_argument(
        "--player",
        metavar="NAME,URL,MODEL",
        action="append",
        type=parse_player_flag,
        dest="players",
        help="Define one AI player (repeatable, minimum 2). Format: name,url,model",
    )
    parser.add_argument(
        "--engine",
        metavar="URL",
        default="http://localhost:8000",
        help="Base URL of the MTG engine API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--deck1",
        metavar="CARDS",
        default=None,
        help="Comma-separated card names for player 1 (default: built-in test deck)",
    )
    parser.add_argument(
        "--deck2",
        metavar="CARDS",
        default=None,
        help="Comma-separated card names for player 2 (default: built-in test deck)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable play-by-play logging and print full board state each turn",
    )
    parser.add_argument(
        "--max-turns",
        metavar="N",
        type=int,
        default=200,
        dest="max_turns",
        help="Maximum turns before forcibly ending the game (default: 200)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate: at least two players required
    players: list[PlayerConfig] = args.players or []
    if len(players) < 2:
        print(
            "Error: at least two --player flags are required.\n"
            "Example: --player \"A,http://localhost:11434/v1,llama3\" "
            "--player \"B,http://localhost:11434/v1,llama3\"",
            file=sys.stderr,
        )
        sys.exit(1)

    deck1 = parse_deck_flag(args.deck1) if args.deck1 else list(DEFAULT_DECK)
    deck2 = parse_deck_flag(args.deck2) if args.deck2 else list(DEFAULT_DECK)

    config = GameConfig(
        players=players,
        engine_url=args.engine,
        deck1=deck1,
        deck2=deck2,
        verbose=args.verbose,
        max_turns=args.max_turns,
    )

    with EngineClient(config.engine_url) as engine:
        ai_players = [AIPlayer(pc) for pc in config.players]
        loop = GameLoop(config, engine, ai_players)
        loop.run()


if __name__ == "__main__":
    main()
