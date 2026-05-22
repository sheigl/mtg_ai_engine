"""
Event system for MTG engine.
EVT-01: Typed event notification bus
EVT-02: Event-to-trigger bridge for trigger detection

CR 603: Triggered abilities fire when game events occur.
Events provide a typed, structured way to communicate game state changes
to subscribers (trigger detection, logging, AI evaluation, etc.).
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

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
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or get_default_bus()
        self._handlers_registered = False

    def register(self, game_state: Any) -> None:
        """Register event handlers on the bus that feed into game_state."""
        if self._handlers_registered:
            return

        # Zone change handler - detects ETB, GTC, etc.
        def _on_zone_change(event: GameEvent) -> None:
            if not isinstance(event, ZoneChangeEvent):
                return
            logger.debug("Bridge: zone change %s -> %s (%s)",
                         event.from_zone, event.to_zone, event.card_name)

        # Phase change handler - detects step-based triggers
        def _on_phase_change(event: GameEvent) -> None:
            if not isinstance(event, PhaseChangeEvent):
                return
            logger.debug("Bridge: phase change %s/%s (%s)",
                         event.phase, event.step, event.player)

        # Damage handler - detects damage-based triggers
        def _on_damage(event: GameEvent) -> None:
            if not isinstance(event, DamageDealtEvent):
                return
            logger.debug("Bridge: damage dealt %d to %s",
                         event.damage_amount, event.target_id)

        # Life change handler - detects life-based triggers
        def _on_life_change(event: GameEvent) -> None:
            if not isinstance(event, LifeChangedEvent):
                return
            logger.debug("Bridge: life changed %d -> %d (%s)",
                         event.old_life, event.new_life, event.player)

        # Counter handler - detects counter-based triggers
        def _on_counter(event: GameEvent) -> None:
            if not isinstance(event, CounterPlacedEvent):
                return
            logger.debug("Bridge: counter %s x%d on %s (%s)",
                         event.counter_type, event.count,
                         event.permanent_id, event.action)

        self.bus.subscribe(EventType.ZONE_CHANGE, _on_zone_change)
        self.bus.subscribe(EventType.PHASE_CHANGE, _on_phase_change)
        self.bus.subscribe(EventType.DAMAGE_DEALT, _on_damage)
        self.bus.subscribe(EventType.LIFE_CHANGED, _on_life_change)
        self.bus.subscribe(EventType.COUNTER_PLACED, _on_counter)

        self._handlers_registered = True

    def unregister(self) -> None:
        """Remove all registered handlers from the bus."""
        if not self._handlers_registered:
            return
        # Collect handlers to avoid modifying dict during iteration
        handlers_to_remove = set()
        for et in EventType:
            handlers_to_remove.update(self.bus.get_listeners(et))
        for handler in handlers_to_remove:
            self.bus.unsubscribe_all(handler)
        self._handlers_registered = False
