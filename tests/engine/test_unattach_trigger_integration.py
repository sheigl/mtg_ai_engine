"""
7-17 Integration: Unattach trigger via the REAL move_permanent_to_zone call site.

The new unattach wiring (Story 7-17, AC #2) lives in ``zones.move_permanent_to_zone``
(zones.py ~304-314). Whenever a previously-attached aura/equipment leaves the
battlefield it calls::

    check_attach_triggers(game_state, perm.id, attach_event="unattach",
                          attached_controller=controller)

with ``controller`` captured from ``perm.controller`` BEFORE the battlefield
removal (zones.py ~225 vs ~222). Because the aura is already gone by call time,
the "you control" filter in triggers.py:1153 can only work if that pre-removal
controller was captured and passed through.

These tests drive ``move_permanent_to_zone`` directly (a real engine entry point,
exactly what the new call site lives inside) rather than calling
``check_attach_triggers`` in isolation, so they exercise the wiring end to end.
Setup mirrors how put_permanent_onto_battlefield attaches an aura on cast
(stack.py ~684): host.attachments = [aura.id], aura.attached_to = host.id.
"""
import uuid

from mtg_engine.engine.zones import move_permanent_to_zone
from mtg_engine.engine.triggers import check_attach_triggers
from mtg_engine.models.game import GameState, Card, Permanent, Phase, Step, PlayerState


def _make_gs(active_player: str = "Alice") -> GameState:
    return GameState(
        game_id="test-unattach",
        seed=717,
        turn=3,
        active_player=active_player,
        priority_holder=active_player,
        phase=Phase.COMBAT,
        step=Step.DECLARE_ATTACKERS,
        players=[
            PlayerState(name="Alice", life_total=20),
            PlayerState(name="Bob", life_total=20),
        ],
        battlefield=[],
    )


def _perm(card_name: str, oracle_text: str, type_line: str, controller: str) -> Permanent:
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name=card_name, type_line=type_line, oracle_text=oracle_text),
        controller=controller,
    )


def _attached_aura(controller: str) -> tuple[Permanent, Permanent]:
    """Return (host_creature, aura) wired as a real attachment.

    host.attachments == [aura.id] and aura.attached_to == host.id — the same
    bookkeeping put_permanent_onto_battlefield maintains on cast (stack.py ~684).
    """
    host = _perm("Goblin Guide", "When Goblin Guide enters, you lose 1 life.",
                 "Creature — Goblin", controller)
    aura = _perm("Divine Favor",
                 "Whenever an aura you control becomes unattached, draw a card.",
                 "Enchantment Aura — Aura Creature", controller)
    host.attachments.append(aura.id)
    aura.attached_to = host.id
    return host, aura


def _attach_trigger_types(gs: GameState) -> list[str]:
    return [t.trigger_type for t in gs.pending_triggers]


class TestUnattachTriggerIntegration:
    def test_unattach_fires_for_aura_controller(self):
        """AC #2 positive case: detaching an aura fires the unattach trigger and the
        'you control' filter matches the aura's ORIGINAL controller — even though the
        aura has already left the battlefield by call time. This proves
        attached_controller was captured before removal (zones.py ~225 -> :313)."""
        gs = _make_gs()
        host, aura = _attached_aura("Alice")
        # Alice also controls a watcher with an unattach trigger.
        watcher = _perm("Thalia, Guardian of Thraben",
                        "Whenever an aura you control becomes unattached, draw two cards.",
                        "Legendary Creature — Human Knight", "Alice")
        gs.battlefield.extend([host, aura, watcher])

        # Drive the REAL entry point: move the attached aura off the battlefield.
        gs2 = move_permanent_to_zone(gs, aura, "graveyard")

        # The aura is gone from the returned battlefield ...
        assert all(p.id != aura.id for p in gs2.battlefield)
        # ... yet the unattach trigger still queued, sourced on the watcher (not the aura).
        attach_triggers = [t for t in gs2.pending_triggers if t.trigger_type == "attach"]
        assert len(attach_triggers) >= 1, f"expected unattach trigger; got {_attach_trigger_types(gs2)}"
        assert all(t.source_permanent_id == watcher.id for t in attach_triggers)

    def test_unattach_negative_different_controller(self):
        """AC #2 negative case: an aura controlled by a DIFFERENT player than the
        watcher does NOT fire that watcher's 'you control' trigger. This proves the
        pre-removal controller capture is correct — it is not simply matching every
        watcher on the battlefield."""
        gs = _make_gs()
        host, aura = _attached_aura("Bob")  # Bob owns the aura
        watcher = _perm("Thalia, Guardian of Thraben",
                        "Whenever an aura you control becomes unattached, draw two cards.",
                        "Legendary Creature — Human Knight", "Alice")  # Alice watches
        gs.battlefield.extend([host, aura, watcher])

        gs2 = move_permanent_to_zone(gs, aura, "graveyard")

        attach_triggers = [t for t in gs2.pending_triggers if t.trigger_type == "attach"]
        assert len(attach_triggers) == 0, (
            f"Bob's aura must not fire Alice's 'you control' trigger; got {_attach_trigger_types(gs2)}"
        )

    def test_unattach_pure_transform(self):
        """Q4: check_attach_triggers returns a NEW GameState and never mutates the
        caller's pending_triggers list in place."""
        gs = _make_gs()
        _, aura = _attached_aura("Alice")
        watcher = _perm("Thalia, Guardian of Thraben",
                        "Whenever an aura you control becomes unattached, draw two cards.",
                        "Legendary Creature — Human Knight", "Alice")
        gs.battlefield.extend([aura, watcher])

        original_pending = gs.pending_triggers
        gs2 = check_attach_triggers(gs, aura.id, attach_event="unattach",
                                    attached_controller="Alice")

        # Returned state is a distinct object carrying the new trigger ...
        assert id(gs2) != id(gs)
        assert len([t for t in gs2.pending_triggers if t.trigger_type == "attach"]) >= 1
        # ... and the original pending_triggers list was NOT mutated (Q4).
        assert original_pending is gs.pending_triggers
        assert all(t.trigger_type != "attach" for t in gs.pending_triggers)

    def test_move_call_site_captures_returned_state(self):
        """The call site must use the returned GameState (pure transform at the
        integration boundary). Capturing it preserves the queued trigger."""
        gs = _make_gs()
        _, aura = _attached_aura("Alice")
        watcher = _perm("Thalia, Guardian of Thraben",
                        "Whenever an aura you control becomes unattached, draw two cards.",
                        "Legendary Creature — Human Knight", "Alice")
        gs.battlefield.extend([aura, watcher])

        # Real entry point, return value captured (the pattern the wiring relies on).
        gs2 = move_permanent_to_zone(gs, aura, "hand")

        assert any(t.trigger_type == "attach" for t in gs2.pending_triggers)
        # Detaching to hand also leaves the aura off the battlefield.
        assert all(p.id != aura.id for p in gs2.battlefield)
