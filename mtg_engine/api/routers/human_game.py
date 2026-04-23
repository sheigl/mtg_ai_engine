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
    max_turns: int = 0
    debug: bool = False
    commander1: str | None = None
    commander2: str | None = None
    series_count: int = 1
    randomize_decks_per_game: bool = False

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

    # Load decks — randomize from MTGGoldfish if not provided (033-deck-randomizer)
    try:
        from mtg_engine.card_data.mtggoldfish import get_random_deck
        deck1_names = req.player1_deck
        deck2_names = req.player2_deck
        commander1_name = req.commander1
        commander2_name = req.commander2
        deck_name1: str | None = None
        deck_name2: str | None = None

        if not deck1_names:
            rd = get_random_deck(req.format)
            if rd:
                deck1_names = rd.to_card_names()
                deck_name1 = rd.name
                if req.format == "commander" and rd.commander:
                    commander1_name = rd.commander
        if not deck2_names:
            rd = get_random_deck(req.format)
            if rd:
                deck2_names = rd.to_card_names()
                deck_name2 = rd.name
                if req.format == "commander" and rd.commander:
                    commander2_name = rd.commander

        if req.format == "commander":
            fallback = list(DEFAULT_COMMANDER_DECK)
            d1 = deck1_names if deck1_names else fallback
            d2 = deck2_names if deck2_names else fallback
            if not commander1_name or not commander2_name:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "Commander format requires commander1 and commander2", "error_code": "MISSING_COMMANDER"},
                )
            if commander1_name not in d1:
                d1 = d1 + [commander1_name]
            if commander2_name not in d2:
                d2 = d2 + [commander2_name]
            deck1_cards, commander1_card = load_commander_deck(d1, commander1_name)
            deck2_cards, commander2_card = load_commander_deck(d2, commander2_name)
        else:
            d1 = deck1_names if deck1_names else list(DEFAULT_DECK)
            d2 = deck2_names if deck2_names else list(DEFAULT_DECK)
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

    # Series mode (032-game-series)
    series_id: str | None = None
    if req.series_count > 1:
        series_settings = {
            "player1_type": req.player1_type,
            "player2_type": req.player2_type,
            "player1_name": req.player1_name,
            "player2_name": req.player2_name,
            "player1_deck": req.player1_deck,
            "player2_deck": req.player2_deck,
            "format": req.format,
            "ai_model": req.ai_model,
            "ai_base_url": req.ai_base_url,
            "ai_enable_thinking": req.ai_enable_thinking,
            "observer_model": req.observer_model,
            "observer_url": req.observer_url,
            "observer_enabled": req.observer_enabled,
            "verbose": req.verbose,
            "max_turns": req.max_turns,
            "debug": req.debug,
            "commander1": req.commander1,
            "commander2": req.commander2,
            "randomize_decks_per_game": req.randomize_decks_per_game,
        }
        series_id = mgr.create_series(req.series_count, series_settings)

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
        deck_name1=deck_name1,
        deck_name2=deck_name2,
    )
    if series_id:
        gs.series_id = series_id
        mgr.get_series(series_id).active_game_id = gs.game_id
        mgr.update(gs.game_id, gs)
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
              final_ai_base_url, final_ai_model, final_ai_enable_thinking, series_id),
        daemon=False,
        name=f"human-game-{game_id[:8]}",
    )
    thread.start()
    logger.info("Started hybrid game loop thread for game %s (human=%s, series=%s)", game_id, human_player_name, series_id)
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
    series_id: str | None = None,
) -> None:
    """Build and run the HybridGameLoop in a daemon thread."""
    summary = None
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
            summary = loop.run()

    except Exception as exc:
        import traceback
        logger.exception("Hybrid game loop for %s raised an unhandled exception", game_id)
        traceback.print_exc()

    # Series continuation (032-game-series)
    if series_id and summary:
        from mtg_engine.api.game_manager import get_manager
        mgr = get_manager()
        try:
            mgr.record_series_result(series_id, game_id, summary.winner, summary.total_turns)
            if not mgr.is_series_complete(series_id):
                sc = mgr.get_series(series_id)
                print(f"[human-game] Series {series_id[:8]}: spawning game {sc.completed_games + 1} of {sc.total_games}", flush=True)
                _spawn_next_human_game(req, series_id, engine_url, human_player_name, ai_player_name, ai_player_type,
                                       merged_ai_base_url, merged_ai_model, merged_ai_enable_thinking)
        except Exception as e:
            logger.warning("Series continuation failed for %s: %s", series_id, e)


def _spawn_next_human_game(
    req: HumanGameRequest,
    series_id: str,
    engine_url: str,
    human_player_name: str,
    ai_player_name: str,
    ai_player_type: str,
    merged_ai_base_url: str,
    merged_ai_model: str,
    merged_ai_enable_thinking: bool | None,
) -> None:
    """Create the next game in a human vs AI series and start its loop."""
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
    deck1_names = req.player1_deck
    deck2_names = req.player2_deck
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
        fallback = list(DEFAULT_COMMANDER_DECK)
        d1 = deck1_names if deck1_names else fallback
        d2 = deck2_names if deck2_names else fallback
        if commander1_name not in d1:
            d1 = d1 + [commander1_name]
        if commander2_name not in d2:
            d2 = d2 + [commander2_name]
        deck1_cards, commander1_card = load_commander_deck(d1, commander1_name)
        deck2_cards, commander2_card = load_commander_deck(d2, commander2_name)
    else:
        d1 = deck1_names if deck1_names else list(DEFAULT_DECK)
        d2 = deck2_names if deck2_names else list(DEFAULT_DECK)
        deck1_cards = load_deck(d1)
        deck2_cards = load_deck(d2)
        commander1_card = None
        commander2_card = None

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
        deck_name1=deck_name1_spawn,
        deck_name2=deck_name2_spawn,
    )
    gs.series_id = series_id
    sc.active_game_id = gs.game_id
    mgr.update(gs.game_id, gs)

    thread = threading.Thread(
        target=_run_hybrid_loop,
        args=(req, gs.game_id, engine_url, human_player_name, ai_player_name, ai_player_type,
              merged_ai_base_url, merged_ai_model, merged_ai_enable_thinking, series_id),
        daemon=False,
        name=f"human-game-{gs.game_id[:8]}",
    )
    thread.start()
    logger.info("Started series game %s for series %s", gs.game_id, series_id)
    _human_player_registry[gs.game_id] = human_player_name


def _make_ai(player_type: str, pc):
    from ai_client.heuristic_player import HeuristicPlayer
    from ai_client.ai_player import AIPlayer
    if player_type == "heuristic":
        return HeuristicPlayer(pc)
    return AIPlayer(pc)
