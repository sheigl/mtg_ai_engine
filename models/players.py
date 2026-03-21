from pydantic import BaseModel

class PlayerModel(BaseModel):
    name: str
    deck: list[str]
    life: int