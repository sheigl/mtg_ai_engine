"""
Event system for MTG engine.
EVT-01: Typed event notification bus
EVT-02: Event-to-trigger bridge for trigger detection

CR 603: Triggered abilities fire when game events occur.
Events provide a typed, structured way to communicate game state changes
to subscribers (trigger detection, logging, AI evaluation, etc.).
"""
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from mtg_engine.models.game import PendingTrigger

logger = logging.getLogger(__name__)


# ─── Event Types ──────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """All event types the engine can emit."""
    ZONE_CHANGE = "zone_change"
    PHASE_CHANGE = "phase_change"
    ATTACK = "attack"
    BLOCK = "block"
    DAMAGE = "damage"
    CAST_SPELL = "cast_spell"
    DRAW_CARD = "draw_card"
    DAMAGE_DEALT = "damage_dealt"
    TOKEN_CREATED = "token_created"
    SPELL_COUNTERED = "spell_countered"
    LIFE_CHANGED = "life_changed"
    COUNTER_PLACED = "counter_placed"
    PERMANENT_ENTERS = "permanent_enters"
    PERMANENT_LEAVES = "permanent_leaves"


# ─── Base Event ───────────────────────────────────────────────────────────────

@dataclass
class GameEvent:
    """Base class for all game events."""
    type: EventType = field(init=False)  # Set by __post_init__ in subclasses
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    game_id: str = ""


# ─── Zone Change Events ──────────────────────────────────────────────────────

@dataclass
class ZoneChangeEvent(GameEvent):
    """A card moved between zones. CR 402."""
    card_id: str = ""
    card_name: str | None = None
    from_zone: str = ""
    to_zone: str = ""
    player: str = ""
    is_token: bool = False
    is_draw: bool = False
    permanent_id: str | None = None
    exile_reason: str | None = None

    def __post_init__(self):
        self.type = EventType.ZONE_CHANGE


@dataclass
class PermanentEntersEvent(GameEvent):
    """A permanent entered the battlefield."""
    permanent_id: str = ""
    controller: str = ""
    card_name: str = ""
    zone: str = "battlefield"

    def __post_init__(self):
        self.type = EventType.PERMANENT_ENTERS


@dataclass
class PermanentLeavesEvent(GameEvent):
    """A permanent left the battlefield."""
    permanent_id: str = ""
    controller: str = ""
    card_name: str = ""
    from_zone: str = ""
    to_zone: str = ""

    def __post_init__(self):
        self.type = EventType.PERMANENT_LEAVES


# ─── Phase Events ─────────────────────────────────────────────────────────────

@dataclass
class PhaseChangeEvent(GameEvent):
    """Game phase or step changed."""
    phase: str = ""
    step: str | None = None
    player: str = ""

    def __post_init__(self):
        self.type = EventType.PHASE_CHANGE


# ─── Combat Events ────────────────────────────────────────────────────────────

@dataclass
class AttackEvent(GameEvent):
    """Creatures were declared as attackers."""
    attacker_ids: list[str] = field(default_factory=list)
    defending_player: str = ""
    attacker_controller: str = ""

    def __post_init__(self):
        self.type = EventType.ATTACK


@dataclass
class BlockEvent(GameEvent):
    """Creatures were declared as blockers."""
    blocker_ids: list[str] = field(default_factory=list)
    attacker_ids: list[str] = field(default_factory=list)
    blocking_player: str = ""

    def __post_init__(self):
        self.type = EventType.BLOCK


@dataclass
class DamageDealtEvent(GameEvent):
    """Damage was dealt to a player or permanent."""
    source_id: str = ""
    source_controller: str = ""
    target_id: str = ""
    damage_amount: int = 0
    is_combat: bool = False

    def __post_init__(self):
        self.type = EventType.DAMAGE_DEALT


@dataclass
class DamageEvent(GameEvent):
    """Damage event (alias for DamageDealtEvent for backward compat)."""
    source_id: str = ""
    source_controller: str = ""
    target_id: str = ""
    damage_amount: int = 0
    is_combat: bool = False

    def __post_init__(self):
        self.type = EventType.DAMAGE


# ─── Spell Events ─────────────────────────────────────────────────────────────

@dataclass
class CastSpellEvent(GameEvent):
    """A spell was cast."""
    caster: str = ""
    spell_name: str = ""
    spell_type_line: str = ""
    mana_cost: str | None = None

    def __post_init__(self):
        self.type = EventType.CAST_SPELL


@dataclass
class SpellCounteredEvent(GameEvent):
    """A spell was countered."""
    spell_name: str = ""
    countered_by: str = ""
    caster: str = ""

    def __post_init__(self):
        self.type = EventType.SPELL_COUNTERED


# ─── Card Draw Events ────────────────────────────────────────────────────────

@dataclass
class DrawCardEvent(GameEvent):
    """Cards were drawn."""
    player: str = ""
    card_count: int = 1
    source: str = "draw_step"

    def __post_init__(self):
        self.type = EventType.DRAW_CARD


# ─── Token Events ─────────────────────────────────────────────────────────────

@dataclass
class TokenCreatedEvent(GameEvent):
    """A token was created."""
    token_name: str = ""
    token_controller: str = ""
    token_type: str = "creature"

    def __post_init__(self):
        self.type = EventType.TOKEN_CREATED


# ─── Life Events ──────────────────────────────────────────────────────────────

@dataclass
class LifeChangedEvent(GameEvent):
    """A player's life total changed."""
    player: str = ""
    old_life: int = 20
    new_life: int = 20
    change_amount: int = 0
    reason: str = ""

    def __post_init__(self):
        self.type = EventType.LIFE_CHANGED


# ─── Counter Events ───────────────────────────────────────────────────────────

@dataclass
class CounterPlacedEvent(GameEvent):
    """Counters were added/removed from a permanent."""
    permanent_id: str = ""
    counter_type: str = ""
    count: int = 0
    action: str = "add"

    def __post_init__(self):
        self.type = EventType.COUNTER_PLACED


# ─── Event Bus ────────────────────────────────────────────────────────────────

EventHandler = Callable[[GameEvent], None]
ListenerMap = dict[EventType, list[EventHandler]]


class EventBus:
    """
    Typed event notification bus.

    Subscribers register for specific event types and receive only those events.
    Events are delivered synchronously in subscription order.
    """

    def __init__(self) -> None:
        self._listeners: ListenerMap = {
            et: [] for et in EventType
        }

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for the given event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        logger.debug("Subscribed handler to %s", event_type.value)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a handler for the given event type."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(handler)
            except ValueError:
                pass
            logger.debug("Unsubscribed handler from %s", event_type.value)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """Remove a handler from all event types."""
        for event_type in list(self._listeners.keys()):
            self.unsubscribe(event_type, handler)

    def emit(self, event: GameEvent) -> None:
        """Emit an event to all subscribers of its type."""
        handlers = self._listeners.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Error in event handler for %s: %r",
                    event.type.value, event,
                )

    def get_listeners(self, event_type: EventType) -> list[EventHandler]:
        """Return a copy of handlers for the given event type."""
        return list(self._listeners.get(event_type, []))


# ─── Default Bus Singleton ────────────────────────────────────────────────────

_default_bus: EventBus | None = None


def get_default_bus() -> EventBus:
    """Return the global default event bus (singleton)."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


# ─── Event-to-Trigger Bridge ─────────────────────────────────────────────────

class EventTriggerBridge:
    """
    Bridges typed events to the existing trigger system.

    When events fire (zone changes, phase changes, damage, etc.),
    this bridge converts them to PendingTrigger entries in GameState
    so that triggered abilities can be queued and resolved normally.

    Each bridge instance is bound to a single game_id. Handlers filter
    incoming events by game_id to avoid cross-game interference.
    """

    def __init__(self, bus: EventBus | None = None, game_id: str = "") -> None:
        self.bus = bus or get_default_bus()
        self._handlers_registered = False
        self._game_id = game_id

    # ── Life/loss trigger patterns ────────────────────────────────────────
    _LIFE_GAIN_TRIGGER_RE = re.compile(
        r"whenever (?:you|a player) gain(?:s)? life", re.IGNORECASE
    )
    _LIFE_LOSS_TRIGGER_RE = re.compile(
        r"whenever (?:you|a player) lose(?:s)? life", re.IGNORECASE
    )
    _COUNTER_TRIGGER_RE = re.compile(
        r"whenever (?:you|a player|a) (?:put|place) (?:a|one|an?) counter",
        re.IGNORECASE,
    )

    def _queue_life_triggers(self, gs: Any, player_name: str, delta: int) -> None:
        """Scan permanents for life-gain/loss triggers and queue PendingTriggers."""
        from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

        is_gain = delta > 0
        pattern = self._LIFE_GAIN_TRIGGER_RE if is_gain else self._LIFE_LOSS_TRIGGER_RE
        for perm in list(gs.battlefield):
            card = perm.card
            abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
            for ab in abilities:
                if not isinstance(ab, TriggeredAbility):
                    continue
                if pattern.search(ab.trigger_condition):
                    is_optional = ab.effect.lower().startswith("you may")
                    gs.pending_triggers.append(PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="life_change",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    ))
                    logger.debug("Bridge: life trigger queued from %s", card.name)

    def _queue_counter_triggers(self, gs: Any, counter_type: str, action: str) -> None:
        """Scan permanents for counter-placed triggers and queue PendingTriggers."""
        from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

        for perm in list(gs.battlefield):
            card = perm.card
            abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
            for ab in abilities:
                if not isinstance(ab, TriggeredAbility):
                    continue
                if self._COUNTER_TRIGGER_RE.search(ab.trigger_condition):
                    is_optional = ab.effect.lower().startswith("you may")
                    gs.pending_triggers.append(PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="counter",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    ))
                    logger.debug("Bridge: counter trigger queued from %s", card.name)

    def register(self, game_state: Any) -> None:
        """Register event handlers on the bus that feed into game_state."""
        if self._handlers_registered:
            return

        # Life change handler - queue life-gain/loss triggers
        def _on_life_change(event: GameEvent) -> None:
            if not isinstance(event, LifeChangedEvent):
                return
            if self._game_id and event.game_id != self._game_id:
                return
            self._queue_life_triggers(
                game_state, event.player, event.change_amount
            )

        # Counter handler - queue counter-placed triggers
        def _on_counter(event: GameEvent) -> None:
            if not isinstance(event, CounterPlacedEvent):
                return
            if self._game_id and event.game_id != self._game_id:
                return
            self._queue_counter_triggers(
                game_state, event.counter_type, event.action
            )

        # Damage handler - forward to existing damage trigger check
        def _on_damage(event: GameEvent) -> None:
            if not isinstance(event, DamageDealtEvent):
                return
            if self._game_id and event.game_id != self._game_id:
                return
            _run_damage_triggers(game_state, event)

        # Zone change handler - forward to existing zone-change trigger detection
        def _on_zone_change(event: GameEvent) -> None:
            if not isinstance(event, ZoneChangeEvent):
                return
            if self._game_id and event.game_id != self._game_id:
                return
            _run_zone_change_triggers(game_state, event)

        # Phase change handler - forward to existing phase trigger detection
        def _on_phase_change(event: GameEvent) -> None:
            if not isinstance(event, PhaseChangeEvent):
                return
            if self._game_id and event.game_id != self._game_id:
                return
            _run_phase_triggers(game_state, event)

        self.bus.subscribe(EventType.LIFE_CHANGED, _on_life_change)
        self.bus.subscribe(EventType.COUNTER_PLACED, _on_counter)
        self.bus.subscribe(EventType.DAMAGE_DEALT, _on_damage)
        self.bus.subscribe(EventType.ZONE_CHANGE, _on_zone_change)
        self.bus.subscribe(EventType.PHASE_CHANGE, _on_phase_change)

        self._handlers_registered = True

    def unregister(self) -> None:
        """Remove all registered handlers from the bus."""
        if not self._handlers_registered:
            return
        handlers_to_remove = set()
        for et in EventType:
            handlers_to_remove.update(self.bus.get_listeners(et))
        for handler in handlers_to_remove:
            self.bus.unsubscribe_all(handler)
        self._handlers_registered = False


# ─── Bridge helper functions (call existing trigger detection) ─────────────

def _run_zone_change_triggers(gs: Any, event: ZoneChangeEvent) -> None:
    """
    Convert a typed ZoneChangeEvent into the legacy dict-based event
    and delegate to the existing trigger detection in triggers.py.
    """
    from mtg_engine.engine.triggers import _on_zone_change as legacy_zone_change
    legacy_event = {
        "card_id": event.card_id,
        "card_name": event.card_name,
        "from_zone": event.from_zone,
        "to_zone": event.to_zone,
        "player": event.player,
        "is_token": event.is_token,
    }
    legacy_zone_change(legacy_event, gs)


def _run_phase_triggers(gs: Any, event: PhaseChangeEvent) -> None:
    """
    Delegate phase-change events to the existing check_phase_triggers.
    """
    from mtg_engine.engine.triggers import check_phase_triggers
    check_phase_triggers(gs)


def _run_damage_triggers(gs: Any, event: DamageDealtEvent) -> None:
    """
    Delegate damage events to the existing check_damage_triggers.
    Builds a minimal assignment list from the event.
    """
    from mtg_engine.engine.triggers import check_damage_triggers
    from mtg_engine.models.actions import DamageAssignment

    if not event.damage_amount:
        return
    assignments = [
        DamageAssignment(
            source_id=event.source_id,
            target_id=event.target_id,
            damage=event.damage_amount,
        )
    ]
    check_damage_triggers(gs, assignments)
