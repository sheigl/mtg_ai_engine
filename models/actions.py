from pydantic import BaseModel, Field
from typing import List, Optional


class CastRequest(BaseModel):
    card_name: str
    target: Optional[str] = None
    additional_info: Optional[dict] = None
    dry_run: bool = False


class ActivateRequest(BaseModel):
    ability_name: str
    target: Optional[str] = None
    additional_info: Optional[dict] = None
    dry_run: bool = False


class PlayLandRequest(BaseModel):
    land_name: str
    dry_run: bool = False


class DeclareAttackersRequest(BaseModel):
    attackers: List[str]
    dry_run: bool = False


class DeclareBlockersRequest(BaseModel):
    blockers: List[str]
    dry_run: bool = False


class AssignCombatDamageRequest(BaseModel):
    damage: int
    target: str
    dry_run: bool = False


class ChoiceRequest(BaseModel):
    choices: List[str]
    selected_choice: str
    dry_run: bool = False


class PassRequest(BaseModel):
    dry_run: bool = False


class LegalActionsResponse(BaseModel):
    legal_actions: List[str]
    dry_run: bool = False


class GameStateResponse(BaseModel):
    game_state: dict
    dry_run: bool = False


class ErrorResponse(BaseModel):
    error_message: str
    dry_run: bool = False
    details: Optional[dict] = None