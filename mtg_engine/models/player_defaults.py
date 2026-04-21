"""Pydantic models for player default settings. Feature 028.

Defines the settings payloads for each player type, the PlayerTypeDefaults
document representation, and helper functions for validation and merging
request values with saved defaults.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Player type enum ──────────────────────────────────────────────────────────

VALID_PLAYER_TYPES = {"human", "ai", "heuristic"}


class PlayerType(str, Enum):
    """Valid player type identifiers for default settings."""
    HUMAN = "human"
    AI = "ai"
    HEURISTIC = "heuristic"


# ── Per-type settings models ─────────────────────────────────────────────────

class HumanPlayerSettings(BaseModel):
    """Default settings for a human (player-controlled) seat."""
    auto_tap: bool = True
    confirm_combat: bool = False


class AiPlayerSettings(BaseModel):
    """Default settings for an LLM-based AI player."""
    base_url: str = ""
    model: str = ""
    enable_thinking: bool | None = None


class HeuristicPlayerSettings(BaseModel):
    """Default settings for a heuristic (rule-based) AI player."""
    personality: dict[str, Any] = Field(default_factory=lambda: {
        "name": "default",
        "chance_to_attack_into_trade": 0.40,
        "attack_into_trade_when_tapped_out": False,
        "chance_to_atktrade_when_opp_has_mana": 0.30,
        "try_to_avoid_attacking_into_certain_block": True,
        "enable_random_favorable_trades_on_block": True,
        "randomly_trade_even_when_have_less_creatures": False,
        "chance_decrease_to_trade_vs_embalm": 0.50,
        "chance_to_hold_combat_tricks": 0.30,
        "chance_to_trade_to_save_planeswalker": 0.70,
        "chance_to_counter_cmc_1": 0.50,
        "chance_to_counter_cmc_2": 0.75,
        "chance_to_counter_cmc_3_plus": 1.00,
        "always_counter_other_counterspells": True,
        "always_counter_damage_spells": False,
        "always_counter_removal_spells": False,
        "always_counter_pump_spells": False,
        "always_counter_auras": False,
        "actively_destroy_artifacts_and_enchantments": True,
        "actively_destroy_immediately_unblockable": True,
        "token_generation_chance": 0.80,
        "hold_land_drop_for_main2_if_unused": False,
        "re_equip_on_creature_death": True,
        "phyrexian_life_threshold": 5,
    })


# ── Settings type mapping ────────────────────────────────────────────────────

SETTINGS_TYPE_MAP: dict[str, type[BaseModel]] = {
    "human": HumanPlayerSettings,
    "ai": AiPlayerSettings,
    "heuristic": HeuristicPlayerSettings,
}


# ── Response models ──────────────────────────────────────────────────────────

class PlayerTypeDefaultsResponse(BaseModel):
    """Response document for a player type defaults entry."""
    player_type: str
    settings: dict[str, Any]
    updated_at: datetime


class SaveDefaultsRequest(BaseModel):
    """Request body for PUT /player-defaults/{player_type}."""
    settings: dict[str, Any]


# ── Helper functions ─────────────────────────────────────────────────────────

def validate_settings_for_type(player_type: str, settings: dict[str, Any]) -> dict[str, Any]:
    """Validate settings dict against the Pydantic schema for the given player type.

    Returns the validated (and possibly normalized) settings dict.
    Raises ValueError if the settings do not conform.
    """
    settings_cls = SETTINGS_TYPE_MAP.get(player_type)
    if settings_cls is None:
        raise ValueError(f"player_type must be one of {VALID_PLAYER_TYPES}")
    try:
        validated = settings_cls.model_validate(settings)
        return validated.model_dump()
    except Exception as e:
        raise ValueError(f"Invalid settings for player type '{player_type}': {e}")


def merge_with_defaults(
    player_type: str,
    request_values: dict[str, Any] | None,
    defaults: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge request values with saved defaults for a player type.

    Request values take precedence over defaults. Only keys present in the
    defaults schema are considered (unknown keys from request are ignored).

    Args:
        player_type: The player type key (human, ai, heuristic).
        request_values: Explicit values from the game creation request.
        defaults: Saved defaults from MongoDB (may be None).

    Returns:
        Merged settings dict with request values overriding defaults.
    """
    if defaults is None:
        if request_values is None:
            return {}
        settings_cls = SETTINGS_TYPE_MAP.get(player_type)
        if settings_cls is None:
            return {}
        return {k: v for k, v in request_values.items() if k in settings_cls.model_fields}

    if request_values is None:
        return defaults

    # Start with defaults, overlay non-empty request values
    result = dict(defaults)
    settings_cls = SETTINGS_TYPE_MAP.get(player_type)
    if settings_cls is None:
        return result

    for key, value in request_values.items():
        if key not in settings_cls.model_fields:
            continue
        # Request value takes precedence if it's non-empty / non-None
        if value is not None and value != "" and value != []:
            result[key] = value
        elif key in result and (result.get(key) is None or result.get(key) == "" or result.get(key) == []):
            result[key] = value

    return result
