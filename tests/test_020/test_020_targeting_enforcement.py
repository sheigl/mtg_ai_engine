"""
User Story 2: Enforce hexproof, shroud, and protection (DEBT) on all targeting endpoints.

Acceptance Criteria:
1. Hexproof: Permanent's controller's opponents cannot target it with spells/abilities
2. Shroud: No player (including controller) can target a permanent with shroud
3. Protection: Cannot target a permanent with protection from a matching quality
   - Quality matching per CR 702.16: color, type, CMC, controller
4. Return clear error messages for illegal targets
5. Apply to /cast, /activate, /put_trigger endpoints

CR References:
- CR 702.11: Hexproof
- CR 702.18: Shroud  
- CR 702.16: Protection
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Permanent, Card
# set_priority not needed for these tests


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.11", "702.18", "702.16")
class TestTargetingHexproof:
    """Test hexproof targeting rules (CR 702.11)."""

    def test_hexproof_opponent_cannot_target(self, game_with_two_players):
        """Scenario 1: Opponent cannot target hexproof permanent with spell."""
        gs = game_with_two_players
        
        # Add hexproof creature to player_2's side
        hexproof_creature = Permanent(
            id="hexproof_thing",
            name="Hexproof Beast",
            card=Card(
                name="Hexproof Beast",
                mana_cost="{1}{G}",
                type_line="Creature — Beast",
                power="2",
                toughness="2",
                keywords=["hexproof"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(hexproof_creature)
        
        # player_1 trying to target opponent's hexproof - should fail
        from mtg_engine.api.routers.game import _validate_targets
        
        # Use a spell card (not the creature's card)
        spell_card = Card(name="Lightning Strike", mana_cost="{R}", type_line="Instant")
        
        with pytest.raises(ValueError, match="has hexproof or shroud"):
            _validate_targets(gs, ["hexproof_thing"], spell_card, "player_1")

    def test_hexproof_controller_can_target(self, game_with_two_players):
        """Scenario 2: Controller can target their own hexproof permanent."""
        gs = game_with_two_players
        caster = "player_1"
        
        # Add hexproof creature to caster's side
        hexproof_creature = Permanent(
            id="my_hexproof",
            name="My Hexproof Beast",
            card=Card(
                name="My Hexproof Beast",
                mana_cost="{1}{G}",
                type_line="Creature — Beast",
                power="2",
                toughness="2",
                keywords=["hexproof"],
            ),
            controller=caster,
            zone="battlefield",
        )
        gs.battlefield.append(hexproof_creature)
        
        # Controller targeting their own hexproof - should succeed
        from mtg_engine.api.routers.game import _validate_targets
        
        # No exception should be raised
        _validate_targets(gs, ["my_hexproof"], hexproof_creature.card, caster)

    def test_hexproof_non_target_abilities_untouched(self, game_with_two_players):
        """Scenario 3: Hexproof doesn't affect non-targeting effects."""
        gs = game_with_two_players
        
        # Add hexproof creature to opponent
        opponent = gs.players[1]
        hexproof_creature = Permanent(
            id="opp_hexproof",
            name="Hexproof Beast",
            card=Card(
                name="Hexproof Beast",
                mana_cost="{1}{G}",
                type_line="Creature — Beast",
                power="2",
                toughness="2",
                keywords=["hexproof"],
            ),
            controller=opponent.name,
            zone="battlefield",
        )
        gs.battlefield.append(hexproof_creature)
        
        # Non-targeting board wipe (no targets specified) should work
        from mtg_engine.api.routers.game import _validate_targets
        
        # Empty targets list - should succeed
        _validate_targets(gs, [], hexproof_creature.card, gs.players[0].name)


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.18")
class TestTargetingShroud:
    """Test shroud targeting rules (CR 702.18)."""

    def test_shroud_no_one_can_target(self, game_with_two_players):
        """Scenario 1: No player (including controller) can target shroud permanent."""
        gs = game_with_two_players
        caster = "player_1"
        
        # Add shroud creature to caster's side
        shroud_creature = Permanent(
            id="my_shroud",
            name="Shrouded Entity",
            card=Card(
                name="Shrouded Entity",
                mana_cost="{2}{U}",
                type_line="Creature — Spirit",
                power="3",
                toughness="3",
                keywords=["shroud"],
            ),
            controller=caster,
            zone="battlefield",
        )
        gs.battlefield.append(shroud_creature)
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # Even controller cannot target
        with pytest.raises(ValueError, match="has hexproof or shroud"):
            _validate_targets(gs, ["my_shroud"], shroud_creature.card, caster)
        
        # Opponent also cannot target
        with pytest.raises(ValueError, match="has hexproof or shroud"):
            _validate_targets(gs, ["my_shroud"], shroud_creature.card, "player_2")

    def test_shroud_vs_hexproof_combined(self, game_with_two_players):
        """Scenario 2: Permanent with both hexproof and shroud (redundant but valid)."""
        gs = game_with_two_players
        
        # Add creature with both
        dual_protect = Permanent(
            id="dual_protect",
            name="Protected Entity",
            card=Card(
                name="Protected Entity",
                mana_cost="{3}",
                type_line="Creature — Artifact Creature",
                power="4",
                toughness="4",
                keywords=["hexproof", "shroud"],
            ),
            controller="player_1",
            zone="battlefield",
        )
        gs.battlefield.append(dual_protect)
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # No one can target
        for player_name in ["player_1", "player_2"]:
            with pytest.raises(ValueError, match="has hexproof or shroud"):
                _validate_targets(gs, ["dual_protect"], dual_protect.card, player_name)


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.16")
class TestTargetingProtection:
    """Test protection targeting rules (CR 702.16)."""

    def test_protection_from_color(self, game_with_two_players):
        """Scenario 1: Cannot target creature with protection from red with red spell."""
        gs = game_with_two_players
        
        # Target has protection from red
        protected_creature = Permanent(
            id="protected_target",
            name="Protected Guardian",
            card=Card(
                name="Protected Guardian",
                mana_cost="{2}{W}",
                type_line="Creature — Human Warrior",
                power="3",
                toughness="3",
                keywords=["protection from red"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(protected_creature)
        
        # Red source (Lightning Bolt)
        red_spell_card = Card(
            name="Lightning Bolt",
            mana_cost="{R}",
            type_line="Instant",
        )
        
        from mtg_engine.api.routers.game import _validate_targets
        
        with pytest.raises(ValueError, match="has protection from red"):
            _validate_targets(gs, ["protected_target"], red_spell_card, "player_1")

    def test_protection_from_color_unrelated_ok(self, game_with_two_players):
        """Scenario 2: Can target creature with protection from red with blue spell."""
        gs = game_with_two_players
        
        # Target has protection from red
        protected_creature = Permanent(
            id="protected_target",
            name="Protected Guardian",
            card=Card(
                name="Protected Guardian",
                mana_cost="{2}{W}",
                type_line="Creature — Human Warrior",
                power="3",
                toughness="3",
                keywords=["protection from red"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(protected_creature)
        
        # Blue source (Counterspell)
        blue_spell_card = Card(
            name="Counterspell",
            mana_cost="{U}{U}",
            type_line="Instant",
        )
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # Should succeed - blue doesn't match protection from red
        _validate_targets(gs, ["protected_target"], blue_spell_card, "player_1")

    def test_protection_from_type(self, game_with_two_players):
        """Scenario 3: Cannot target creature with protection from creatures with creature spell."""
        gs = game_with_two_players
        
        # Target has protection from creatures
        protected_creature = Permanent(
            id="protected_target",
            name="Anointed Procession",
            card=Card(
                name="Anointed Procession",
                mana_cost="{2}{W}",
                type_line="Creature — Human Cleric",
                power="2",
                toughness="3",
                keywords=["protection from creatures"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(protected_creature)
        
        # Creature spell (same type)
        creature_spell_card = Card(
            name="Giant Growth",
            mana_cost="{R}",
            type_line="Creature — Beast",
        )
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # The spell's type line should be checked
        with pytest.raises(ValueError, match="has protection from"):
            _validate_targets(gs, ["protected_target"], creature_spell_card, "player_1")

    def test_protection_from_everything(self, game_with_two_players):
        """Scenario 4: Cannot target creature with protection from everything with anything."""
        gs = game_with_two_players
        
        # Target has protection from everything
        protected_creature = Permanent(
            id="protected_target",
            name="Progenitus",
            card=Card(
                name="Progenitus",
                mana_cost="{5}{U}{U}{B}{B}{R}{R}{W}{W}",
                type_line="Creature — Beast",
                power="6",
                toughness="6",
                keywords=["protection from everything"],
            ),
            controller="player_2",
            zone="battlefield",
        )
        gs.battlefield.append(protected_creature)
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # Any spell should fail
        any_spell = Card(name="Random Spell", mana_cost="{1}", type_line="Instant")
        
        with pytest.raises(ValueError, match="has protection from everything"):
            _validate_targets(gs, ["protected_target"], any_spell, "player_1")

    def test_protection_same_controller(self, game_with_two_players):
        """Scenario 5: Protection doesn't prevent self-targeting."""
        gs = game_with_two_players
        
        # Your own protected creature
        protected_creature = Permanent(
            id="my_protected",
            name="My Protector",
            card=Card(
                name="My Protector",
                mana_cost="{W}",
                type_line="Creature — Human Soldier",
                power="1",
                toughness="1",
                keywords=["protection from black"],
            ),
            controller="player_1",
            zone="battlefield",
        )
        gs.battlefield.append(protected_creature)
        
        # White source (your own spell)
        white_spell = Card(
            name="Sacred Foundry",
            mana_cost="{W}",
            type_line="Instant",
        )
        
        from mtg_engine.api.routers.game import _validate_targets
        
        # Same controller can target (protection only affects opponents)
        _validate_targets(gs, ["my_protected"], white_spell, "player_1")
