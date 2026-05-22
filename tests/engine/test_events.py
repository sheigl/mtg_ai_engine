"""
Phase 1300: Event System tests.
EVT-01: Event Bus Infrastructure — typed events + bus
EVT-02: Event-to-Trigger Bridge — connect bus to triggers

CR 603: Triggered abilities fire when game events occur.
"""
import pytest
from unittest.mock import Mock, call

from mtg_engine.engine.events import (
    EventBus,
    GameEvent,
    ZoneChangeEvent,
    PhaseChangeEvent,
    AttackEvent,
    BlockEvent,
    DamageEvent,
    CastSpellEvent,
    DrawCardEvent,
    DamageDealtEvent,
    TokenCreatedEvent,
    SpellCounteredEvent,
    LifeChangedEvent,
    CounterPlacedEvent,
    PermanentEntersEvent,
    PermanentLeavesEvent,
    EventType,
)


# ─── EVT-01: Event Bus Infrastructure ────────────────────────────────────────

class TestEventType:
    def test_event_type_values(self):
        assert EventType.ZONE_CHANGE == "zone_change"
        assert EventType.PHASE_CHANGE == "phase_change"
        assert EventType.ATTACK == "attack"
        assert EventType.BLOCK == "block"
        assert EventType.DAMAGE == "damage"
        assert EventType.CAST_SPELL == "cast_spell"
        assert EventType.DRAW_CARD == "draw_card"
        assert EventType.DAMAGE_DEALT == "damage_dealt"
        assert EventType.TOKEN_CREATED == "token_created"
        assert EventType.SPELL_COUNTERED == "spell_countered"
        assert EventType.LIFE_CHANGED == "life_changed"
        assert EventType.COUNTER_PLACED == "counter_placed"
        assert EventType.PERMANENT_ENTERS == "permanent_enters"
        assert EventType.PERMANENT_LEAVES == "permanent_leaves"


class TestGameEvent:
    def test_zone_change_has_timestamp(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        )
        assert hasattr(event, "timestamp")
        assert event.timestamp > 0

    def test_zone_change_has_id(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        )
        assert hasattr(event, "id")
        assert len(event.id) > 0


class TestZoneChangeEvent:
    def test_zone_change_fields(self):
        event = ZoneChangeEvent(
            card_id="card-1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        )
        assert event.card_id == "card-1"
        assert event.card_name == "Mountain"
        assert event.from_zone == "library"
        assert event.to_zone == "hand"
        assert event.player == "Alice"

    def test_zone_change_defaults(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Forest",
            from_zone="battlefield",
            to_zone="graveyard",
            player="Bob",
        )
        assert event.is_token is False
        assert event.is_draw is False

    def test_zone_change_with_token(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Token",
            from_zone="battlefield",
            to_zone="graveyard",
            player="Alice",
            is_token=True,
        )
        assert event.is_token is True

    def test_zone_change_is_draw(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name=None,
            from_zone="library",
            to_zone="hand",
            player="Alice",
            is_draw=True,
        )
        assert event.is_draw is True
        assert event.card_name is None

    def test_zone_change_to_battlefield(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Goblin",
            from_zone="hand",
            to_zone="battlefield",
            player="Alice",
        )
        assert event.to_zone == "battlefield"

    def test_zone_change_from_battlefield(self):
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Goblin",
            from_zone="battlefield",
            to_zone="graveyard",
            player="Alice",
        )
        assert event.from_zone == "battlefield"


class TestPhaseChangeEvent:
    def test_phase_change_fields(self):
        event = PhaseChangeEvent(
            phase="combat",
            step="declare_attackers",
            player="Alice",
        )
        assert event.phase == "combat"
        assert event.step == "declare_attackers"
        assert event.player == "Alice"

    def test_phase_change_no_step(self):
        event = PhaseChangeEvent(
            phase="beginning",
            step=None,
            player="Bob",
        )
        assert event.phase == "beginning"
        assert event.step is None


class TestAttackEvent:
    def test_attack_event_fields(self):
        event = AttackEvent(
            attacker_ids=["perm-1", "perm-2"],
            defending_player="Alice",
            attacker_controller="Bob",
        )
        assert "perm-1" in event.attacker_ids
        assert event.defending_player == "Alice"
        assert event.attacker_controller == "Bob"


class TestBlockEvent:
    def test_block_event_fields(self):
        event = BlockEvent(
            blocker_ids=["perm-3"],
            attacker_ids=["perm-1"],
            blocking_player="Alice",
        )
        assert "perm-3" in event.blocker_ids
        assert "perm-1" in event.attacker_ids
        assert event.blocking_player == "Alice"


class TestDamageEvent:
    def test_damage_event_fields(self):
        event = DamageEvent(
            source_id="perm-1",
            source_controller="Bob",
            target_id="Alice",
            damage_amount=3,
            is_combat=True,
        )
        assert event.source_id == "perm-1"
        assert event.target_id == "Alice"
        assert event.damage_amount == 3
        assert event.is_combat is True


class TestDamageDealtEvent:
    def test_damage_dealt_event_fields(self):
        event = DamageDealtEvent(
            source_id="perm-1",
            source_controller="Bob",
            target_id="Alice",
            damage_amount=3,
            is_combat=True,
        )
        assert event.source_id == "perm-1"
        assert event.damage_amount == 3


class TestCastSpellEvent:
    def test_cast_spell_event_fields(self):
        event = CastSpellEvent(
            caster="Alice",
            spell_name="Lightning Bolt",
            spell_type_line="instant",
            mana_cost="{R}",
        )
        assert event.caster == "Alice"
        assert event.spell_name == "Lightning Bolt"
        assert event.spell_type_line == "instant"
        assert event.mana_cost == "{R}"


class TestDrawCardEvent:
    def test_draw_card_event_fields(self):
        event = DrawCardEvent(
            player="Alice",
            card_count=1,
            source="draw_step",
        )
        assert event.player == "Alice"
        assert event.card_count == 1
        assert event.source == "draw_step"


class TestTokenCreatedEvent:
    def test_token_created_event_fields(self):
        event = TokenCreatedEvent(
            token_name="Goblin Warrior",
            token_controller="Alice",
            token_type="creature",
        )
        assert event.token_name == "Goblin Warrior"
        assert event.token_controller == "Alice"


class TestSpellCounteredEvent:
    def test_spell_countered_event_fields(self):
        event = SpellCounteredEvent(
            spell_name="Lightning Bolt",
            countered_by="Counterspell",
            caster="Alice",
        )
        assert event.spell_name == "Lightning Bolt"
        assert event.countered_by == "Counterspell"
        assert event.caster == "Alice"


class TestLifeChangedEvent:
    def test_life_changed_event_fields(self):
        event = LifeChangedEvent(
            player="Alice",
            old_life=20,
            new_life=17,
            change_amount=-3,
            reason="damage",
        )
        assert event.player == "Alice"
        assert event.old_life == 20
        assert event.new_life == 17
        assert event.change_amount == -3
        assert event.reason == "damage"

    def test_life_changed_gain(self):
        event = LifeChangedEvent(
            player="Bob",
            old_life=15,
            new_life=18,
            change_amount=3,
            reason="lifelink",
        )
        assert event.change_amount == 3
        assert event.new_life == 18


class TestCounterPlacedEvent:
    def test_counter_placed_event_fields(self):
        event = CounterPlacedEvent(
            permanent_id="perm-1",
            counter_type="+1/+1",
            count=2,
            action="add",
        )
        assert event.permanent_id == "perm-1"
        assert event.counter_type == "+1/+1"
        assert event.count == 2
        assert event.action == "add"

    def test_counter_placed_remove(self):
        event = CounterPlacedEvent(
            permanent_id="perm-2",
            counter_type="-1/-1",
            count=1,
            action="remove",
        )
        assert event.action == "remove"


class TestPermanentEntersEvent:
    def test_perm_enters_event_fields(self):
        event = PermanentEntersEvent(
            permanent_id="perm-1",
            controller="Alice",
            card_name="Goblin",
            zone="battlefield",
        )
        assert event.permanent_id == "perm-1"
        assert event.controller == "Alice"
        assert event.card_name == "Goblin"


class TestPermanentLeavesEvent:
    def test_perm_leaves_event_fields(self):
        event = PermanentLeavesEvent(
            permanent_id="perm-1",
            controller="Alice",
            card_name="Goblin",
            from_zone="battlefield",
            to_zone="graveyard",
        )
        assert event.permanent_id == "perm-1"
        assert event.from_zone == "battlefield"
        assert event.to_zone == "graveyard"


class TestEventBus:
    def test_bus_create(self):
        bus = EventBus()
        assert bus is not None

    def test_subscribe_callback(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        assert handler in bus._listeners[EventType.ZONE_CHANGE]

    def test_subscribe_multiple_types(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        bus.subscribe(EventType.PHASE_CHANGE, handler)
        assert handler in bus._listeners[EventType.ZONE_CHANGE]
        assert handler in bus._listeners[EventType.PHASE_CHANGE]

    def test_emit_calls_subscribers(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        )
        bus.emit(event)
        handler.assert_called_once_with(event)

    def test_emit_calls_all_subscribers_for_type(self):
        bus = EventBus()
        h1 = Mock()
        h2 = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, h1)
        bus.subscribe(EventType.ZONE_CHANGE, h2)
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Forest",
            from_zone="hand",
            to_zone="battlefield",
            player="Bob",
        )
        bus.emit(event)
        h1.assert_called_once_with(event)
        h2.assert_called_once_with(event)

    def test_emit_does_not_call_unrelated_type_handlers(self):
        bus = EventBus()
        zone_handler = Mock()
        phase_handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, zone_handler)
        bus.subscribe(EventType.PHASE_CHANGE, phase_handler)
        bus.emit(PhaseChangeEvent(phase="combat", step="beginning_of_combat", player="Alice"))
        zone_handler.assert_not_called()
        phase_handler.assert_called_once()

    def test_unsubscribe(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        bus.unsubscribe(EventType.ZONE_CHANGE, handler)
        assert handler not in bus._listeners[EventType.ZONE_CHANGE]

    def test_unsubscribe_all_types(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        bus.subscribe(EventType.PHASE_CHANGE, handler)
        bus.unsubscribe_all(handler)
        assert handler not in bus._listeners.get(EventType.ZONE_CHANGE, [])
        assert handler not in bus._listeners.get(EventType.PHASE_CHANGE, [])

    def test_emit_to_empty_listener(self):
        bus = EventBus()
        event = ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        )
        # Should not raise
        bus.emit(event)

    def test_emit_order_preserved(self):
        bus = EventBus()
        order = []
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: order.append(1))
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: order.append(2))
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: order.append(3))
        bus.emit(ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        ))
        assert order == [1, 2, 3]

    def test_get_listeners(self):
        bus = EventBus()
        h1 = Mock()
        h2 = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, h1)
        bus.subscribe(EventType.ZONE_CHANGE, h2)
        listeners = bus.get_listeners(EventType.ZONE_CHANGE)
        assert len(listeners) == 2
        assert h1 in listeners
        assert h2 in listeners

    def test_get_listeners_empty(self):
        bus = EventBus()
        listeners = bus.get_listeners(EventType.DAMAGE)
        assert len(listeners) == 0

    def test_emit_cross_type_no_error(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(EventType.ZONE_CHANGE, handler)
        # Emitting a different type should not crash
        bus.emit(PhaseChangeEvent(phase="combat", step="declare_attackers", player="Alice"))
        handler.assert_not_called()


class TestEventBusIntegration:
    def test_zone_change_flow(self):
        """Simulate a card moving from library to hand."""
        bus = EventBus()
        received = []
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: received.append(e))
        bus.emit(ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        ))
        assert len(received) == 1
        assert isinstance(received[0], ZoneChangeEvent)
        assert received[0].card_name == "Mountain"

    def test_phase_change_flow(self):
        """Simulate phase transitions."""
        bus = EventBus()
        phases = []
        bus.subscribe(EventType.PHASE_CHANGE, lambda e: phases.append((e.phase, e.step)))
        bus.emit(PhaseChangeEvent(phase="combat", step="beginning_of_combat", player="Alice"))
        bus.emit(PhaseChangeEvent(phase="combat", step="declare_attackers", player="Alice"))
        assert len(phases) == 2
        assert phases[0] == ("combat", "beginning_of_combat")
        assert phases[1] == ("combat", "declare_attackers")

    def test_damage_flow(self):
        """Simulate combat damage being dealt."""
        bus = EventBus()
        damages = []
        bus.subscribe(EventType.DAMAGE_DEALT, lambda e: damages.append(e))
        bus.emit(DamageDealtEvent(
            source_id="perm-1",
            source_controller="Bob",
            target_id="Alice",
            damage_amount=3,
            is_combat=True,
        ))
        assert len(damages) == 1
        assert damages[0].damage_amount == 3

    def test_multiple_subscribers_different_events(self):
        """Each handler only receives its subscribed event type."""
        bus = EventBus()
        zone_events = []
        phase_events = []
        damage_events = []
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: zone_events.append(e))
        bus.subscribe(EventType.PHASE_CHANGE, lambda e: phase_events.append(e))
        bus.subscribe(EventType.DAMAGE_DEALT, lambda e: damage_events.append(e))

        bus.emit(ZoneChangeEvent(
            card_id="c1", card_name="Mountain", from_zone="library",
            to_zone="hand", player="Alice",
        ))
        bus.emit(PhaseChangeEvent(phase="combat", step="declare_attackers", player="Alice"))
        bus.emit(DamageDealtEvent(
            source_id="p1", source_controller="Bob", target_id="Alice",
            damage_amount=2, is_combat=True,
        ))

        assert len(zone_events) == 1
        assert len(phase_events) == 1
        assert len(damage_events) == 1


class TestEventBusWithGameState:
    """Integration tests with GameState model."""
    def test_event_bus_with_game_state(self):
        from mtg_engine.models.game import GameState, PlayerState

        gs = GameState(
            game_id="test-1",
            seed=42,
            active_player="Alice",
            priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        )

        bus = EventBus()
        events_received = []
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: events_received.append(e))

        bus.emit(ZoneChangeEvent(
            card_id="c1",
            card_name="Goblin",
            from_zone="hand",
            to_zone="battlefield",
            player="Alice",
        ))

        assert len(events_received) == 1
        assert events_received[0].player == "Alice"


# ─── EVT-02: Event-to-Trigger Bridge ─────────────────────────────────────────

class TestEventToTriggerBridge:
    """Tests for connecting event bus to trigger detection system."""

    def test_bridge_registers_on_bus(self):
        """Bridge should register itself as a listener on the event bus."""
        from mtg_engine.engine.events import EventTriggerBridge
        from mtg_engine.models.game import GameState, PlayerState

        bus = EventBus()
        bridge = EventTriggerBridge(bus)

        gs = GameState(
            game_id="test-1",
            seed=42,
            active_player="Alice",
            priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        )
        bridge.register(gs)

        # Bridge should have registered handlers for various event types
        zone_listeners = bus.get_listeners(EventType.ZONE_CHANGE)
        assert len(zone_listeners) > 0

    def test_bridge_handles_zone_change_for_etb(self):
        """Zone change to battlefield should be handled by bridge without crash."""
        from mtg_engine.engine.events import EventTriggerBridge
        from mtg_engine.models.game import GameState, PlayerState

        gs = GameState(
            game_id="test-1",
            seed=42,
            active_player="Alice",
            priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        )

        bus = EventBus()
        bridge = EventTriggerBridge(bus)
        bridge.register(gs)

        # Should not crash
        bus.emit(ZoneChangeEvent(
            card_id="perm-1",
            card_name="Goblin",
            from_zone="hand",
            to_zone="battlefield",
            player="Alice",
        ))

    def test_bridge_handles_phase_change(self):
        """Phase change events should be handled by bridge."""
        from mtg_engine.engine.events import EventTriggerBridge
        from mtg_engine.models.game import GameState, PlayerState

        gs = GameState(
            game_id="test-1",
            seed=42,
            active_player="Alice",
            priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        )

        bus = EventBus()
        bridge = EventTriggerBridge(bus)
        bridge.register(gs)

        # Should not crash
        bus.emit(PhaseChangeEvent(
            phase="beginning",
            step="upkeep",
            player="Alice",
        ))


class TestEventBusSingleton:
    """Test that EventBus can work as a singleton."""

    def test_default_bus(self):
        from mtg_engine.engine.events import get_default_bus

        bus1 = get_default_bus()
        bus2 = get_default_bus()
        assert bus1 is bus2

    def test_default_bus_emit(self):
        from mtg_engine.engine.events import get_default_bus

        bus = get_default_bus()
        received = []
        bus.subscribe(EventType.ZONE_CHANGE, lambda e: received.append(e))

        bus.emit(ZoneChangeEvent(
            card_id="c1",
            card_name="Mountain",
            from_zone="library",
            to_zone="hand",
            player="Alice",
        ))

        assert len(received) == 1
