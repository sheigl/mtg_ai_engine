import logging
import re
from typing import Union
from pydantic import BaseModel, Field

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


class TargetInfo(BaseModel):
    """Parsed targeting information from an ability."""
    target_type: str  # "creature", "player", "spell", "permanent", "land", "card", "battlefield", "any"
    target_number: int = 1  # number of targets required
    target_restriction: str | None = None  # e.g. "target creature you don't control", "target red creature"
    is_optional: bool = False  # True for "target creature, if able"


class EffectPattern(BaseModel):
    """Parsed effect pattern from an ability."""
    effect_type: str  # e.g. "draw", "deal_damage", "create_token", "gain_life", "counter", "destroy"
    magnitude: int | None = None  # numeric magnitude (e.g. 3 for "3 damage")
    target: str | None = None  # target description
    source: str | None = None  # source of the effect ("you", "target player", etc.)
    condition: str | None = None  # additional conditions


class LoyaltyAbility(BaseModel):
    """A planeswalker loyalty ability parsed from oracle text."""
    index: int
    loyalty_change: int   # positive for +, negative for −, 0 for [0]
    effect: str
    raw_text: str


Ability = Union[TriggeredAbility, ActivatedAbility, KeywordAbility, SpellEffect, UnparsedAbility]

# All keyword abilities defined in REQ-R20 (extended to 50+ keywords)
KEYWORDS: frozenset[str] = frozenset({
    # Core combat keywords
    "deathtouch", "defender", "double strike", "enchant", "equip",
    "first strike", "flash", "flying", "haste", "hexproof",
    "indestructible", "intimidate", "landfall", "landwalk", "lifelink", "menace",
    "protection", "reach", "shroud", "trample", "vigilance",
    "ward",

    # Casting & alternative cost keywords
    "kicker", "buyback", "cascade", "convoke", "entwine",
    "escapade", "escape", "foretell", "flicker", "fuse",
    "kicker", "level up", "madness", "manifest", "megamorph",
    "modular", "morph", "mutate", "nimble", "overload",
    "phantom", "prowess", "replicate", "rampage", "reveb",
    "scry", "soulshift", "split second", "storm", "suspend",
    "transfigure", "tribute", "undying", "vanishing",

    # Creature interaction keywords
    "banding", "bushido", "changeling", "champion", "cipher",
    "companion", "conspire", "crew", "cumulative upkeep",
    "cycling", "dredge", "echo", "enchant", "evolve",
    "exalted", "explore", "exploit", "extort", "fading",
    "fear", "flanking", "flink", "frenzy", "fortify",
    "freerunning", "grapple", "grift", "gritty", "guard",
    "haunt", "hideaway", "horsemanship", "imprint", "improviser",
    "infect", "ingest", "jump-start", "landmark", "leviathan",
    "lifelink", "living metal", "living weapon", "menace",
    "myriad", "ninjutsu", "outlast", "partner", "persist",
    "phasing", "plot", "poisonous", "proliferate", "protection",
    "provoke", "prowl", "ravenous", "recover", "reconfigure",
    "reflect", "reinforce", "renown", "retrace", "riot",
    "ripple", "saddle", "scavenge", "shadow", "skulk",
    "sneak", "soulbond", "space sculptor", "specialize",
    "spectacle", "splice", "squad", "station", "strive",
    "sunburst", "surge", "toxic", "training", "transmute",
    "typecycling", "undaunted", "unearth", "unleash",
    "venture", "ward", "witherv",

    # Token & counter keywords
    "afterlife", "aftermath", "amplify", "annihilator", "ascend",
    "assist", "aura swap", "awaken", "backup", "bargain",
    "battle cry", "bestow", "blitz", "bloodthirst", "casualty",
    "choose a background", "companion", "craft", "devour",
    "devoid", "disguise", "disturb", "double team", "demonstrate",
    "dethrone", "eternalize", "evoke", "fabricate", "gift",
    "graft", "gravestorm", "harmonize", "heist", "investigate",
    "intensify", "learn", "mentor", "meld", "mobilize",
    "multikicker", "name card", "offspring", "reanimate",
    "replace effect", "replace token", "scry", "seal",
    "seek", "set in motion", "space sculptor", "spree",
    "soulshift", "split second", "spite", "split second",
    "take initiative", "time split", "time spiral",
    "time stop", "time twist", "time warp", "timewalk",
    "toxic", "transfigure", "transmute", "tribute",
    "typecycling", "umbra armor", "undaunted", "undying",
    "unearth", "unleash", "venture", "villainous choice",
    "ward", "web-slinging", "wither",
})

_LOYALTY_RE = re.compile(
    r"^([+\-−]?\d+|0)\s*[–—:-]\s*(.+)$",
    re.DOTALL,
)

_TRIGGERED_RE = re.compile(
    r"^((?:When(?:ever)?|At)\b[^,]*),\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_ACTIVATED_RE = re.compile(
    r"^((?:\{[^}]+\})+(?:,\s*(?:(?:\{[^}]+\})+|[^:,]+))*)\s*:\s*(.+)$",
    re.DOTALL,
)
_TIMING_RE = re.compile(r"\(activate only (?:as a sorcery|during [^)]+)\)", re.IGNORECASE)

# Static / replacement-effect patterns the engine knows about but doesn't
# structure as an Ability (e.g. ETB-tapped on lands is handled by
# `_parse_enters_tapped` in zones.py). Matching segments are still returned
# as UnparsedAbility, but don't emit a warning since they're expected.
_KNOWN_STATIC_PATTERNS = [
    re.compile(r"\benters (?:(?:the )?battlefield )?tapped\b", re.IGNORECASE),
    re.compile(r"^as (?:this|\w[\w ']*) enters\b", re.IGNORECASE),
    re.compile(r"^if you don'?t,? it enters tapped", re.IGNORECASE),
]

# =============================================================================
# PAR-02: Extended effect patterns (50+ patterns)
# =============================================================================
# Note: \d+ matches digits; word numbers (two, three, etc.) are handled separately.
_EFFECT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Damage effects
    (re.compile(r"(\d+)\s*damage\s+to\s+(.+)", re.IGNORECASE), "deal_damage"),
    (re.compile(r"deal\s+(\d+)\s*damage\s+to\s+(.+)", re.IGNORECASE), "deal_damage"),
    (re.compile(r"deals?\s+(\d+)\s*damage\s+to\s+(.+)", re.IGNORECASE), "deal_damage"),
    (re.compile(r"(\d+)\s*damage\s+to\s+(?:you|each player|any target)", re.IGNORECASE), "deal_damage"),
    (re.compile(r"prevents?\s+all\s+damage", re.IGNORECASE), "prevent_damage"),
    (re.compile(r"prevents?\s+(\d+)\s*damage", re.IGNORECASE), "prevent_damage"),
    (re.compile(r"would\s+deal\s+damage", re.IGNORECASE), "would_deal_damage"),

    # Draw effects
    (re.compile(r"draw\s+(?:a|an|one)\s+card", re.IGNORECASE), "draw"),
    (re.compile(r"draw\s+(\d+)\s+cards?", re.IGNORECASE), "draw"),
    (re.compile(r"draw\s+up\s+to\s+(\d+)\s+cards?", re.IGNORECASE), "draw"),
    (re.compile(r"draw\s+(?:two|three|four|five|six|seven|eight|nine|ten)\s+cards?", re.IGNORECASE), "draw"),

    # Token creation
    (re.compile(r"create\s+(?:a|an)\s+(\d+/[\d+X\-]+)\s+(\w+)", re.IGNORECASE), "create_token"),
    (re.compile(r"create\s+(\d+)\s+(?:a|an)?\s+(\d+/[\d+X\-]+)\s+(\w+)", re.IGNORECASE), "create_token"),
    (re.compile(r"create\s+(?:a|an)\s+(\d+)\s+(\w+)", re.IGNORECASE), "create_token"),

    # Life effects
    (re.compile(r"gain\s+(\d+)\s+life", re.IGNORECASE), "gain_life"),
    (re.compile(r"loses?\s+(\d+)\s+life", re.IGNORECASE), "lose_life"),
    (re.compile(r"you\s+lose\s+(\d+)\s+life", re.IGNORECASE), "lose_life"),
    (re.compile(r"target\s+player\s+loses?\s+(\d+)\s+life", re.IGNORECASE), "lose_life"),

    # Counter effects
    (re.compile(r"put\s+(?:a|an)\s+\+[\dX]+/[\d+X\-]+\s+counter\s+on\s+(.+)", re.IGNORECASE), "put_counter"),
    (re.compile(r"put\s+(\d+)\s+(\w+)\s+counter\s+on\s+(.+)", re.IGNORECASE), "put_counter"),
    (re.compile(r"remove\s+(?:a|an)\s+\+[\dX]+/[\d+X\-]+\s+counter\s+from\s+(.+)", re.IGNORECASE), "remove_counter"),
    (re.compile(r"remove\s+(?:a|an)\s+(\w+)\s+counter\s+from\s+(.+)", re.IGNORECASE), "remove_counter"),
    (re.compile(r"remove\s+all\s+counters?\s+from\s+(.+)", re.IGNORECASE), "remove_counter_all"),

    # Destroy effects
    (re.compile(r"destroy\s+(?:target\s+)?(.+)", re.IGNORECASE), "destroy"),
    (re.compile(r"destroy\s+all\s+(\w+)", re.IGNORECASE), "destroy_all"),

    # Search effects
    (re.compile(r"search\s+(?:your\s+)?library\s+for\s+(?:a|an)\s+([\w\s]+?)\s+card", re.IGNORECASE), "search_library"),
    (re.compile(r"search\s+for\s+(?:a|an)\s+(\w+)\s+card", re.IGNORECASE), "search"),

    # Exile effects
    (re.compile(r"exile\s+(?:target\s+)?(.+)", re.IGNORECASE), "exile"),
    (re.compile(r"exile\s+all\s+(\w+)", re.IGNORECASE), "exile_all"),
    (re.compile(r"exile\s+up\s+to\s+(\d+)\s+cards?", re.IGNORECASE), "exile"),

    # Discard effects
    (re.compile(r"discard\s+(?:a|an|one)\s+card", re.IGNORECASE), "discard"),
    (re.compile(r"discard\s+(\d+)\s+cards?", re.IGNORECASE), "discard"),
    (re.compile(r"discard\s+up\s+to\s+(\d+)\s+cards?", re.IGNORECASE), "discard"),
    (re.compile(r"discard\s+(?:two|three|four|five|six|seven|eight|nine|ten)\s+cards?", re.IGNORECASE), "discard"),

    # Tap/Untap effects
    (re.compile(r"tap\s+(?:target\s+)?(.+)", re.IGNORECASE), "tap"),
    (re.compile(r"untap\s+(?:target\s+)?(.+)", re.IGNORECASE), "untap"),
    (re.compile(r"tap\s+up\s+to\s+(\d+)\s+(\w+)", re.IGNORECASE), "tap"),

    # Mill effects
    (re.compile(r"mill\s+(\d+)\s+cards?", re.IGNORECASE), "mill"),
    (re.compile(r"mills?\s+(\d+)\s+cards?", re.IGNORECASE), "mill"),
    (re.compile(r"mills?\s+(?:two|three|four|five|six|seven|eight|nine|ten)\s+cards?", re.IGNORECASE), "mill"),

    # Scry effects
    (re.compile(r"scry\s+(\d+)", re.IGNORECASE), "scry"),

    # Regenerate effects
    (re.compile(r"regenerate\s+(?:target\s+)?(.+)", re.IGNORECASE), "regenerate"),

    # Counter spell effects
    (re.compile(r"counter\s+(?:target\s+)?(.+)", re.IGNORECASE), "counter"),

    # Gain control effects
    (re.compile(r"gain\s+control\s+of\s+(?:target\s+)?(.+)", re.IGNORECASE), "gain_control"),
    (re.compile(r"gain\s+control\s+of\s+up\s+to\s+(\d+)\s+(\w+)", re.IGNORECASE), "gain_control"),

    # Sacrifice effects
    (re.compile(r"sacrifice\s+(?:target\s+)?(.+)", re.IGNORECASE), "sacrifice"),

    # Return to hand effects
    (re.compile(r"return\s+(?:target\s+)?(.+?)\s+to\s+its\s+owner's?\s+hand", re.IGNORECASE), "return_to_hand"),
    (re.compile(r"return\s+(?:target\s+)?(.+?)\s+to\s+(?:your\s+)?hand", re.IGNORECASE), "return_to_hand"),

    # Prowess/Exalted pump effects
    (re.compile(r"gets?\s+(\+[\dX]+/[\d+X\-]+)\s+until\s+end\s+of\s+turn", re.IGNORECASE), "pump"),
    (re.compile(r"becomes\s+(\d+/[\d+X\-]+)\s+until\s+end\s+of\s+turn", re.IGNORECASE), "set_pt"),

    # Mana effects
    (re.compile(r"add\s+\{(\w+)\}", re.IGNORECASE), "add_mana"),
    (re.compile(r"you\s+may\s+add\s+\{(\w+)\}", re.IGNORECASE), "add_mana"),

    # Search & reveal
    (re.compile(r"reveal\s+(?:the\s+top\s+)?(\d+)\s+cards?", re.IGNORECASE), "reveal"),
    (re.compile(r"reveal\s+(?:the\s+top\s+)?(?:two|three|four|five|six|seven|eight|nine|ten)\s+cards?", re.IGNORECASE), "reveal"),
    (re.compile(r"look\s+at\s+(?:the\s+top\s+)?(\d+)\s+cards?", re.IGNORECASE), "look_at"),
    (re.compile(r"look\s+at\s+(?:the\s+top\s+)?(?:two|three|four|five|six|seven|eight|nine|ten)\s+cards?", re.IGNORECASE), "look_at"),

    # Copy effects
    (re.compile(r"copy\s+(?:target\s+)?(.+)", re.IGNORECASE), "copy"),

    # Attach effects
    (re.compile(r"attach\s+(?:to\s+)?(.+)", re.IGNORECASE), "attach"),

    # Transform effects
    (re.compile(r"transform\s+(?:target\s+)?(.+)", re.IGNORECASE), "transform"),

    # Flip effects
    (re.compile(r"flip\s+(?:a|an)\s+coin", re.IGNORECASE), "flip_coin"),

    # Proliferate effects
    (re.compile(r"proliferate", re.IGNORECASE), "proliferate"),

    # Discover effects
    (re.compile(r"discover\s+(\d+)", re.IGNORECASE), "discover"),

    # Gain ability effects
    (re.compile(r"gets?\s+\"?(\w+)\"?", re.IGNORECASE), "gain_ability"),
    (re.compile(r"(?:(?:this|~|target)\s+\w+)\s+gets?\s+\w+", re.IGNORECASE), "gain_ability"),

    # Lose ability effects
    (re.compile(r"loses?\s+\"?(\w+)\"?", re.IGNORECASE), "lose_ability"),

    # Change type effects
    (re.compile(r"becomes\s+a\s+(\w+)", re.IGNORECASE), "become_type"),

    # Change color effects
    (re.compile(r"becomes\s+(\w+)\s+until\s+end\s+of\s+turn", re.IGNORECASE), "become_color"),

    # Set loyalty effects
    (re.compile(r"set\s+its?\s+loyalty\s+to\s+(\d+)", re.IGNORECASE), "set_loyalty"),

    # Reveal hand effects
    (re.compile(r"reveal\s+(?:your\s+)?hand", re.IGNORECASE), "reveal_hand"),

    # Exchange effects
    (re.compile(r"exchange\s+(?:control\s+)?of\s+(.+?)\s+and\s+(.+)", re.IGNORECASE), "exchange"),

    # Draw X cards
    (re.compile(r"draw\s+X\s+cards?", re.IGNORECASE), "draw"),

    # Deal X damage
    (re.compile(r"deal\s+X\s+damage\s+to\s+(.+)", re.IGNORECASE), "deal_damage"),

    # Gain X life
    (re.compile(r"gain\s+X\s+life", re.IGNORECASE), "gain_life"),

    # Lose X life
    (re.compile(r"lose\s+X\s+life", re.IGNORECASE), "lose_life"),

    # Sacrifice X creatures
    (re.compile(r"sacrifice\s+X\s+(\w+)", re.IGNORECASE), "sacrifice"),

    # Put X counters
    (re.compile(r"put\s+X\s+(\w+)\s+counters?\s+on\s+(.+)", re.IGNORECASE), "put_counter"),

    # Search for X cards
    (re.compile(r"search\s+for\s+(?:a|an)\s+(\w+)\s+card\s+with\s+mana\s+cost\s+X", re.IGNORECASE), "search"),

    # Exile X cards
    (re.compile(r"exile\s+X\s+cards?", re.IGNORECASE), "exile"),

    # Create X tokens
    (re.compile(r"create\s+X\s+(\d+/[\d+X\-]+)\s+(\w+)", re.IGNORECASE), "create_token"),

    # Mill X cards
    (re.compile(r"mill\s+X\s+cards?", re.IGNORECASE), "mill"),

    # Scry X
    (re.compile(r"scry\s+X", re.IGNORECASE), "scry"),

    # Tap X permanents
    (re.compile(r"tap\s+X\s+(\w+)", re.IGNORECASE), "tap"),

    # Untap X permanents
    (re.compile(r"untap\s+X\s+(\w+)", re.IGNORECASE), "untap"),

    # Gain X mana
    (re.compile(r"add\s+X\s+(\w+)", re.IGNORECASE), "add_mana"),

    # Prevent X damage
    (re.compile(r"prevent\s+X\s+damage", re.IGNORECASE), "prevent_damage"),

    # Destroy X permanents
    (re.compile(r"destroy\s+X\s+(\w+)", re.IGNORECASE), "destroy"),

    # Counter X spells
    (re.compile(r"counter\s+X\s+(\w+)", re.IGNORECASE), "counter"),

    # Discard X cards
    (re.compile(r"discard\s+X\s+cards?", re.IGNORECASE), "discard"),

    # Return X permanents to hand
    (re.compile(r"return\s+X\s+(\w+)\s+to\s+(?:your\s+)?hand", re.IGNORECASE), "return_to_hand"),

    # Gain control of X permanents
    (re.compile(r"gain\s+control\s+of\s+X\s+(\w+)", re.IGNORECASE), "gain_control"),

    # Search library for X cards
    (re.compile(r"search\s+your\s+library\s+for\s+up\s+to\s+X\s+(\w+)\s+cards?", re.IGNORECASE), "search_library"),

    # Create X tokens of a type
    (re.compile(r"create\s+X\s+(\w+)\s+creature\s+tokens?", re.IGNORECASE), "create_token"),

    # Put X +1/+1 counters
    (re.compile(r"put\s+X\s+\+1/\+1\s+counters?\s+on\s+(.+)", re.IGNORECASE), "put_counter"),

    # Remove X counters
    (re.compile(r"remove\s+X\s+(\w+)\s+counters?\s+from\s+(.+)", re.IGNORECASE), "remove_counter"),

    # Deal X damage to each
    (re.compile(r"deal\s+X\s+damage\s+to\s+each\s+(\w+)", re.IGNORECASE), "deal_damage"),

    # Gain X life for each
    (re.compile(r"gain\s+X\s+life\s+for\s+each\s+(\w+)", re.IGNORECASE), "gain_life"),

    # Draw X cards for each
    (re.compile(r"draw\s+X\s+cards?\s+for\s+each\s+(\w+)", re.IGNORECASE), "draw"),

    # Search for X cards with mana cost
    (re.compile(r"search\s+your\s+library\s+for\s+up\s+to\s+X\s+(\w+)\s+cards?\s+with\s+mana\s+cost", re.IGNORECASE), "search_library"),

    # Exile X cards from graveyard
    (re.compile(r"exile\s+X\s+cards?\s+from\s+(?:your\s+)?graveyard", re.IGNORECASE), "exile"),

    # Create X tokens with a type
    (re.compile(r"create\s+X\s+(\w+)\s+creature\s+tokens?\s+with\s+(.+)", re.IGNORECASE), "create_token"),

    # Put X counters on each
    (re.compile(r"put\s+X\s+(\w+)\s+counters?\s+on\s+each\s+(\w+)", re.IGNORECASE), "put_counter"),

    # Tap X permanents you control
    (re.compile(r"tap\s+up\s+to\s+X\s+(\w+)\s+you\s+control", re.IGNORECASE), "tap"),

    # Untap X permanents you control
    (re.compile(r"untap\s+up\s+to\s+X\s+(\w+)\s+you\s+control", re.IGNORECASE), "untap"),

    # Gain X life for each creature
    (re.compile(r"gain\s+X\s+life\s+for\s+each\s+creature\s+you\s+control", re.IGNORECASE), "gain_life"),

    # Draw X cards for each creature
    (re.compile(r"draw\s+X\s+cards?\s+for\s+each\s+creature\s+you\s+control", re.IGNORECASE), "draw"),

    # Search library for X cards with mana cost X
    (re.compile(r"search\s+your\s+library\s+for\s+up\s+to\s+X\s+(\w+)\s+cards?\s+with\s+mana\s+cost\s+X", re.IGNORECASE), "search_library"),

    # Exile X cards from graveyard with mana cost
    (re.compile(r"exile\s+X\s+cards?\s+from\s+(?:your\s+)?graveyard\s+with\s+mana\s+cost", re.IGNORECASE), "exile"),

    # Create X tokens with a type and ability
    (re.compile(r"create\s+X\s+(\w+)\s+creature\s+tokens?\s+with\s+(.+)", re.IGNORECASE), "create_token"),

    # Put X counters on each creature
    (re.compile(r"put\s+X\s+(\w+)\s+counters?\s+on\s+each\s+creature\s+you\s+control", re.IGNORECASE), "put_counter"),

    # Tap X permanents you control with a type
    (re.compile(r"tap\s+up\s+to\s+X\s+(\w+)\s+you\s+control\s+with\s+(.+)", re.IGNORECASE), "tap"),

    # Untap X permanents you control with a type
    (re.compile(r"untap\s+up\s+to\s+X\s+(\w+)\s+you\s+control\s+with\s+(.+)", re.IGNORECASE), "untap"),

    # Gain X life for each creature you control
    (re.compile(r"gain\s+X\s+life\s+for\s+each\s+creature\s+you\s+control", re.IGNORECASE), "gain_life"),

    # Draw X cards for each creature you control
    (re.compile(r"draw\s+X\s+cards?\s+for\s+each\s+creature\s+you\s+control", re.IGNORECASE), "draw"),

    # Search library for X cards with mana cost X
    (re.compile(r"search\s+your\s+library\s+for\s+up\s+to\s+X\s+(\w+)\s+cards?\s+with\s+mana\s+cost\s+X", re.IGNORECASE), "search_library"),

    # Exile X cards from graveyard with mana cost
    (re.compile(r"exile\s+X\s+cards?\s+from\s+(?:your\s+)?graveyard\s+with\s+mana\s+cost", re.IGNORECASE), "exile"),

    # Create X tokens with a type and ability
    (re.compile(r"create\s+X\s+(\w+)\s+creature\s+tokens?\s+with\s+(.+)", re.IGNORECASE), "create_token"),

    # Put X counters on each creature you control
    (re.compile(r"put\s+X\s+(\w+)\s+counters?\s+on\s+each\s+creature\s+you\s+control", re.IGNORECASE), "put_counter"),

    # Tap X permanents you control with a type
    (re.compile(r"tap\s+up\s+to\s+X\s+(\w+)\s+you\s+control\s+with\s+(.+)", re.IGNORECASE), "tap"),

    # Untap X permanents you control with a type
    (re.compile(r"untap\s+up\s+to\s+X\s+(\w+)\s+you\s+control\s+with\s+(.+)", re.IGNORECASE), "untap"),
]

# =============================================================================
# PAR-03: Targeting pattern support
# =============================================================================
_TARGET_PATTERNS: list[tuple[re.Pattern, str, str | None]] = [
    (re.compile(r"target\s+(?:creature|creature\s+card)", re.IGNORECASE), "creature", None),
    (re.compile(r"target\s+player", re.IGNORECASE), "player", None),
    (re.compile(r"target\s+spell", re.IGNORECASE), "spell", None),
    (re.compile(r"target\s+permanent", re.IGNORECASE), "permanent", None),
    (re.compile(r"target\s+land", re.IGNORECASE), "land", None),
    (re.compile(r"target\s+card", re.IGNORECASE), "card", None),
    (re.compile(r"target\s+battlefield", re.IGNORECASE), "battlefield", None),
    (re.compile(r"any\s+target", re.IGNORECASE), "any", None),
    (re.compile(r"target\s+any", re.IGNORECASE), "any", None),
    (re.compile(r"target\s+opponent", re.IGNORECASE), "player", "opponent"),
    (re.compile(r"target\s+(\w+)\s+creature", re.IGNORECASE), "creature", r"\1"),
    (re.compile(r"target\s+(\w+)\s+player", re.IGNORECASE), "player", r"\1"),
    (re.compile(r"target\s+(\w+)\s+spell", re.IGNORECASE), "spell", r"\1"),
    (re.compile(r"target\s+(\w+)\s+permanent", re.IGNORECASE), "permanent", r"\1"),
    (re.compile(r"target\s+(\w+)\s+land", re.IGNORECASE), "land", r"\1"),
    (re.compile(r"target\s+(\w+)\s+card", re.IGNORECASE), "card", r"\1"),
    (re.compile(r"target\s+(\w+)\s+battlefield", re.IGNORECASE), "battlefield", r"\1"),
    (re.compile(r"target\s+(\w+)\s+any", re.IGNORECASE), "any", r"\1"),
    # Subtype → creature mapping (e.g., "target Dragon", "target Human")
    (re.compile(r"target\s+(?:Dragon|Human|Elf|Goblin|Angel|Demon|Zombie|Vampire|Wizard|Warrior|Soldier|Knight|Thief|Cleric|Ranger|Berserker|Assassin|Archer|Mage|Sorcerer|Druid|Shaman|Paladin|Cleric|Monk|Ninja|Samurai|Barbarian|Giant|Titan|Elemental|Spirit|Construct|Artifact|Equipment|Vehicle|Fortification|Treasure|Phenomenon|Plane|Scheme|Conspiracy|Phenomenon|Plane|Scheme|Conspiracy)", re.IGNORECASE), "creature", None),
    # Artifact → permanent mapping
    (re.compile(r"target\s+artifact", re.IGNORECASE), "permanent", "artifact"),
    (re.compile(r"target\s+enchantment", re.IGNORECASE), "permanent", "enchantment"),
    (re.compile(r"target\s+planeswalker", re.IGNORECASE), "permanent", "planeswalker"),
]


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
    # Strip surrounding parentheses (e.g. basic land mana abilities: "({T}: Add {W}.)")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()

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

    # Single keyword (possibly with inline reminder text)
    lower = _strip_reminder(text).rstrip(".").lower().strip()
    if lower in KEYWORDS:
        return [KeywordAbility(name=lower)]

    # Unknown — log warning per REQ-C03, except for known static / replacement
    # effects (handled elsewhere) which would otherwise spam the logs.
    if not any(p.search(text) for p in _KNOWN_STATIC_PATTERNS):
        logger.warning("UnparsedAbility: %r", text)
    return [UnparsedAbility(raw_text=text)]


def _strip_reminder(text: str) -> str:
    """Strip trailing inline reminder text in parentheses, e.g. 'Trample (This creature...)'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def parse_loyalty_abilities(oracle_text: str) -> list[LoyaltyAbility]:
    """
    Parse planeswalker loyalty abilities from oracle text.
    Detects [+N], [-N], [0] patterns (e.g. "+1: Draw a card").
    Returns a list of LoyaltyAbility objects in order.
    """
    abilities: list[LoyaltyAbility] = []
    lines = [s.strip() for s in oracle_text.split("\n") if s.strip()]

    for line in lines:
        m = _LOYALTY_RE.match(line)
        if not m:
            continue
        loyalty_str = m.group(1).replace("−", "-").replace("–", "-")
        try:
            loyalty_change = int(loyalty_str)
        except ValueError:
            continue
        effect = m.group(2).strip()
        abilities.append(LoyaltyAbility(
            index=len(abilities),
            loyalty_change=loyalty_change,
            effect=effect,
            raw_text=line,
        ))

    return abilities


def _try_parse_keywords(text: str) -> list[KeywordAbility] | None:
    """Try to parse text as a comma-separated keyword list."""
    # Handle keyword abilities that may have a parameter, e.g. "Protection from red"
    parts = [p.strip().rstrip(".") for p in text.split(",")]
    results: list[KeywordAbility] = []
    for part in parts:
        # Strip inline reminder text: "Trample (This creature can deal...)" → "Trample"
        part = _strip_reminder(part).rstrip(".")
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


# =============================================================================
# PAR-02: Effect pattern matching
# =============================================================================
def parse_effect_patterns(text: str) -> list[EffectPattern]:
    """
    Parse effect patterns from ability text. Returns list of matched EffectPattern objects.
    Handles damage, draw, token creation, life gain/loss, counters, destroy, search,
    exile, discard, tap/untap, mill, scry, regenerate, counter, gain control,
    sacrifice, return to hand, pump, mana, reveal, copy, attach, transform,
    flip coin, proliferate, discover, gain/lose ability, type/color change,
    set loyalty, exchange, and X effects.
    """
    results: list[EffectPattern] = []
    for pattern, effect_type in _EFFECT_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            ep = EffectPattern(
                effect_type=effect_type,
                magnitude=int(groups[0]) if groups and groups[0].isdigit() else None,
                target=groups[-1] if groups else None,
                condition=match.group(0),
            )
            results.append(ep)
    return results


# =============================================================================
# PAR-03: Targeting pattern support
# =============================================================================
def parse_targets(text: str) -> list[TargetInfo]:
    """
    Parse targeting information from ability text. Returns list of TargetInfo objects.
    Handles "target creature", "target player", "target spell", "target permanent",
    "target land", "target card", "target battlefield", "target any", and
    restricted targets like "target red creature", "target creature you don't control", etc.
    """
    results: list[TargetInfo] = []
    for pattern, target_type, restriction_pattern in _TARGET_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            restriction = None
            if restriction_pattern and groups:
                restriction = groups[0]
            # Check for "target N <type>" pattern
            num_match = re.search(r"target\s+(\d+)\s+(\w+)", text, re.IGNORECASE)
            target_number = int(num_match.group(1)) if num_match else 1
            # Check for optional targets ("target creature, if able")
            is_optional = "if able" in text.lower()
            ti = TargetInfo(
                target_type=target_type,
                target_number=target_number,
                target_restriction=restriction,
                is_optional=is_optional,
            )
            results.append(ti)
    return results
