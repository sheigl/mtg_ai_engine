"""
In-memory game store with MongoDB persistence. REQ-P03, REQ-P02.
GameManager is a singleton dict of game_id → GameState.
Never share mutable state between games.
"""
import copy
import logging
import random
import uuid
from typing import Optional
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card
from mtg_engine.export.store import get_export_store
from mtg_engine.export.transcript import TranscriptRecorder
from mtg_engine.engine.verbose_log import VerboseLogger, ensure_zone_listener_registered

logger = logging.getLogger(__name__)


class SeriesResult:
    def __init__(self, game_id: str, winner: str | None, turn: int) -> None:
        self.game_id = game_id
        self.winner = winner
        self.turn = turn


class SeriesConfig:
    def __init__(
        self,
        series_id: str,
        total_games: int,
        settings: dict,
    ) -> None:
        self.series_id = series_id
        self.total_games = total_games
        self.settings = settings
        self.completed_games = 0
        self.results: list[SeriesResult] = []
        self.active_game_id: str | None = None
        self.wins: dict[str, int] = {}


class GameManager:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}
        self._recorders: dict[str, TranscriptRecorder] = {}
        self._verbose_loggers: dict[str, VerboseLogger] = {}
        self._paused: set[str] = set()
        self._series: dict[str, SeriesConfig] = {}
        self._store = None
        try:
            from mtg_engine.persistence.game_state_store import get_game_state_store
            self._store = get_game_state_store()
        except Exception:
            logger.warning("GameManager: game state store unavailable", exc_info=True)

    def pause(self, game_id: str) -> None:
        self._paused.add(game_id)

    def resume(self, game_id: str) -> None:
        self._paused.discard(game_id)

    def is_paused(self, game_id: str) -> bool:
        return game_id in self._paused

    def create_game(
        self,
        player1_name: str,
        player2_name: str,
        deck1: list[Card],
        deck2: list[Card],
        seed: int | None = None,
        verbose: bool = False,
        debug: bool = False,
        format: str = "standard",
        commander1_card: Optional[Card] = None,
        commander2_card: Optional[Card] = None,
        player1_type: str = "ai",
        player2_type: str = "ai",
        deck_name1: str | None = None,
        deck_name2: str | None = None,
    ) -> GameState:
        """Create a new game, shuffle libraries, deal opening hands. REQ-G01, REQ-G04"""
        # Ensure the global zone-change listener is registered (once per process)
        ensure_zone_listener_registered()

        game_id = str(uuid.uuid4())
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        rng = random.Random(seed)

        # Commander: starting life is 40
        starting_life = 40 if format == "commander" else 20

        # Shuffle decks using seeded RNG
        deck1 = list(deck1)
        deck2 = list(deck2)
        rng.shuffle(deck1)
        rng.shuffle(deck2)

        # Deal opening hands (7 cards each)
        hand1, lib1 = deck1[:7], deck1[7:]
        hand2, lib2 = deck2[:7], deck2[7:]

        p1 = PlayerState(name=player1_name, hand=hand1, library=lib1, life=starting_life)
        p2 = PlayerState(name=player2_name, hand=hand2, library=lib2, life=starting_life)

        # Set deck name and compute color identity (033-deck-randomizer)
        p1.deck_name = deck_name1
        p2.deck_name = deck_name2
        ci1 = sorted({c for card in deck1 for c in card.color_identity})
        ci2 = sorted({c for card in deck2 for c in card.color_identity})
        p1.color_identity = ci1
        p2.color_identity = ci2

        # Commander: set up command zones
        if format == "commander":
            if commander1_card is not None:
                p1.commander_name = commander1_card.name
                p1.command_zone = [commander1_card]
                p1.commander_cast_counts = {}
            if commander2_card is not None:
                p2.commander_name = commander2_card.name
                p2.command_zone = [commander2_card]
                p2.commander_cast_counts = {}

        gs = GameState(
            game_id=game_id,
            seed=seed,
            turn=1,
            active_player=player1_name,
            priority_holder=player1_name,
            phase=Phase.BEGINNING,
            step=Step.UNTAP,
            players=[p1, p2],
            format=format,
            debug_enabled=debug,
            mulligan_phase_active=True,
        )
        gs.refresh_hash()
        self._games[game_id] = gs

        # Wire legacy zone-change triggers for death/ETB detection
        from mtg_engine.engine.triggers import initialize_triggers
        initialize_triggers(gs)

        # Wire EventBus bridge for life-change, counter, damage events
        try:
            from mtg_engine.engine.events import EventTriggerBridge, get_default_bus
            bridge = EventTriggerBridge(get_default_bus(), game_id=game_id)
            bridge.register(gs)
        except Exception:
            logger.debug("EventBus bridge not available", exc_info=True)

        # Use the export store's transcript so GET /export/{id}/transcript sees all events
        store = get_export_store(game_id)
        recorder = store.transcript
        vlogger = VerboseLogger(game_id, enabled=verbose)
        recorder.register_listener(vlogger.on_event)
        self._recorders[game_id] = recorder
        self._verbose_loggers[game_id] = vlogger

        if store.persister is not None:
            store.persister.register_on_store(store)
            store.persister.init_game_document(
                player1_name, player1_type, player2_name, player2_type, format,
            )

        return gs

    def get(self, game_id: str) -> GameState:
        gs = self._games.get(game_id)
        if gs is None:
            raise KeyError(game_id)
        return gs

    def get_recorder(self, game_id: str) -> TranscriptRecorder:
        """Return the TranscriptRecorder for a game. Raises KeyError if not found."""
        recorder = self._recorders.get(game_id)
        if recorder is None:
            raise KeyError(game_id)
        return recorder

    def set_verbose(self, game_id: str, enabled: bool) -> None:
        """Enable or disable verbose logging for a game. Raises KeyError if not found."""
        vlogger = self._verbose_loggers.get(game_id)
        if vlogger is None:
            raise KeyError(game_id)
        if enabled:
            vlogger.enable()
        else:
            vlogger.disable()

    def update(self, game_id: str, gs: GameState) -> None:
        gs.refresh_hash()
        self._games[game_id] = gs
        self._persist(game_id)

    def delete(self, game_id: str) -> GameState:
        gs = self._games.pop(game_id, None)
        if gs is None:
            raise KeyError(game_id)
        self._recorders.pop(game_id, None)
        vlogger = self._verbose_loggers.pop(game_id, None)
        if vlogger:
            vlogger.disable()
        if self._store and gs:
            self._store.mark_complete(game_id)
        return gs

    def snapshot(self, game_id: str) -> GameState:
        """Return a deep copy for dry_run simulations. REQ-P05"""
        gs = self.get(game_id)
        return copy.deepcopy(gs)

    def __contains__(self, game_id: str) -> bool:
        return game_id in self._games

    # ── Persistence (034-game-persistence) ─────────────────────────────────

    def _persist(self, game_id: str) -> None:
        """Persist the current game state to MongoDB (fire-and-forget)."""
        if not self._store:
            return
        gs = self._games.get(game_id)
        if gs is None:
            return
        try:
            series_config = None
            if gs.series_id and gs.series_id in self._series:
                sc = self._series[gs.series_id]
                series_config = {
                    "series_id": sc.series_id,
                    "total_games": sc.total_games,
                    "settings": sc.settings,
                    "completed_games": sc.completed_games,
                    "active_game_id": sc.active_game_id,
                    "wins": sc.wins,
                }
            # Sync transcript entries from recorder to GameState for persistence
            recorder = self._recorders.get(game_id)
            if recorder:
                gs.transcript_entries = [e.model_dump(mode='json') for e in recorder._entries]
            state_dict = gs.model_dump(mode='json')
            self._store.upsert(
                game_id,
                state_dict,
                series_config=series_config,
                is_complete=gs.is_game_over,
            )
        except Exception:
            logger.warning("GameManager: failed to persist %s", game_id, exc_info=True)

    def save_game(self, game_id: str) -> None:
        """Explicitly save a game state to MongoDB."""
        self._persist(game_id)

    def mark_complete(self, game_id: str) -> None:
        """Mark a game as complete in MongoDB."""
        if self._store:
            try:
                self._store.mark_complete(game_id)
            except Exception:
                logger.warning("GameManager: failed to mark complete %s", game_id, exc_info=True)

    def restore_games(self) -> int:
        """Load all non-completed games from MongoDB. Returns count of restored games."""
        if not self._store:
            logger.info("GameManager: no persistence store, skipping restore")
            return 0
        try:
            docs = self._store.load_all_active()
            count = 0
            for doc in docs:
                try:
                    gs = GameState.model_validate(doc["state"])
                    self._games[gs.game_id] = gs
                    if doc.get("series_config"):
                        sc_data = doc["series_config"]
                        sc = SeriesConfig(
                            series_id=sc_data["series_id"],
                            total_games=sc_data["total_games"],
                            settings=sc_data.get("settings", {}),
                        )
                        sc.completed_games = sc_data.get("completed_games", 0)
                        sc.active_game_id = sc_data.get("active_game_id")
                        sc.wins = sc_data.get("wins", {})
                        self._series[sc.series_id] = sc
                    # Recreate export store, recorder, and verbose logger
                    store = get_export_store(gs.game_id)
                    recorder = store.transcript
                    # Restore transcript entries from saved state
                    if gs.transcript_entries:
                        from mtg_engine.export.transcript import TranscriptEntry
                        for entry_data in gs.transcript_entries:
                            entry = TranscriptEntry.model_validate(entry_data)
                            recorder._entries.append(entry)
                            recorder._seq = max(recorder._seq, entry.seq)
                    p1 = gs.players[0] if gs.players else None
                    p2 = gs.players[1] if len(gs.players) > 1 else None
                    vlogger = VerboseLogger(gs.game_id, enabled=gs.debug_enabled)
                    recorder.register_listener(vlogger.on_event)
                    self._recorders[gs.game_id] = recorder
                    self._verbose_loggers[gs.game_id] = vlogger
                    # Register persister for future events
                    if store.persister is not None:
                        store.persister.register_on_store(store)
                        store.persister.init_game_document(
                            p1.name if p1 else "Player 1",
                            p1.player_type if p1 and hasattr(p1, 'player_type') else "ai",
                            p2.name if p2 else "Player 2",
                            p2.player_type if p2 and hasattr(p2, 'player_type') else "ai",
                            gs.format,
                        )
                    count += 1
                    logger.info("GameManager: restored game %s", gs.game_id)
                except Exception:
                    logger.warning("GameManager: failed to restore game from doc", exc_info=True)
            logger.info("GameManager: restored %d games from MongoDB", count)
            return count
        except Exception:
            logger.warning("GameManager: failed to restore games", exc_info=True)
            return 0

    # ── Series mode (032-game-series) ───────────────────────────────────────

    def create_series(self, total_games: int, settings: dict) -> str:
        """Register a new series and return its series_id."""
        series_id = str(uuid.uuid4())
        self._series[series_id] = SeriesConfig(series_id, total_games, settings)
        return series_id

    def get_series(self, series_id: str) -> SeriesConfig:
        sc = self._series.get(series_id)
        if sc is None:
            raise KeyError(series_id)
        return sc

    def record_series_result(self, series_id: str, game_id: str, winner: str | None, turn: int) -> None:
        """Record the result of one game in a series."""
        sc = self._series.get(series_id)
        if sc is None:
            return
        sc.results.append(SeriesResult(game_id, winner, turn))
        sc.completed_games += 1
        if winner and winner != "draw":
            sc.wins[winner] = sc.wins.get(winner, 0) + 1

    def is_series_complete(self, series_id: str) -> bool:
        """Return True if the series has played all scheduled games."""
        sc = self._series.get(series_id)
        if sc is None:
            return True
        return sc.completed_games >= sc.total_games


# Module-level singleton
_manager = GameManager()

def get_manager() -> GameManager:
    return _manager
