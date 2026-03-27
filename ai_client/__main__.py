"""Entry point: python -m ai_client [OPTIONS]"""
import argparse
import sys

from .ai_player import AIPlayer
from .client import EngineClient
from .game_loop import GameLoop
from .heuristic_player import HeuristicPlayer
from .models import AiPersonalityProfile, GameConfig, PlayerConfig
from .observer import ObserverAI
from .prompts import DEFAULT_COMMANDER_DECK, DEFAULT_DECK


def parse_player_flag(value: str) -> PlayerConfig:
    """
    Parse a --player flag value of the form 'name,url,model'.
    url and model may be empty when player_type is 'heuristic'.
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
    # url/model validation deferred to _make_player where player_type is known
    return PlayerConfig(name=name, base_url=url, model=model)


def _make_player(config: PlayerConfig) -> "AIPlayer | HeuristicPlayer":
    """Factory: return the correct player implementation based on player_type."""
    if config.player_type == "heuristic":
        return HeuristicPlayer(config)
    # LLM player — validate that url and model are present
    if not config.base_url or not (
        config.base_url.startswith("http://") or config.base_url.startswith("https://")
    ):
        print(
            f"Error: player '{config.name}' has player_type=llm but missing or invalid URL: {config.base_url!r}",
            file=__import__("sys").stderr,
        )
        __import__("sys").exit(1)
    if not config.model:
        print(
            f"Error: player '{config.name}' has player_type=llm but no model specified.",
            file=__import__("sys").stderr,
        )
        __import__("sys").exit(1)
    return AIPlayer(config)


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
        "--format",
        metavar="FORMAT",
        choices=["standard", "commander"],
        default="standard",
        dest="format",
        help="Game format: standard or commander (default: standard)",
    )
    parser.add_argument(
        "--commander",
        metavar="NAME",
        action="append",
        dest="commanders",
        help="Commander name (repeatable, exactly 2 required for --format commander)",
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
        help="Maximum turns before forcibly ending the game (default: 200). Use 0 for no limit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug panel: forward AI prompts/responses to the engine and activate observer AI commentary",
    )
    parser.add_argument(
        "--observer",
        metavar="URL,MODEL",
        default=None,
        help=(
            "LLM endpoint and model for the observer AI. "
            "Format: url,model  e.g. http://localhost:8080/v1,devstral. "
            "Can be used independently of --debug. "
            "Required when --debug is used with heuristic players (no LLM endpoint to default to)."
        ),
    )
    parser.add_argument(
        "--player1-type",
        choices=["llm", "heuristic"],
        default="llm",
        dest="player1_type",
        help=(
            "Decision engine for player 1: 'llm' calls an LLM endpoint (default), "
            "'heuristic' uses a local score-based engine with no API calls."
        ),
    )
    parser.add_argument(
        "--player2-type",
        choices=["llm", "heuristic"],
        default="llm",
        dest="player2_type",
        help=(
            "Decision engine for player 2: 'llm' calls an LLM endpoint (default), "
            "'heuristic' uses a local score-based engine with no API calls."
        ),
    )
    parser.add_argument(
        "--personality",
        metavar="PROFILE",
        default="default",
        help=(
            "AI personality profile for heuristic players: 'default' or 'aggro' "
            "(default: default). Applies to both players unless overridden."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate: at least two players required
    players: list[PlayerConfig] = args.players or []
    # Assign player types from --player1-type / --player2-type flags
    player_types = [args.player1_type, args.player2_type]
    # Resolve personality profile (US17, T056)
    _personality_name = getattr(args, "personality", "default")
    if _personality_name == "aggro":
        _personality = AiPersonalityProfile.AGGRO  # type: ignore[attr-defined]
    else:
        _personality = AiPersonalityProfile.DEFAULT  # type: ignore[attr-defined]
    for i, pc in enumerate(players):
        if i < len(player_types):
            pc.player_type = player_types[i]
        pc.personality = _personality

    if len(players) < 2:
        print(
            "Error: at least two --player flags are required.\n"
            "Example: --player \"A,http://localhost:11434/v1,llama3\" "
            "--player \"B,http://localhost:11434/v1,llama3\"",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate commander flags
    game_format: str = args.format
    commanders: list[str] = args.commanders or []
    commander1: str | None = None
    commander2: str | None = None
    if game_format == "commander":
        if len(commanders) != 2:
            print(
                "Error: --format commander requires exactly 2 --commander flags.\n"
                "Example: --commander \"Ghalta, Primal Hunger\" --commander \"Multani, Maro-Sorcerer\"",
                file=sys.stderr,
            )
            sys.exit(1)
        commander1 = commanders[0]
        commander2 = commanders[1]

    if game_format == "commander":
        # Prepend commander to default deck so load_commander_deck can find it.
        # User-provided decks must already include the commander card name.
        deck1 = parse_deck_flag(args.deck1) if args.deck1 else [commander1] + list(DEFAULT_COMMANDER_DECK)
        deck2 = parse_deck_flag(args.deck2) if args.deck2 else [commander2] + list(DEFAULT_COMMANDER_DECK)
    else:
        deck1 = parse_deck_flag(args.deck1) if args.deck1 else list(DEFAULT_DECK)
        deck2 = parse_deck_flag(args.deck2) if args.deck2 else list(DEFAULT_DECK)

    config = GameConfig(
        players=players,
        engine_url=args.engine,
        deck1=deck1,
        deck2=deck2,
        verbose=args.verbose,
        max_turns=args.max_turns,
        format=game_format,
        commander1=commander1,
        commander2=commander2,
    )

    # Parse --observer flag
    observer_base_url: str | None = None
    observer_model: str | None = None
    if args.observer:
        obs_parts = args.observer.split(",", 1)
        if len(obs_parts) != 2:
            print(
                "Error: --observer must be in format 'URL,MODEL', "
                "e.g. http://localhost:8080/v1,devstral-2:24b",
                file=sys.stderr,
            )
            sys.exit(1)
        observer_base_url, observer_model = obs_parts
    elif args.debug:
        # Default observer to the first LLM player's endpoint (if any)
        llm_player = next((p for p in players if p.player_type == "llm"), None)
        if llm_player:
            observer_base_url = llm_player.base_url
            observer_model = llm_player.model
        else:
            print(
                "[DEBUG] Warning: all players are heuristic — no LLM endpoint to use as observer. "
                "Pass --observer URL,MODEL to enable commentary.",
                file=sys.stderr,
            )

    with EngineClient(config.engine_url) as engine:
        ai_players = [_make_player(pc) for pc in config.players]

        observer: ObserverAI | None = None
        if observer_base_url and observer_model:
            observer = ObserverAI(observer_base_url, observer_model)
            print(f"[Observer] Commentary enabled. Model: {observer_model}")
        if args.debug:
            print("[DEBUG] Debug panel enabled.")

        loop = GameLoop(config, engine, ai_players, debug=args.debug, observer=observer)
        loop.run()


if __name__ == "__main__":
    main()
