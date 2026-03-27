"""Data structures for the AI CLI client."""
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# AIMemory — per-game, per-player cross-turn tracking (US13, T002)
# ---------------------------------------------------------------------------

@dataclass
class AIMemory:
    """
    Cross-turn game-state tracking for a single AI player in a single game.
    One instance is created per AI player at game start and passed into every
    HeuristicPlayer decision call.  Per-turn fields are cleared by new_turn().
    """
    # Cards learned about opponent through effects (keyed by player name)
    revealed_cards: dict[str, list] = field(default_factory=dict)
    # Permanent IDs returned to hand this turn (cleared at turn start)
    bounced_this_turn: set[str] = field(default_factory=set)
    # Equipment permanent IDs attached this turn (cleared at turn start)
    attached_this_turn: set[str] = field(default_factory=set)
    # Permanent IDs animated into creatures this turn (cleared at turn start)
    animated_this_turn: set[str] = field(default_factory=set)
    # Card ID of Fog spell being held for defensive use (cleared on use)
    chosen_fog_effect: str | None = None
    # Attacker IDs designated as trick bait this combat
    trick_attackers: set[str] = field(default_factory=set)
    # Permanent IDs of goaded or must-attack creatures (cleared when effect ends)
    mandatory_attackers: set[str] = field(default_factory=set)
    # Land/mana-source IDs held back from main phase 1 activations
    held_mana_for_main2: set[str] = field(default_factory=set)
    # Mana-source IDs reserved for combat-step instant-speed responses
    held_mana_for_declblk: set[str] = field(default_factory=set)

    def new_turn(self) -> None:
        """Clear all per-turn fields. Called at the start of each AI turn."""
        self.bounced_this_turn.clear()
        self.attached_this_turn.clear()
        self.animated_this_turn.clear()
        self.chosen_fog_effect = None
        self.trick_attackers.clear()
        self.held_mana_for_main2.clear()
        self.held_mana_for_declblk.clear()
        # revealed_cards and mandatory_attackers persist across turns

    # ── Convenience methods (US13, T044) ────────────────────────────────
    def add_revealed_card(self, player_name: str, card: dict) -> None:
        """Record a card revealed from the opponent's hand."""
        self.revealed_cards.setdefault(player_name, []).append(card)

    def get_revealed_cards(self, player_name: str) -> list[dict]:
        """Return all known cards in the specified player's hand."""
        return self.revealed_cards.get(player_name, [])

    def add_bounced(self, perm_id: str) -> None:
        """Record that a permanent was bounced to hand this turn."""
        self.bounced_this_turn.add(perm_id)

    def add_mandatory_attacker(self, perm_id: str) -> None:
        """Record that a creature must attack (e.g., goaded)."""
        self.mandatory_attackers.add(perm_id)

    def clear_mandatory_attacker(self, perm_id: str) -> None:
        """Remove a creature from the mandatory-attacker set."""
        self.mandatory_attackers.discard(perm_id)


# ---------------------------------------------------------------------------
# AiPersonalityProfile — named behavioral configuration (US17, T003)
# ---------------------------------------------------------------------------

@dataclass
class AiPersonalityProfile:
    """
    Named configuration controlling all behavioral probability and boolean
    properties of the AI.  Bound to a player instance; not global.
    Two built-in profiles are provided as class constants: DEFAULT and AGGRO.
    """
    name: str = "default"

    # ── Combat aggression ────────────────────────────────────────────────
    chance_to_attack_into_trade: float = 0.40
    attack_into_trade_when_tapped_out: bool = False
    chance_to_atktrade_when_opp_has_mana: float = 0.30
    try_to_avoid_attacking_into_certain_block: bool = True
    enable_random_favorable_trades_on_block: bool = True
    randomly_trade_even_when_have_less_creatures: bool = False
    chance_decrease_to_trade_vs_embalm: float = 0.50

    # ── Combat tricks ────────────────────────────────────────────────────
    chance_to_hold_combat_tricks: float = 0.30

    # ── Planeswalker protection ──────────────────────────────────────────
    chance_to_trade_to_save_planeswalker: float = 0.70

    # ── Counterspell probabilities (by CMC tier) ─────────────────────────
    chance_to_counter_cmc_1: float = 0.50
    chance_to_counter_cmc_2: float = 0.75
    chance_to_counter_cmc_3_plus: float = 1.00

    # ── Counterspell boolean flags ────────────────────────────────────────
    always_counter_other_counterspells: bool = True
    always_counter_damage_spells: bool = False
    always_counter_removal_spells: bool = False
    always_counter_pump_spells: bool = False
    always_counter_auras: bool = False

    # ── Removal behavior ──────────────────────────────────────────────────
    actively_destroy_artifacts_and_enchantments: bool = True
    actively_destroy_immediately_unblockable: bool = True

    # ── Token generation ──────────────────────────────────────────────────
    token_generation_chance: float = 0.80

    # ── Land / mana management ────────────────────────────────────────────
    hold_land_drop_for_main2_if_unused: bool = False
    re_equip_on_creature_death: bool = True

    # ── Phyrexian mana ────────────────────────────────────────────────────
    phyrexian_life_threshold: int = 5


    @classmethod
    def from_dict(cls, d: dict) -> "AiPersonalityProfile":
        """
        Factory method for runtime profile customization from a plain dict.
        Unrecognized keys are silently ignored. (US17 T106)
        """
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)


# Class-level profile constants (defined after the class body)
AiPersonalityProfile.DEFAULT = AiPersonalityProfile(name="default")  # type: ignore[attr-defined]
AiPersonalityProfile.AGGRO = AiPersonalityProfile(  # type: ignore[attr-defined]
    name="aggro",
    chance_to_attack_into_trade=0.80,
    attack_into_trade_when_tapped_out=True,
    chance_to_counter_cmc_1=0.00,
    chance_to_counter_cmc_2=0.25,
    token_generation_chance=0.90,
)


# ---------------------------------------------------------------------------
# BlockClassification — safe/trade/chump labeling for blockers (US36, T004)
# ---------------------------------------------------------------------------

class BlockClassification(Enum):
    """Classification of a proposed block outcome."""
    SAFE = "safe"    # Blocker kills attacker AND blocker survives
    TRADE = "trade"  # Both die (mutual lethal)
    CHUMP = "chump"  # Only blocker dies (attacker survives)


# ---------------------------------------------------------------------------
# Existing models
# ---------------------------------------------------------------------------

@dataclass
class PlayerConfig:
    """One AI player, parsed from a --player CLI flag."""
    name: str
    base_url: str = ""
    model: str = ""
    player_type: str = "llm"  # "llm" | "heuristic"
    personality: "AiPersonalityProfile" = field(
        default_factory=lambda: AiPersonalityProfile.DEFAULT  # type: ignore[attr-defined]
    )


@dataclass
class GameConfig:
    """Top-level game configuration assembled from CLI arguments."""
    players: list[PlayerConfig]
    engine_url: str = "http://localhost:8000"
    deck1: list[str] = field(default_factory=list)
    deck2: list[str] = field(default_factory=list)
    verbose: bool = False
    max_turns: int = 200
    format: str = "standard"
    commander1: str | None = None
    commander2: str | None = None


@dataclass
class TurnRecord:
    """Captures a single AI decision for console logging."""
    turn_number: int
    player_name: str
    phase: str
    step: str
    legal_actions: list[dict]
    chosen_index: int
    reasoning: str
    action_description: str
    fallback_used: bool = False


@dataclass
class GameSummary:
    """Result produced at game end."""
    game_id: str
    winner: str | None
    total_turns: int
    total_decisions: int
    termination_reason: str
    commander_damage: dict = field(default_factory=dict)
