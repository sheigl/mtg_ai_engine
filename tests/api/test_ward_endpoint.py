"""
Story 7-5e: Ward keyword (CR 702.145) — API-level tests.

``tests/engine/test_ward_integration.py`` exercises the Ward engine logic
directly (pure-transform contract, self-targeting guard, AI auto-resolve).
This file closes the gap on the HTTP surface:

* a human queues ``pending_ward_payment`` via a REAL ``POST /cast`` at an
  opponent's ward permanent,
* ``ward_pay`` with sufficient mana lets the spell continue and deducts the
  ward cost,
* ``ward_pay`` with INSUFFICIENT mana is rejected with INSUFFICIENT_MANA and
  the pending ward is KEPT (CR 702.145a — the counter is mandatory; the
  player must then pick ``ward_counter``),
* ``ward_counter`` counters the spell (removed from the stack, source card to
  the caster's graveyard),
* the ward legal actions do NOT include ``pass`` (Ward is mandatory —
  "do nothing" is not a legal outcome).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.api.routers.game import get_manager
from mtg_engine.models.game import Card, ManaPool, Permanent, Phase, Step

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()
    yield
    mgr._games.clear()
    mgr._recorders.clear()


_BOLT = Card(
    name="Bolt",
    id="bolt-1",
    mana_cost="{R}",
    type_line="Instant",
    oracle_text="Deal 3 damage to any target.",
)


def _ward_perm() -> Permanent:
    """A ward permanent controlled by p2 (Ward {2}, the story's example cost)."""
    return Permanent(
        id=f"ward-{uuid.uuid4()}",
        card=Card(
            name="Silver Scourge",
            mana_cost="{1}{G}",
            type_line="Legendary Creature — Elemental Wolf",
            power="2",
            toughness="2",
            keywords=["ward"],
            oracle_text="Ward {2}",
        ),
        controller="p2",
    )


def _create_ward_game(pool: ManaPool | None = None) -> tuple[str, str]:
    """Create a game with Bolt in p1 (human)'s hand, a ward permanent under
    p2's control on the battlefield, and p1 holding priority in the main
    phase. Returns (game_id, ward_permanent_id)."""
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

    # Default: enough to cast Bolt {R} and then pay Ward {2} from colorless.
    if pool is None:
        pool = ManaPool(R=1, C=2)

    players = list(gs.players)
    p1 = players[0].model_copy(update={"hand": [Card(**_BOLT.model_dump())], "mana_pool": pool})
    players[0] = p1
    ward = _ward_perm()
    gs = gs.model_copy(
        update={
            "players": players,
            "human_player_name": "p1",
            "phase": Phase.PRECOMBAT_MAIN,
            "step": Step.MAIN,
            "priority_holder": "p1",
            "active_player": "p1",
            "mulligan_phase_active": False,
        }
    )
    gs.battlefield.append(ward)
    mgr._games[game_id] = gs
    return game_id, ward.id


def _cast_bolt_at_ward(game_id: str, ward_id: str) -> None:
    resp = client.post(
        f"/game/{game_id}/cast",
        json={"card_id": "bolt-1", "targets": [ward_id], "mana_payment": {"R": 1}},
    )
    assert resp.status_code == 200, resp.text


class TestWardEndpoint:
    def test_cast_at_ward_queues_payment_for_human(self):
        """(a) A human casting a spell at an opponent's ward permanent queues
        pending_ward_payment via the real POST /cast route."""
        game_id, ward_id = _create_ward_game()

        _cast_bolt_at_ward(game_id, ward_id)

        gs = get_manager()._games[game_id]
        assert gs.pending_ward_payment is not None
        assert gs.pending_ward_payment["player"] == "p1"
        assert gs.pending_ward_payment["ward_cost"] == "{2}"
        # The spell is on the stack awaiting the pay/counter decision...
        assert any(s.source_card.name == "Bolt" for s in gs.stack)
        # ...and the cast cost {R} was deducted.
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.R == 0
        assert p1.mana_pool.C == 2

    def test_ward_pay_sufficient_mana_lets_spell_continue(self):
        """(b) ward_pay with sufficient mana: the spell continues on the stack
        and the ward cost is deducted from the payer's pool."""
        game_id, ward_id = _create_ward_game()  # pool R=1 (cast) + C=2 (ward)
        _cast_bolt_at_ward(game_id, ward_id)

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_pay"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_ward_payment is None
        # Spell continues uncountered.
        assert any(s.source_card.name == "Bolt" for s in gs.stack)
        # Ward {2} (generic) deducted from the pool.
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.C == 0

    def test_ward_pay_insufficient_mana_rejected_and_pending_kept(self):
        """(c) ward_pay with INSUFFICIENT mana is rejected (INSUFFICIENT_MANA)
        and the pending ward is KEPT — CR 702.145a makes the counter mandatory
        when the cost is not paid, so the player must then pick ward_counter.
        Regression test for the handler that previously cleared the pending
        state unconditionally and let the spell through for free."""
        game_id, ward_id = _create_ward_game(pool=ManaPool(R=1, C=1))  # C=1 < Ward {2}
        _cast_bolt_at_ward(game_id, ward_id)

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_pay"})
        assert resp.status_code == 422, resp.text
        assert "INSUFFICIENT_MANA" in resp.text

        gs = get_manager()._games[game_id]
        # Pending ward NOT cleared — the decision is still outstanding.
        assert gs.pending_ward_payment is not None
        assert gs.pending_ward_payment["player"] == "p1"
        # Spell still on the stack, uncountered.
        assert any(s.source_card.name == "Bolt" for s in gs.stack)

    def test_ward_counter_counters_spell(self):
        """(d) ward_counter removes the spell from the stack and moves its
        source card to the caster's graveyard (CR 702.157b)."""
        game_id, ward_id = _create_ward_game()
        _cast_bolt_at_ward(game_id, ward_id)

        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "ward_counter"})
        assert resp.status_code == 200, resp.text

        gs = get_manager()._games[game_id]
        assert gs.pending_ward_payment is None
        # Spell removed from the stack...
        assert not any(s.source_card.name == "Bolt" for s in gs.stack)
        # ...and its source card is in the caster's graveyard.
        p1 = next(p for p in gs.players if p.name == "p1")
        assert any(c.name == "Bolt" for c in p1.graveyard)

    def test_ward_legal_actions_do_not_include_pass(self):
        """(e) While a ward payment is pending, the legal actions offer only
        ward_pay and ward_counter — NO pass. Ward is mandatory (CR 702.145a);
        offering pass would let the spell resolve uncountered with
        pending_ward_payment dangling. Regression test for the legal-action
        branch that previously appended a pass action."""
        game_id, ward_id = _create_ward_game()
        _cast_bolt_at_ward(game_id, ward_id)

        la = client.get(f"/game/{game_id}/legal-actions")
        assert la.status_code == 200, la.text
        actions = la.json()["data"]["legal_actions"]
        names = [a.get("card_name") for a in actions]
        assert "ward_pay" in names
        assert "ward_counter" in names
        assert not any(a.get("action_type") == "pass" for a in actions)
