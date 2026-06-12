from enum import Enum
from typing import Optional
from pydantic import BaseModel


class BattleSubtype(str, Enum):
    SIEGE = "Siege"


class BattleModel(BaseModel):
    name: str = ""
    defense_counters: int = 0
    protector: Optional[str] = None
    controller: str = ""
    subtype: str = ""
    last_damage_controller: Optional[str] = None
    oracle_text: str = ""

    @property
    def is_siege(self) -> bool:
        return self.subtype == "Siege"

    @property
    def is_defeated(self) -> bool:
        return self.defense_counters <= 0

    def deal_damage(self, amount: int, source_controller: Optional[str] = None) -> None:
        self.defense_counters = max(0, self.defense_counters - amount)
        if source_controller:
            self.last_damage_controller = source_controller

    def change_protector(self, new_protector: str) -> None:
        self.protector = new_protector

    @staticmethod
    def from_type_line(
        name: str,
        type_line: str,
        oracle_text: str = "",
        controller: str = "",
        protector: Optional[str] = None,
    ) -> "BattleModel":
        subtype = ""
        if "—" in type_line:
            subtype = type_line.split("—")[1].strip().split()[0] if type_line.split("—")[1].strip() else ""

        return BattleModel(
            name=name,
            controller=controller,
            protector=protector,
            subtype=subtype,
            oracle_text=oracle_text,
        )


def get_siege_abilities(oracle_text: str) -> dict[str, bool]:
    result = {
        "exile_on_defeat": False,
        "cast_transformed": False,
        "requires_attack": False,
    }
    if not oracle_text:
        return result
    text_lower = oracle_text.lower()
    if "when the last defense counter is removed from this permanent" in text_lower:
        result["exile_on_defeat"] = True
    if "cast it transformed" in text_lower or "cast it transformed" in text_lower:
        result["cast_transformed"] = True
    return result
