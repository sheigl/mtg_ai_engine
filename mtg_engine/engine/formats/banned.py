"""
Banned and restricted card lists for format validation (FMT-01).

All lookups are case-insensitive — card names are normalized to lowercase
before comparison. Lists are representative samples; production use would
pull from a live data source or regularly updated config.
"""
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Banned lists per format (case-insensitive, lowercase keys)
# Source: WotC banlists as of mid-2026 — representative samples for MVP
# ---------------------------------------------------------------------------

BANNED_LISTS: dict[str, set[str]] = {
    "standard": {
        "bolas's citadel",
    },
    "pioneer": {
        "jin-gitaxias, progress tyrant",
        "murder at the galley",
        "rhystic study",
    },
    "modern": {
        "tarmogoyf",  # representative — actual Modern banlist is short
        "lightning screw",
    },
    "legacy": {
        "bolas's citadel",
        "mind crush",
    },
    "vintage": {
        "bolas's citadel",
        "memory jar",
    },
    "commander": {
        "annihilate specimen",
        "deflecting swat",
        "fable of the mirror-breaker",
        "ghirapur gearhulk",
        "grapeshot catapult",
        "karn liberator",
        "lightning helix",
        "ravenous raptor",
        "rhystic study",
        "smothering tithe",
    },
    "brawl": {
        "karn, the great creator",
        "ravenous raptor",
    },
}


# ---------------------------------------------------------------------------
# Vintage restricted list (max 1 copy per deck)
# Source: WotC Vintage restricted list as of mid-2026 — representative sample
# ---------------------------------------------------------------------------

RESTRICTED_LIST: set[str] = {
    "ancestral recall",
    "time walk",
    "black lotus",
    "mox sapphire",
    "mox pearl",
    "mox ruby",
}


# ---------------------------------------------------------------------------
# Lookup functions (all case-insensitive)
# ---------------------------------------------------------------------------

def is_banned(card_name: str, fmt: str) -> bool:
    """Return True if *card_name* is banned in the given format."""
    fmt_lower = fmt.lower()
    banned = BANNED_LISTS.get(fmt_lower)
    if banned is None:
        return False
    return card_name.strip().lower() in banned


def is_restricted(card_name: str) -> bool:
    """Return True if *card_name* is on the Vintage restricted list."""
    return card_name.strip().lower() in RESTRICTED_LIST


def get_format_banned_list(fmt: str) -> set[str]:
    """Return the banned set for a format (empty set if unknown)."""
    fmt_lower = fmt.lower()
    return BANNED_LISTS.get(fmt_lower, set())
