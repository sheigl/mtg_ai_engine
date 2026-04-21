"""POST /human-game — create a game with one human-controlled seat."""
import logging
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, model_validator

from mtg_engine.persistence.player_defaults import get_merged_player_settings_sync

router = APIRouter(tags=["human-game"])
logger = logging.getLogger(__name__)

# Maps game_id → human player name so the frontend can recover it after refresh
_human_player_registry: dict[str, str] = {}


class HumanGameRequest(BaseModel):
    player1_type: str = "human"
    player2_type: str = "heuristic"
    player1_deck: list[str] = []
    player2_deck: list[str] = []
    player1_name: str = "You"
    player2_name: str = "Bot"
    format: str = "standard"
    ai_model: str = ""
    ai_base_url: str = ""
    ai_enable_thinking: bool | None = None
    observer_model: str | None = None
    observer_url: str | None = None
    observer_enabled: bool = True
    verbose: bool = False
    max_turns: int = 200
    debug: bool = False
    commander1: str | None = None
    commander2: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> "HumanGameRequest":
        # Normalize "llm" → "ai" so both the AI game form and this endpoint agree
        if self.player1_type == "llm":
            self.player1_type = "ai"
        if self.player2_type == "llm":
            self.player2_type = "ai"
        valid = {"human", "ai", "heuristic"}
        if self.player1_type not in valid:
            raise ValueError(f"player1_type must be one of {valid}")
        if self.player2_type not in valid:
            raise ValueError(f"player2_type must be one of {valid}")
        if self.player1_type != "human" and self.player2_type != "human":
            raise ValueError("At least one player must be 'human'")
        if self.player1_type == "human" and self.player2_type == "human":
            raise ValueError("Both players cannot be 'human' (1v1 only in v1)")
        if self.player1_name.strip() == self.player2_name.strip():
            raise ValueError("player1_name and player2_name must be different")
        return self


class HumanGameResponse(BaseModel):
    game_id: str
    human_player_name: str
    redirect_url: str


@router.post("/human-game")
def create_human_game(req: HumanGameRequest, request: Request) -> dict:
    """Create a game with a human seat and start the AI loop in a daemon thread."""
    from mtg_engine.api.game_manager import get_manager
    from mtg_engine.card_data.deck_loader import load_deck, load_commander_deck
    from ai_client.prompts import DEFAULT_DECK, DEFAULT_COMMANDER_DECK

    mgr = get_manager()

    # Load decks
    try:
        if req.format == "commander":
            fallback = list(DEFAULT_COMMANDER_DECK)
            d1 = req.player1_deck if req.player1_deck else fallback
            d2 = req.player2_deck if req.player2_deck else fallback
        else:
            d1 = req.player1_deck if req.player1_deck else list(DEFAULT_DECK)
            d2 = req.player2_deck if req.player2_deck else list(DEFAULT_DECK)

        if req.format == "commander":
            if not req.commander1 or not req.commander2:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "Commander format requires commander1 and commander2", "error_code": "MISSING_COMMANDER"},
                )
            if req.commander1 not in d1:
                d1 = d1 + [req.commander1]
            if req.commander2 not in d2:
                d2 = d2 + [req.commander2]
            deck1_cards, commander1_card = load_commander_deck(d1, req.commander1)
            deck2_cards, commander2_card = load_commander_deck(d2, req.commander2)
        else:
            deck1_cards = load_deck(d1)
            deck2_cards = load_deck(d2)
            commander1_card = None
            commander2_card = None
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc), "error_code": "DECK_LOAD_ERROR"})

    # Create game — map "heuristic" → "ai" for persistence type label
    def _persist_type(t: str) -> str:
        return "human" if t == "human" else "ai"

    gs = mgr.create_game(
        req.player1_name,
        req.player2_name,
        deck1_cards,
        deck2_cards,
        verbose=req.verbose,
        debug=req.debug,
        format=req.format,
        player1_type=_persist_type(req.player1_type),
        player2_type=_persist_type(req.player2_type),
        commander1_card=commander1_card,
        commander2_card=commander2_card,
    )
    game_id = gs.game_id

    human_player_name = req.player1_name if req.player1_type == "human" else req.player2_name
    ai_player_type = req.player2_type if req.player1_type == "human" else req.player1_type
    ai_player_name = req.player2_name if req.player1_type == "human" else req.player1_name

    # Fetch and merge AI player defaults with request values (Feature 028)
    ai_request_values = {
        "base_url": req.ai_base_url or "",
        "model": req.ai_model or "",
        "enable_thinking": req.ai_enable_thinking,
    }
    try:
        merged_ai = get_merged_player_settings_sync(ai_player_type, ai_request_values)
        final_ai_base_url = merged_ai.get("base_url", req.ai_base_url) or ""
        final_ai_model = merged_ai.get("model", req.ai_model) or ""
        final_ai_enable_thinking = req.ai_enable_thinking if req.ai_enable_thinking is not None else merged_ai.get("enable_thinking")
    except Exception:
        final_ai_base_url = req.ai_base_url
        final_ai_model = req.ai_model
        final_ai_enable_thinking = req.ai_enable_thinking

    engine_url = str(request.base_url).rstrip("/")

    thread = threading.Thread(
        target=_run_hybrid_loop,
        args=(req, game_id, engine_url, human_player_name, ai_player_name, ai_player_type,
              final_ai_base_url, final_ai_model, final_ai_enable_thinking),
        daemon=False,
        name=f"human-game-{game_id[:8]}",
    )
    thread.start()
    logger.info("Started hybrid game loop thread for game %s (human=%s)", game_id, human_player_name)
    _human_player_registry[game_id] = human_player_name

    return {"data": HumanGameResponse(
        game_id=game_id,
        human_player_name=human_player_name,
        redirect_url=f"/human-game/{game_id}",
    ).model_dump()}


@router.get("/human-game/{game_id}/player")
def get_human_player(game_id: str) -> dict:
    """Return the human player name for a human game."""
    name = _human_player_registry.get(game_id)
    if name is None:
        raise HTTPException(status_code=404, detail="Not a human game or game not found")
    return {"data": {"human_player_name": name}}


def _run_hybrid_loop(
    req: HumanGameRequest,
    game_id: str,
    engine_url: str,
    human_player_name: str,
    ai_player_name: str,
    ai_player_type: str,
    merged_ai_base_url: str = "",
    merged_ai_model: str = "",
    merged_ai_enable_thinking: bool | None = None,
) -> None:
    """Build and run the HybridGameLoop in a daemon thread."""
    try:
        from ai_client.models import GameConfig, PlayerConfig
        from ai_client.heuristic_player import HeuristicPlayer
        from ai_client.ai_player import AIPlayer
        from ai_client.hybrid_game_loop import HybridGameLoop
        from ai_client.client import EngineClient
        from ai_client.observer import ObserverAI
        from ai_client.prompts import DEFAULT_DECK

        ai_pc = PlayerConfig(
            name=ai_player_name,
            base_url=merged_ai_base_url,
            model=merged_ai_model,
            player_type="heuristic" if ai_player_type == "heuristic" else "llm",
            enable_thinking=merged_ai_enable_thinking,
        )

        # Human seat uses a dummy PlayerConfig — the loop skips it
        human_pc = PlayerConfig(
            name=human_player_name,
            base_url="",
            model="",
            player_type="heuristic",
        )

        # player1 is always index 0 in config
        if req.player1_type == "human":
            pc_list = [human_pc, ai_pc]
            player_list_fn = lambda: [HeuristicPlayer(human_pc), _make_ai(ai_player_type, ai_pc)]
        else:
            pc_list = [ai_pc, human_pc]
            player_list_fn = lambda: [_make_ai(ai_player_type, ai_pc), HeuristicPlayer(human_pc)]

        game_config = GameConfig(
            players=pc_list,
            engine_url=engine_url,
            deck1=req.player1_deck or list(DEFAULT_DECK),
            deck2=req.player2_deck or list(DEFAULT_DECK),
            verbose=req.verbose,
            max_turns=req.max_turns,
            format=req.format,
        )

        players = player_list_fn()

        observer = None
        if req.observer_enabled and req.observer_url and req.observer_model:
            observer = ObserverAI(req.observer_url, req.observer_model, enable_thinking=merged_ai_enable_thinking)

        with EngineClient(engine_url) as engine:
            loop = HybridGameLoop(
                human_player_name=human_player_name,
                config=game_config,
                engine=engine,
                players=players,
                debug=req.debug,
                observer=observer,
                game_id=game_id,
            )
            loop.run()

    except Exception as exc:
        import traceback
        logger.exception("Hybrid game loop for %s raised an unhandled exception", game_id)
        traceback.print_exc()


def _make_ai(player_type: str, pc):
    from ai_client.heuristic_player import HeuristicPlayer
    from ai_client.ai_player import AIPlayer
    if player_type == "heuristic":
        return HeuristicPlayer(pc)
    return AIPlayer(pc)
