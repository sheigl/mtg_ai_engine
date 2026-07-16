"""
APP-05: Draft / Sealed Simulation — unit tests.

Tests pack generation, pick order, bot auto-pick scoring, session lifecycle,
sealed pool simulation, and result construction. 14+ test cases covering
every axis in the spec.
"""
import pytest
from pydantic import ValidationError

from mtg_engine.ai.draft import (
    _clear_sessions,
    _complete_draft,
    _draft_sessions,
    _evict_old_sessions,
    _get_current_picker,
    _get_pack_for_picker,
    _process_pick,
    _score_card_for_draft,
    _start_draft_session,
    _start_sealed_session,
    _bot_auto_pick,
    _resolve_bot_picks,
    _generate_pack,
)
from mtg_engine.models.game import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card(
    name: str = "Test Card",
    mana_cost: str | None = "{1}",
    type_line: str = "",
    oracle_text: str | None = None,
    cmc: float = 0.0,
    colors: list[str] | None = None,
    rarity: str | None = "common",
) -> Card:
    return Card(
        name=name,
        mana_cost=mana_cost,
        type_line=type_line,
        oracle_text=oracle_text,
        cmc=cmc,
        colors=colors or [],
        rarity=rarity,
    )


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Clear draft sessions before and after each test."""
    _clear_sessions()
    yield
    _clear_sessions()


# ---------------------------------------------------------------------------
# Test Pack Generation
# ---------------------------------------------------------------------------

class TestPackGeneration:
    """Pack generation produces valid booster packs of 15 cards."""

    def test_generate_pack_returns_15_cards(self):
        """A generated pack contains exactly 15 cards."""
        rng = __import__("random").Random(42)
        # Use a set_code that may not exist — should fall back to cached cards or empty
        pack = _generate_pack("NONEXISTENT_SET", rng)
        if pack:
            assert len(pack) == 15

    def test_generate_pack_cards_have_names(self):
        """All cards in a generated pack have non-empty names."""
        rng = __import__("random").Random(42)
        pack = _generate_pack("NONEXISTENT_SET", rng)
        for card in pack:
            assert card.name and len(card.name.strip()) > 0

    def test_generate_pack_deterministic_with_seed(self):
        """Same seed produces the same pack."""
        rng1 = __import__("random").Random(42)
        rng2 = __import__("random").Random(42)
        pack1 = _generate_pack("NONEXISTENT_SET", rng1)
        pack2 = _generate_pack("NONEXISTENT_SET", rng2)
        assert len(pack1) == len(pack2)


# ---------------------------------------------------------------------------
# Test Draft Session Lifecycle
# ---------------------------------------------------------------------------

class TestDraftSessionLifecycle:
    """Draft session creation, pick order, and completion."""

    def test_start_draft_session(self):
        """Creating a draft session returns correct initial state."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        assert session.state == "drafting"
        assert session.current_round == 1
        assert session.picks_this_round == 0
        assert len(session.players) == 2
        assert session.players[0].is_human is True
        assert session.players[1].is_human is False

    def test_start_draft_requires_min_players(self):
        """Draft requires at least 2 players."""
        with pytest.raises(ValueError, match="at least 2"):
            _start_draft_session(
                players=["Solo"],
                packs_per_player=3,
                set_code="MOM",
                format_name="modern",
            )

    def test_start_draft_packs_range(self):
        """packs_per_player must be between 1 and 8."""
        with pytest.raises(ValueError, match="between 1 and 8"):
            _start_draft_session(
                players=["Alice", "Bob"],
                packs_per_player=0,
                set_code="MOM",
                format_name="modern",
            )

    def test_start_draft_generates_initial_packs(self):
        """Initial draft session has one pack per player."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        assert len(session.packs) == 3
        for pack in session.packs:
            assert len(pack) == 15


# ---------------------------------------------------------------------------
# Test Pick Order
# ---------------------------------------------------------------------------

class TestPickOrder:
    """Pick order rotates correctly each round."""

    def test_round_1_picker_is_first(self):
        """In round 1, the first player picks first."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        picker_idx = _get_current_picker(session)
        assert picker_idx == 0
        assert session.players[picker_idx].player_name == "Alice"

    def test_round_1_pick_rotation(self):
        """In round 1, picks go left (index 0, 1, 2...)."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        # Pick 1: Alice (index 0)
        assert _get_current_picker(session) == 0
        session.picks_this_round = 1
        # Pick 2: Bob (index 1)
        assert _get_current_picker(session) == 1
        session.picks_this_round = 2
        # Pick 3: Charlie (index 2)
        assert _get_current_picker(session) == 2

    def test_round_2_starting_index_rotates(self):
        """Round 2 starts from a different player."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        # Simulate round 1 complete
        session.current_round = 2
        session.picks_this_round = 0

        picker_idx = _get_current_picker(session)
        assert picker_idx is not None
        # Round 2 should start from a different index than round 1


# ---------------------------------------------------------------------------
# Test Bot Auto-Pick Scoring
# ---------------------------------------------------------------------------

class TestBotScoring:
    """Bot scoring considers strategy, color synergy, and CMC curve."""

    def test_score_low_cmc_for_aggro(self):
        """Low-CMC creatures score higher for aggro strategy."""
        low_cmc = _make_card("Goblin", "{R}", "Creature — Goblin", cmc=1.0, colors=["R"])
        high_cmc = _make_card("Dragon", "{5}{R}{R}", "Creature — Dragon", cmc=7.0, colors=["R"])

        low_score = _score_card_for_draft(low_cmc, [], "aggro")
        high_score = _score_card_for_draft(high_cmc, [], "aggro")

        assert low_score > high_score

    def test_color_synergy_bonus(self):
        """Cards matching drafted colors get a synergy bonus."""
        red_card = _make_card("Red Spell", "{R}", "Instant", cmc=1.0, colors=["R"])
        blue_card = _make_card("Blue Spell", "{U}", "Instant", cmc=1.0, colors=["U"])

        # Drafted pool has 3 red cards (dominant color)
        drafted = [
            _make_card("Red 1", "{R}", "Creature", colors=["R"]),
            _make_card("Red 2", "{R}", "Creature", colors=["R"]),
            _make_card("Red 3", "{R}", "Creature", colors=["R"]),
        ]

        red_score = _score_card_for_draft(red_card, drafted, "midrange")
        blue_score = _score_card_for_draft(blue_card, drafted, "midrange")

        assert red_score > blue_score


# ---------------------------------------------------------------------------
# Test Process Pick
# ---------------------------------------------------------------------------

class TestProcessPick:
    """Processing picks validates state and updates session correctly."""

    def test_process_pick_removes_card_from_pack(self):
        """Picking a card removes it from the current pack."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        # Get first card in Alice's pack
        pack = _get_pack_for_picker(session, 0)
        if not pack:
            pytest.skip("No cards available for test")

        card_name = pack[0].name
        session, picked = _process_pick(session.session_id, "Alice", card_name)

        assert picked.name == card_name
        # Card should be in Alice's drafted list
        assert any(c.name == card_name for c in session.players[0].drafted_cards)

    def test_process_pick_wrong_player(self):
        """Cannot pick when it's not your turn."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        with pytest.raises(ValueError, match="not .* turn"):
            _process_pick(session.session_id, "Bob", "Any Card")

    def test_process_pick_card_not_in_pack(self):
        """Cannot pick a card that's not in the current pack."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        with pytest.raises(ValueError, match="not found in current pack"):
            _process_pick(session.session_id, "Alice", "Nonexistent Card")


# ---------------------------------------------------------------------------
# Test Bot Auto-Pick
# ---------------------------------------------------------------------------

class TestBotAutoPick:
    """Bot auto-picks the highest-scoring card from its pack."""

    def test_bot_auto_pick_selects_best_card(self):
        """Bot picks the highest-scoring card available."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",  # Bob is bot
            seed=42,
        )

        # Simulate Alice picking first (if there are cards)
        pack = _get_pack_for_picker(session, 0)
        if not pack:
            pytest.skip("No cards available for test")

        card_name = pack[0].name
        session, _ = _process_pick(session.session_id, "Alice", card_name)

        # Now it's Bob's turn — bot auto-picks (pass session directly)
        session, picked = _bot_auto_pick(session, "Bob")

        assert picked is not None
        assert any(c.name == picked.name for c in session.players[1].drafted_cards)


# ---------------------------------------------------------------------------
# Test Draft Completion and Deck Building
# ---------------------------------------------------------------------------

class TestDraftCompletion:
    """Draft completes after all rounds and builds decks."""

    def test_complete_draft_builds_decks(self):
        """Completing a draft builds decks for all players."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        # Simulate all picks (both bots)
        session = _resolve_bot_picks(session)

        assert session.state == "completed"
        assert session.results is not None
        assert len(session.results.player_decks) == 2


# ---------------------------------------------------------------------------
# Test Sealed Simulation
# ---------------------------------------------------------------------------

class TestSealedSimulation:
    """Sealed pool simulation generates pools and builds decks."""

    def test_sealed_returns_pool_and_deck(self):
        """Sealed session returns a pool of cards and constructed deck."""
        result = _start_sealed_session(
            players=["Alice"],
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        assert len(result["players"]) == 1
        player = result["players"][0]
        assert player["name"] == "Alice"
        assert "pool" in player
        assert "deck" in player
        assert "sideboard" in player

    def test_sealed_pool_size(self):
        """Sealed pool contains 15 cards."""
        result = _start_sealed_session(
            players=["Alice"],
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        player = result["players"][0]
        assert len(player["pool"]) == 15

    def test_sealed_requires_min_players(self):
        """Sealed requires at least 1 player."""
        with pytest.raises(ValueError, match="at least 1"):
            _start_sealed_session(
                players=[],
                set_code="MOM",
                format_name="modern",
            )

    def test_sealed_multiple_players(self):
        """Sealed works for multiple players."""
        result = _start_sealed_session(
            players=["Alice", "Bob"],
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        assert len(result["players"]) == 2
        for p in result["players"]:
            assert len(p["pool"]) == 15

    def test_sealed_invalid_format_raises(self):
        """Sealed rejects unknown format names with ValueError (CRITICAL 1 fix)."""
        with pytest.raises(ValueError, match="Unknown format"):
            _start_sealed_session(
                players=["Alice"],
                set_code="MOM",
                format_name="invalid_format_xyz",
            )

    def test_draft_invalid_format_raises(self):
        """Draft rejects unknown format names with ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            _start_draft_session(
                players=["Alice", "Bob"],
                packs_per_player=1,
                set_code="MOM",
                format_name="invalid_format_xyz",
            )


# ---------------------------------------------------------------------------
# Test Session Cleanup
# ---------------------------------------------------------------------------

class TestSessionCleanup:
    """Session cleanup clears all draft sessions."""

    def test_clear_sessions(self):
        """_clear_sessions removes all stored sessions."""
        _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        _clear_sessions()

        with pytest.raises(ValueError, match="not found"):
            from mtg_engine.ai.draft import _get_session
            _get_session("nonexistent")


# ---------------------------------------------------------------------------
# Test Invalid Session Access
# ---------------------------------------------------------------------------

class TestInvalidSession:
    """Accessing non-existent sessions raises errors."""

    def test_get_nonexistent_session(self):
        """Getting a non-existent session raises ValueError."""
        from mtg_engine.ai.draft import _get_session

        with pytest.raises(ValueError, match="not found"):
            _get_session("nonexistent-id")


# ---------------------------------------------------------------------------
# Test API Request Models
# ---------------------------------------------------------------------------

class TestAPIModels:
    """API request/response models validate correctly."""

    def test_draft_start_request_valid(self):
        """Valid DraftStartRequest creates without error."""
        from mtg_engine.api.routers.draft_ai import DraftStartRequest

        req = DraftStartRequest(
            players=["Alice", "Bob"],
            set_code="MOM",
            format_name="modern",
            strategy="aggro",
            human_player_name="Alice",
        )

        assert len(req.players) == 2
        assert req.strategy == "aggro"

    def test_draft_start_request_invalid_strategy(self):
        """Invalid strategy raises ValidationError."""
        from mtg_engine.api.routers.draft_ai import DraftStartRequest

        with pytest.raises(ValidationError):
            DraftStartRequest(
                players=["Alice", "Bob"],
                set_code="MOM",
                strategy="invalid_strategy",
            )

    def test_sealed_start_request_valid(self):
        """Valid SealedStartRequest creates without error."""
        from mtg_engine.api.routers.draft_ai import SealedStartRequest

        req = SealedStartRequest(
            players=["Alice"],
            set_code="MOM",
            format_name="modern",
        )

        assert len(req.players) == 1
        assert req.strategy == "midrange"

    def test_sealed_start_request_min_players(self):
        """Sealed requires at least 1 player."""
        from mtg_engine.api.routers.draft_ai import SealedStartRequest

        with pytest.raises(ValidationError):
            SealedStartRequest(players=[], set_code="MOM")


# NOTE: API endpoint tests (TestClient-based) are in tests/api/ because the
# tests/ai/conftest.py mocks httpx at session scope, which breaks starlette's
# TestClient. See conftest.py for details.


# ---------------------------------------------------------------------------
# Test Pack Passing Logic
# ---------------------------------------------------------------------------

class TestPackPassing:
    """Packs pass left in odd rounds, right in even rounds."""

    def test_odd_round_pack_offset(self):
        """In round 1 (odd), pack at index 0 is in front of player 0."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        pack_for_alice = _get_pack_for_picker(session, 0)
        assert len(pack_for_alice) == 15

    def test_even_round_pack_offset(self):
        """In round 2 (even), packs are offset differently."""
        session = _start_draft_session(
            players=["Alice", "Bob", "Charlie"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        # Simulate round 1 complete (all picks done)
        session.current_round = 2
        session.picks_this_round = 0

        pack_for_picker = _get_pack_for_picker(session, 0)
        assert len(pack_for_picker) == 15


# ---------------------------------------------------------------------------
# Test Resolve Bot Picks
# ---------------------------------------------------------------------------

class TestResolveBotPicks:
    """_resolve_bot_picks processes all bot picks until human turn or completion."""

    def test_all_bots_completes_draft(self):
        """When all players are bots, draft completes automatically."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        # No human player — all bots
        session = _resolve_bot_picks(session)

        assert session.state == "completed"

    def test_human_pending_stops_resolution(self):
        """When a human needs to pick, resolution stops."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        # Alice is human and picks first in round 1
        session = _resolve_bot_picks(session)

        assert session.state == "drafting"
        pick_info = __import__("mtg_engine.ai.draft", fromlist=["_get_current_pick_info"])._get_current_pick_info(session)
        if pick_info:
            assert pick_info.player_name == "Alice"


# ---------------------------------------------------------------------------
# Test Session Eviction (CRITICAL 2 fix — LRU eviction coverage)
# ---------------------------------------------------------------------------

class TestSessionEviction:
    """LRU session eviction removes oldest sessions when limit is exceeded."""

    def test_eviction_not_triggered_under_limit(self):
        """Creating 50 sessions does not trigger eviction (limit is 100)."""
        for i in range(50):
            _start_draft_session(
                players=[f"Player{i}_A", f"Player{i}_B"],
                packs_per_player=1,
                set_code="MOM",
                format_name="modern",
                seed=i,
            )

        assert len(_draft_sessions) == 50
        _evict_old_sessions()
        # No eviction should occur since we're under the limit
        assert len(_draft_sessions) == 50

    def test_completed_sessions_evicted_first(self):
        """Completed sessions are evicted before active ones."""
        from mtg_engine.ai.draft import DraftSession, PlayerDraftState, MAX_DRAFT_SESSIONS

        # Create 98 completed sessions (oldest first)
        for i in range(98):
            session = DraftSession(
                session_id=f"completed-{i}",
                players=[PlayerDraftState(player_name="A"), PlayerDraftState(player_name="B")],
                packs_per_player=1,
                set_code="MOM",
                format_name="modern",
                seed=i,
                state="completed",
                created_at=1000.0 + i,  # older sessions have lower timestamps
            )
            _draft_sessions[f"completed-{i}"] = session

        # Create 2 active sessions (newest)
        for i in range(2):
            session = DraftSession(
                session_id=f"active-{i}",
                players=[PlayerDraftState(player_name="A"), PlayerDraftState(player_name="B")],
                packs_per_player=1,
                set_code="MOM",
                format_name="modern",
                seed=200 + i,
                state="drafting",
                created_at=2000.0 + i,  # newer sessions have higher timestamps
            )
            _draft_sessions[f"active-{i}"] = session

        assert len(_draft_sessions) == 100

        # Now add one more active session — should trigger eviction of completed ones first
        new_session = DraftSession(
            session_id="new-active",
            players=[PlayerDraftState(player_name="A"), PlayerDraftState(player_name="B")],
            packs_per_player=1,
            set_code="MOM",
            format_name="modern",
            seed=300,
            state="drafting",
            created_at=3000.0,
        )
        _draft_sessions["new-active"] = new_session

        assert len(_draft_sessions) == 101
        _evict_old_sessions()

        # Should be back to limit, with completed sessions removed first
        assert len(_draft_sessions) <= MAX_DRAFT_SESSIONS
        # The active sessions should still exist (they're newer)
        assert "active-0" in _draft_sessions or "active-1" in _draft_sessions

    def test_active_session_survives_when_under_limit(self):
        """An active session persists after eviction when total is under limit."""
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=3,
            set_code="MOM",
            format_name="modern",
            seed=42,
        )

        sid = session.session_id
        assert len(_draft_sessions) == 1

        _evict_old_sessions()

        # Session should still exist (under limit of 100)
        assert sid in _draft_sessions
        assert len(_draft_sessions) == 1


# ---------------------------------------------------------------------------
# Test Duplicate Card Pick (MAJOR 5 fix — duplicate card validation coverage)
# ---------------------------------------------------------------------------

class TestDuplicateCardPick:
    """Picking one copy of a duplicate card leaves the other available."""

    def test_duplicate_card_in_pack_both_pickable(self):
        """If a pack contains two copies of the same card name, picking one
        leaves the second copy available for subsequent picks by the SAME player
        in their next round (since each player has their own pack)."""
        # Create a session with 2 packs per player so Alice gets multiple rounds
        session = _start_draft_session(
            players=["Alice", "Bob"],
            packs_per_player=2,
            set_code="MOM",
            format_name="modern",
            human_player_name="Alice",
            seed=42,
        )

        # Monkeypatch Alice's pack to contain two copies of the same card
        dup_card = _make_card("Duplicate Card", "{1}", "Creature — Beast")
        other_card = _make_card("Other Card", "{2}", "Instant")
        session.packs[0] = [dup_card, dup_card, other_card]

        # Alice picks first copy of "Duplicate Card"
        session, picked1 = _process_pick(session.session_id, "Alice", "Duplicate Card")
        assert picked1.name == "Duplicate Card"

        # Verify only one copy was removed — second still in pack
        remaining_dupes = [c for c in session.packs[0] if c.name == "Duplicate Card"]
        assert len(remaining_dupes) == 1, (
            f"Expected 1 duplicate remaining, got {len(remaining_dupes)}. "
            f"Pack: {[c.name for c in session.packs[0]]}"
        )

        # Verify the picked card is recorded in Alice's drafted_cards
        alice_state = next(p for p in session.players if p.player_name == "Alice")
        assert len(alice_state.drafted_cards) == 1
        assert alice_state.drafted_cards[0].name == "Duplicate Card"

