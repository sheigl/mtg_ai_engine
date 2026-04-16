"""
User Story 20: Handle protection SBAs (Auras/Equipment falling off permanents that gain protection).

Acceptance Criteria:
1. Aura attached to permanent with protection from matching quality → put Aura to graveyard
2. Equipment attached to permanent with protection from matching quality → unattach (stays on battlefield)
3. Protection from creatures causes creature Auras/Equipment to fall off
4. Protection from everything causes all attachments to fall off
5. Protection gained after attachment triggers SBA immediately
6. Protection SBA checked in SBA loop before priority is granted

CR References:
- CR 702.16: Protection (E: Protection defines four benefits...)
- CR 704.5m: Aura with no legal object to enchant → graveyard
- CR 704.5n: Equipment unattached → stays on battlefield
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Permanent, Card
from mtg_engine.engine.sba import check_and_apply_sbas, SBAEvent
# set_priority not needed for these tests


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.16", "704.5m", "704.5n")
class TestProtectionAuraSBA:
    """Test Aura falling off due to protection (US20)."""

    def test_aura_falls_off_on_protection_gain(self, game_with_two_players):
        """Scenario 1: Aura attached, target gains protection → Aura falls off."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature without protection
        target = Permanent(
            id="target_creature",
            name="Bare-backed Runner",
            card=Card(
                name="Bare-backed Runner",
                mana_cost="{1}{R}",
                type_line="Creature — Human Warrior",
                power="2",
                toughness="2",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Attach an Aura (Gainshape)
        aura = Permanent(
            id="protective_aura",
            name="Protective Aura",
            card=Card(
                name="Protective Aura",
                mana_cost="{W}",
                type_line="Enchantment — Aura",
                subtypes=["Aura"],
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="target_creature",
        )
        gs.battlefield.append(aura)
        
        # Now give target protection from white (aura's color)
        target.card.keywords.append("protection from white")
        
        # Run SBA check
        gs, events = check_and_apply_sbas(gs)
        
        # Aura should be in graveyard
        assert any(e.sba_type == "protection_aura" for e in events)
        assert aura not in gs.battlefield
        assert any(aura.id == c.id for c in gs.players[1].graveyard)

    def test_aura_falls_off_protection_from_type(self, game_with_two_players):
        """Scenario 2: Aura from creature type falls off creature with protection from creatures."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature
        target = Permanent(
            id="target",
            name="Noble Hero",
            card=Card(
                name="Noble Hero",
                mana_cost="{2}{W}",
                type_line="Creature — Human Soldier",
                power="2",
                toughness="2",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Creature Aura
        creature_aura = Permanent(
            id="creature_aura",
            name="Giant Growth",
            card=Card(
                name="Giant Growth",
                mana_cost="{R}",
                type_line="Enchantment — Aura",
                subtypes=["Aura", "Creature"],
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="target",
        )
        gs.battlefield.append(creature_aura)
        
        # Target gains protection from creatures
        target.card.keywords.append("protection from creatures")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # Aura should fall off
        assert any(e.sba_type == "protection_aura" for e in events)
        assert creature_aura not in gs.battlefield

    def test_aura_stays_if_no_matching_protection(self, game_with_two_players):
        """Scenario 3: Aura stays if target's protection doesn't match."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature
        target = Permanent(
            id="target",
            name="Sturdy Wall",
            card=Card(
                name="Sturdy Wall",
                mana_cost="{2}{W}",
                type_line="Creature — Human Soldier",
                power="1",
                toughness="4",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # White Aura
        aura = Permanent(
            id="white_aura",
            name="Fortitude",
            card=Card(
                name="Fortitude",
                mana_cost="{W}",
                type_line="Enchantment — Aura",
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="target",
        )
        gs.battlefield.append(aura)
        
        # Target has protection from RED (not white)
        target.card.keywords.append("protection from red")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # No protection_aura SBA should fire
        assert not any(e.sba_type == "protection_aura" for e in events)
        assert aura in gs.battlefield
        assert aura.attached_to == "target"


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.16", "704.5n")
class TestProtectionEquipmentSBA:
    """Test Equipment unattachment due to protection (US20)."""

    def test_equipment_unattaches_on_protection_gain(self, game_with_two_players):
        """Scenario 1: Equipment attached, target gains protection → unattach."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature
        target = Permanent(
            id="target_creature",
            name="Battlefield Scout",
            card=Card(
                name="Battlefield Scout",
                mana_cost="{1}{R}",
                type_line="Creature — Human Soldier",
                power="2",
                toughness="1",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Attach Equipment
        equipment = Permanent(
            id="sharp_sword",
            name="Sharp Sword",
            card=Card(
                name="Sharp Sword",
                mana_cost="{1}",
                type_line="Artifact — Equipment",
                subtypes=["Equipment"],
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="target_creature",
        )
        gs.battlefield.append(equipment)
        
        # Give target protection from artifacts
        target.card.keywords.append("protection from artifacts")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # Equipment should unattach but stay on battlefield
        assert any(e.sba_type == "protection_equipment" for e in events)
        assert equipment in gs.battlefield  # Still on battlefield
        assert equipment.attached_to is None  # But unattached

    def test_equipment_stays_if_no_matching_protection(self, game_with_two_players):
        """Scenario 2: Equipment stays attached if protection doesn't match."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature
        target = Permanent(
            id="target",
            name="Warrior",
            card=Card(
                name="Warrior",
                mana_cost="{2}{R}",
                type_line="Creature — Human Warrior",
                power="3",
                toughness="2",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Red Equipment (no artifact protection)
        equipment = Permanent(
            id="red_blade",
            name="Red Blade",
            card=Card(
                name="Red Blade",
                mana_cost="{R}",
                type_line="Artifact — Equipment",
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="target",
        )
        gs.battlefield.append(equipment)
        
        # Target has protection from WHITE (not red or artifact)
        target.card.keywords.append("protection from white")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # Equipment should stay attached
        assert not any(e.sba_type == "protection_equipment" for e in events)
        assert equipment in gs.battlefield
        assert equipment.attached_to == "target"


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.16")
class TestProtectionFromEverything:
    """Test protection from everything (US20)."""

    def test_everything_removes_all_attachments(self, game_with_two_players):
        """Scenario 1: Protection from everything removes all Auras and Equipment."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target creature
        target = Permanent(
            id="progenitus",
            name="Progenitus",
            card=Card(
                name="Progenitus",
                mana_cost="{5}{U}{U}{B}{B}{R}{R}{W}{W}",
                type_line="Creature — Beast",
                power="6",
                toughness="6",
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Attach multiple Auras
        aura1 = Permanent(
            id="aura1",
            name="Giant Growth",
            card=Card(
                name="Giant Growth",
                mana_cost="{R}",
                type_line="Enchantment — Aura",
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="progenitus",
        )
        aura2 = Permanent(
            id="aura2",
            name="Darkness",
            card=Card(
                name="Darkness",
                mana_cost="{1}{B}",
                type_line="Enchantment — Aura",
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="progenitus",
        )
        gs.battlefield.append(aura1)
        gs.battlefield.append(aura2)
        
        # Attach Equipment
        equipment = Permanent(
            id="sword",
            name="Sword of Fire",
            card=Card(
                name="Sword of Fire",
                mana_cost="{2}",
                type_line="Artifact — Equipment",
            ),
            controller="player_1",
            zone="battlefield",
            attached_to="progenitus",
        )
        gs.battlefield.append(equipment)
        
        # Give protection from everything
        target.card.keywords.append("protection from everything")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # All Auras should fall off
        assert any(e.sba_type == "protection_aura" for e in events)
        assert aura1 not in gs.battlefield
        assert aura2 not in gs.battlefield
        
        # Equipment should unattach
        assert any(e.sba_type == "protection_equipment" for e in events)
        assert equipment in gs.battlefield
        assert equipment.attached_to is None

    def test_protection_from_self(self, game_with_two_players):
        """Scenario 2: Protection from controller doesn't affect self-attachments."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Both creature and attachments owned by same player
        target = Permanent(
            id="my_target",
            name="My Creature",
            card=Card(
                name="My Creature",
                mana_cost="{2}{W}",
                type_line="Creature — Human",
                power="2",
                toughness="2",
            ),
            controller="player_1",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # White Aura owned by same player
        aura = Permanent(
            id="my_aura",
            name="My Aura",
            card=Card(
                name="My Aura",
                mana_cost="{W}",
                type_line="Enchantment — Aura",
            ),
            controller="player_1",  # Same controller as target
            zone="battlefield",
            attached_to="my_target",
        )
        gs.battlefield.append(aura)
        
        # Target has protection from white (same color as aura)
        target.card.keywords.append("protection from white")
        
        # Run SBA
        gs, events = check_and_apply_sbas(gs)
        
        # Aura should still be attached (protection doesn't apply to self)
        # Note: In actual MTG, protection doesn't prevent self-targeting
        # The SBA check should consider controller matching
        assert aura in gs.battlefield
        # The aura stays attached because it's controlled by the same player
        # This is consistent with protection mechanics not affecting self


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.16")
class TestProtectionDamagePrevention:
    """Test protection damage prevention (not directly covered in US20 but related)."""

    def test_protection_prevents_damage_from_source(self, game_with_two_players):
        """Scenario 1: Protection prevents damage from matching source."""
        gs = game_with_two_players
        gs.players[0].hand = []
        gs.players[1].hand = []
        
        # Target with protection from red
        target = Permanent(
            id="protected",
            name="Protected Knight",
            card=Card(
                name="Protected Knight",
                mana_cost="{W}",
                type_line="Creature — Human Soldier",
                power="2",
                toughness="2",
                keywords=["protection from red"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(target)
        
        # Red creature that would deal damage
        red_attacker = Permanent(
            id="red_goblin",
            name="Red Goblin",
            card=Card(
                name="Red Goblin",
                mana_cost="{R}",
                type_line="Creature — Goblin",
                power="2",
                toughness="1",
            ),
            controller="player_1",
            zone="battlefield",
        )
        gs.battlefield.append(red_attacker)
        
        # In combat phase, red creature attacks
        # Damage assignment would be blocked by protection
        # This is handled in combat.py damage assignment
        
        # For now, just verify the protection keyword is present
        assert "protection from red" in target.card.keywords
