"""
Keyword ability system.

Phase 400: Keyword gap closure. Provides structured keyword ability classes
that mirror Forge's keyword directory (34+ files).
"""
from mtg_engine.ability.keywords.base import KeywordAbility
from mtg_engine.ability.keywords.etb import EtbKeyword
from mtg_engine.ability.keywords.leave import LeaveBattlefieldKeyword
from mtg_engine.ability.keywords.counter import CounterKeyword, PlusOnePlusOneCounter, MinusOneMinusOneCounter
from mtg_engine.ability.keywords.level import LevelUpKeyword
from mtg_engine.ability.keywords.toxic import ToxicKeyword
from mtg_engine.ability.keywords.meld import MeldKeyword
from mtg_engine.ability.keywords.cycle import TypeCyclingKeyword
from mtg_engine.ability.keywords.flanking import FlankingKeyword

__all__ = [
    "KeywordAbility",
    "EtbKeyword",
    "LeaveBattlefieldKeyword",
    "CounterKeyword",
    "PlusOnePlusOneCounter",
    "MinusOneMinusOneCounter",
    "LevelUpKeyword",
    "ToxicKeyword",
    "MeldKeyword",
    "TypeCyclingKeyword",
    "FlankingKeyword",
]
