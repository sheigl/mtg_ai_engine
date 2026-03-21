from pydantic import BaseModel

class GameModel(BaseModel):
    players: list[PlayerModel]
    current_turn: int
    state: str