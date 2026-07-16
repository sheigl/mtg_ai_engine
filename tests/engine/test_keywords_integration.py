"""
Integration tests for Kicker keyword (KW-16).
CR 702.33: Kicker is an additional optional cost that may be paid as the spell is cast.
"""
import pytest
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player
from mtg_engine.engine.mana import can_pay_cost
from mtg_engine.ability.keywords.kicker import Kicker
from mtg_engine.ability.keywords.flashback import Flashback
from mtg_engine.ability.keywords.escape import Escape
from mtg_engine.ability.keywords.delve import Delve


def _make_game(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-kicker",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_kicker_card() -> Card:
    """Create a test card with kicker keyword."""
    return Card(
        name="Burst Lightning",
        type_line="Instant",
        oracle_text="Kicker {4}\nBurst Lightning deals 2 damage to any target. If this spell was kicked, it deals 4 damage instead.",
        mana_cost="{R}",
        keywords=["kicker"],
    )


# Test 1: Kicker queues pending choice for human player
def test_kicker_queues_pending_choice_for_human():
    """Test that kicker queues pending_kicker_choice for human player."""
    gs = _make_game()
    gs.human_player_name = "p1"
    
    kicker_perm = Permanent(
        card=_make_kicker_card(),
        controller="p1",
    )
    
    kicker = Kicker()
    gs = kicker.apply(gs, kicker_perm)
    
    assert gs.pending_kicker_choice is not None
    assert gs.pending_kicker_choice["player"] == "p1"
    assert gs.pending_kicker_choice["card_name"] == "Burst Lightning"
    assert gs.pending_kicker_choice["kicker_cost"] == "{4}"
    assert gs.pending_kicker_choice["base_cost"] == "{R}"
    assert gs.pending_kicker_choice["resolved"] is False


# Test 2: AI auto-resolves kicker when mana is available
def test_ai_auto_resolves_kicker_when_mana_available():
    """Test that AI auto-resolves kicker when it can afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"
    
    kicker_card = _make_kicker_card()
    gs.players[1].hand.append(kicker_card)  # p2 (AI) has the card
    
    kicker_perm = Permanent(
        card=kicker_card,
        controller="p2",
    )
    
    # Give p2 enough mana to pay kicker cost ({4} = 4 generic)
    gs.players[1].mana_pool = ManaPool(C=4)
    
    kicker = Kicker()
    gs = kicker.apply(gs, kicker_perm)
    
    assert gs.pending_kicker_choice is not None
    assert gs.pending_kicker_choice["resolved"] is True
    assert gs.pending_kicker_choice["player"] == "p2"
    # Mana spent on kicker cost
    assert gs.players[1].mana_pool.C == 0


# Test 3: AI skips kicker when mana is not available
def test_ai_skips_kicker_when_mana_insufficient():
    """Test that AI skips kicker when it can't afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"
    
    kicker_card = _make_kicker_card()
    gs.players[1].hand.append(kicker_card)  # p2 (AI) has the card
    
    kicker_perm = Permanent(
        card=kicker_card,
        controller="p2",
    )
    
    # Give p2 only 3 generic mana (not enough for {4})
    gs.players[1].mana_pool = ManaPool(C=3)
    
    kicker = Kicker()
    gs = kicker.apply(gs, kicker_perm)
    
    assert gs.pending_kicker_choice is not None
    assert gs.pending_kicker_choice["resolved"] is True
    assert gs.pending_kicker_choice["player"] == "p2"
    # Mana NOT spent on kicker cost
    assert gs.players[1].mana_pool.C == 3


# Test 4: Pure transform — original GameState unchanged
def test_kicker_pure_transform():
    """Test that kicker.apply() returns a new GameState object (pure transform)."""
    gs = _make_game()
    gs.human_player_name = "p1"
    
    kicker_card = _make_kicker_card()
    gs.players[0].hand.append(kicker_card)
    
    kicker_perm = Permanent(
        card=kicker_card,
        controller="p1",
    )
    
    old_gs_id = id(gs)
    
    kicker = Kicker()
    new_gs = kicker.apply(gs, kicker_perm)
    
    assert id(new_gs) != old_gs_id  # New object returned


# Test 5: Kicker detection from oracle text
def test_kicker_detection_from_oracle():
    """Test that Kicker class can detect kicker from oracle text."""
    assert Kicker.from_oracle_text("Kicker {4}\nDeals 4 damage.") is True
    assert Kicker.from_oracle_text("This spell has kicker ability.") is True
    assert Kicker.from_oracle_text("") is False
    assert Kicker.from_oracle_text(None) is False


# Test 6: Kicker parse_kicker_cost
def test_kicker_parse_cost():
    """Test that Kicker class can parse kicker cost from oracle text."""
    assert Kicker.parse_kicker_cost("Kicker {4}") == "{4}"
    assert Kicker.parse_kicker_cost("Kicker {1}{U}") == "{1}{U}"
    assert Kicker.parse_kicker_cost("No kicker here") is None
    assert Kicker.parse_kicker_cost("") is None


# Test 7: Kicker has_kicker helper
def test_kicker_has_kicker():
    """Test Kicker.has_kicker helper."""
    assert Kicker.has_kicker(["kicker"]) is True
    assert Kicker.has_kicker(["flash", "haste"]) is False
    assert Kicker.has_kicker(["Kicker"]) is True  # Case insensitive


# Test 8: Kicker applies to permanent with kicker keyword
def test_kicker_applies_to_card():
    """Test that Kicker.applies() returns True for cards with kicker."""
    card = _make_kicker_card()
    kicker_perm = Permanent(
        card=card,
        controller="p1",
    )
    
    gs = _make_game()
    kicker = Kicker()
    assert kicker.applies(gs, kicker_perm) is True


# Test 9: Kicker apply returns game_state unchanged when no kicker text
def test_kicker_noop_when_no_kicker_text():
    """Test that kicker.apply() returns unchanged game_state when card has no kicker."""
    gs = _make_game()
    
    no_kicker_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_kicker_perm = Permanent(
        card=no_kicker_card,
        controller="p1",
    )
    
    old_gs_id = id(gs)
    kicker = Kicker()
    new_gs = kicker.apply(gs, no_kicker_perm)
    
    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_kicker_choice is None


# Test 10: Kicker with colored mana cost
def test_kicker_colored_mana_cost():
    """Test kicker with colored mana cost."""
    gs = _make_game()
    gs.human_player_name = "p1"
    
    kicker_card = Card(
        name="Kicker Spell",
        type_line="Instant",
        oracle_text="Kicker {1}{U}\nIf this spell was kicked, draw a card.",
        mana_cost="{1}{U}",
        keywords=["kicker"],
    )
    kicker_perm = Permanent(
        card=kicker_card,
        controller="p2",
    )
    
    # AI player (p2) has enough mana
    gs.players[1].mana_pool = ManaPool(U=1, C=1)
    
    kicker = Kicker()
    gs = kicker.apply(gs, kicker_perm)
    
    assert gs.pending_kicker_choice is not None
    assert gs.pending_kicker_choice["kicker_cost"] == "{1}{U}"
    assert gs.pending_kicker_choice["resolved"] is True
    # After paying {1}{U}, p2 should have 0 U and 0 C
    assert gs.players[1].mana_pool.U == 0
    assert gs.players[1].mana_pool.C == 0


# ============================================================
# KW-17: Flashback integration tests
# CR 702.34: Flashback lets you cast from graveyard for its
# flashback cost, then exile the card instead of any other zone.
# ============================================================


def _make_flashback_card() -> Card:
    """Create a test card with Flashback keyword."""
    return Card(
        name="Phantasmal Images",
        type_line="Sorcery",
        oracle_text="Flashback {2}{U}\nPhantasmal Images is a 2/2 blue creature with morph. You may cast Phantasmal Images from your graveyard for its flashback cost. If you do, it's exiled instead of put into any other zone.",
        mana_cost="{U}",
        keywords=["flashback"],
    )


def _make_flashback_colored_card() -> Card:
    """Create a test card with colored Flashback cost."""
    return Card(
        name="Ghostly Flicker",
        type_line="Instant",
        oracle_text="Flashback {2}{W}{U}\nYou may flashback this spell from your graveyard.",
        mana_cost="{U}",
        keywords=["flashback"],
    )


def _make_flashback_plain_card() -> Card:
    """Create a test card with plain flashback keyword (no cost in text)."""
    return Card(
        name="Shadow Step",
        type_line="Instant",
        oracle_text="Flashback\nYou may cast Shadow Step from your graveyard for its flashback cost.",
        mana_cost="{U}",
        keywords=["flashback"],
    )


# Test 11: Flashback queues pending exile choice for human player
def test_flashback_queues_pending_choice_for_human():
    """Test that Flashback queues pending_flashback_exile for human player."""
    gs = _make_game()
    gs.human_player_name = "p1"

    fb_perm = Permanent(
        card=_make_flashback_card(),
        controller="p1",
    )

    fb = Flashback()
    gs = fb.apply(gs, fb_perm)

    assert gs.pending_flashback_exile is not None
    assert gs.pending_flashback_exile["player"] == "p1"
    assert gs.pending_flashback_exile["card_name"] == "Phantasmal Images"
    assert gs.pending_flashback_exile["flashback_cost"] == "{2}{U}"
    assert gs.pending_flashback_exile["resolved"] is False


# Test 12: AI auto-resolves Flashback when mana is available (pays + exiles)
def test_ai_auto_resolves_flashback_when_mana_available():
    """Test that AI auto-resolves Flashback when it can afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"

    fb_card = _make_flashback_card()
    gs.players[1].hand.append(fb_card)  # p2 (AI) has the card

    fb_perm = Permanent(
        card=fb_card,
        controller="p2",
    )

    # Give p2 enough mana to pay Flashback cost ({2}{U} = 2 generic + 1 U)
    gs.players[1].mana_pool = ManaPool(C=2, U=1)

    fb = Flashback()
    gs = fb.apply(gs, fb_perm)

    assert gs.pending_flashback_exile is not None
    assert gs.pending_flashback_exile["resolved"] is True
    assert gs.pending_flashback_exile["player"] == "p2"
    # Mana spent on Flashback cost (2 C, 1 U)
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.U == 0


# Test 13: AI skips Flashback when mana is not available
def test_ai_skips_flashback_when_mana_insufficient():
    """Test that AI skips Flashback when it can't afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"

    fb_card = _make_flashback_card()
    gs.players[1].hand.append(fb_card)  # p2 (AI) has the card

    fb_perm = Permanent(
        card=fb_card,
        controller="p2",
    )

    # Give p2 only 1 generic mana (not enough for {2}{U})
    gs.players[1].mana_pool = ManaPool(C=1)

    fb = Flashback()
    gs = fb.apply(gs, fb_perm)

    assert gs.pending_flashback_exile is not None
    assert gs.pending_flashback_exile["resolved"] is True
    assert gs.pending_flashback_exile["player"] == "p2"
    # Mana NOT spent on Flashback cost
    assert gs.players[1].mana_pool.C == 1


# Test 14: Flashback pure transform — original GameState unchanged
def test_flashback_pure_transform():
    """Test that Flashback.apply() returns a new GameState object (pure transform)."""
    gs = _make_game()
    gs.human_player_name = "p1"

    fb_card = _make_flashback_card()
    gs.players[0].hand.append(fb_card)

    fb_perm = Permanent(
        card=fb_card,
        controller="p1",
    )

    old_gs_id = id(gs)

    fb = Flashback()
    new_gs = fb.apply(gs, fb_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 15: Flashback detection from oracle text
def test_flashback_detection_from_oracle():
    """Test that Flashback class can detect Flashback from oracle text."""
    assert Flashback.from_oracle_text("Flashback {2}{U}\n...") is True
    assert Flashback.from_oracle_text("Flashback\n...") is True
    assert Flashback.from_oracle_text("This spell has flashback ability.") is True
    assert Flashback.from_oracle_text("") is False
    assert Flashback.from_oracle_text(None) is False


# Test 16: Flashback parse_flashback_cost
def test_flashback_parse_cost():
    """Test that Flashback class can parse Flashback cost from oracle text."""
    assert Flashback.parse_flashback_cost("Flashback {2}{U}") == "{2}{U}"
    assert Flashback.parse_flashback_cost("Flashback {1}{W}{U}") == "{1}{W}{U}"
    assert Flashback.parse_flashback_cost("No flashback here") is None
    assert Flashback.parse_flashback_cost("") is None


# Test 17: Flashback has_flashback helper
def test_flashback_has_flashback():
    """Test Flashback.has_flashback helper."""
    assert Flashback.has_flashback(["flashback"]) is True
    assert Flashback.has_flashback(["haste", "flying"]) is False
    assert Flashback.has_flashback(["Flashback"]) is True  # Case insensitive


# Test 18: Flashback applies to permanent with Flashback keyword
def test_flashback_applies_to_card():
    """Test that Flashback.applies() returns True for cards with Flashback."""
    card = _make_flashback_card()
    fb_perm = Permanent(
        card=card,
        controller="p1",
    )

    gs = _make_game()
    fb = Flashback()
    assert fb.applies(gs, fb_perm) is True


# Test 19: Flashback apply returns game_state unchanged when no Flashback text
def test_flashback_noop_when_no_flashback_text():
    """Test that Flashback.apply() returns unchanged game_state when card has no Flashback."""
    gs = _make_game()

    no_fb_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_fb_perm = Permanent(
        card=no_fb_card,
        controller="p1",
    )

    old_gs_id = id(gs)
    fb = Flashback()
    new_gs = fb.apply(gs, no_fb_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_flashback_exile is None


# Test 20: Flashback with plain "Flashback" keyword (no explicit cost in text)
def test_flashback_plain_keyword():
    """Test Flashback detection from plain keyword text."""
    assert Flashback.from_oracle_text("Flashback") is True
    assert Flashback.from_oracle_text("Flashback\n...") is True
    assert Flashback.parse_flashback_cost("Flashback") is None  # No cost specified


# ============================================================
# KW-18: Escape integration tests
# CR 702.45: Escape lets you cast a legendary card from exile
# by paying its escape cost, exiling N other cards from your graveyard.
# ============================================================


def _make_escape_card() -> Card:
    """Create a test card with Escape keyword."""
    return Card(
        name="Gaddock Teeg",
        type_line="Creature — Human Wizard",
        oracle_text="Escape {3}{B}\nEscape 3 other cards from your graveyard: Cast Gaddock Teeg from your graveyard. If you cast it this way, it exiles on leaving the battlefield.",
        mana_cost="{B}",
        keywords=["escape"],
    )


def _make_escape_colored_card() -> Card:
    """Create a test card with colored Escape cost."""
    return Card(
        name="Umbra Stalker",
        type_line="Creature — Zombie Horror",
        oracle_text="Escape {1}{B}{G}\nEscape 3 other cards from your graveyard: Cast Umbra Stalker from your graveyard. If you cast it this way, it exiles on leaving the battlefield.",
        mana_cost="{B}",
        keywords=["escape"],
    )


def _make_escape_plain_card() -> Card:
    """Create a test card with plain Escape keyword (no explicit cost)."""
    return Card(
        name="Teferi's Protection",
        type_line="Instant",
        oracle_text="Escape\nTeferi's Protection counters target instant or sorcery spell.",
        mana_cost="{U}",
        keywords=["escape"],
    )


# Test 21: Escape queues pending exile choice for human player
def test_escape_queues_pending_choice_for_human():
    """Test that Escape queues pending_escape_exile for human player."""
    gs = _make_game()
    gs.human_player_name = "p1"

    escape_perm = Permanent(
        card=_make_escape_card(),
        controller="p1",
    )

    escape = Escape()
    gs = escape.apply(gs, escape_perm)

    assert gs.pending_escape_exile is not None
    assert gs.pending_escape_exile["player"] == "p1"
    assert gs.pending_escape_exile["card_name"] == "Gaddock Teeg"
    assert gs.pending_escape_exile["escape_cost"] == "{3}{B}"
    assert gs.pending_escape_exile["exile_count"] == 3
    assert gs.pending_escape_exile["resolved"] is False


# Test 22: AI auto-resolves Escape when mana is available (pays cost)
def test_ai_auto_resolves_escape_when_mana_available():
    """Test that AI auto-resolves Escape when it can afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"

    escape_card = _make_escape_card()
    gs.players[1].hand.append(escape_card)  # p2 (AI) has the card

    escape_perm = Permanent(
        card=escape_card,
        controller="p2",
    )

    # Give p2 enough mana to pay Escape cost ({3}{B} = 3 generic + 1 B)
    gs.players[1].mana_pool = ManaPool(C=3, B=1)

    escape = Escape()
    gs = escape.apply(gs, escape_perm)

    assert gs.pending_escape_exile is not None
    assert gs.pending_escape_exile["resolved"] is True
    assert gs.pending_escape_exile["player"] == "p2"
    # Mana spent on Escape cost (3 C, 1 B)
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.B == 0


# Test 23: AI skips Escape when mana is not available
def test_ai_skips_escape_when_mana_insufficient():
    """Test that AI skips Escape when it can't afford the cost."""
    gs = _make_game()
    gs.human_player_name = "p1"

    escape_card = _make_escape_card()
    gs.players[1].hand.append(escape_card)  # p2 (AI) has the card

    escape_perm = Permanent(
        card=escape_card,
        controller="p2",
    )

    # Give p2 only 2 generic mana (not enough for {3}{B})
    gs.players[1].mana_pool = ManaPool(C=2)

    escape = Escape()
    gs = escape.apply(gs, escape_perm)

    assert gs.pending_escape_exile is not None
    assert gs.pending_escape_exile["resolved"] is True
    assert gs.pending_escape_exile["player"] == "p2"
    # Mana NOT spent on Escape cost
    assert gs.players[1].mana_pool.C == 2


# Test 24: Escape pure transform — original GameState unchanged
def test_escape_pure_transform():
    """Test that Escape.apply() returns a new GameState object (pure transform)."""
    gs = _make_game()
    gs.human_player_name = "p1"

    escape_card = _make_escape_card()
    gs.players[0].hand.append(escape_card)

    escape_perm = Permanent(
        card=escape_card,
        controller="p1",
    )

    old_gs_id = id(gs)

    escape = Escape()
    new_gs = escape.apply(gs, escape_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 25: Escape detection from oracle text
def test_escape_detection_from_oracle():
    """Test that Escape class can detect Escape from oracle text."""
    assert Escape.from_oracle_text("Escape {3}{B}\n...") is True
    assert Escape.from_oracle_text("Escape\n...") is True
    assert Escape.from_oracle_text("This spell has escape ability.") is True
    assert Escape.from_oracle_text("") is False
    assert Escape.from_oracle_text(None) is False


# Test 26: Escape parse_escape_cost
def test_escape_parse_cost():
    """Test that Escape class can parse Escape cost from oracle text."""
    assert Escape.parse_escape_cost("Escape {3}{B}") == "{3}{B}"
    assert Escape.parse_escape_cost("Escape {1}{B}{G}") == "{1}{B}{G}"
    assert Escape.parse_escape_cost("No escape here") is None
    assert Escape.parse_escape_cost("") is None


# Test 27: Escape has_escape helper
def test_escape_has_escape():
    """Test Escape.has_escape helper."""
    assert Escape.has_escape(["escape"]) is True
    assert Escape.has_escape(["haste", "flying"]) is False
    assert Escape.has_escape(["Escape"]) is True  # Case insensitive


# Test 28: Escape applies to permanent with Escape keyword
def test_escape_applies_to_card():
    """Test that Escape.applies() returns True for cards with Escape."""
    card = _make_escape_card()
    escape_perm = Permanent(
        card=card,
        controller="p1",
    )

    gs = _make_game()
    escape = Escape()
    assert escape.applies(gs, escape_perm) is True


# Test 29: Escape apply returns game_state unchanged when no Escape text
def test_escape_noop_when_no_escape_text():
    """Test that Escape.apply() returns unchanged game_state when card has no Escape."""
    gs = _make_game()

    no_escape_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_escape_perm = Permanent(
        card=no_escape_card,
        controller="p1",
    )

    old_gs_id = id(gs)
    escape = Escape()
    new_gs = escape.apply(gs, no_escape_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_escape_exile is None


# Test 30: Escape with plain "Escape" keyword (no explicit cost in text)
def test_escape_plain_keyword():
    """Test Escape detection from plain keyword text."""
    assert Escape.from_oracle_text("Escape") is True
    assert Escape.from_oracle_text("Escape\n...") is True
    assert Escape.parse_escape_cost("Escape") is None  # No cost specified


# Test 31: Escape with colored mana cost
def test_escape_colored_mana_cost():
    """Test Escape with colored mana cost."""
    gs = _make_game()
    gs.human_player_name = "p1"

    escape_card = _make_escape_colored_card()
    escape_perm = Permanent(
        card=escape_card,
        controller="p2",
    )

    # AI player (p2) has enough mana ({1}{B}{G} = 1 generic + 1 B + 1 G)
    gs.players[1].mana_pool = ManaPool(C=1, B=1, G=1)

    escape = Escape()
    gs = escape.apply(gs, escape_perm)

    assert gs.pending_escape_exile is not None
    assert gs.pending_escape_exile["escape_cost"] == "{1}{B}{G}"
    assert gs.pending_escape_exile["resolved"] is True
    # After paying {1}{B}{G}, p2 should have 0 C, 0 B, 0 G
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.B == 0
    assert gs.players[1].mana_pool.G == 0


# ─── Delve keyword tests (KW-19) ─────────────────────────────────────────────

def _make_game_for_delve(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state for Delve tests."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-delve",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_delve_card() -> Card:
    """Create a test card with Delve keyword."""
    return Card(
        name="Delve Spell",
        type_line="Sorcery",
        oracle_text="Delve {2}{U}\nExile a card from your graveyard: Cast Delve Spell without paying its mana cost.",
        mana_cost="{2}{U}",
        keywords=["delve"],
    )


def _make_delve_card_no_count() -> Card:
    """Create a test card with Delve but no specific count."""
    return Card(
        name="Delve Spell No Count",
        type_line="Sorcery",
        oracle_text="Delve\nExile a card from your graveyard: Cast Delve Spell without paying its mana cost.",
        mana_cost="{2}",
        keywords=["delve"],
    )


def test_delve_queues_pending_choice_for_human():
    """Test that Delve queues pending_delve_choice for human player."""
    gs = _make_game_for_delve()
    gs.human_player_name = "p1"

    delve_card = _make_delve_card()
    delve_perm = Permanent(
        card=delve_card,
        controller="p1",
    )

    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert gs.pending_delve_choice is not None
    assert gs.pending_delve_choice["player"] == "p1"
    assert gs.pending_delve_choice["card_id"] == delve_card.id
    assert gs.pending_delve_choice["card_name"] == "Delve Spell"
    assert gs.pending_delve_choice["delve_cost"] == "{2}{U}"
    assert gs.pending_delve_choice["cards_to_exile"] == 2  # generic cost = 2
    assert gs.pending_delve_choice["resolved"] is False


def test_ai_auto_resolves_delve_when_graveyard_has_cards():
    """Test that AI auto-resolves Delve when graveyard has enough cards."""
    gs = _make_game_for_delve()

    delve_card = _make_delve_card()
    gs.players[1].graveyard = [
        Card(name="Old Card 1", type_line="Instant"),
        Card(name="Old Card 2", type_line="Instant"),
        Card(name="Old Card 3", type_line="Instant"),
    ]

    delve_perm = Permanent(
        card=delve_card,
        controller="p2",
    )

    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert gs.pending_delve_choice is not None
    assert gs.pending_delve_choice["player"] == "p2"
    assert gs.pending_delve_choice["delve_cost"] == "{2}{U}"
    assert gs.pending_delve_choice["cards_to_exile"] == 2  # generic cost = 2
    assert gs.pending_delve_choice["resolved"] is True
    # AI selects the oldest 2 cards
    assert len(gs.pending_delve_choice["card_ids"]) == 2
    assert gs.pending_delve_choice["card_ids"][0] == gs.players[1].graveyard[0].id
    assert gs.pending_delve_choice["card_ids"][1] == gs.players[1].graveyard[1].id


def test_ai_skips_delve_when_graveyard_empty():
    """Test that AI skips Delve when graveyard is empty."""
    gs = _make_game_for_delve()
    # Ensure graveyard is empty

    delve_card = _make_delve_card()
    delve_perm = Permanent(
        card=delve_card,
        controller="p2",
    )

    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert gs.pending_delve_choice is not None
    assert gs.pending_delve_choice["player"] == "p2"
    assert gs.pending_delve_choice["cards_to_exile"] == 0
    assert gs.pending_delve_choice["resolved"] is True
    assert gs.pending_delve_choice["card_ids"] == []


def test_delve_pure_transform():
    """Test that Delve.apply() returns a new GameState object."""
    gs = _make_game_for_delve()
    gs.human_player_name = "p1"

    delve_card = _make_delve_card()
    delve_perm = Permanent(
        card=delve_card,
        controller="p1",
    )

    old_id = id(gs)
    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert id(gs) != old_id


def test_delve_detection_from_oracle():
    """Test Delve detection from oracle text."""
    assert Delve.from_oracle_text("Delve {2}{U}\nExile a card from your graveyard") is True
    assert Delve.from_oracle_text("Delve\n...") is True
    assert Delve.from_oracle_text("Flashback\n...") is False


def test_delve_parse_cost():
    """Test Delve cost parsing."""
    assert Delve.parse_delve_cost("Delve {2}{U}\n...") == "{2}{U}"
    assert Delve.parse_delve_cost("Delve {3}\n...") == "{3}"
    assert Delve.parse_delve_cost("Delve {1}{B}\n...") == "{1}{B}"
    assert Delve.parse_delve_cost("Flashback") is None


def test_delve_parse_count():
    """Test Delve count parsing."""
    assert Delve.parse_delve_count("Exile 1 card from your graveyard") == 1
    assert Delve.parse_delve_count("Exile 3 cards from your graveyard") == 3
    assert Delve.parse_delve_count("Exile two cards from your graveyard") == 2


def test_delve_has_delve():
    """Test Delve has_delve helper."""
    assert Delve.has_delve(["delve", "flashback"]) is True
    assert Delve.has_delve(["flashback", "kicker"]) is False


def test_delve_applies_to_card():
    """Test that Delve applies to cards with Delve keyword."""
    gs = _make_game_for_delve()
    delve_card = _make_delve_card()
    delve_perm = Permanent(card=delve_card, controller="p1")

    assert Delve().applies(gs, delve_perm) is True


def test_delve_noop_when_no_delve_text():
    """Test that Delve is a no-op for cards without Delve text."""
    gs = _make_game_for_delve()
    gs.human_player_name = "p1"

    non_delve_card = Card(
        name="Normal Spell",
        type_line="Sorcery",
        oracle_text="This spell does something else.",
        mana_cost="{2}{U}",
    )
    non_delve_perm = Permanent(
        card=non_delve_card,
        controller="p1",
    )

    delve = Delve()
    gs = delve.apply(gs, non_delve_perm)

    assert gs.pending_delve_choice is None


def test_delve_with_only_generic_cost():
    """Test Delve with only generic mana cost."""
    gs = _make_game_for_delve()
    gs.human_player_name = "p1"

    delve_card = _make_delve_card_no_count()
    delve_perm = Permanent(
        card=delve_card,
        controller="p1",
    )

    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert gs.pending_delve_choice is not None
    assert gs.pending_delve_choice["delve_cost"] is None  # No cost specified
    assert gs.pending_delve_choice["cards_to_exile"] == 2  # Default to generic cost


def test_delve_ai_exiles_max_available():
    """Test that AI exiles up to the number available in graveyard."""
    gs = _make_game_for_delve()

    # Only 1 card in graveyard, but cost is 2
    gs.players[1].graveyard = [
        Card(name="Old Card 1", type_line="Instant"),
    ]

    delve_card = _make_delve_card()
    delve_perm = Permanent(
        card=delve_card,
        controller="p2",
    )

    delve = Delve()
    gs = delve.apply(gs, delve_perm)

    assert gs.pending_delve_choice is not None
    assert gs.pending_delve_choice["cards_to_exile"] == 1  # Only 1 available
    assert gs.pending_delve_choice["resolved"] is True
    assert len(gs.pending_delve_choice["card_ids"]) == 1


# ============================================================
# KW-20: Cascade integration tests
# CR 702.85: Exile cards from library top until finding nonland
# card with CMC < cascade spell's CMC. Cast it for free or exile.
# ============================================================

from mtg_engine.ability.keywords.cascade import (
    apply_cascade,
    resolve_cascade_cast,
    resolve_cascade_exile,
)


def _make_game_for_cascade(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state for Cascade tests."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-cascade",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_cascade_card(cmc: float = 3.0) -> Card:
    """Create a test card with Cascade keyword."""
    return Card(
        name="Lightning Helix",
        type_line="Instant — Arc Lightning",
        oracle_text="Cascade\nDeal 3 damage to any target.",
        mana_cost="{2}{R}",
        keywords=["cascade"],
        cmc=cmc,
    )


def _make_low_cmc_card(cmc: float = 1.0) -> Card:
    """Create a low-CMC nonland card for cascade to find."""
    return Card(
        name="Flicker of Fate",
        type_line="Instant",
        oracle_text="Exile target creature, then return it to the battlefield.",
        mana_cost="{U}",
        cmc=cmc,
    )


def _make_land_card() -> Card:
    """Create a land card that cascade skips."""
    return Card(
        name="Island",
        type_line="Basic Land — Island",
        oracle_text="{T}: Add {U}.",
        cmc=0.0,
    )


# Test 32: Cascade queues pending choice for human player when card found
def test_cascade_queues_pending_choice_for_human():
    """Test that cascade exiles cards and queues a choice for the human."""
    gs = _make_game_for_cascade()
    gs.human_player_name = "p1"

    # Library: land (skipped), then low-CMC card (found)
    gs.players[0].library = [
        _make_land_card(),
        _make_low_cmc_card(cmc=1.0),
    ]

    gs = apply_cascade(gs, "p1", cascade_cmc=3)

    assert gs.pending_cascade is not None
    assert gs.pending_cascade["player"] == "p1"
    assert gs.pending_cascade["found_card"]["name"] == "Flicker of Fate"
    assert gs.pending_cascade["cascade_cmc"] == 3
    # Library should be empty (both cards exiled)
    assert len(gs.players[0].library) == 0
    # One land card in exiled_cards list
    assert len(gs.pending_cascade["exiled_cards"]) == 1


# Test 33: AI auto-resolves cascade by casting the found card for free
def test_ai_auto_resolves_cascade_casts_found_card():
    """Test that AI casts the cascading card and puts exiled on bottom."""
    gs = _make_game_for_cascade()
    # p2 is AI (not human_player_name)

    # Library: land, then low-CMC card
    gs.players[1].library = [
        _make_land_card(),
        _make_low_cmc_card(cmc=2.0),
    ]

    old_stack_len = len(gs.stack)
    gs = apply_cascade(gs, "p2", cascade_cmc=4)

    # No pending choice for AI (auto-resolved)
    assert gs.pending_cascade is None
    # Found card added to stack as free spell
    assert len(gs.stack) == old_stack_len + 1
    new_spell = gs.stack[-1]
    assert new_spell.source_card.name == "Flicker of Fate"
    assert new_spell.controller == "p2"
    assert new_spell.metadata.get("cascade_cast") is True
    # Exiled land card put on bottom of library
    assert len(gs.players[1].library) == 1
    assert gs.players[1].library[0].name == "Island"


# Test 34: Cascade when no valid card found (all lands or high CMC)
def test_cascade_no_valid_card_found():
    """Test cascade when library has only lands/high-CMC cards."""
    gs = _make_game_for_cascade()

    # Library: all lands and a high-CMC card (CMC 5 >= cascade_cmc 3)
    gs.players[0].library = [
        _make_land_card(),
        Card(name="Big Spell", type_line="Sorcery", cmc=5.0),
    ]

    original_lib_len = len(gs.players[0].library)
    gs = apply_cascade(gs, "p1", cascade_cmc=3)

    # No pending choice (nothing found)
    assert gs.pending_cascade is None
    # All exiled cards go back to bottom of library
    assert len(gs.players[0].library) == original_lib_len


# Test 35: Cascade pure transform — original GameState unchanged
def test_cascade_pure_transform():
    """Test that apply_cascade returns a new GameState object."""
    gs = _make_game_for_cascade()
    gs.human_player_name = "p1"

    gs.players[0].library = [
        _make_low_cmc_card(cmc=1.0),
    ]

    old_id = id(gs)
    new_gs = apply_cascade(gs, "p1", cascade_cmc=3)

    assert id(new_gs) != old_id


# Test 36: resolve_cascade_cast puts found card on stack and clears pending
def test_resolve_cascade_cast():
    """Test that resolving 'cast' choice puts the card on the stack."""
    gs = _make_game_for_cascade()
    gs.human_player_name = "p1"

    # Set up a pending cascade manually (simulating apply_cascade result)
    found_card = _make_low_cmc_card(cmc=1.0)
    exiled_land = _make_land_card()
    gs.pending_cascade = {
        "player": "p1",
        "found_card": found_card.model_dump(),
        "exiled_cards": [exiled_land.model_dump()],
        "cascade_cmc": 3,
    }

    old_stack_len = len(gs.stack)
    gs = resolve_cascade_cast(gs)

    assert gs.pending_cascade is None
    # Found card on stack
    assert len(gs.stack) == old_stack_len + 1
    assert gs.stack[-1].source_card.name == "Flicker of Fate"
    # Exiled cards on bottom of library
    assert len(gs.players[0].library) == 1


# Test 37: resolve_cascade_exile keeps found card exiled and clears pending
def test_resolve_cascade_exile():
    """Test that resolving 'exile' choice keeps the card exiled."""
    gs = _make_game_for_cascade()
    gs.human_player_name = "p1"

    found_card = _make_low_cmc_card(cmc=1.0)
    exiled_land = _make_land_card()
    gs.pending_cascade = {
        "player": "p1",
        "found_card": found_card.model_dump(),
        "exiled_cards": [exiled_land.model_dump()],
        "cascade_cmc": 3,
    }

    old_exile_len = len(gs.players[0].exile)
    gs = resolve_cascade_exile(gs)

    assert gs.pending_cascade is None
    # Found card stays exiled
    assert len(gs.players[0].exile) == old_exile_len + 1
    assert gs.players[0].exile[-1].name == "Flicker of Fate"
    # Other exiled cards on bottom of library
    assert len(gs.players[0].library) == 1


# ============================================================
# KW-21: Storm integration tests
# CR 702.90a: Copy the spell N times where N = spells cast this turn - 1.
# ============================================================

from mtg_engine.ability.keywords.storm import create_storm_copies, get_storm_count


def _make_game_for_storm(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state for Storm tests."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-storm",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_storm_card() -> Card:
    """Create a test card with Storm keyword."""
    return Card(
        name="Tidecaller's Blessing",
        type_line="Sorcery — Control Weather",
        oracle_text="Storm\nDraw two cards.",
        mana_cost="{2}{U}",
        keywords=["storm"],
        cmc=3.0,
    )


# Test 38: Storm creates correct number of copies based on spells cast
def test_storm_creates_copies_from_spell_count():
    """Test that storm creates N-1 copies where N = spells_cast_this_turn."""
    gs = _make_game_for_storm()

    # Add a storm spell to the stack
    storm_card = _make_storm_card()
    from mtg_engine.models.game import StackObject as SO
    original = SO(source_card=storm_card, controller="p1")
    gs.stack.append(original)

    old_id = original.id
    # 4 spells cast this turn → 3 copies
    gs.spells_cast_this_turn = 4

    old_stack_len = len(gs.stack)
    gs = create_storm_copies(gs, "p1", old_id)

    assert len(gs.stack) == old_stack_len + 3  # 3 storm copies
    # All copies are marked as is_copy=True
    for i in range(1, 4):
        assert gs.stack[-i].is_copy is True
        assert gs.stack[-i].source_card.name == "Tidecaller's Blessing"


# Test 39: Storm creates zero copies when only one spell cast this turn
def test_storm_zero_copies_when_first_spell():
    """Test that storm creates no copies if it's the first spell of the turn."""
    gs = _make_game_for_storm()

    storm_card = _make_storm_card()
    from mtg_engine.models.game import StackObject as SO
    original = SO(source_card=storm_card, controller="p1")
    gs.stack.append(original)

    old_id = original.id
    gs.spells_cast_this_turn = 1  # Only this spell cast

    old_stack_len = len(gs.stack)
    gs = create_storm_copies(gs, "p1", old_id)

    assert len(gs.stack) == old_stack_len  # No copies created


# Test 40: Storm pure transform — original GameState unchanged
def test_storm_pure_transform():
    """Test that create_storm_copies returns a new GameState object."""
    gs = _make_game_for_storm()

    storm_card = _make_storm_card()
    from mtg_engine.models.game import StackObject as SO
    original = SO(source_card=storm_card, controller="p1")
    gs.stack.append(original)

    old_id = original.id
    gs.spells_cast_this_turn = 3

    old_gs_id = id(gs)
    new_gs = create_storm_copies(gs, "p1", old_id)

    assert id(new_gs) != old_gs_id


# Test 41: Storm copies are in LIFO order (last copy added resolves first)
def test_storm_copies_lifo_order():
    """Test that storm copies are appended to stack so last one resolves first."""
    gs = _make_game_for_storm()

    storm_card = _make_storm_card()
    from mtg_engine.models.game import StackObject as SO
    original = SO(source_card=storm_card, controller="p1")
    gs.stack.append(original)

    old_id = original.id
    gs.spells_cast_this_turn = 3  # 2 copies

    gs = create_storm_copies(gs, "p1", old_id)

    # Original is at index 0, copies at indices 1 and 2
    assert len(gs.stack) == 3
    assert not gs.stack[0].is_copy  # Original
    assert gs.stack[1].is_copy      # Copy 0 (added first, resolves second)
    assert gs.stack[2].is_copy      # Copy 1 (added last, resolves first)


# Test 42: get_storm_count helper returns correct values
def test_get_storm_count():
    """Test the storm count helper function."""
    gs = _make_game_for_storm()

    assert get_storm_count(gs) == 0       # 0 spells → 0 copies
    gs.spells_cast_this_turn = 1
    assert get_storm_count(gs) == 0       # 1 spell → 0 copies
    gs.spells_cast_this_turn = 5
    assert get_storm_count(gs) == 4       # 5 spells → 4 copies


# Test 43: Storm handles missing stack object gracefully
def test_storm_missing_stack_object():
    """Test that storm returns unchanged state when source not found."""
    gs = _make_game_for_storm()
    gs.spells_cast_this_turn = 5

    old_id = id(gs)
    new_gs = create_storm_copies(gs, "p1", "nonexistent-id")

    # Returns a copy (pure transform), but no copies added
    assert len(new_gs.stack) == 0


# ============================================================
# KW-22: Madness integration tests
# CR 702.35: When you would discard a card with madness, you may
# reveal it and pay its madness cost. If you do, exile it instead of
# discarding it. You may cast the card this turn.
# ============================================================

from mtg_engine.ability.keywords.madness import Madness


def _make_game_for_madness(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state for Madness tests."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-madness",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_madness_card() -> Card:
    """Create a test card with Madness keyword."""
    return Card(
        name="Madness Spell",
        type_line="Sorcery",
        oracle_text="Madness {1}{U}\nDraw two cards.",
        mana_cost="{2}{U}",
        keywords=["madness"],
    )


def _make_madness_colored_card() -> Card:
    """Create a test card with colored Madness cost."""
    return Card(
        name="Madness Instant",
        type_line="Instant",
        oracle_text="Madness {2}{R}\nDeal 3 damage to any target.",
        mana_cost="{1}{R}",
        keywords=["madness"],
    )


# Test 44: Madness queues pending choice for human player
def test_madness_queues_pending_choice_for_human():
    """Test that Madness queues pending_madness_choice for human player."""
    gs = _make_game_for_madness()
    gs.human_player_name = "p1"

    madness_perm = Permanent(
        card=_make_madness_card(),
        controller="p1",
    )

    madness = Madness()
    gs = madness.apply(gs, madness_perm)

    assert gs.pending_madness_choice is not None
    assert gs.pending_madness_choice["player"] == "p1"
    assert gs.pending_madness_choice["card_name"] == "Madness Spell"
    assert gs.pending_madness_choice["madness_cost"] == "{1}{U}"
    assert gs.pending_madness_choice["resolved"] is False


# Test 45: AI auto-resolves Madness when mana is available (pays + exiles)
def test_ai_auto_resolves_madness_when_mana_available():
    """Test that AI auto-resolves Madness when it can afford the cost."""
    gs = _make_game_for_madness()
    gs.human_player_name = "p1"

    madness_card = _make_madness_card()
    gs.players[1].hand.append(madness_card)  # p2 (AI) has the card

    madness_perm = Permanent(
        card=madness_card,
        controller="p2",
    )

    # Give p2 enough mana to pay Madness cost ({1}{U} = 1 generic + 1 U)
    gs.players[1].mana_pool = ManaPool(C=1, U=1)

    madness = Madness()
    gs = madness.apply(gs, madness_perm)

    assert gs.pending_madness_choice is not None
    assert gs.pending_madness_choice["resolved"] is True
    assert gs.pending_madness_choice["player"] == "p2"
    # Mana spent on Madness cost (1 C, 1 U)
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.U == 0


# Test 46: AI skips Madness when mana is not available
def test_ai_skips_madness_when_mana_insufficient():
    """Test that AI skips Madness when it can't afford the cost."""
    gs = _make_game_for_madness()
    gs.human_player_name = "p1"

    madness_card = _make_madness_card()
    gs.players[1].hand.append(madness_card)  # p2 (AI) has the card

    madness_perm = Permanent(
        card=madness_card,
        controller="p2",
    )

    # Give p2 only 1 generic mana (not enough for {1}{U})
    gs.players[1].mana_pool = ManaPool(C=1)

    madness = Madness()
    gs = madness.apply(gs, madness_perm)

    assert gs.pending_madness_choice is not None
    assert gs.pending_madness_choice["resolved"] is True
    assert gs.pending_madness_choice["player"] == "p2"
    # Mana NOT spent on Madness cost
    assert gs.players[1].mana_pool.C == 1


# Test 47: Madness pure transform — original GameState unchanged
def test_madness_pure_transform():
    """Test that Madness.apply() returns a new GameState object (pure transform)."""
    gs = _make_game_for_madness()
    gs.human_player_name = "p1"

    madness_card = _make_madness_card()
    gs.players[0].hand.append(madness_card)

    madness_perm = Permanent(
        card=madness_card,
        controller="p1",
    )

    old_gs_id = id(gs)

    madness = Madness()
    new_gs = madness.apply(gs, madness_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 48: Madness detection from oracle text
def test_madness_detection_from_oracle():
    """Test that Madness class can detect Madness from oracle text."""
    assert Madness.from_oracle_text("Madness {1}{U}\n...") is True
    assert Madness.from_oracle_text("Madness\n...") is True
    assert Madness.from_oracle_text("This spell has madness ability.") is True
    assert Madness.from_oracle_text("") is False
    assert Madness.from_oracle_text(None) is False


# Test 49: Madness parse_madness_cost
def test_madness_parse_cost():
    """Test that Madness class can parse Madness cost from oracle text."""
    assert Madness.parse_madness_cost("Madness {1}{U}") == "{1}{U}"
    assert Madness.parse_madness_cost("Madness {2}{R}") == "{2}{R}"
    assert Madness.parse_madness_cost("No madness here") is None
    assert Madness.parse_madness_cost("") is None


# Test 50: Madness has_madness helper
def test_madness_has_madness():
    """Test Madness.has_madness helper."""
    assert Madness.has_madness(["madness"]) is True
    assert Madness.has_madness(["haste", "flying"]) is False
    assert Madness.has_madness(["Madness"]) is True  # Case insensitive


# Test 51: Madness applies to permanent with Madness keyword
def test_madness_applies_to_card():
    """Test that Madness.applies() returns True for cards with Madness."""
    card = _make_madness_card()
    madness_perm = Permanent(
        card=card,
        controller="p1",
    )

    gs = _make_game_for_madness()
    madness = Madness()
    assert madness.applies(gs, madness_perm) is True


# Test 52: Madness apply returns game_state unchanged when no Madness text
def test_madness_noop_when_no_madness_text():
    """Test that Madness.apply() returns unchanged game_state when card has no Madness."""
    gs = _make_game_for_madness()

    no_madness_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_madness_perm = Permanent(
        card=no_madness_card,
        controller="p1",
    )

    old_gs_id = id(gs)
    madness = Madness()
    new_gs = madness.apply(gs, no_madness_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_madness_choice is None


# Test 53: Madness with colored mana cost
def test_madness_colored_mana_cost():
    """Test Madness with colored mana cost."""
    gs = _make_game_for_madness()
    gs.human_player_name = "p1"

    madness_card = _make_madness_colored_card()
    madness_perm = Permanent(
        card=madness_card,
        controller="p2",
    )

    # AI player (p2) has enough mana ({2}{R} = 2 generic + 1 R)
    gs.players[1].mana_pool = ManaPool(C=2, R=1)

    madness = Madness()
    gs = madness.apply(gs, madness_perm)

    assert gs.pending_madness_choice is not None
    assert gs.pending_madness_choice["madness_cost"] == "{2}{R}"
    assert gs.pending_madness_choice["resolved"] is True
    # After paying {2}{R}, p2 should have 0 C and 0 R
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.R == 0


# ============================================================
# KW-23: Dredge integration tests
# CR 702.60: When you would draw a card with dredge N, instead put the
# top N cards of your library on top in any order and return this card
# from your graveyard to your hand.
# ============================================================

from mtg_engine.ability.keywords.dredge import Dredge


def _make_game_for_dredge(player_names=("p1", "p2")) -> GameState:
    """Create a minimal test game state for Dredge tests."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-dredge",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0] if len(player_names) == 2 else None,
    )


def _make_dredge_card() -> Card:
    """Create a test card with Dredge keyword."""
    return Card(
        name="Dredge Spell",
        type_line="Sorcery",
        oracle_text="Dredge 3\nWhen you dredge this card, put the top three cards of your library on top in any order.",
        mana_cost="{B}",
        keywords=["dredge"],
    )


def _make_dredge_card_n2() -> Card:
    """Create a test card with Dredge 2."""
    return Card(
        name="Dredge Two",
        type_line="Instant",
        oracle_text="Dredge 2\nWhen you dredge this card, put the top two cards of your library on top.",
        mana_cost="{1}{B}",
        keywords=["dredge"],
    )


# Test 54: Dredge queues pending choice for human player
def test_dredge_queues_pending_choice_for_human():
    """Test that Dredge queues pending_dredge_choice for human player."""
    gs = _make_game_for_dredge()
    gs.human_player_name = "p1"

    dredge_perm = Permanent(
        card=_make_dredge_card(),
        controller="p1",
    )

    dredge = Dredge()
    gs = dredge.apply(gs, dredge_perm)

    assert gs.pending_dredge_choice is not None
    assert gs.pending_dredge_choice["player"] == "p1"
    assert gs.pending_dredge_choice["card_name"] == "Dredge Spell"
    assert gs.pending_dredge_choice["dredge_n"] == 3
    assert gs.pending_dredge_choice["resolved"] is False


# Test 55: AI auto-resolves Dredge when library has enough cards (returns to hand)
def test_ai_auto_resolves_dredge_when_library_has_cards():
    """Test that AI auto-resolves Dredge when library has enough cards."""
    gs = _make_game_for_dredge()
    gs.human_player_name = "p1"

    dredge_card = _make_dredge_card_n2()  # Dredge 2
    gs.players[1].library = [
        Card(name="Card A", type_line="Instant"),
        Card(name="Card B", type_line="Sorcery"),
        Card(name="Card C", type_line="Creature"),
    ]

    dredge_perm = Permanent(
        card=dredge_card,
        controller="p2",
    )

    hand_before = len(gs.players[1].hand)
    dredge = Dredge()
    gs = dredge.apply(gs, dredge_perm)

    assert gs.pending_dredge_choice is not None
    assert gs.pending_dredge_choice["resolved"] is True
    assert gs.pending_dredge_choice["player"] == "p2"
    # Card returned to hand
    assert len(gs.players[1].hand) == hand_before + 1


# Test 56: AI skips Dredge when library doesn't have enough cards
def test_ai_skips_dredge_when_library_insufficient():
    """Test that AI skips Dredge when library has fewer than N cards."""
    gs = _make_game_for_dredge()
    gs.human_player_name = "p1"

    dredge_card = _make_dredge_card()  # Dredge 3
    gs.players[1].library = [
        Card(name="Card A", type_line="Instant"),
    ]  # Only 1 card, need 3 for dredge

    dredge_perm = Permanent(
        card=dredge_card,
        controller="p2",
    )

    hand_before = len(gs.players[1].hand)
    dredge = Dredge()
    gs = dredge.apply(gs, dredge_perm)

    assert gs.pending_dredge_choice is not None
    assert gs.pending_dredge_choice["resolved"] is True
    assert gs.pending_dredge_choice["player"] == "p2"
    # Card NOT returned to hand (not enough library cards)
    assert len(gs.players[1].hand) == hand_before


# Test 57: Dredge pure transform — original GameState unchanged
def test_dredge_pure_transform():
    """Test that Dredge.apply() returns a new GameState object (pure transform)."""
    gs = _make_game_for_dredge()
    gs.human_player_name = "p1"

    dredge_card = _make_dredge_card()
    gs.players[0].hand.append(dredge_card)

    dredge_perm = Permanent(
        card=dredge_card,
        controller="p1",
    )

    old_gs_id = id(gs)

    dredge = Dredge()
    new_gs = dredge.apply(gs, dredge_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 58: Dredge detection from oracle text
def test_dredge_detection_from_oracle():
    """Test that Dredge class can detect Dredge from oracle text."""
    assert Dredge.from_oracle_text("Dredge 3\n...") is True
    assert Dredge.from_oracle_text("This spell has dredge ability.") is False  # No number
    assert Dredge.from_oracle_text("") is False
    assert Dredge.from_oracle_text(None) is False


# Test 59: Dredge parse_dredge_value
def test_dredge_parse_value():
    """Test that Dredge class can parse dredge value from oracle text."""
    assert Dredge.parse_dredge_value("Dredge 3") == 3
    assert Dredge.parse_dredge_value("Dredge 2") == 2
    assert Dredge.parse_dredge_value("No dredge here") == 1  # Default to 1


# Test 60: Dredge has_dredge helper
def test_dredge_has_dredge():
    """Test Dredge.has_dredge helper."""
    assert Dredge.has_dredge(["dredge"]) is True
    assert Dredge.has_dredge(["haste", "flying"]) is False
    assert Dredge.has_dredge(["Dredge"]) is True  # Case insensitive


# Test 61: Dredge applies to permanent with Dredge keyword
def test_dredge_applies_to_card():
    """Test that Dredge.applies() returns True for cards with Dredge."""
    card = _make_dredge_card()
    dredge_perm = Permanent(
        card=card,
        controller="p1",
    )

    gs = _make_game_for_dredge()
    dredge = Dredge()
    assert dredge.applies(gs, dredge_perm) is True


# Test 62: Dredge apply returns game_state unchanged when no Dredge text
def test_dredge_noop_when_no_dredge_text():
    """Test that Dredge.apply() returns unchanged game_state when card has no Dredge."""
    gs = _make_game_for_dredge()

    no_dredge_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_dredge_perm = Permanent(
        card=no_dredge_card,
        controller="p1",
    )

    old_gs_id = id(gs)
    dredge = Dredge()
    new_gs = dredge.apply(gs, no_dredge_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_dredge_choice is None


# ============================================================
# KW-24: Ninjutsu integration tests
# CR 702.61: Return unblocked attacking creature to hand, put ninjutsu creature onto battlefield tapped and attacking
# ============================================================

from mtg_engine.models.game import CombatState, AttackerInfo
from mtg_engine.ability.keywords.ninjutsu import Ninjutsu


def _make_ninjutsu_card() -> Card:
    """Create a test card with Ninjutsu keyword."""
    return Card(
        name="Kiora's Follower",
        type_line="Creature — Merfolk Rogue",
        oracle_text="Ninjutsu {2}{U}\nWhen Kiora's Follower enters, draw a card.",
        mana_cost="{1}{U}",
        keywords=["ninjutsu"],
    )


def _make_ninja_attacker_card() -> Card:
    """Create a test attacker creature."""
    return Card(
        name="Merfolk Raider",
        type_line="Creature — Merfolk Pirate",
        oracle_text="{T}: Add {U}.",
        mana_cost="{1}{U}",
    )


def _make_game_for_ninjutsu() -> GameState:
    """Create a minimal test game state for Ninjutsu."""
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-ninjutsu",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_BLOCKERS,
        players=[p1, p2],
    )


# Test 63: Ninjutsu queues pending choice for human player
def test_ninjutsu_queues_pending_choice_for_human():
    """Test that Ninjutsu queues pending_ninjutsu_choice for human player."""
    gs = _make_game_for_ninjutsu()
    gs.human_player_name = "p1"

    ninja_card = _make_ninjutsu_card()
    ninja_perm = Permanent(card=ninja_card, controller="p1")

    ninjutsu = Ninjutsu()
    gs = ninjutsu.apply(gs, ninja_perm, attacker_perm_id="attacker-1", defending_player="p2")

    assert gs.pending_ninjutsu_choice is not None
    assert gs.pending_ninjutsu_choice["player"] == "p1"
    assert gs.pending_ninjutsu_choice["ninja_card_name"] == "Kiora's Follower"
    assert gs.pending_ninjutsu_choice["attacker_perm_id"] == "attacker-1"
    assert gs.pending_ninjutsu_choice["defending_player"] == "p2"
    assert gs.pending_ninjutsu_choice["resolved"] is False


# Test 64: AI auto-resolves Ninjutsu when unblocked attacker exists
def test_ai_auto_resolves_ninjutsu_when_unblocked_attacker_exists():
    """Test that AI auto-resolves Ninjutsu when there's an unblocked attacking creature."""
    gs = _make_game_for_ninjutsu()
    gs.human_player_name = "p1"

    # Create attacker on battlefield
    attacker_card = _make_ninja_attacker_card()
    attacker_perm = Permanent(card=attacker_card, controller="p2", tapped=True)
    gs.battlefield.append(attacker_perm)

    # Set up combat state with unblocked attacker
    gs.combat = CombatState(
        attackers=[AttackerInfo(permanent_id=attacker_perm.id, defending_id="p1")]
    )

    # Put ninja card in p2's hand
    ninja_card = _make_ninjutsu_card()
    gs.players[1].hand.append(ninja_card)

    ninja_perm = Permanent(card=ninja_card, controller="p2")

    hand_before_p2 = len(gs.players[1].hand)
    hand_before_attacker_owner = len(gs.players[1].hand)  # attacker owner is p2 too

    ninjutsu = Ninjutsu()
    gs = ninjutsu.apply(gs, ninja_perm)

    assert gs.pending_ninjutsu_choice is not None
    assert gs.pending_ninjutsu_choice["resolved"] is True
    assert gs.pending_ninjutsu_choice["ninja_card_name"] == "Kiora's Follower"


# Test 65: AI skips Ninjutsu when no unblocked attacker exists
def test_ai_skips_ninjutsu_when_no_unblocked_attacker():
    """Test that AI skips Ninjutsu when there are no unblocked attackers."""
    gs = _make_game_for_ninjutsu()
    gs.human_player_name = "p1"

    # No combat state — no attackers at all
    ninja_card = _make_ninjutsu_card()
    ninja_perm = Permanent(card=ninja_card, controller="p2")

    ninjutsu = Ninjutsu()
    gs = ninjutsu.apply(gs, ninja_perm)

    assert gs.pending_ninjutsu_choice is not None
    assert gs.pending_ninjutsu_choice["resolved"] is True
    assert gs.pending_ninjutsu_choice["attacker_perm_id"] is None


# Test 66: Ninjutsu pure transform — original GameState unchanged
def test_ninjutsu_pure_transform():
    """Test that Ninjutsu.apply() returns a new GameState object (pure transform)."""
    gs = _make_game_for_ninjutsu()
    gs.human_player_name = "p1"

    ninja_card = _make_ninjutsu_card()
    ninja_perm = Permanent(card=ninja_card, controller="p1")

    old_gs_id = id(gs)

    ninjutsu = Ninjutsu()
    new_gs = ninjutsu.apply(gs, ninja_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 67: Ninjutsu detection from oracle text
def test_ninjutsu_detection_from_oracle():
    """Test that Ninjutsu class can detect Ninjutsu from oracle text."""
    assert Ninjutsu.from_oracle_text("Ninjutsu {2}{U}") is True
    assert Ninjutsu.from_oracle_text("") is False
    assert Ninjutsu.from_oracle_text(None) is False


# Test 68: Ninjutsu apply returns game_state unchanged when no Ninjutsu text
def test_ninjutsu_noop_when_no_ninjutsu_text():
    """Test that Ninjutsu.apply() returns unchanged game_state when card has no Ninjutsu."""
    gs = _make_game_for_ninjutsu()

    no_ninja_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_ninja_perm = Permanent(card=no_ninja_card, controller="p1")

    old_gs_id = id(gs)
    ninjutsu = Ninjutsu()
    new_gs = ninjutsu.apply(gs, no_ninja_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_ninjutsu_choice is None


# ============================================================
# KW-25: Dash integration tests
# CR 702.138: Alternative casting cost, creature gains haste, returns to hand at end step
# ============================================================

from mtg_engine.ability.keywords.dash import Dash, handle_dash_return_to_hand


def _make_dash_card() -> Card:
    """Create a test card with Dash keyword."""
    return Card(
        name="Fleet-Footed Monk",
        type_line="Creature — Human Monk",
        oracle_text="Dash {3}{W}\nWhen Fleet-Footed Monk enters, create a 1/1 white Soldier creature token.",
        mana_cost="{2}{W}",
        keywords=["dash"],
    )


def _make_dash_colored_card() -> Card:
    """Create a test card with colored Dash cost."""
    return Card(
        name="Swiftblade Vindicator",
        type_line="Creature — Human Knight",
        oracle_text="Dash {2}{R}\nHaste, double strike.",
        mana_cost="{3}{R}",
        keywords=["dash"],
    )


def _make_game_for_dash() -> GameState:
    """Create a minimal test game state for Dash."""
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-dash",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )


# Test 69: Dash queues pending choice for human player
def test_dash_queues_pending_choice_for_human():
    """Test that Dash queues pending_dash_choice for human player."""
    gs = _make_game_for_dash()
    gs.human_player_name = "p1"

    dash_card = _make_dash_card()
    dash_perm = Permanent(card=dash_card, controller="p1")

    dash = Dash()
    gs = dash.apply(gs, dash_perm)

    assert gs.pending_dash_choice is not None
    assert gs.pending_dash_choice["player"] == "p1"
    assert gs.pending_dash_choice["card_name"] == "Fleet-Footed Monk"
    assert gs.pending_dash_choice["dash_cost"] == "{3}{W}"
    assert gs.pending_dash_choice["resolved"] is False


# Test 70: AI auto-resolves Dash when mana is sufficient
def test_ai_auto_resolves_dash_when_affordable():
    """Test that AI auto-resolves Dash when player has enough mana."""
    gs = _make_game_for_dash()
    gs.human_player_name = "p1"

    dash_card = _make_dash_card()
    dash_perm = Permanent(card=dash_card, controller="p2")

    # Give p2 enough mana: 3 generic + 1 W
    gs.players[1].mana_pool = ManaPool(C=3, W=1)

    dash = Dash()
    gs = dash.apply(gs, dash_perm)

    assert gs.pending_dash_choice is not None
    assert gs.pending_dash_choice["resolved"] is True
    assert gs.pending_dash_choice["card_name"] == "Fleet-Footed Monk"
    # Mana should be deducted
    assert gs.players[1].mana_pool.C == 0
    assert gs.players[1].mana_pool.W == 0


# Test 71: AI skips Dash when mana is insufficient
def test_ai_skips_dash_when_not_affordable():
    """Test that AI skips Dash when player doesn't have enough mana."""
    gs = _make_game_for_dash()
    gs.human_player_name = "p1"

    dash_card = _make_dash_colored_card()  # {2}{R}
    dash_perm = Permanent(card=dash_card, controller="p2")

    # Give p2 insufficient mana: only 1 generic, no R
    gs.players[1].mana_pool = ManaPool(C=1)

    dash = Dash()
    gs = dash.apply(gs, dash_perm)

    assert gs.pending_dash_choice is not None
    assert gs.pending_dash_choice["resolved"] is True
    # Mana should NOT be deducted (can't afford)
    assert gs.players[1].mana_pool.C == 1


# Test 72: Dash pure transform — original GameState unchanged
def test_dash_pure_transform():
    """Test that Dash.apply() returns a new GameState object (pure transform)."""
    gs = _make_game_for_dash()
    gs.human_player_name = "p1"

    dash_card = _make_dash_card()
    dash_perm = Permanent(card=dash_card, controller="p1")

    old_gs_id = id(gs)

    dash = Dash()
    new_gs = dash.apply(gs, dash_perm)

    assert id(new_gs) != old_gs_id  # New object returned


# Test 73: Dash detection from oracle text
def test_dash_detection_from_oracle():
    """Test that Dash class can detect Dash from oracle text."""
    assert Dash.from_oracle_text("Dash {3}{W}") is True
    assert Dash.from_oracle_text("") is False
    assert Dash.from_oracle_text(None) is False


# Test 74: Dash apply returns game_state unchanged when no Dash text
def test_dash_noop_when_no_dash_text():
    """Test that Dash.apply() returns unchanged game_state when card has no Dash."""
    gs = _make_game_for_dash()

    no_dash_card = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    no_dash_perm = Permanent(card=no_dash_card, controller="p1")

    old_gs_id = id(gs)
    dash = Dash()
    new_gs = dash.apply(gs, no_dash_perm)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)
    assert new_gs.pending_dash_choice is None


# Test 75: handle_dash_return_to_hand returns dashed creatures to hand
def test_handle_dash_return_to_hand():
    """Test that dashed creatures are returned to owner's hand at end step."""
    gs = _make_game_for_dash()

    dash_card = _make_dash_card()
    dash_perm = Permanent(card=dash_card, controller="p1")
    gs.battlefield.append(dash_perm)
    gs.dashed_creatures = {dash_perm.id: "p1"}

    hand_before = len(gs.players[0].hand)
    bf_before = len(gs.battlefield)

    gs = handle_dash_return_to_hand(gs)

    assert len(gs.players[0].hand) == hand_before + 1  # Card returned to hand
    assert len(gs.battlefield) == bf_before - 1  # Removed from battlefield
    assert gs.dashed_creatures == {}  # Tracking cleared


# Test 76: handle_dash_return_to_hand is no-op when no dashed creatures
def test_handle_dash_return_to_hand_noop():
    """Test that handle_dash_return_to_hand does nothing when there are no dashed creatures."""
    gs = _make_game_for_dash()

    old_gs_id = id(gs)
    new_gs = handle_dash_return_to_hand(gs)

    assert id(new_gs) != old_gs_id  # Still returns new object (model_copy)


# --- Hexproof & Shroud query helpers (KW-29/30) ---

def _make_hexproof_shroud_game() -> GameState:
    """Create a minimal test game state for hexproof/shroud tests."""
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-hex-shroud",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
    )


# Test 77: is_hexproof returns True for hexproof permanent on battlefield
def test_is_hexproof_true_on_battlefield():
    """Test that is_hexproof correctly identifies a hexproof permanent."""
    from mtg_engine.ability.keywords.hexproof import is_hexproof

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Angel of Mercy",
        type_line="Creature — Angel",
        keywords=["hexproof", "flying"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_hexproof(gs, perm.id) is True


# Test 78: is_hexproof returns False for non-hexproof permanent
def test_is_hexproof_false_no_keyword():
    """Test that is_hexproof returns False for a permanent without hexproof."""
    from mtg_engine.ability.keywords.hexproof import is_hexproof

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_hexproof(gs, perm.id) is False


# Test 79: can_target_hexproof allows owner targeting but blocks opponent
def test_can_target_hexproof_owner_vs_opponent():
    """Test hexproof targeting: owner can target, opponent cannot."""
    from mtg_engine.ability.keywords.hexproof import can_target_hexproof

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Angel of Mercy",
        type_line="Creature — Angel",
        keywords=["hexproof"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    # Owner can target own hexproof permanent
    assert can_target_hexproof(gs, perm.id, "p1") is True
    # Opponent cannot target opponent's hexproof permanent
    assert can_target_hexproof(gs, perm.id, "p2") is False


# Test 80: is_shrouded returns True for shrouded permanent on battlefield
def test_is_shrouded_true_on_battlefield():
    """Test that is_shrouded correctly identifies a shrouded permanent."""
    from mtg_engine.ability.keywords.shroud import is_shrouded

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Ancient One",
        type_line="Creature — Eldrazi",
        keywords=["shroud"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_shrouded(gs, perm.id) is True


# Test 81: is_shrouded returns False for non-shrouded permanent
def test_is_shrouded_false_no_keyword():
    """Test that is_shrouded returns False for a permanent without shroud."""
    from mtg_engine.ability.keywords.shroud import is_shrouded

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_shrouded(gs, perm.id) is False


# Test 82: can_target_shrouded blocks all targeting regardless of controller
def test_can_target_shrouded_blocks_everyone():
    """Test shroud targeting: nobody can target a shrouded permanent."""
    from mtg_engine.ability.keywords.shroud import can_target_shrouded

    gs = _make_hexproof_shroud_game()
    card = Card(
        name="Ancient One",
        type_line="Creature — Eldrazi",
        keywords=["shroud"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    # Owner cannot target own shrouded permanent
    assert can_target_shrouded(gs, perm.id) is False
    # Opponent also cannot target (same result since shroud blocks everyone)
    assert can_target_shrouded(gs, perm.id) is False


# Test 83: hexproof vs shroud distinction in targeting
def test_hexproof_vs_shroud_distinction():
    """Test that hexproof and shroud behave differently for owner targeting."""
    from mtg_engine.ability.keywords.hexproof import can_target_hexproof
    from mtg_engine.ability.keywords.shroud import can_target_shrouded

    gs = _make_hexproof_shroud_game()

    # Hexproof permanent (p1 controls)
    hex_card = Card(name="Hex Angel", type_line="Creature", keywords=["hexproof"])
    hex_perm = Permanent(card=hex_card, controller="p1")
    gs.battlefield.append(hex_perm)

    # Shrouded permanent (p1 controls)
    shroud_card = Card(name="Shroud Angel", type_line="Creature", keywords=["shroud"])
    shroud_perm = Permanent(card=shroud_card, controller="p1")
    gs.battlefield.append(shroud_perm)

    # Owner CAN target own hexproof permanent
    assert can_target_hexproof(gs, hex_perm.id, "p1") is True
    # Owner CANNOT target own shrouded permanent
    assert can_target_shrouded(gs, shroud_perm.id) is False


# --- Menace query helpers (KW-31) ---

from mtg_engine.ability.keywords.menace import is_menacing, can_block_menacing


def _make_menace_game() -> GameState:
    """Create a minimal test game state for menace tests."""
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-menace",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_BLOCKERS,
        players=[p1, p2],
    )


# Test 84: is_menacing returns True for menacing permanent on battlefield
def test_is_menacing_true_on_battlefield():
    """Test that is_menacing correctly identifies a menacing permanent."""
    gs = _make_menace_game()
    card = Card(
        name="Bloodseeker",
        type_line="Creature — Vampire Warrior",
        keywords=["menace"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_menacing(gs, perm.id) is True


# Test 85: is_menacing returns False for non-menacing permanent
def test_is_menacing_false_no_keyword():
    """Test that is_menacing returns False for a permanent without menace."""
    gs = _make_menace_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert is_menacing(gs, perm.id) is False


# Test 86: can_block_menace allows non-menacing attacker with single blocker
def test_can_block_non_menacing_one_blocker():
    """Test that non-menacing attackers can be blocked by a single creature."""
    gs = _make_menace_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    attacker = Permanent(card=card, controller="p1")
    blocker_card = Card(name="Guard Dog", type_line="Creature", keywords=[])
    blocker = Permanent(card=blocker_card, controller="p2")
    gs.battlefield.extend([attacker, blocker])

    assert can_block_menacing(gs, attacker.id, [blocker.id]) is True


# Test 87: can_block_menace requires two blockers for menacing attacker
def test_can_block_menacing_requires_two():
    """Test that menacing attackers require at least 2 blockers."""
    gs = _make_menace_game()
    card = Card(
        name="Bloodseeker",
        type_line="Creature — Vampire Warrior",
        keywords=["menace"],
    )
    attacker = Permanent(card=card, controller="p1")

    blocker_card = Card(name="Guard Dog", type_line="Creature", keywords=[])
    blocker1 = Permanent(card=blocker_card, controller="p2")
    blocker2 = Permanent(card=Card(name="Guard Dog 2", type_line="Creature"), controller="p2")
    gs.battlefield.extend([attacker, blocker1, blocker2])

    # 1 blocker is illegal for menacing attacker
    assert can_block_menacing(gs, attacker.id, [blocker1.id]) is False
    # 2 blockers is legal
    assert can_block_menacing(gs, attacker.id, [blocker1.id, blocker2.id]) is True


# Test 88: menace vs non-menace distinction in blocking rules
def test_menace_vs_non_menace_blocking_distinction():
    """Test that menacing and non-menacing attackers behave differently."""
    gs = _make_menace_game()

    # Menacing attacker (p1 controls)
    menace_card = Card(name="Bloodseeker", type_line="Creature", keywords=["menace"])
    menace_perm = Permanent(card=menace_card, controller="p1")
    gs.battlefield.append(menace_perm)

    # Non-menacing attacker (p1 controls)
    normal_card = Card(name="Wolf", type_line="Creature", keywords=["haste"])
    normal_perm = Permanent(card=normal_card, controller="p1")
    gs.battlefield.append(normal_perm)

    # Single blocker
    blocker_card = Card(name="Guard Dog", type_line="Creature", keywords=[])
    blocker = Permanent(card=blocker_card, controller="p2")
    gs.battlefield.append(blocker)

    # Menacing attacker: 1 blocker is illegal
    assert can_block_menacing(gs, menace_perm.id, [blocker.id]) is False
    # Non-menacing attacker: 1 blocker is legal
    assert can_block_menacing(gs, normal_perm.id, [blocker.id]) is True


# --- Reach query helpers (KW-29) ---

from mtg_engine.ability.keywords.reach import has_reach, can_block_flying


def _make_reach_game() -> GameState:
    """Create a minimal test game state for reach tests."""
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-reach",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_BLOCKERS,
        players=[p1, p2],
    )


# Test 89: has_reach returns True for reaching permanent on battlefield
def test_has_reach_true_on_battlefield():
    """Test that has_reach correctly identifies a reaching permanent."""
    gs = _make_reach_game()
    card = Card(
        name="Serra Angel",
        type_line="Creature — Angel",
        keywords=["flying", "reach"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert has_reach(gs, perm.id) is True


# Test 90: has_reach returns False for non-reaching permanent
def test_has_reach_false_no_keyword():
    """Test that has_reach returns False for a permanent without reach."""
    gs = _make_reach_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    perm = Permanent(card=card, controller="p1")
    gs.battlefield.append(perm)

    assert has_reach(gs, perm.id) is False


# Test 91: can_block_flying returns True for reach blocker
def test_can_block_flying_with_reach():
    """Test that a creature with reach can block flying creatures."""
    gs = _make_reach_game()
    card = Card(
        name="Llanowar Elite",
        type_line="Creature — Elf Warrior",
        keywords=["reach"],
    )
    blocker = Permanent(card=card, controller="p2")
    gs.battlefield.append(blocker)

    assert can_block_flying(gs, blocker.id) is True


# Test 92: can_block_flying returns True for flying blocker
def test_can_block_flying_with_flying():
    """Test that a creature with flying can block other flying creatures."""
    gs = _make_reach_game()
    card = Card(
        name="Bird",
        type_line="Creature — Bird",
        keywords=["flying"],
    )
    blocker = Permanent(card=card, controller="p2")
    gs.battlefield.append(blocker)

    assert can_block_flying(gs, blocker.id) is True


# Test 93: can_block_flying returns False for neither flying nor reach
def test_can_block_flying_false_no_keywords():
    """Test that a creature without flying or reach cannot block flying."""
    gs = _make_reach_game()
    card = Card(
        name="Wolf",
        type_line="Creature — Wolf",
        keywords=["haste"],
    )
    blocker = Permanent(card=card, controller="p2")
    gs.battlefield.append(blocker)

    assert can_block_flying(gs, blocker.id) is False


# Test 94: reach vs flying distinction in blocking rules
def test_reach_vs_flying_blocking_distinction():
    """Test that reach and flying both allow blocking flying creatures."""
    gs = _make_reach_game()

    # Blocker with reach only (no flying)
    reach_card = Card(name="Serra Angel", type_line="Creature", keywords=["reach"])
    reach_perm = Permanent(card=reach_card, controller="p2")
    gs.battlefield.append(reach_perm)

    # Blocker with flying only (no reach)
    fly_card = Card(name="Bird", type_line="Creature", keywords=["flying"])
    fly_perm = Permanent(card=fly_card, controller="p2")
    gs.battlefield.append(fly_perm)

    # Blocker with neither
    normal_card = Card(name="Wolf", type_line="Creature", keywords=[])
    normal_perm = Permanent(card=normal_card, controller="p2")
    gs.battlefield.append(normal_perm)

    # Reach can block flying
    assert can_block_flying(gs, reach_perm.id) is True
    # Flying can block flying
    assert can_block_flying(gs, fly_perm.id) is True
    # Neither cannot block flying
    assert can_block_flying(gs, normal_perm.id) is False


# Test 95: has_reach returns False for permanent not on battlefield
def test_has_reach_not_found():
    """Test that has_reach returns False when the permanent is not found."""
    gs = _make_reach_game()
    assert has_reach(gs, "nonexistent-id") is False


# Test 96: can_block_flying returns False for permanent not on battlefield
def test_can_block_flying_not_found():
    """Test that can_block_flying returns False when the permanent is not found."""
    gs = _make_reach_game()
    assert can_block_flying(gs, "nonexistent-id") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
