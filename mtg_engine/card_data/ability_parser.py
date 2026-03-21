import logging
import re
from typing import Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# REQ-C02: Ability types
class TriggeredAbility(BaseModel):
    trigger_condition: str
    effect: str
    raw_text: str


class ActivatedAbility(BaseModel):
    cost: str
    effect: str
    timing_restriction: str | None = None
    raw_text: str


class KeywordAbility(BaseModel):
    name: str


class SpellEffect(BaseModel):
    effect: str
    raw_text: str


class UnparsedAbility(BaseModel):
    raw_text: str


Ability = Union[TriggeredAbility, ActivatedAbility, KeywordAbility, SpellEffect, UnparsedAbility]

# All keyword abilities defined in REQ-R20
KEYWORDS: frozenset[str] = frozenset({
    "deathtouch", "defender", "double strike", "enchant", "equip",
    "first strike", "flash", "flying", "haste", "hexproof",
    "indestructible", "intimidate", "landwalk", "lifelink", "menace",
    "protection", "reach", "shroud", "trample", "vigilance",
    "banding", "flanking", "provoke", "bushido", "soulshift",
    "ninjutsu", "haunt", "convoke", "dredge", "transmute",
    "bloodthirst", "graft", "recover", "ripple", "split second",
    "suspend", "vanishing", "absorb", "aura swap", "delve", "fortify",
    "frenzy", "gravestorm", "poisonous", "transfigure", "champion",
    "changeling", "evoke", "hideaway", "prowl", "reinforce",
    "conspire", "persist", "wither", "retrace", "devour", "exalted",
    "unearth", "cascade", "annihilator", "level up", "rebound",
    "totem armor", "infect", "battle cry", "living weapon", "undying",
    "miracle", "soulbond", "overload", "scavenge", "unleash",
    "cipher", "evolve", "extort", "fuse", "bestow", "tribute",
    "dethrone", "hidden agenda", "outlast", "prowess", "dash",
    "exploit", "renown", "awaken", "devoid", "ingest", "myriad",
    "surge", "skulk", "emerge", "escalate", "meld", "crew",
    "fabricate", "partner", "undaunted", "improvise", "aftermath",
    "embalm", "eternalize", "afflict", "ascend", "assist",
    "jump-start", "mentor", "riot", "spectacle", "escape",
    "companion", "mutate", "encore", "boast", "foretell",
    "demonstrate", "daybound", "nightbound", "disturb", "dungeon",
    "ward", "blitz", "casualty", "connive", "domain", "enlist",
    "read ahead", "reconfigure", "training", "cleave", "compleated",
    "prototype", "backup", "bargain", "disguise", "cloak", "plot",
    "suspect", "manifest dread", "saddle", "gift",
})

_TRIGGERED_RE = re.compile(
    r"^((?:When(?:ever)?|At)\b[^,]*),\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_ACTIVATED_RE = re.compile(
    r"^(\{[^}]+\}(?:,\s*\{[^}]+\})*(?:,\s*[^:,]+)?)\s*:\s*(.+)$",
    re.DOTALL,
)
_TIMING_RE = re.compile(r"\(activate only (?:as a sorcery|during [^)]+)\)", re.IGNORECASE)


def parse_oracle_text(oracle_text: str, type_line: str = "") -> list[Ability]:
    """
    Parse oracle text into structured ability objects. REQ-C02

    For instants/sorceries the entire oracle text is a SpellEffect.
    For permanents, each line/clause is parsed individually.
    """
    if not oracle_text or not oracle_text.strip():
        return []

    type_lower = type_line.lower()
    is_spell = "instant" in type_lower or "sorcery" in type_lower

    if is_spell:
        return [SpellEffect(effect=oracle_text.strip(), raw_text=oracle_text.strip())]

    abilities: list[Ability] = []
    # Split on newlines; each paragraph is typically one ability
    segments = [s.strip() for s in oracle_text.split("\n") if s.strip()]

    for segment in segments:
        parsed = _parse_segment(segment)
        abilities.extend(parsed)

    return abilities


def _parse_segment(text: str) -> list[Ability]:
    """Parse a single oracle text segment into one or more abilities."""
    # Check for comma-separated keywords first (e.g. "Flying, vigilance")
    keyword_results = _try_parse_keywords(text)
    if keyword_results:
        return keyword_results

    # Triggered ability
    m = _TRIGGERED_RE.match(text)
    if m:
        trigger_part = m.group(1).strip()
        effect_part = m.group(2).strip()
        return [TriggeredAbility(
            trigger_condition=trigger_part,
            effect=effect_part,
            raw_text=text,
        )]

    # Activated ability: "{cost}: effect"
    m = _ACTIVATED_RE.match(text)
    if m:
        cost = m.group(1).strip()
        effect_and_timing = m.group(2).strip()
        timing_match = _TIMING_RE.search(effect_and_timing)
        timing = timing_match.group(0) if timing_match else None
        effect = _TIMING_RE.sub("", effect_and_timing).strip().rstrip("(").strip()
        return [ActivatedAbility(
            cost=cost,
            effect=effect,
            timing_restriction=timing,
            raw_text=text,
        )]

    # Single keyword
    lower = text.rstrip(".").lower().strip()
    if lower in KEYWORDS:
        return [KeywordAbility(name=lower)]

    # Unknown — log warning per REQ-C03
    logger.warning("UnparsedAbility: %r", text)
    return [UnparsedAbility(raw_text=text)]


def _try_parse_keywords(text: str) -> list[KeywordAbility] | None:
    """Try to parse text as a comma-separated keyword list."""
    # Handle keyword abilities that may have a parameter, e.g. "Protection from red"
    parts = [p.strip().rstrip(".") for p in text.split(",")]
    results: list[KeywordAbility] = []
    for part in parts:
        lower = part.lower()
        # Exact match
        if lower in KEYWORDS:
            results.append(KeywordAbility(name=lower))
            continue
        # Keyword with parameter (e.g. "protection from red", "bushido 2")
        base = re.split(r"\s+\d+$|\s+from\b|\s+\{", lower)[0].strip()
        if base in KEYWORDS:
            results.append(KeywordAbility(name=lower))
            continue
        # Not a keyword
        return None
    return results if results else None
