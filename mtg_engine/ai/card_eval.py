"""
AI card evaluation helpers (AI-03).

Provides card-quality scoring functions used by the heuristic AI and
available for direct use in AI tests and training data.

Parity with Forge's ComputerUtilCard / ComputerUtilAbility.
"""
import re
from typing import Optional

# Regex patterns shared with the heuristic player
_DRAW_RE = re.compile(r'draw\s', re.IGNORECASE)
_REMOVE_RE = re.compile(r'destroy target|exile target|deals?\s+\d+\s+damage\s+to\s+(?:any\s+target|target\s+creature)', re.IGNORECASE)
_COUNTER_RE = re.compile(r'counter target spell', re.IGNORECASE)
_RAMP_RE = re.compile(r'search your library for.*?land|put.*?land.*?onto the battlefield', re.IGNORECASE)
_WIPE_RE = re.compile(r'destroy all creatures|exile all creatures|all creatures get -\d+/-\d+', re.IGNORECASE)
_LIFEGAIN_RE = re.compile(r'you gain (\d+) life|gain (\d+) life', re.IGNORECASE)
_TOKENS_RE = re.compile(r'create.*?token|put.*?token.*?onto the battlefield', re.IGNORECASE)
_TUTOR_RE = re.compile(r'search your library for (?:a |an |any )?(\w+(?:\s\w+)?)\s*(?:card|spell)', re.IGNORECASE)


def _oracle_text(card: dict) -> str:
    return (card.get("oracle_text") or card.get("parsed") or "")


def has_keyword(card: dict, keyword: str) -> bool:
    """Check if a card has a given keyword (flying, haste, etc.)."""
    for kw in (card.get("keywords") or []):
        if kw.lower() == keyword.lower():
            return True
    return keyword.lower() in _oracle_text(card).lower()


def compute_cmc(mana_cost: Optional[str]) -> float:
    """
    Compute converted mana cost from a mana cost string like ``{2}{R}{R}``.
    """
    if not mana_cost:
        return 0.0
    total = 0
    generic_match = re.search(r'\{(\d+)\}', mana_cost)
    if generic_match:
        total += int(generic_match.group(1))
    colored = re.findall(r'\{([WUBRG])\}', mana_cost)
    total += len(colored)
    hybrid = re.findall(r'\{[WUBRG]/[WUBRG]\}', mana_cost)
    total += len(hybrid)
    return float(total)


def is_removal_spell(card: dict) -> bool:
    """Return True if the card is removal (destroy, exile, damage to target)."""
    text = _oracle_text(card)
    return bool(_REMOVE_RE.search(text))


def is_counterspell(card: dict) -> bool:
    """Return True if the card can counter a spell."""
    text = _oracle_text(card)
    return bool(_COUNTER_RE.search(text))


def is_board_wipe(card: dict) -> bool:
    """Return True if the card is a board wipe."""
    text = _oracle_text(card)
    return bool(_WIPE_RE.search(text))


def is_draw_spell(card: dict) -> bool:
    """Return True if the card provides card draw."""
    text = _oracle_text(card)
    return bool(_DRAW_RE.search(text))


def is_ramp(card: dict) -> bool:
    """Return True if the card provides mana ramp."""
    text = _oracle_text(card)
    return bool(_RAMP_RE.search(text))


def is_life_gain(card: dict) -> bool:
    """Return True if the card provides life gain."""
    text = _oracle_text(card)
    return bool(_LIFEGAIN_RE.search(text))


def is_token_generator(card: dict) -> bool:
    """Return True if the card creates tokens."""
    text = _oracle_text(card)
    return bool(_TOKENS_RE.search(text))


def is_tutor(card: dict) -> bool:
    """Return True if the card is a tutor (searches library)."""
    text = _oracle_text(card)
    return bool(_TUTOR_RE.search(text))


def estimate_card_quality(card: dict) -> float:
    """
    Return a 0-10 quality estimate for a card based solely on its oracle text.

    This is a simplified version of Forge's ``ComputerUtilCard.evaluateCard()``.
    """
    text = _oracle_text(card)
    score = 3.0  # baseline

    if is_removal_spell(card):
        score += 2.5
    if is_counterspell(card):
        score += 2.0
    if is_board_wipe(card):
        score += 3.0
    if is_draw_spell(card):
        score += 1.5
    if is_ramp(card):
        score += 1.5
    if is_tutor(card):
        score += 2.0
    if is_token_generator(card):
        score += 1.0
    if has_keyword(card, "flying"):
        score += 0.5
    if has_keyword(card, "haste"):
        score += 0.5
    if has_keyword(card, "trample"):
        score += 0.5
    if has_keyword(card, "deathtouch"):
        score += 0.5
    if has_keyword(card, "lifelink"):
        score += 0.5
    if has_keyword(card, "hexproof"):
        score += 0.5

    return min(10.0, max(0.0, score))
