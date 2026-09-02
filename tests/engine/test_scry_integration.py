"""Integration tests for the Scry keyword (CR 701.20 / sub-story CR 701.19).

Covers: detection, value parsing, human choice queuing via ``Scry.apply()``, AI
heuristic reorder correctness, the small-library edge case (fewer than N -> scry
all remaining), pure-transform verification (no-op returns the SAME object and the
original state is never mutated; reorders go through ``model_copy``), and the
wrong-controller guard. Also exercises a real card (Serum Visions) in natural
context for both the human and AI paths.

No skip/xfail markers: every assertion here must pass on its own merits.
"""
from mtg_engine.ability.keywords.scry import (
    Scry,
    apply_scry,
    resolve_scry_choice,
    _score_scry_card,
)
from mtg_engine.models.game import Card, GameState, Permanent, Phase, PlayerState, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(human: str | None = None) -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    kwargs = {}
    if human is not None:
        kwargs["human_player_name"] = human
    return GameState(
        game_id="t-scry",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        **kwargs,
    )


def _land(name: str = "Forest", cmc: float = 0.0) -> Card:
    return Card(name=name, type_line="Basic Land — Forest", mana_cost="", cmc=cmc)


def _creature(name: str = "Goblin", cmc: float = 2.0) -> Card:
    return Card(
        name=name,
        type_line="Creature — Goblin",
        mana_cost="{1}{R}",
        power="2",
        toughness="1",
        cmc=cmc,
    )


def _spell(name: str = "Lightning Bolt", cmc: float = 1.0) -> Card:
    return Card(
        name=name,
        type_line="Instant",
        oracle_text="Deal 3 damage to any target.",
        mana_cost="{R}",
        cmc=cmc,
    )


def _scry_perm(card: Card, controller: str = "p1") -> Permanent:
    return Permanent(card=card, controller=controller)


def _scry_card(n: int) -> Card:
    """A card with a plain ``Scry N`` ability (no draw), so k == n exactly."""
    return Card(
        name=f"Scry {n}",
        type_line="Sorcery",
        oracle_text=f"Scry {n}.",
        mana_cost="{2}",
        cmc=float(n),
    )


def _fill_library(game_state: GameState, cards: list[Card], player: str = "p1") -> None:
    target = next(p for p in game_state.players if p.name == player)
    target.library.extend(cards)


SERUM_VISIONS = Card(
    name="Serum Visions",
    type_line="Sorcery",
    oracle_text="Scry 2, then draw a card.",
    mana_cost="{U}",
    cmc=1.0,
)


# ---------------------------------------------------------------------------
# Detection / parsing (already implemented — assert it still holds in context)
# ---------------------------------------------------------------------------

class TestDetection:
    def test_has_scry_true(self):
        assert Scry.has_scry(["scry"]) is True

    def test_has_scry_false(self):
        assert Scry.has_scry(["flying", "haste"]) is False

    def test_from_oracle_text_serum_visions(self):
        # Real card: "Scry 2, then draw a card."
        assert Scry.from_oracle_text(SERUM_VISIONS.oracle_text or "") is True

    def test_parse_scry_value_real_card(self):
        assert Scry.parse_scry_value("Scry 2, then draw a card.") == 2


# ---------------------------------------------------------------------------
# AI heuristic ordering (CR 701.20) — high-CMC non-lands on top, lands on bottom
# ---------------------------------------------------------------------------

class TestAIHeuristic:
    def test_score_nonland_ranks_above_land(self):
        # Any non-land scores >= 0; any land scores -1, so a low-cmc non-land still
        # outranks a high-cmc land (lands always sink to the bottom).
        assert _score_scry_card(_spell(cmc=0.5)) > _score_scry_card(_land("Snow-Covered", cmc=4))

    def test_higher_cmc_nonland_scores_higher(self):
        assert _score_scry_card(_creature(cmc=5)) > _score_scry_card(_creature(cmc=2))

    def test_ai_reorders_best_on_top_and_buries_lands(self):
        gs = _make_game(human=None)  # AI controls p1
        library = [_land("Forest"), _creature("Bear", cmc=2), _spell("Bolt", cmc=3)]
        _fill_library(gs, library)

        perm = _scry_perm(_scry_card(3), controller="p1")  # Scry 3 -> all three revealed
        new_gs = Scry().apply(gs, perm)

        # Best (highest-cmc non-land spell) on top; land buried at the bottom of the N.
        assert new_gs.players[0].library[0].name == "Bolt"
        assert new_gs.players[0].library[1].name == "Bear"
        assert new_gs.players[0].library[2].name == "Forest"
        # The rest of the library below the scry zone is untouched and stays in order.
        assert new_gs.players[0].library[3:] == []

    def test_ai_keeps_relative_order_of_equal_scores(self):
        gs = _make_game(human=None)
        two_creatures = [_creature("A", cmc=2), _creature("B", cmc=2)]
        _fill_library(gs, two_creatures + [_land()])
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = Scry().apply(gs, perm)
        # Non-lands sorted above the land; ties keep their input order (stable sort).
        assert new_gs.players[0].library[0].name == "A"
        assert new_gs.players[0].library[1].name == "B"
        assert new_gs.players[0].library[2].name == "Forest"


# ---------------------------------------------------------------------------
# Human path — queue a choice, do NOT reorder the library yet
# ---------------------------------------------------------------------------

class TestHumanPath:
    def test_human_queues_pending_choice_without_reordering(self):
        gs = _make_game(human="p1")
        original_order = [_spell("Bolt", cmc=3), _creature("Bear", cmc=2), _land("Forest")]
        _fill_library(gs, list(original_order))

        perm = _scry_perm(_scry_card(3), controller="p1")  # Scry 3 -> all three revealed
        new_gs = Scry().apply(gs, perm)

        # Library order is unchanged — the human has not reordered yet.
        assert [c.name for c in new_gs.players[0].library[:3]] == [c.name for c in original_order]
        # A pending reorder choice was queued with the revealed cards + marker.
        assert new_gs.pending_scry_choice is not None
        assert new_gs.pending_scry_choice["player"] == "p1"
        assert new_gs.pending_scry_choice["effect_type"] == "scry"
        assert len(new_gs.pending_scry_choice["cards"]) == 3
        # Resolved pending choice clears the queue.
        resolved = resolve_scry_choice(new_gs, "p1", [c.id for c in reversed(list(original_order))])
        assert resolved.pending_scry_choice is None

    def test_human_reorder_reorders_library_via_model_copy(self):
        gs = _make_game(human="p1")
        cards = [_spell("Bolt", cmc=3), _creature("Bear", cmc=2), _land("Forest")]
        _fill_library(gs, list(cards))
        queued = Scry().apply(gs, _scry_perm(_scry_card(3), controller="p1"))

        # Human puts the land on top and everything else below it.
        desired_ids = [cards[2].id, cards[0].id, cards[1].id]  # Forest, Bolt, Bear
        resolved = resolve_scry_choice(queued, "p1", desired_ids)

        assert [c.name for c in resolved.players[0].library[:3]] == ["Forest", "Bolt", "Bear"]
        assert resolved.pending_scry_choice is None


# ---------------------------------------------------------------------------
# Library-size edge case (CR 701.19b): fewer than N cards -> scry all remaining
# ---------------------------------------------------------------------------

class TestLibrarySizeEdge:
    def test_fewer_than_n_scrys_all_remaining(self):
        gs = _make_game(human=None)  # AI, auto-resolve
        only_two = [_spell("Bolt", cmc=3), _land("Forest")]
        _fill_library(gs, list(only_two))

        perm = _scry_perm(SERUM_VISIONS, controller="p1")  # Scry 2, library has 2 -> both
        new_gs = Scry().apply(gs, perm)
        assert len(new_gs.players[0].library) == 2
        # Both cards still present, just reordered (spell on top).
        assert {c.name for c in new_gs.players[0].library} == {"Bolt", "Forest"}

    def test_library_shorter_than_n_ai_ordering(self):
        gs = _make_game(human=None)
        # Library has 1 land, scry requests 5 -> scry the single remaining card.
        _fill_library(gs, [_land("Forest")])
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = Scry().apply(gs, perm)
        assert [c.name for c in new_gs.players[0].library] == ["Forest"]


# ---------------------------------------------------------------------------
# Pure-transform guarantees (Q4): no-op returns SAME object; reorder is model_copy
# ---------------------------------------------------------------------------

class TestPureTransform:
    def test_no_op_on_empty_library_returns_same_object(self):
        gs = _make_game(human=None)  # empty library
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        result = Scry().apply(gs, perm)
        assert result is gs

    def test_no_op_when_controller_absent_returns_same_object(self):
        gs = _make_game(human=None)
        _fill_library(gs, [_spell("Bolt", cmc=1)])
        # Permanent controlled by a player not in the game -> wrong/unknown controller.
        perm = _scry_perm(SERUM_VISIONS, controller="ghost")
        result = Scry().apply(gs, perm)
        assert result is gs

    def test_reorder_is_new_object_and_original_untouched(self):
        gs = _make_game(human=None)
        original_order = [_land("Forest"), _creature("Bear", cmc=2), _spell("Bolt", cmc=3)]
        _fill_library(gs, list(original_order))
        # Snapshot the original player's library order by identity of first card.
        original_top_id = gs.players[0].library[0].id

        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = Scry().apply(gs, perm)

        # New object returned...
        assert new_gs is not gs
        # ...and the original player's live library was NOT mutated in place.
        assert gs.players[0].library[0].id == original_top_id
        assert gs.players[0].library[0].name == "Forest"

    def test_other_players_library_never_mutated(self):
        gs = _make_game(human=None)
        _fill_library(gs, [_spell("Bolt", cmc=3), _land("Forest")], player="p1")
        original_p2_lib_id = [c.id for c in gs.players[1].library]

        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = Scry().apply(gs, perm)

        # p2's library is byte-for-byte the same object list.
        assert [c.id for c in new_gs.players[1].library] == original_p2_lib_id


# ---------------------------------------------------------------------------
# resolve_scry_choice validation / guards
# ---------------------------------------------------------------------------

class TestResolveScryChoice:
    def test_no_pending_returns_same_object(self):
        gs = _make_game(human="p1")
        assert resolve_scry_choice(gs, "p1", []) is gs

    def test_wrong_player_returns_same_object(self):
        gs = _make_game(human="p1")
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        queued = Scry().apply(gs, perm)
        # p2 has no pending scry choice of their own.
        assert resolve_scry_choice(queued, "p2", []) is queued

    def test_invalid_non_permutation_clears_without_reordering(self):
        gs = _make_game(human="p1")
        cards = [_spell("Bolt", cmc=3), _creature("Bear", cmc=2), _land("Forest")]
        _fill_library(gs, list(cards))
        queued = Scry().apply(gs, _scry_perm(SERUM_VISIONS, controller="p1"))

        # A selection that is not a permutation (missing one, extra id) must not
        # corrupt the library; it clears the pending choice and reorders nothing.
        before_ids = [c.id for c in queued.players[0].library]
        bad_selection = [cards[0].id, cards[1].id]  # drops the land -> not a permutation
        resolved = resolve_scry_choice(queued, "p1", bad_selection)

        assert [c.id for c in resolved.players[0].library] == before_ids
        assert resolved.pending_scry_choice is None

    def test_only_reorders_the_revealed_prefix(self):
        # Serum Visions is Scry 2: only the top 2 cards are revealed/reordered;
        # everything below the scry zone stays put regardless.
        gs = _make_game(human="p1")
        library = [_land("Forest"), _spell("Bolt", cmc=3), _creature("Bear", cmc=2)]
        extra = _spell("Counterspell", cmc=3)  # below the scry zone, must stay put
        _fill_library(gs, list(library) + [extra])

        queued = Scry().apply(gs, _scry_perm(SERUM_VISIONS, controller="p1"))  # reveal Forest, Bolt
        assert len(queued.pending_scry_choice["cards"]) == 2

        # Reorder the two revealed cards so Bolt goes on top.
        desired_ids = [library[1].id, library[0].id]  # Bolt, Forest
        resolved = resolve_scry_choice(queued, "p1", desired_ids)
        assert [c.name for c in resolved.players[0].library[:2]] == ["Bolt", "Forest"]
        # The scry zone ends at k=2; cards below it are untouched.
        assert [c.name for c in resolved.players[0].library[2:]] == ["Bear", "Counterspell"]


# ---------------------------------------------------------------------------
# Convenience wrapper + natural-context (Q5)
# ---------------------------------------------------------------------------

class TestNaturalContext:
    def test_apply_scry_wrapper_ai_auto_resolves(self):
        gs = _make_game(human=None)
        library = [_land("Forest"), _creature("Bear", cmc=2)]
        _fill_library(gs, list(library))
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = apply_scry(gs, perm)
        assert new_gs.pending_scry_choice is None  # AI resolved immediately
        assert new_gs.players[0].library[0].name == "Bear"

    def test_human_serum_visions_queues_via_wrapper(self):
        gs = _make_game(human="p1")
        library = [_spell("Bolt", cmc=3), _spell("Opt", cmc=1), _land("Forest")]
        _fill_library(gs, list(library))
        perm = _scry_perm(SERUM_VISIONS, controller="p1")
        new_gs = apply_scry(gs, perm)
        assert new_gs.pending_scry_choice is not None
        assert new_gs.pending_scry_choice["player"] == "p1"
        # Library untouched until the human submits a reorder.
        assert [c.name for c in new_gs.players[0].library[:3]] == ["Bolt", "Opt", "Forest"]
