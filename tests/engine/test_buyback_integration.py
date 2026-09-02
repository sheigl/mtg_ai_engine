"""
Story 7-6a: Buyback keyword (CR 702.27/702.28) — integration tests.

Buyback {cost} is an ADDITIONAL cost that may be paid as a sorcery spell is
cast. If paid, the spell returns to its owner's hand instead of going to
their graveyard when it resolves.

This suite exercises the REAL engine entry points:

* ``BuybackKeyword.apply()`` — the pure-transform human/AI split (no-op
  guards, pending_buyback_choice queueing, AI affordability heuristic).
* ``cast_spell(buyback_paid=...)`` — the buyback cost is appended to the
  base cost and deducted in the single payment flow; the stack object is
  marked ``buyback_paid`` ONLY when the flag was actually set (regression
  test for the old placeholder that marked every buyback card as paid).
* ``resolve_top()`` — the paid spell returns to hand; the unpaid one goes
  to the graveyard (CR 702.28).
* The REAL API surface (``POST /cast``, ``GET /legal-actions``,
  ``POST /choice``, ``POST /pass``) via TestClient: the human defers the
  cast with ``pending_buyback_choice``, the legal actions offer
  ``buyback_pay`` / ``buyback_pass`` (and NO ``pass``), and the full
  cast → choice → pass → resolution flow puts the card in hand (paid) or
  graveyard (not paid) with the correct mana deductions.
"""
import pytest
from fastapi.testclient import TestClient

from mtg_engine.ability.keywords.buyback import BuybackKeyword
from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.models.game import Card, GameState, ManaPool, Permanent, Phase, PlayerState, Step


# ─── Shared fixtures ──────────────────────────────────────────────────────────

def _make_card(card_id="wom-1", name="Whispers of the Muse", mana_cost="{1}{W}",
               type_line="Sorcery", oracle_text="Draw two cards. Buyback {4}", **kwargs):
    return Card(
        id=card_id,
        name=name,
        mana_cost=mana_cost,
        type_line=type_line,
        oracle_text=oracle_text,
        **kwargs,
    )


def _make_gs(pool=None, human=None, hand=None):
    """A main-phase game with p1 active and holding priority (sorcery speed)."""
    p1 = PlayerState(
        name="p1", life=20, mana_pool=pool or ManaPool(),
        hand=hand if hand is not None else [_make_card()],
    )
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    kwargs = {}
    if human is not None:
        kwargs["human_player_name"] = human
    return GameState(
        game_id="t-buyback", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
        **kwargs,
    )


def _buyback_perm(controller="p1"):
    return Permanent(card=_make_card(), controller=controller)


# ─── apply() — pure transform, no-op guards, human/AI split ─────────────────

class TestApplyBuyback:
    def test_human_queues_pending_buyback_choice(self):
        """A human caster queues pending_buyback_choice (resolved=False)."""
        gs = _make_gs(pool=ManaPool(W=1, C=5), human="p1")
        gs2 = BuybackKeyword().apply(gs, _buyback_perm())

        assert gs2 is not gs  # pure transform: new object
        assert gs.pending_buyback_choice is None  # original unmutated
        pending = gs2.pending_buyback_choice
        assert pending is not None
        assert pending["player"] == "p1"
        assert pending["card_id"] == "wom-1"
        assert pending["card_name"] == "Whispers of the Muse"
        assert pending["buyback_cost"] == "{4}"
        assert pending["base_cost"] == "{1}{W}"
        assert pending["resolved"] is False
        assert pending["paid"] is False

    def test_ai_resolves_paid_true_when_affordable(self):
        """AI with base+buyback available in the pool auto-pays (paid=True)."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))  # no human → AI path
        gs2 = BuybackKeyword().apply(gs, _buyback_perm())
        pending = gs2.pending_buyback_choice
        assert pending is not None
        assert pending["resolved"] is True
        assert pending["paid"] is True

    def test_ai_resolves_paid_false_when_unaffordable(self):
        """AI without enough mana for base+buyback declines (paid=False)."""
        gs = _make_gs(pool=ManaPool(W=1, C=1))  # base only, no room for {4}
        gs2 = BuybackKeyword().apply(gs, _buyback_perm())
        pending = gs2.pending_buyback_choice
        assert pending is not None
        assert pending["resolved"] is True
        assert pending["paid"] is False

    def test_noop_no_buyback_returns_same_object(self):
        """A sorcery without buyback is a no-op (SAME object returned)."""
        gs = _make_gs(pool=ManaPool(C=5), human="p1",
                      hand=[_make_card(oracle_text="Draw a card.")])
        perm = Permanent(card=_make_card(oracle_text="Draw a card."), controller="p1")
        gs2 = BuybackKeyword().apply(gs, perm)
        assert gs2 is gs
        assert gs.pending_buyback_choice is None

    def test_noop_instant_returns_same_object(self):
        """Buyback only applies to sorcery-speed spells — instants are no-ops."""
        gs = _make_gs(pool=ManaPool(C=5), human="p1",
                      hand=[_make_card(type_line="Instant")])
        perm = Permanent(card=_make_card(type_line="Instant"), controller="p1")
        gs2 = BuybackKeyword().apply(gs, perm)
        assert gs2 is gs
        assert gs.pending_buyback_choice is None

    def test_noop_creature_returns_same_object(self):
        """Creatures are not sorcery-speed — buyback is silently ignored."""
        gs = _make_gs(pool=ManaPool(C=5), human="p1",
                      hand=[_make_card(type_line="Creature — Bird", power="2", toughness="2")])
        perm = Permanent(card=_make_card(type_line="Creature — Bird", power="2", toughness="2"),
                         controller="p1")
        gs2 = BuybackKeyword().apply(gs, perm)
        assert gs2 is gs
        assert gs.pending_buyback_choice is None

    def test_noop_unparseable_cost_returns_same_object(self):
        """Bare 'Buyback' with no parseable cost is a no-op."""
        gs = _make_gs(pool=ManaPool(C=5), human="p1",
                      hand=[_make_card(oracle_text="Buyback. Draw a card.")])
        perm = Permanent(card=_make_card(oracle_text="Buyback. Draw a card."), controller="p1")
        gs2 = BuybackKeyword().apply(gs, perm)
        assert gs2 is gs
        assert gs.pending_buyback_choice is None

    def test_keyword_list_detection(self):
        """Detection works via the keywords list as well as oracle text."""
        card = _make_card(keywords=["buyback"])
        gs = _make_gs(pool=ManaPool(W=1, C=5), human="p1", hand=[card])
        gs2 = BuybackKeyword().apply(gs, Permanent(card=card, controller="p1"))
        assert gs2.pending_buyback_choice is not None
        assert gs2.pending_buyback_choice["buyback_cost"] == "{4}"


# ─── cast_spell — payment flow + placeholder regression ──────────────────────

class TestCastSpellBuyback:
    def test_buyback_paid_marks_stack_and_deducts_combined_cost(self):
        """buyback_paid=True: base + buyback deducted, stack marked paid."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        gs = cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=True)
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is True
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0  # base {1}{W}: W pip
        assert p1.mana_pool.C == 0  # generic 1 (base) + 4 (buyback)
        assert all(c.id != "wom-1" for c in p1.hand)

    def test_buyback_paid_false_not_marked_placeholder_regression(self):
        """REGRESSION: the old placeholder marked buyback_paid=True whenever the
        card merely HAD buyback. With the flag False the stack object must be
        unmarked and only the base cost deducted."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        gs = cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=False)
        assert gs.stack[0].buyback_paid is False
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0  # base W pip
        assert p1.mana_pool.C == 4  # only the 1 generic base pip deducted

    def test_buyback_paid_empty_payment_topped_up_from_pool(self):
        """An empty payment is topped up from the pool to cover base+buyback."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        gs = cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=True)
        assert gs.stack[0].buyback_paid is True
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0
        assert p1.mana_pool.C == 0

    def test_buyback_paid_insufficient_mana_raises(self):
        """buyback_paid=True with an unpayable combined cost raises ValueError."""
        gs = _make_gs(pool=ManaPool(W=1, C=1))  # base only
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=True)
        # No spell on the stack, card still in hand.
        assert gs.stack == []
        p1 = next(p for p in gs.players if p.name == "p1")
        assert any(c.id == "wom-1" for c in p1.hand)

    def test_buyback_from_graveyard_ignored(self):
        """The buyback append does not apply to graveyard casts."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        p1 = next(p for p in gs.players if p.name == "p1")
        card = p1.hand[0]
        p1.hand[:] = []
        p1.graveyard.append(card)
        gs = cast_spell(gs, "p1", "wom-1", [], {}, from_graveyard=True, buyback_paid=True)
        # from_graveyard without an alternative cost is aftermath-style; the
        # buyback cost must NOT have been appended (only base deducted).
        p1_after = next(p for p in gs.players if p.name == "p1")
        assert p1_after.mana_pool.C == 4  # 1 generic base only


# ─── resolve_top — CR 702.28 destination ─────────────────────────────────────

class TestResolveTopBuyback:
    def test_paid_spell_returns_to_hand(self):
        """A paid buyback spell returns to its owner's hand on resolution."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        gs = cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=True)
        gs = resolve_top(gs)
        p1 = next(p for p in gs.players if p.name == "p1")
        assert sum(1 for c in p1.hand if c.id == "wom-1") == 1
        assert sum(1 for c in p1.graveyard if c.id == "wom-1") == 0
        assert gs.stack == []

    def test_unpaid_spell_goes_to_graveyard(self):
        """An unpaid buyback spell goes to the graveyard on resolution."""
        gs = _make_gs(pool=ManaPool(W=1, C=5))
        gs = cast_spell(gs, "p1", "wom-1", [], {}, buyback_paid=False)
        gs = resolve_top(gs)
        p1 = next(p for p in gs.players if p.name == "p1")
        assert sum(1 for c in p1.hand if c.id == "wom-1") == 0
        assert sum(1 for c in p1.graveyard if c.id == "wom-1") == 1
        assert gs.stack == []


# ─── API surface — TestClient ────────────────────────────────────────────────

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()
    yield
    mgr._games.clear()
    mgr._recorders.clear()


def _create_buyback_game(pool=None, human="p1") -> str:
    """Create a game with Whispers of the Muse in p1's hand and p1 holding
    priority in the main phase (sorcery speed). Mirrors the ward endpoint
    test setup: real decks via the API, then a targeted state mutation."""
    resp = client.post(
        "/game",
        json={
            "player1_name": "p1",
            "player2_name": "p2",
            "deck1": ["Forest"] * 60,
            "deck2": ["Island"] * 60,
            "seed": 7,
        },
    )
    assert resp.status_code == 200, resp.text
    game_id = resp.json()["data"]["game_id"]

    mgr = get_manager()
    gs = mgr._games[game_id]

    if pool is None:
        # Enough for base {1}{W} + buyback {4}.
        pool = ManaPool(W=1, C=5)

    players = list(gs.players)
    p1 = players[0].model_copy(update={
        "hand": [Card(**_make_card().model_dump())],
        "mana_pool": pool,
    })
    players[0] = p1
    update = {
        "players": players,
        "phase": Phase.PRECOMBAT_MAIN,
        "step": Step.MAIN,
        "priority_holder": "p1",
        "active_player": "p1",
        "mulligan_phase_active": False,
    }
    if human is not None:
        update["human_player_name"] = human
    gs = gs.model_copy(update=update)
    mgr._games[game_id] = gs
    return game_id


class TestBuybackApi:
    def test_cast_defers_and_queues_pending_for_human(self):
        """POST /cast on a human buyback sorcery defers the cast and queues
        pending_buyback_choice — the card stays in hand, nothing on the stack."""
        game_id = _create_buyback_game()

        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is not None
        assert gs.pending_buyback_choice["player"] == "p1"
        assert gs.pending_buyback_choice["buyback_cost"] == "{4}"
        assert gs.pending_buyback_choice["resolved"] is False
        # The cast is deferred: card still in hand, no spell on the stack.
        p1 = next(p for p in gs.players if p.name == "p1")
        assert any(c.id == "wom-1" for c in p1.hand)
        assert gs.stack == []

    def test_legal_actions_offer_buyback_choices_and_no_pass(self):
        """While the buyback choice is pending, legal actions offer
        buyback_pay + buyback_pass and NO pass (the cast cannot be left
        dangling — same mandatory-decision pattern as Ward)."""
        game_id = _create_buyback_game()
        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        la = client.get(f"/game/{game_id}/legal-actions")
        assert la.status_code == 200, la.text
        actions = la.json()["data"]["legal_actions"]
        names = [a.get("card_name") for a in actions]
        assert "buyback_pay" in names
        assert "buyback_pass" in names
        assert not any(a.get("action_type") == "pass" for a in actions)

    def test_buyback_pay_full_flow_returns_to_hand(self):
        """Full flow: cast → buyback_pay → pass → resolution. The spell
        resolves with the effect applied, the card returns to p1's hand,
        and base + buyback mana was deducted."""
        game_id = _create_buyback_game()
        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "buyback_pay"})
        assert resp.status_code == 200, resp.text
        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is None
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is True
        # Base + buyback deducted immediately at cast time.
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0
        assert p1.mana_pool.C == 0

        # Active player passes; the AI opponent auto-passes → resolve_top.
        resp = client.post(f"/game/{game_id}/pass", json={})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.stack == []
        p1 = next(p for p in gs.players if p.name == "p1")
        assert sum(1 for c in p1.hand if c.id == "wom-1") == 1
        assert sum(1 for c in p1.graveyard if c.id == "wom-1") == 0

    def test_buyback_pass_full_flow_goes_to_graveyard(self):
        """Full flow: cast → buyback_pass → pass → resolution. The card goes
        to the graveyard and only the base cost was deducted."""
        game_id = _create_buyback_game()
        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "buyback_pass"})
        assert resp.status_code == 200, resp.text
        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is None
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is False
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0
        assert p1.mana_pool.C == 4  # only the 1 generic base pip deducted

        resp = client.post(f"/game/{game_id}/pass", json={})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.stack == []
        p1 = next(p for p in gs.players if p.name == "p1")
        assert sum(1 for c in p1.hand if c.id == "wom-1") == 0
        assert sum(1 for c in p1.graveyard if c.id == "wom-1") == 1

    def test_buyback_pay_insufficient_mana_rejected_and_pending_kept(self):
        """buyback_pay with an unpayable combined cost is rejected with
        INSUFFICIENT_MANA and the pending choice is KEPT (the player must
        then pick buyback_pass — the cast cannot complete without the
        decision)."""
        game_id = _create_buyback_game(pool=ManaPool(W=1, C=1))  # base only
        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "buyback_pay"})
        assert resp.status_code == 422, resp.text
        assert "INSUFFICIENT_MANA" in resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is not None
        assert gs.pending_buyback_choice["player"] == "p1"
        # Cast still deferred.
        assert gs.stack == []
        p1 = next(p for p in gs.players if p.name == "p1")
        assert any(c.id == "wom-1" for c in p1.hand)

        # The player can still decline buyback and complete the cast.
        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "buyback_pass"})
        assert resp.status_code == 200, resp.text
        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is None
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is False

    def test_ai_cast_auto_resolves_buyback(self):
        """An AI caster auto-resolves the buyback decision at cast time: the
        spell goes straight onto the stack (no pending choice) with the
        heuristic decision, and pending_buyback_choice is cleared."""
        game_id = _create_buyback_game(human=None)  # no human → AI path

        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is None  # auto-resolved, cleared
        assert len(gs.stack) == 1
        # Pool W=1 C=5 covers base {1}{W} + buyback {4} → AI pays.
        assert gs.stack[0].buyback_paid is True
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0
        assert p1.mana_pool.C == 0

    def test_ai_cast_unaffordable_declines_buyback(self):
        """An AI caster that cannot afford base+buyback declines: the spell
        is cast without the buyback flag and only the base cost is deducted."""
        game_id = _create_buyback_game(pool=ManaPool(W=1, C=1), human=None)

        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "wom-1"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_buyback_choice is None
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is False
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.W == 0
        assert p1.mana_pool.C == 0

    def test_non_buyback_cast_unaffected(self):
        """A plain sorcery without buyback casts normally (no pending choice,
    no buyback flag) — the interception is a no-op for other spells."""
        game_id = _create_buyback_game()
        # Replace the buyback card in hand with a plain sorcery.
        mgr = get_manager()
        gs = mgr._games[game_id]
        players = list(gs.players)
        plain = Card(id="plain-1", name="Plain Sorcery", mana_cost="{1}",
                     type_line="Sorcery", oracle_text="Draw a card.")
        p1 = players[0].model_copy(update={"hand": [plain]})
        players[0] = p1
        gs = gs.model_copy(update={"players": players})
        mgr._games[game_id] = gs

        resp = client.post(f"/game/{game_id}/cast", json={"card_id": "plain-1"})
        assert resp.status_code == 200, resp.text

        gs = mgr._games[game_id]
        assert gs.pending_buyback_choice is None
        assert len(gs.stack) == 1
        assert gs.stack[0].buyback_paid is False
