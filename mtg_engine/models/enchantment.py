import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from mtg_engine.models.card_type import CardType, CoreType


class AuraTargetType(str, Enum):
    """Types of objects an Aura can target via its 'Enchant X' ability."""
    CREATURE = "Creature"
    LAND = "Land"
    ARTIFACT = "Artifact"
    ENCHANTMENT = "Enchantment"
    PLANESWALKER = "Planewalker"
    BATTLE = "Battle"
    PERMANENT = "Permanent"
    PLAYER = "Player"


# Mapping from enchant text keywords to AuraTargetType values
_ENCHANT_KEYWORD_MAP: dict[str, AuraTargetType] = {
    "creature": AuraTargetType.CREATURE,
    "land": AuraTargetType.LAND,
    "artifact": AuraTargetType.ARTIFACT,
    "enchantment": AuraTargetType.ENCHANTMENT,
    "planeswalker": AuraTargetType.PLANESWALKER,
    "battle": AuraTargetType.BATTLE,
    "permanent": AuraTargetType.PERMANENT,
    "player": AuraTargetType.PLAYER,
}

# Mapping from AuraTargetType to CardType.CoreType
_TARGET_TYPE_TO_CORE_TYPE: dict[AuraTargetType, CoreType] = {
    AuraTargetType.CREATURE: CoreType.CREATURE,
    AuraTargetType.LAND: CoreType.ENCHANTMENT,
    AuraTargetType.ARTIFACT: CoreType.ARTIFACT,
    AuraTargetType.ENCHANTMENT: CoreType.ENCHANTMENT,
    AuraTargetType.PLANESWALKER: CoreType.PLANEWALKER,
    AuraTargetType.BATTLE: CoreType.BATTLE,
}


class AuraTarget(BaseModel):
    """Represents what an Aura can enchant (from 'Enchant X' in oracle text).

    CR 303.4 — An Aura spell targets the object it will enchant.
    """
    target_types: list[AuraTargetType] = Field(default_factory=list)
    control_restriction: Optional[str] = None
    creature_type_restriction: Optional[str] = None
    can_enchant_anything: bool = False
    raw_text: str = ""

    def can_enchant_permanent(self, type_line: str) -> bool:
        if self.can_enchant_anything:
            return True
        if not self.target_types:
            return False
        type_lower = type_line.lower()
        for ttype in self.target_types:
            if ttype == AuraTargetType.LAND:
                if "land" in type_lower:
                    return True
            else:
                core = _TARGET_TYPE_TO_CORE_TYPE.get(ttype)
                if core and core.value.lower() in type_lower:
                    return True
        return False

    def can_enchant_player(self) -> bool:
        return AuraTargetType.PLAYER in self.target_types

    def requires_creature_type(self, creature_type: str) -> bool:
        if not self.creature_type_restriction:
            return False
        return self.creature_type_restriction.lower() == creature_type.lower()

    def can_enchant(self, target_type: AuraTargetType) -> bool:
        return target_type in self.target_types


def _extract_enchant_targets(text: str) -> list[str]:
    """Extract all target type keywords from 'Enchant X' patterns.

    Handles: 'Enchant creature', 'Enchant creature you control',
    'Enchant creature, land, or planeswalker', 'Enchant target creature',
    'Enchant Goblin' (creature type restriction).
    """
    targets: list[str] = []
    # Find "enchant ..." and capture everything up to the next sentence or end
    m = re.search(r"enchant\s+(.+?)(?:\.|$|\n)", text.lower())
    if not m:
        return targets
    rest = m.group(1).strip()
    # Remove control qualifiers
    for qual in ("you control", "an opponent controls", "an opponent owns", "target"):
        rest = rest.replace(qual, "")
    # Split on commas, "and", "or"
    rest = re.sub(r"\b(?:and|or)\b", ",", rest)
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    for part in parts:
        part = part.strip()
        if part and part not in targets:
            targets.append(part)
    return targets


def parse_aura_target(oracle_text: str) -> AuraTarget:
    result = AuraTarget(raw_text=oracle_text)
    if not oracle_text:
        return result

    targets = _extract_enchant_targets(oracle_text)

    for t in targets:
        target_type = _ENCHANT_KEYWORD_MAP.get(t)
        if target_type:
            if target_type == AuraTargetType.PERMANENT:
                result.can_enchant_anything = True
            if target_type not in result.target_types:
                result.target_types.append(target_type)
        else:
            # Not a known keyword — treat as creature type restriction
            result.creature_type_restriction = t.capitalize()
            if AuraTargetType.CREATURE not in result.target_types:
                result.target_types.append(AuraTargetType.CREATURE)

    # Check for control restrictions
    control_patterns = [
        (r"enchant\s+.+?\s+you control", "you_control"),
        (r"enchant\s+.+?\s+an opponent controls", "opponent_controls"),
        (r"enchant\s+.+?\s+an opponent owns", "opponent_controls"),
    ]
    for ctrl_pat, restriction in control_patterns:
        if re.search(ctrl_pat, oracle_text.lower()):
            result.control_restriction = restriction
            break

    return result


def is_aura_type_line(type_line: str) -> bool:
    ct = CardType()
    if "Aura" in type_line:
        return True
    return "enchantment" in type_line.lower() and "aura" in type_line.lower()
