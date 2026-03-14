import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.actions import (
    CastRequest, ActivateRequest, PlayLandRequest,
    DeclareAttackersRequest, DeclareBlockersRequest,
    AssignCombatDamageRequest, ChoiceRequest, PassRequest,
    AttackDeclaration, BlockDeclaration, DamageAssignment,
)


def test_cast_request():
    req = CastRequest(card_id="abc123", targets=["creature_456"], mana_payment={"R": 1})
    assert req.card_id == "abc123"
    assert req.targets == ["creature_456"]
    assert req.mana_payment == {"R": 1}
    assert req.dry_run is False
    # JSON round-trip
    data = req.model_dump_json()
    req2 = CastRequest.model_validate_json(data)
    assert req2.card_id == req.card_id


def test_cast_request_dry_run():
    req = CastRequest(card_id="abc123", dry_run=True)
    assert req.dry_run is True


def test_activate_request():
    req = ActivateRequest(permanent_id="perm_1", ability_index=0, mana_payment={"G": 1})
    assert req.permanent_id == "perm_1"
    assert req.ability_index == 0
    assert req.dry_run is False


def test_play_land_request():
    req = PlayLandRequest(card_id="forest_1")
    assert req.card_id == "forest_1"
    assert req.dry_run is False


def test_declare_attackers_request():
    decls = [AttackDeclaration(attacker_id="creature_1", defending_id="player_2")]
    req = DeclareAttackersRequest(attack_declarations=decls)
    assert len(req.attack_declarations) == 1
    assert req.attack_declarations[0].attacker_id == "creature_1"


def test_declare_blockers_request():
    decls = [BlockDeclaration(blocker_id="creature_2", attacker_id="creature_1")]
    req = DeclareBlockersRequest(block_declarations=decls)
    assert req.block_declarations[0].blocker_id == "creature_2"


def test_assign_combat_damage_request():
    assignments = [DamageAssignment(source_id="attacker_1", target_id="player_2", damage=3)]
    req = AssignCombatDamageRequest(assignments=assignments)
    assert req.assignments[0].damage == 3


def test_choice_request():
    req = ChoiceRequest(choice_id="choice_1", selection="option_a")
    assert req.choice_id == "choice_1"
    assert req.selection == "option_a"


def test_pass_request():
    req = PassRequest()
    assert req.dry_run is False
    req2 = PassRequest(dry_run=True)
    assert req2.dry_run is True
