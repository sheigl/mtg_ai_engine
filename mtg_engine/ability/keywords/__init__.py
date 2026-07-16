"""
Keyword ability system.

Phase 400: Keyword gap closure. Provides structured keyword ability classes
that mirror Forge's keyword directory (50+ files).
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
from mtg_engine.ability.keywords.storm import Storm
from mtg_engine.ability.keywords.cascade import Cascade
from mtg_engine.ability.keywords.convoke import Convoke
from mtg_engine.ability.keywords.delve import Delve
from mtg_engine.ability.keywords.scry import Scry
from mtg_engine.ability.keywords.ward import Ward
from mtg_engine.ability.keywords.crew import Crew
from mtg_engine.ability.keywords.dredge import Dredge
from mtg_engine.ability.keywords.kicker import Kicker
from mtg_engine.ability.keywords.flashback import Flashback
from mtg_engine.ability.keywords.equip import Equip
from mtg_engine.ability.keywords.ninjutsu import Ninjutsu
from mtg_engine.ability.keywords.dash import Dash
from mtg_engine.ability.keywords.madness import Madness
from mtg_engine.ability.keywords.escape import Escape

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
    "Storm",
    "Cascade",
    "Convoke",
    "Delve",
    "Scry",
    "Ward",
    "Crew",
    "Dredge",
    "Kicker",
    "Flashback",
    "Equip",
    "Ninjutsu",
    "Dash",
    "Madness",
    "Escape",
]
