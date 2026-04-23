"""
POST /ai-game — create and start an autonomous AI vs AI game from the UI.
Feature 015-ui-game-creator.

Creates the game synchronously via GameManager, then starts the AI decision
loop in a daemon thread so the endpoint returns immediately with the game_id.
"""
import logging
import sys
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from mtg_engine.api.game_manager import get_manager
from mtg_engine.card_data.deck_loader import load_deck, load_commander_deck
from mtg_engine.persistence.player_defaults import get_merged_player_settings_sync
from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-game"])


# ── Request / Response models ────────────────────────────────────────────────

class AIPlayerConfig(BaseModel):
    name: str
    player_type: str = "heuristic"  # "llm" | "heuristic"
    base_url: str = ""
    model: str = ""
    enable_thinking: bool | None = None

    @field_validator("player_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("llm", "heuristic"):
            raise ValueError("player_type must be 'llm' or 'heuristic'")
        return v

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Player name must not be empty")
        return v.strip()


class AIGameRequest(BaseModel):
    player1: AIPlayerConfig
    player2: AIPlayerConfig
    deck1: list[str] = []
    deck2: list[str] = []
    format: str = "standard"
    commander1: str | None = None
    commander2: str | None = None
    verbose: bool = False
    max_turns: int = 0
    debug: bool = False
    observer_url: str | None = None
    observer_model: str | None = None
    series_count: int = 1
    randomize_decks_per_game: bool = False

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "AIGameRequest":
        if self.player1.name == self.player2.name:
            raise ValueError("player1 and player2 must have different names")
        if self.player1.player_type == "llm":
            if not self.player1.base_url or not (
                self.player1.base_url.startswith("http://")
                or self.player1.base_url.startswith("https://")
            ):
                raise ValueError(
                    "player1 has player_type=llm but base_url is missing or invalid"
                )
            if not self.player1.model:
                raise ValueError("player1 has player_type=llm but model is missing")
        if self.player2.player_type == "llm":
            if not self.player2.base_url or not (
                self.player2.base_url.startswith("http://")
                or self.player2.base_url.startswith("https://")
            ):
                raise ValueError(
                    "player2 has player_type=llm but base_url is missing or invalid"
                )
            if not self.player2.model:
                raise ValueError("player2 has player_type=llm but model is missing")
        if self.format == "commander":
            if not self.commander1 or not self.commander2:
                raise ValueError(
                    "Commander format requires commander1 and commander2"
                )
        if self.observer_url and not self.observer_model:
            raise ValueError("observer_model is required when observer_url is set")
        return self


class AIGameResponse(BaseModel):
    game_id: str


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/ai-game")
def create_ai_game(req: AIGameRequest, request: Request) -> dict:
    """
    Create a game and start the AI loop in a background daemon thread.
    Returns game_id immediately; the game advances autonomously.
    """
    mgr = get_manager()

    # Load decks — randomize from MTGGoldfish if not provided (033-deck-randomizer)
    try:
        from mtg_engine.card_data.mtggoldfish import get_random_deck
        deck1_names = req.deck1
        deck2_names = req.deck2
        commander1_name = req.commander1
        commander2_name = req.commander2
        deck_name1: str | None = None
        deck_name2: str | None = None

        if not deck1_names:
            random_deck = get_random_deck(req.format)
            if random_deck:
                deck1_names = random_deck.to_card_names()
                deck_name1 = random_deck.name
                if req.format == "commander" and random_deck.commander:
                    commander1_name = random_deck.commander
        if not deck2_names:
            random_deck = get_random_deck(req.format)
            if random_deck:
                deck2_names = random_deck.to_card_names()
                deck_name2 = random_deck.name
                if req.format == "commander" and random_deck.commander:
                    commander2_name = random_deck.commander

        if req.format == "commander":
            d1 = deck1_names if deck1_names else [commander1_name] + list(DEFAULT_COMMANDER_DECK)
            d2 = deck2_names if deck2_names else [commander2_name] + list(DEFAULT_COMMANDER_DECK)
            deck1_cards, commander1_card = load_commander_deck(d1, commander1_name)
            deck2_cards, commander2_card = load_commander_deck(d2, commander2_name)
        else:
            d1 = deck1_names if deck1_names else list(DEFAULT_DECK)
            d2 = deck2_names if deck2_names else list(DEFAULT_DECK)
            deck1_cards = load_deck(d1)
            deck2_cards = load_deck(d2)
            commander1_card = None
            commander2_card = None
    except ValueError as exc:
        msg = str(exc)
        code = (
            "SINGLETON_VIOLATION" if "Singleton" in msg
            else "COLOR_IDENTITY_VIOLATION" if "Color identity" in msg
            else "INVALID_COMMANDER" if "legendary" in msg.lower() or "not found" in msg
            else "DECK_LOAD_ERROR"
        )
        raise HTTPException(status_code=422, detail={"error": msg, "error_code": code})

    # Create game in-process (no HTTP round-trip)
    # Series mode (032-game-series)
    series_id: str | None = None
    if req.series_count > 1:
        series_settings = {
            "player1": req.player1.model_dump(),
            "player2": req.player2.model_dump(),
            "deck1": req.deck1,
            "deck2": req.deck2,
            "format": req.format,
            "commander1": req.commander1,
            "commander2": req.commander2,
            "verbose": req.verbose,
            "max_turns": req.max_turns,
            "debug": req.debug,
            "observer_url": req.observer_url,
            "observer_model": req.observer_model,
            "randomize_decks_per_game": req.randomize_decks_per_game,
            "request": {
                "base_url": str(request.base_url).rstrip("/"),
            },
        }
        series_id = mgr.create_series(req.series_count, series_settings)

    gs = mgr.create_game(
        req.player1.name,
        req.player2.name,
        deck1_cards,
        deck2_cards,
        verbose=req.verbose,
        debug=req.debug,
        format=req.format,
        commander1_card=commander1_card if req.format == "commander" else None,
        commander2_card=commander2_card if req.format == "commander" else None,
        deck_name1=deck_name1,
        deck_name2=deck_name2,
    )
    if series_id:
        gs.series_id = series_id
        mgr.get_series(series_id).active_game_id = gs.game_id
        mgr.update(gs.game_id, gs)
    game_id = gs.game_id

    # Fetch and merge AI player defaults with request values (Feature 028)
    def _resolve_ai_player(cfg: AIPlayerConfig) -> tuple[str, str, bool | None]:
        ptype = "llm" if cfg.player_type == "llm" else "heuristic"
        if ptype == "heuristic":
            return cfg.base_url, cfg.model, cfg.enable_thinking
        # For LLM players, merge with defaults
        request_values = {
            "base_url": cfg.base_url or "",
            "model": cfg.model or "",
            "enable_thinking": cfg.enable_thinking,
        }
        try:
            merged = get_merged_player_settings_sync(ptype, request_values)
            return (
                merged.get("base_url", cfg.base_url) or "",
                merged.get("model", cfg.model) or "",
                cfg.enable_thinking if cfg.enable_thinking is not None else merged.get("enable_thinking"),
            )
        except Exception:
            return cfg.base_url, cfg.model, cfg.enable_thinking

    final_p1_url, final_p1_model, final_p1_thinking = _resolve_ai_player(req.player1)
    final_p2_url, final_p2_model, final_p2_thinking = _resolve_ai_player(req.player2)

    # Derive the engine URL from the incoming request so the daemon thread
    # connects to the correct server (avoids hardcoded localhost:8000).
    engine_url = str(request.base_url).rstrip("/")

    # Start AI loop in a daemon thread so we return immediately
    thread = threading.Thread(
        target=_run_ai_loop,
        args=(req, game_id, engine_url, final_p1_url, final_p1_model, final_p1_thinking,
              final_p2_url, final_p2_model, final_p2_thinking, series_id),
        daemon=False,
        name=f"ai-game-{game_id[:8]}",
    )
    thread.start()
    logger.info("Started AI game loop thread for game %s (series=%s)", game_id, series_id)

    return {"data": {"game_id": game_id, "series_id": series_id}}


def _run_ai_loop(
    req: AIGameRequest,
    game_id: str,
    engine_url: str,
    merged_p1_url: str = "",
    merged_p1_model: str = "",
    merged_p1_thinking: bool | None = None,
    merged_p2_url: str = "",
    merged_p2_model: str = "",
    merged_p2_thinking: bool | None = None,
    series_id: str | None = None,
) -> None:
    """
    Build the GameLoop from the request and run it.
    Runs in a daemon thread; exceptions are logged but do not crash the server.
    """
    print(f"[ai-game] Loop thread starting for game {game_id[:8]} (engine: {engine_url})", flush=True)
    print(f"[ai-game] Testing HTTP connectivity...", flush=True)
    
    import httpx
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{engine_url}/health")
            print(f"[ai-game] Health check response: {resp.status_code} {resp.text}", flush=True)
    except Exception as e:
        print(f"[ai-game] Health check failed: {e}", flush=True)

    summary = None
    try:
        # Import here to avoid circular imports at module load time
        from ai_client.models import GameConfig, PlayerConfig
        from ai_client.ai_player import AIPlayer
        from ai_client.heuristic_player import HeuristicPlayer
        from ai_client.game_loop import GameLoop
        from ai_client.client import EngineClient
        from ai_client.observer import ObserverAI
        from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK

        # Build PlayerConfig objects — use merged values from defaults (Feature 028)
        pc1 = PlayerConfig(
            name=req.player1.name,
            base_url=merged_p1_url,
            model=merged_p1_model,
            player_type=req.player1.player_type,
            enable_thinking=merged_p1_thinking,
        )
        pc2 = PlayerConfig(
            name=req.player2.name,
            base_url=merged_p2_url,
            model=merged_p2_model,
            player_type=req.player2.player_type,
            enable_thinking=merged_p2_thinking,
        )

        # Build GameConfig (decks already loaded; pass card names back for config)
        game_config = GameConfig(
            players=[pc1, pc2],
            engine_url=engine_url,
            deck1=req.deck1 or list(DEFAULT_DECK),
            deck2=req.deck2 or list(DEFAULT_DECK),
            verbose=req.verbose,
            max_turns=req.max_turns,
            format=req.format,
            commander1=req.commander1,
            commander2=req.commander2,
        )

        # Build player instances
        def _make_player(pc: PlayerConfig):
            if pc.player_type == "heuristic":
                return HeuristicPlayer(pc)
            return AIPlayer(pc)

        players = [_make_player(pc1), _make_player(pc2)]

        # Resolve observer
        observer: ObserverAI | None = None
        obs_url = req.observer_url
        obs_model = req.observer_model
        obs_thinking: bool | None = None
        if req.debug and not obs_url:
            # Default to first LLM player's endpoint
            llm = next((p for p in [req.player1, req.player2] if p.player_type == "llm"), None)
            if llm:
                obs_url = llm.base_url
                obs_model = llm.model
                obs_thinking = llm.enable_thinking
        elif obs_url:
            # Observer URL explicitly set — inherit thinking from whichever LLM player
            # shares the same endpoint, otherwise leave as model default
            llm = next(
                (p for p in [req.player1, req.player2]
                 if p.player_type == "llm" and p.base_url == obs_url),
                None,
            )
            if llm:
                obs_thinking = llm.enable_thinking
        if obs_url and obs_model:
            observer = ObserverAI(obs_url, obs_model, enable_thinking=obs_thinking)

        # The engine self-address for EngineClient (loop uses HTTP to submit actions)
        with EngineClient(engine_url) as engine:
            loop = GameLoop(
                config=game_config,
                engine=engine,
                players=players,
                debug=req.debug,
                observer=observer,
                game_id=game_id,  # skip game creation — already done above
            )
            summary = loop.run()

    except Exception as e:
        import traceback
        print(f"[CRITICAL] AI game loop exception: {e}", flush=True)
        traceback.print_exc()
        logger.exception("AI game loop for %s raised an unhandled exception", game_id)

    # Series continuation (032-game-series)
    if series_id and summary:
        from mtg_engine.api.game_manager import get_manager
        mgr = get_manager()
        try:
            mgr.record_series_result(series_id, game_id, summary.winner, summary.total_turns)
            if not mgr.is_series_complete(series_id):
                sc = mgr.get_series(series_id)
                print(f"[ai-game] Series {series_id[:8]}: spawning game {sc.completed_games + 1} of {sc.total_games}", flush=True)
                _spawn_next_ai_game(req, series_id, engine_url, merged_p1_url, merged_p1_model, merged_p1_thinking,
                                    merged_p2_url, merged_p2_model, merged_p2_thinking)
        except Exception as e:
            logger.warning("Series continuation failed for %s: %s", series_id, e)


def _spawn_next_ai_game(
    req: AIGameRequest,
    series_id: str,
    engine_url: str,
    merged_p1_url: str,
    merged_p1_model: str,
    merged_p1_thinking: bool | None,
    merged_p2_url: str,
    merged_p2_model: str,
    merged_p2_thinking: bool | None,
) -> None:
    """Create the next game in a series and start its loop."""
    from mtg_engine.api.game_manager import get_manager
    from mtg_engine.card_data.deck_loader import load_deck, load_commander_deck
    from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK
    mgr = get_manager()
    try:
        sc = mgr.get_series(series_id)
    except KeyError:
        return

    # Reload decks — randomize per game if configured (033-deck-randomizer)
    from mtg_engine.card_data.mtggoldfish import get_random_deck
    deck1_names = req.deck1
    deck2_names = req.deck2
    commander1_name = req.commander1
    commander2_name = req.commander2
    deck_name1_spawn: str | None = None
    deck_name2_spawn: str | None = None

    randomize = sc.settings.get("randomize_decks_per_game", False)
    if randomize or not deck1_names:
        rd = get_random_deck(req.format)
        if rd:
            deck1_names = rd.to_card_names()
            deck_name1_spawn = rd.name
            if req.format == "commander" and rd.commander:
                commander1_name = rd.commander
    if randomize or not deck2_names:
        rd = get_random_deck(req.format)
        if rd:
            deck2_names = rd.to_card_names()
            deck_name2_spawn = rd.name
            if req.format == "commander" and rd.commander:
                commander2_name = rd.commander

    if req.format == "commander":
        d1 = deck1_names if deck1_names else [commander1_name] + list(DEFAULT_COMMANDER_DECK)
        d2 = deck2_names if deck2_names else [commander2_name] + list(DEFAULT_COMMANDER_DECK)
        deck1_cards, commander1_card = load_commander_deck(d1, commander1_name)
        deck2_cards, commander2_card = load_commander_deck(d2, commander2_name)
    else:
        d1 = deck1_names if deck1_names else list(DEFAULT_DECK)
        d2 = deck2_names if deck2_names else list(DEFAULT_DECK)
        deck1_cards = load_deck(d1)
        deck2_cards = load_deck(d2)
        commander1_card = None
        commander2_card = None

    gs = mgr.create_game(
        req.player1.name,
        req.player2.name,
        deck1_cards,
        deck2_cards,
        verbose=req.verbose,
        debug=req.debug,
        format=req.format,
        commander1_card=commander1_card if req.format == "commander" else None,
        commander2_card=commander2_card if req.format == "commander" else None,
        deck_name1=deck_name1_spawn,
        deck_name2=deck_name2_spawn,
    )
    gs.series_id = series_id
    sc.active_game_id = gs.game_id
    mgr.update(gs.game_id, gs)

    thread = threading.Thread(
        target=_run_ai_loop,
        args=(req, gs.game_id, engine_url, merged_p1_url, merged_p1_model, merged_p1_thinking,
              merged_p2_url, merged_p2_model, merged_p2_thinking, series_id),
        daemon=False,
        name=f"ai-game-{gs.game_id[:8]}",
    )
    thread.start()
    logger.info("Started series game %s for series %s", gs.game_id, series_id)
