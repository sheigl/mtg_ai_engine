"""
In-memory game store. REQ-P03, REQ-P02.
GameManager is a singleton dict of game_id → GameState.
Never share mutable state between games.
"""
import copy
import random
import uuid
from typing import Optional
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card
from mtg_engine.export.transcript import TranscriptRecorder
from mtg_engine.engine.verbose_log import VerboseLogger, ensure_zone_listener_registered


class GameManager:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}
        self._recorders: dict[str, TranscriptRecorder] = {}
        self._verbose_loggers: dict[str, VerboseLogger] = {}

    def create_game(
        self,
        player1_name: str,
        player2_name: str,
        deck1: list[Card],
        deck2: list[Card],
        seed: int | None = None,
        verbose: bool = False,
        format: str = "standard",
        commander1_card: Optional[Card] = None,
        commander2_card: Optional[Card] = None,
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

        # Commander: set up command zones
        if format == "commander":
            if commander1_card is not None:
                p1.commander_name = commander1_card.name
                p1.command_zone = [commander1_card]
                p1.commander_cast_count = 0
            if commander2_card is not None:
                p2.commander_name = commander2_card.name
                p2.command_zone = [commander2_card]
                p2.commander_cast_count = 0

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
        )
        gs.refresh_hash()
        self._games[game_id] = gs

        # Create per-game recorder and verbose logger
        recorder = TranscriptRecorder(game_id)
        vlogger = VerboseLogger(game_id, enabled=verbose)
        recorder.register_listener(vlogger.on_event)
        self._recorders[game_id] = recorder
        self._verbose_loggers[game_id] = vlogger

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

    def delete(self, game_id: str) -> GameState:
        gs = self._games.pop(game_id, None)
        if gs is None:
            raise KeyError(game_id)
        # Clean up recorder and logger
        self._recorders.pop(game_id, None)
        vlogger = self._verbose_loggers.pop(game_id, None)
        if vlogger:
            vlogger.disable()
        return gs

    def snapshot(self, game_id: str) -> GameState:
        """Return a deep copy for dry_run simulations. REQ-P05"""
        gs = self.get(game_id)
        return copy.deepcopy(gs)

    def __contains__(self, game_id: str) -> bool:
        return game_id in self._games


# Module-level singleton
_manager = GameManager()

def get_manager() -> GameManager:
    return _manager
