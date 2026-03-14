from pathlib import Path
import pytest
from pydantic import BaseModel
from mtg_ai_engine.models.actions import (CastRequest, ActivateRequest, PlayLandRequest, DeclareAttackersRequest, DeclareBlockersRequest, AssignCombatDamageRequest, ChoiceRequest, PassRequest, LegalActionsResponse, GameStateResponse, ErrorResponse)

# Test cases for action request/response models

def test_cast_request():
    request = CastRequest(card_name="Lightning Bolt", target="creature123", additional_info={"mode": "direct"}, dry_run=True)
    assert request.card_name == "Lightning Bolt"
    assert request.target == "creature123"
    assert request.additional_info == {"mode": "direct"}
    assert request.dry_run is True

def test_activate_request():
    request = ActivateRequest(ability_name="Flash", target="creature456", additional_info={"mode": "instant"}, dry_run=True)
    assert request.ability_name == "Flash"
    assert request.target == "creature456"
    assert request.additional_info == {"mode": "instant"}
    assert request.dry_run is True

def test_play_land_request():
    request = PlayLandRequest(land_name="Forest", dry_run=True)
    assert request.land_name == "Forest"
    assert request.dry_run is True

def test_declare_attackers_request():
    request = DeclareAttackersRequest(attackers=["creature123", "creature456"], dry_run=True)
    assert request.attackers == ["creature123", "creature456"]
    assert request.dry_run is True

def test_declare_blockers_request():
    request = DeclareBlockersRequest(blockers=["creature789", "creature012"], dry_run=True)
    assert request.blockers == ["creature789", "creature012"]
    assert request.dry_run is True

def test_assign_combat_damage_request():
    request = AssignCombatDamageRequest(damage=4, target="player1", dry_run=True)
    assert request.damage == 4
    assert request.target == "player1"
    assert request.dry_run is True

def test_choice_request():
    request = ChoiceRequest(choices=["Option A", "Option B"], selected_choice="Option A", dry_run=True)
    assert request.choices == ["Option A", "Option B"]
    assert request.selected_choice == "Option A"
    assert request.dry_run is True

def test_pass_request():
    request = PassRequest(dry_run=True)
    assert request.dry_run is True

def test_legal_actions_response():
    response = LegalActionsResponse(legal_actions=["Cast Lightning Bolt", "Play Forest"], dry_run=True)
    assert response.legal_actions == ["Cast Lightning Bolt", "Play Forest"]
    assert response.dry_run is True

def test_game_state_response():
    response = GameStateResponse(game_state={"players": [{"name": "Player1", "life": 20}]}, dry_run=True)
    assert response.game_state == {"players": [{"name": "Player1", "life": 20}]}
    assert response.dry_run is True

def test_error_response():
    response = ErrorResponse(error_message="Invalid action", dry_run=True, details={"error_code": 400})
    assert response.error_message == "Invalid action"
    assert response.dry_run is True
    assert response.details == {"error_code": 400}