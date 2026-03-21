"""
In-memory game store. REQ-P03, REQ-P02.
GameManager is a singleton dict of game_id → GameState.
Never share mutable state between games.
"""
import copy
import random
import uuid
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card

class GameManager:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}

    def create_game(
        self,
        player1_name: str,
        player2_name: str,
        deck1: list[Card],
        deck2: list[Card],
        seed: int | None = None,
    ) -> GameState:
        """Create a new game, shuffle libraries, deal opening hands. REQ-G01, REQ-G04"""
        game_id = str(uuid.uuid4())
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        rng = random.Random(seed)

        # Shuffle decks using seeded RNG
        deck1 = list(deck1)
        deck2 = list(deck2)
        rng.shuffle(deck1)
        rng.shuffle(deck2)

        # Deal opening hands (7 cards each)
        hand1, lib1 = deck1[:7], deck1[7:]
        hand2, lib2 = deck2[:7], deck2[7:]

        p1 = PlayerState(name=player1_name, hand=hand1, library=lib1)
        p2 = PlayerState(name=player2_name, hand=hand2, library=lib2)

        gs = GameState(
            game_id=game_id,
            seed=seed,
            turn=1,
            active_player=player1_name,
            priority_holder=player1_name,
            phase=Phase.BEGINNING,
            step=Step.UNTAP,
            players=[p1, p2],
        )
        gs.refresh_hash()
        self._games[game_id] = gs
        return gs

    def get(self, game_id: str) -> GameState:
        gs = self._games.get(game_id)
        if gs is None:
            raise KeyError(game_id)
        return gs

    def update(self, game_id: str, gs: GameState) -> None:
        gs.refresh_hash()
        self._games[game_id] = gs

    def delete(self, game_id: str) -> GameState:
        gs = self._games.pop(game_id, None)
        if gs is None:
            raise KeyError(game_id)
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
