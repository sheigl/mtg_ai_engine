"""API tests for ETB (Enters the Battlefield) choice endpoints (034-etb-choices).

Tests /choice endpoint for etb_pay and etb_tapped choice IDs,
and legal actions when pending_etb_choice exists.
"""

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.models.game import Card, Step, Phase
from mtg_engine.api.routers.game import get_manager

client = TestClient(app)


def _clear_games():
    """Reset the in-memory game manager."""
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()


@pytest.fixture(autouse=True)
def clear_games_fixture():
    """Auto-clear games before each test."""
    _clear_games()
    yield
    _clear_games()


def _create_game_with_human(human="p1", p1_life=20, p2_life=20):
    """Create a game with a human player and shockland in hand.
    
    Returns (game_id, shockland_card_id).
    """
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Steam Vents"] * 60,
        "deck2": ["Forest"] * 60,
        "seed": 42,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    game_id = data["game_id"]
    
    # Set up human player and game state
    mgr = get_manager()
    gs = mgr._games[game_id]
    
    # Set human player name
    gs = gs.model_copy(update={"human_player_name": human})
    
    # Update player life
    players = list(gs.players)
    players[0] = players[0].model_copy(update={"life": p1_life})
    players[1] = players[1].model_copy(update={"life": p2_life})
    gs = gs.model_copy(update={"players": players})
    
    # Create a shockland card and put it in p1's hand
    shockland = Card(
        name="Steam Vents",
        id="card-shockland",
        type_line="Land — Island Mountain",
        oracle_text=(
            "As Steam Vents enters, you may pay 2 life. "
            "If you don't, it enters tapped."
        ),
        controller="p1",
    )
    
    # Replace p1's hand with just the shockland
    p1 = players[0]
    p1 = p1.model_copy(update={"hand": [shockland]})
    players[0] = p1
    gs = gs.model_copy(update={"players": players})
    
    # Advance to main phase (skip mulligan)
    gs = gs.model_copy(update={
        "step": Step.MAIN,
        "phase": Phase.PRECOMBAT_MAIN,
        "priority_holder": "p1",
        "active_player": "p1",
        "mulligan_phase_active": False,
    })
    
    mgr._games[game_id] = gs
    return game_id, shockland.id


def _advance_to_main_phase(game_id):
    """Advance game to main phase by passing mulligan."""
    for _ in range(15):
        state = client.get(f"/game/{game_id}").json()["data"]
        if state["step"] == "main" and state["phase"] == "precombat_main":
            break
        client.post(f"/game/{game_id}/pass", json={"dry_run": False})


# ─── ETB Choice Endpoint: etb_pay ───────────────────────────────────────────

class TestETBPayChoice:
    def test_etb_pay_deducts_life_and_untaps(self):
        """POST /choice with etb_pay deducts life and untaps permanent."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        # Play the land via API
        resp = client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        assert resp.status_code == 200
        
        # Now submit ETB choice
        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_pay"})
        assert resp.status_code == 200
        
        # Check game state
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert gs.pending_etb_choice is None
        assert gs.players[0].life == 18
        perm = gs.battlefield[0]
        assert perm.card.name == "Steam Vents"
        assert not perm.tapped

    def test_etb_pay_returns_200(self):
        """etb_pay returns HTTP 200."""
        game_id, card_id = _create_game_with_human(human="p1")
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_pay"})
        assert resp.status_code == 200


# ─── ETB Choice Endpoint: etb_tapped ───────────────────────────────────────

class TestETBTappedChoice:
    def test_etb_tapped_clears_pending_and_stays_tapped(self):
        """POST /choice with etb_tapped clears pending, permanent stays tapped."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_tapped"})
        assert resp.status_code == 200
        
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert gs.pending_etb_choice is None
        assert gs.players[0].life == 20
        perm = gs.battlefield[0]
        assert perm.tapped is True

    def test_etb_tapped_returns_200(self):
        """etb_tapped returns HTTP 200."""
        game_id, card_id = _create_game_with_human(human="p1")
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        resp = client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_tapped"})
        assert resp.status_code == 200


# ─── Legal Actions with Pending ETB Choice ───────────────────────────────────

class TestLegalActionsPendingETB:
    def test_legal_actions_include_etb_pay_and_etb_tapped(self):
        """When pending_etb_choice exists, legal actions include etb_pay and etb_tapped."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        
        resp = client.get(f"/game/{game_id}/legal-actions")
        assert resp.status_code == 200
        actions = resp.json()["data"]["legal_actions"]
        card_names = [a.get("card_name") for a in actions]
        assert "etb_pay" in card_names
        assert "etb_tapped" in card_names

    def test_legal_actions_include_pass_with_pending_etb(self):
        """When pending_etb_choice exists, legal actions include pass."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        
        resp = client.get(f"/game/{game_id}/legal-actions")
        actions = resp.json()["data"]["legal_actions"]
        action_types = [a.get("action_type") for a in actions]
        assert "pass" in action_types

    @pytest.mark.skip(reason="Checkland ETB legal actions not fully implemented")
    def test_legal_actions_checkland_not_fully_implemented(self):
        """Placeholder: checkland legal actions have TODO in source."""
        pass

    @pytest.mark.skip(reason="Fetchland ETB legal actions not fully implemented")
    def test_legal_actions_fetchland_not_fully_implemented(self):
        """Placeholder: fetchland legal actions have TODO in source."""
        pass

    @pytest.mark.skip(reason="Snow dual ETB legal actions not fully implemented")
    def test_legal_actions_snow_dual_not_fully_implemented(self):
        """Placeholder: snow dual legal actions have TODO in source."""
        pass


# ─── Game State After ETB Choice ─────────────────────────────────────────────

class TestGameStateAfterETB:
    def test_game_state_has_no_pending_after_etb_pay(self):
        """After etb_pay, pending_etb_choice is None."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_pay"})
        
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert gs.pending_etb_choice is None

    def test_game_state_has_no_pending_after_etb_tapped(self):
        """After etb_tapped, pending_etb_choice is None."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_tapped"})
        
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert gs.pending_etb_choice is None

    def test_game_state_battlefield_has_permanent_after_etb_pay(self):
        """After etb_pay, battlefield has the permanent."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_pay"})
        
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert len(gs.battlefield) == 1
        assert gs.battlefield[0].card.name == "Steam Vents"
        assert not gs.battlefield[0].tapped

    def test_game_state_battlefield_has_permanent_after_etb_tapped(self):
        """After etb_tapped, battlefield has the permanent tapped."""
        game_id, card_id = _create_game_with_human(human="p1")
        
        client.post(f"/game/{game_id}/play-land", json={"card_id": card_id})
        client.post(f"/game/{game_id}/choice", json={"choice_id": "etb_tapped"})
        
        mgr = get_manager()
        gs = mgr._games[game_id]
        assert len(gs.battlefield) == 1
        assert gs.battlefield[0].card.name == "Steam Vents"
        assert gs.battlefield[0].tapped is True
