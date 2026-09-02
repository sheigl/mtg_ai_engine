"""
7-3 Investigated Trigger Integration Tests (Sprint 7)

Tests for the "whenever you investigate" trigger category (CR 701.32, MODERN
rules) and the ``investigate`` game action, added in Sprint 7 P0 (story 7-3).

Coverage:
  Unit-style (drives ``check_investigated_triggers`` directly):
    - pattern registration / index-to-filter mapping
    - you-filter negative
    - no-match
    - multiple permanents

  Natural-context (drives the REAL engine entry points
  ``stack._investigate`` and the effect-resolution pipeline):
    - fires when a player investigates
    - a non-investigate token creation does NOT fire "investigated"
    - the investigate token is a 1/1 red Goblin with "investigate"

Q1 (exactly-once): the "investigated" pattern is referenced ONLY by
``check_investigated_triggers`` (never by the zone-change listener nor by the
generic token path for action-keyed watchers).
``test_investigate_non_investigate_token_does_not_fire`` proves a plain token
creation queues no "investigated" trigger.
"""
import uuid

import pytest

from mtg_engine.models.game import (
    GameState,
    Permanent,
    Card,
    PlayerState,
    StackObject,
)
from mtg_engine.engine.triggers import (
    check_investigated_triggers,
    INVESTIGATED_TRIGGER_PATTERNS,
    TOKEN_TRIGGER_PATTERNS,
    TRIGGER_PATTERNS,
)
from mtg_engine.engine.stack import (
    _investigate,
    _create_tokens,
    _apply_single_effect_text,
    _apply_spell_effect,
)


# --- Test helpers ---------------------------------------------------------

def _make_gs() -> GameState:
    return GameState(
        game_id="investigated-test",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(name="Alice", life=20),
            PlayerState(name="Bob", life=20),
        ],
        battlefield=[],
    )


def _perm(name, oracle_text, controller="Alice", type_line="Enchantment") -> Permanent:
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name=name, type_line=type_line, oracle_text=oracle_text),
        controller=controller,
    )


def _investigated_count(gs: GameState) -> int:
    return sum(1 for t in gs.pending_triggers if t.trigger_type == "investigated")


def _trigger_types(gs: GameState) -> list[str]:
    return [t.trigger_type for t in gs.pending_triggers]


def _investigate_tokens(gs: GameState, controller="Alice") -> list[Permanent]:
    return [
        p for p in gs.battlefield
        if p.is_token and p.controller == controller
        and "Goblin" in (p.card.type_line or "")
    ]


# --- Unit-style: pattern registration & filters ---------------------------

class TestInvestigatedPattern:
    def test_investigated_pattern_matches(self):
        """The investigated list is exactly the 2 action phrasings; the
        token-fallback phrasing is deliberately NOT owned by this category
        (7-3 test round 1 fix: token-ETB phrasings are owned by the generic
        token-trigger path so each watcher fires exactly once)."""
        assert "investigated" in TRIGGER_PATTERNS
        assert TRIGGER_PATTERNS["investigated"] is INVESTIGATED_TRIGGER_PATTERNS
        assert len(INVESTIGATED_TRIGGER_PATTERNS) == 2

        # index 0 - you
        assert INVESTIGATED_TRIGGER_PATTERNS[0].search("whenever you investigate")
        # index 1 - any player (both inflected forms)
        assert INVESTIGATED_TRIGGER_PATTERNS[1].search("whenever a player investigates")
        assert INVESTIGATED_TRIGGER_PATTERNS[1].search("whenever a player investigate")
        # token-fallback phrasing is NOT in the investigated category...
        for pat in INVESTIGATED_TRIGGER_PATTERNS:
            assert pat.search("whenever a clue token enters the battlefield") is None
            assert pat.search("whenever an investigate token enters the battlefield") is None
        # ...it is owned by the generic token-trigger path instead.
        assert any(
            pat.search("whenever an investigate token enters the battlefield")
            for pat in TOKEN_TRIGGER_PATTERNS
        )
        # non-matches
        assert INVESTIGATED_TRIGGER_PATTERNS[0].search("whenever a creature enters the battlefield") is None
        assert INVESTIGATED_TRIGGER_PATTERNS[1].search("whenever a creature dies") is None

    def test_investigated_you_negative(self):
        """'whenever you investigate' must NOT fire for a watcher who did NOT
        investigate (index-0 you-filter)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card.", controller="Bob"))
        gs = check_investigated_triggers(gs, "Alice")  # Alice investigates, Bob watches
        assert _investigated_count(gs) == 0

        # Control: Bob watches and Bob investigates -> fires.
        gs2 = _make_gs()
        gs2.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card.", controller="Bob"))
        gs2 = check_investigated_triggers(gs2, "Bob")
        assert _investigated_count(gs2) == 1

    def test_investigated_no_match(self):
        """A permanent with no investigate trigger queues nothing."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Bear", "2/2", type_line="Creature - Beast"))
        gs.battlefield.append(_perm("DrawGuy", "Whenever you draw a card, draw another card."))
        gs = check_investigated_triggers(gs, "Alice")
        assert _investigated_count(gs) == 0

    def test_investigate_multiple_permanents(self):
        """Each 'whenever you investigate' watcher controlled by the
        investigating player fires once."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher A", "Whenever you investigate, draw a card."))
        gs.battlefield.append(_perm("Watcher B", "Whenever you investigate, scry 1."))
        gs = check_investigated_triggers(gs, "Alice")
        assert _investigated_count(gs) == 2


# --- Natural-context: real investigate entry points -----------------------

class TestInvestigateWiring:
    def test_investigate_fires_via_effect(self):
        """Performing the investigate action through the effect-resolution
        pipeline (the real entry point for a card's investigate effect) fires
        the trigger, creates the token, and handles the top library card."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card."))
        # Top card is a land -> revealed & kept revealed (moved to hand).
        gs.players[0].library = [Card(name="Forest", type_line="Basic Land - Forest")]

        so = StackObject(
            source_card=Card(name="Detective", type_line="Creature - Human",
                             oracle_text="Investigate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, so, "Investigate.")

        assert _investigated_count(gs) == 1
        assert any(c.name == "Forest" for c in gs.players[0].hand)
        assert len(_investigate_tokens(gs)) == 1

    def test_investigate_non_investigate_token_does_not_fire(self):
        """Creating a plain (non-investigate) token must NOT queue an
        'investigated' trigger (Q1: no false positives)."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card."))

        # A Bird token is created via the generic token path (not investigate).
        gs = _create_tokens(gs, "Alice", "a", "1", "1", "Bird")

        # A plain token really exists on the battlefield...
        assert any(p.is_token and "Bird" in (p.card.type_line or "") for p in gs.battlefield)
        # ...but it is NOT an investigate token, so no "investigated" trigger.
        assert _investigated_count(gs) == 0

    def test_investigate_token_is_1_1_red_goblin(self):
        """The investigate action creates a 1/1 red Goblin creature token with
        the 'investigate' keyword (CR 701.32)."""
        gs = _make_gs()
        gs.players[0].library = [Card(name="Forest", type_line="Basic Land - Forest")]

        gs = _investigate(gs, "Alice")

        tokens = _investigate_tokens(gs)
        assert len(tokens) == 1
        token = tokens[0]
        assert token.card.power == "1"
        assert token.card.toughness == "1"
        assert token.card.colors == ["R"]
        assert "Goblin" in (token.card.type_line or "")
        assert "investigate" in (token.card.keywords or [])
        assert token.is_token is True

    def test_investigate_non_land_to_bottom(self):
        """A NON-land top card goes to the BOTTOM of the library (the rest of
        the library keeps its order); the investigate token is created and the
        investigated trigger fires. Edge: an empty library does not crash and
        the token is still created."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card."))
        top = Card(name="Fireball", type_line="Instant", oracle_text="Deal 3 damage.")
        mid = Card(name="Forest", type_line="Basic Land - Forest")
        bot = Card(name="Lightning Bolt", type_line="Instant", oracle_text="Deal 3 damage.")
        gs.players[0].library = [top, mid, bot]

        gs = _investigate(gs, "Alice")

        # Non-land top card moved to the bottom; the rest kept their order.
        assert [c.name for c in gs.players[0].library] == [
            "Forest", "Lightning Bolt", "Fireball",
        ]
        # The investigate token was created...
        tokens = _investigate_tokens(gs)
        assert len(tokens) == 1
        assert tokens[0].card.power == "1"
        assert tokens[0].card.toughness == "1"
        assert tokens[0].card.colors == ["R"]
        assert "investigate" in (tokens[0].card.keywords or [])
        # ...and the investigated trigger fired.
        assert _investigated_count(gs) == 1

        # Edge: empty library — no crash, token still created.
        gs.players[0].library = []
        gs = _investigate(gs, "Alice")
        assert len(_investigate_tokens(gs)) == 2
        assert _investigated_count(gs) == 2

    def test_investigate_spell_path_reminder_text_not_shadowed(self):
        """The canonical [[Investigate]] (M19) oracle text — the "Investigate."
        instruction plus the parenthetical reminder containing
        'create a 1/1 red Goblin creature token with "investigate."' — must
        resolve as an investigate action on the SPELL path, not as a plain
        create-token effect. The create-token pattern precedes the investigate
        pattern in _apply_spell_effect and used to match the reminder text
        first (shadowing the investigate match); reminder text is not rules
        text (CR 201.8) and is now stripped before matching."""
        gs = _make_gs()
        gs.battlefield.append(_perm("Watcher", "Whenever you investigate, draw a card."))
        # Top card is a land -> revealed & kept revealed (moved to hand).
        gs.players[0].library = [Card(name="Forest", type_line="Basic Land - Forest")]

        card = Card(
            name="Investigate",
            type_line="Sorcery",
            oracle_text=(
                "Investigate.\n"
                "(A player may pay {1} and sacrifice a creature to investigate. "
                "To investigate, look at the top card of your library. If it's a land, "
                "you may reveal it and keep it revealed. Otherwise, you may put it on "
                "the bottom of your library. Then create a 1/1 red Goblin creature "
                 'token with "investigate." Investigate tokens have "Whenever this '
                 'creature dies, exile it. If it\'s exiled this way, you may cast it '
                 'without paying its mana cost.")'
            ),
        )
        so = StackObject(source_card=card, controller="Alice")

        gs = _apply_spell_effect(gs, so)

        # The investigate token (with keyword + color), NOT a plain
        # colorless/keywordless token from _create_tokens.
        tokens = _investigate_tokens(gs)
        assert len(tokens) == 1, "expected the investigate token, not a plain token"
        token = tokens[0]
        assert token.card.power == "1"
        assert token.card.toughness == "1"
        assert token.card.colors == ["R"]
        assert "investigate" in (token.card.keywords or [])
        # The library interaction happened: land top card revealed -> in hand.
        assert [c.name for c in gs.players[0].library] == []
        assert [c.name for c in gs.players[0].hand] == ["Forest"]
        # Exactly ONE investigated trigger queued for the watcher.
        assert _investigated_count(gs) == 1

    def test_token_fallback_watcher_fires_exactly_once(self):
        """7-3 test round 1 regression: a token-fallback-phrased watcher
        ("whenever an investigate token enters the battlefield") must fire
        EXACTLY ONCE when a player investigates — via the generic
        token-trigger path only. Previously it double-fired (1x 'token' via
        check_token_triggers + 1x 'investigated' via the removed
        INVESTIGATED_TRIGGER_PATTERNS[2] fallback), drawing two cards for a
        one-fire ability. Also asserts a generic token watcher and an action
        watcher each fire exactly once (three distinct watchers, one fire
        each, no cross-firing)."""
        gs = _make_gs()
        fallback_watcher = _perm("FallbackWatcher",
                                 "Whenever an investigate token enters the battlefield, draw a card.")
        generic_watcher = _perm("GenericWatcher",
                                "Whenever a token enters the battlefield, draw a card.")
        action_watcher = _perm("ActionWatcher",
                               "Whenever you investigate, draw a card.")
        gs.battlefield.extend([fallback_watcher, generic_watcher, action_watcher])
        gs.players[0].library = [Card(name="Forest", type_line="Basic Land - Forest")]

        gs = _investigate(gs, "Alice")

        def _count(perm_id: str) -> int:
            return sum(1 for t in gs.pending_triggers if t.source_permanent_id == perm_id)

        # Each of the three distinct watchers fires exactly once...
        assert _count(fallback_watcher.id) == 1, (
            f"token-fallback watcher must fire exactly once, got {_count(fallback_watcher.id)}"
        )
        assert _count(generic_watcher.id) == 1, "generic token watcher must fire exactly once"
        assert _count(action_watcher.id) == 1, "action watcher must fire exactly once"
        # ...and the token-fallback watcher's single trigger is the 'token'
        # type (owned by the token path), not 'investigated'.
        fallback_types = [
            t.trigger_type for t in gs.pending_triggers
            if t.source_permanent_id == fallback_watcher.id
        ]
        assert fallback_types == ["token"]
        # Total: exactly 3 triggers from the 3 watchers (no duplicates, no
        # cross-firing between watchers).
        watcher_ids = {fallback_watcher.id, generic_watcher.id, action_watcher.id}
        watcher_triggers = [
            t for t in gs.pending_triggers if t.source_permanent_id in watcher_ids
        ]
        assert len(watcher_triggers) == 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
