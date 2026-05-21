import re
from typing import Optional
from pydantic import BaseModel, Field


def parse_equip_cost(oracle_text: str) -> Optional[str]:
    """Extract the equip cost from oracle text.

    Handles: 'Equip {1}', 'Equip—Sacrifice a creature.',
    'Equip {2}. Equip only as a sorcery.'
    """
    if not oracle_text:
        return None
    m = re.search(r"\bEquip\b\s*[—\-]?\s*(\{.+\}|[A-Za-z][^.,\n]+?)(?:\.|$|\s+(?:only|Equip))", oracle_text)
    if m:
        return m.group(1).strip()
    m = re.search(r"^\bEquip\b\s*[—\-]?\s*(\{.+\}|[A-Za-z][^.,\n]+)$", oracle_text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def parse_crew_cost(oracle_text: str) -> int:
    """Extract the crew value from oracle text.

    Handles: 'Crew 3', 'Crew 1'
    Returns 0 if no crew ability.
    """
    if not oracle_text:
        return 0
    m = re.search(r"crew\s+(\d+)", oracle_text.lower())
    if m:
        return int(m.group(1))
    return 0


def can_equip(equipment_type_line: str, target_type_line: str) -> bool:
    """Check if an Equipment can equip a permanent (must be a creature, CR 301.5c)."""
    if "equipment" not in equipment_type_line.lower():
        return False
    return is_creature_type_line(target_type_line)


def is_creature_type_line(type_line: str) -> bool:
    """Check if a type line indicates a creature permanent."""
    return "creature" in type_line.lower()


class EquipmentModel(BaseModel):
    name: str = ""
    equip_cost: Optional[str] = None
    type_line: str = ""
    power_bonus: int = 0
    toughness_bonus: int = 0
    granted_keywords: list[str] = Field(default_factory=list)
    can_attach: bool = True

    @staticmethod
    def from_oracle_text(name: str, oracle_text: str, type_line: str) -> "EquipmentModel":
        equip_cost = parse_equip_cost(oracle_text)
        return EquipmentModel(
            name=name,
            equip_cost=equip_cost,
            type_line=type_line,
        )


class VehicleModel(BaseModel):
    name: str = ""
    crew_cost: int = 0
    type_line: str = ""
    power: int = 0
    toughness: int = 0
    keywords: list[str] = Field(default_factory=list)
    is_creature: bool = False
    crewed_this_turn: bool = False

    @staticmethod
    def from_oracle_text(name: str, oracle_text: str, type_line: str) -> "VehicleModel":
        crew_cost = parse_crew_cost(oracle_text)
        return VehicleModel(
            name=name,
            crew_cost=crew_cost,
            type_line=type_line,
        )

    def can_crew(self, total_power: int) -> bool:
        if self.crewed_this_turn:
            return False
        return total_power >= self.crew_cost

    def crew(self) -> None:
        self.is_creature = True
        self.crewed_this_turn = True

    def uncrew(self) -> None:
        self.is_creature = False
        self.crewed_this_turn = False
