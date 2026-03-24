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
from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-game"])


# ── Request / Response models ────────────────────────────────────────────────

class AIPlayerConfig(BaseModel):
    name: str
    player_type: str = "heuristic"  # "llm" | "heuristic"
    base_url: str = ""
    model: str = ""

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
    max_turns: int = 200
    debug: bool = False
    observer_url: str | None = None
    observer_model: str | None = None

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

    # Load decks
    try:
        if req.format == "commander":
            d1 = req.deck1 if req.deck1 else [req.commander1] + list(DEFAULT_COMMANDER_DECK)
            d2 = req.deck2 if req.deck2 else [req.commander2] + list(DEFAULT_COMMANDER_DECK)
            deck1_cards, commander1_card = load_commander_deck(d1, req.commander1)
            deck2_cards, commander2_card = load_commander_deck(d2, req.commander2)
        else:
            d1 = req.deck1 if req.deck1 else list(DEFAULT_DECK)
            d2 = req.deck2 if req.deck2 else list(DEFAULT_DECK)
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
    )
    game_id = gs.game_id

    # Derive the engine URL from the incoming request so the daemon thread
    # connects to the correct server (avoids hardcoded localhost:8000).
    engine_url = str(request.base_url).rstrip("/")

    # Start AI loop in a daemon thread so we return immediately
    thread = threading.Thread(
        target=_run_ai_loop,
        args=(req, game_id, engine_url),
        daemon=True,
        name=f"ai-game-{game_id[:8]}",
    )
    thread.start()
    logger.info("Started AI game loop thread for game %s", game_id)

    return {"data": {"game_id": game_id}}


def _run_ai_loop(req: AIGameRequest, game_id: str, engine_url: str) -> None:
    """
    Build the GameLoop from the request and run it.
    Runs in a daemon thread; exceptions are logged but do not crash the server.
    """
    print(f"[ai-game] Loop thread starting for game {game_id[:8]} (engine: {engine_url})", flush=True)
    try:
        # Import here to avoid circular imports at module load time
        from ai_client.models import GameConfig, PlayerConfig
        from ai_client.ai_player import AIPlayer
        from ai_client.heuristic_player import HeuristicPlayer
        from ai_client.game_loop import GameLoop
        from ai_client.client import EngineClient
        from ai_client.observer import ObserverAI
        from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK

        # Build PlayerConfig objects
        def _make_pc(cfg: AIPlayerConfig) -> PlayerConfig:
            return PlayerConfig(
                name=cfg.name,
                base_url=cfg.base_url,
                model=cfg.model,
                player_type=cfg.player_type,
            )

        pc1 = _make_pc(req.player1)
        pc2 = _make_pc(req.player2)

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
        if req.debug and not obs_url:
            # Default to first LLM player's endpoint
            llm = next((p for p in [req.player1, req.player2] if p.player_type == "llm"), None)
            if llm:
                obs_url = llm.base_url
                obs_model = llm.model
        if obs_url and obs_model:
            observer = ObserverAI(obs_url, obs_model)

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
            loop.run()

    except Exception:
        import traceback
        traceback.print_exc()
        logger.exception("AI game loop for %s raised an unhandled exception", game_id)
