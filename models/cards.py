from pydantic import BaseModel

class CardModel(BaseModel):
    name: str
    type: str
    cost: int
    abilities: list[str]