"""
User Story 18: Adventure Cards.

Acceptance Criteria:
1. Adventure cast with face_index=1 sets is_adventure=True
2. Adventure resolution exiles card (to adventure_cards, not graveyard)
3. Creature cast from adventure exile after adventure resolves
4. Counter sends adventure to graveyard (not adventure_cards)
5. Legal actions include adventure creature half from exile

CR References:
- CR 702.61: Adventure
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, CardFace, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.api.routers.game import _compute_legal_actions


@pytest.fixture
def adventure_card_game():
    """Create a game with an adventure card in player_1's hand."""
    witch = CardFace(
        name="Witch's Chain",
        mana_cost="{B}",
        type_line="Creature - Spirit",
        oracle_text="Flying",
        power="1",
        toughness="1",
    )
    chain = CardFace(
        name="Chain of Vapor",
        mana_cost="{1}{U}",
        type_line="Instant",
        oracle_text="Counter target spell.",
    )
    adventure = Card(
        name="Witch's Chain // Chain of Vapor",
        mana_cost="{B}{1}{U}",
        type_line="",
        card_layout="adventure",
        faces=[witch, chain],
    )
    return GameState(
        game_id="test_adventure",
        seed=42,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[adventure],
                mana_pool=ManaPool(B=1, U=2),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                mana_pool=ManaPool(U=2),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.fixture
def countered_adventure_game():
    """Create a game where an adventure spell is on the stack, ready to be countered."""
    witch = CardFace(
        name="Witch's Chain",
        mana_cost="{B}",
        type_line="Creature - Spirit",
        oracle_text="Flying",
        power="1",
        toughness="1",
    )
    chain = CardFace(
        name="Chain of Vapor",
        mana_cost="{1}{U}",
        type_line="Instant",
        oracle_text="Counter target spell.",
    )
    adventure = Card(
        name="Witch's Chain // Chain of Vapor",
        mana_cost="{B}{1}{U}",
        type_line="",
        card_layout="adventure",
        faces=[witch, chain],
    )
    countermagic = Card(
        name="Counterspell",
        mana_cost="{U}{U}",
        type_line="Instant",
        oracle_text="Counter target spell.",
    )
    return GameState(
        game_id="test_countered_adventure",
        seed=99,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[adventure],
                mana_pool=ManaPool(B=1, U=2),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
            PlayerState(
                name="player_2",
                life=20,
                hand=[countermagic],
                mana_pool=ManaPool(U=2),
                library=[],
                graveyard=[],
                exile=[],
                command_zone=[],
                deck=[],
            ),
        ],
        turn=1,
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        active_player="player_1",
        priority_holder="player_1",
        stack=[],
        battlefield=[],
        graveyards={"player_1": [], "player_2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.61")
class TestAdventureCastAndResolution:
    """Test adventure spell casting and resolution."""

    def test_adventure_cast_sets_is_adventure_flag(self, adventure_card_game):
        """Scenario 1: Casting adventure half with face_index=1 sets is_adventure=True."""
        gs = adventure_card_game
        card_id = gs.players[0].hand[0].id

        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.is_adventure is True
        assert stack_obj.source_card.name == "Chain of Vapor"
        assert stack_obj.source_card.type_line == "Instant"

        # Card removed from hand
        assert len(gs.players[0].hand) == 0

    def test_adventure_resolution_exiles_to_adventure_cards(self, adventure_card_game):
        """Scenario 2: Resolving adventure spell exiles card to adventure_cards, not graveyard."""
        gs = adventure_card_game
        card_id = gs.players[0].hand[0].id

        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        assert len(gs.stack) == 1
        assert gs.players[0].graveyard == []
        assert gs.players[0].adventure_cards == []

        gs = resolve_top(gs)

        assert len(gs.stack) == 0
        assert gs.players[0].graveyard == []
        assert len(gs.players[0].adventure_cards) == 1
        assert gs.players[0].adventure_cards[0].card_layout == "adventure"

    def test_adventure_resolution_non_adventure_face_goes_to_graveyard(self):
        """Non-adventure instant/sorcery should go to graveyard normally."""
        fire = Card(
            name="Fire",
            mana_cost="{R}",
            type_line="Instant",
            oracle_text="Fire deals 2 damage to any target.",
            card_layout="normal",
        )
        gs = GameState(
            game_id="test_normal_instant",
            seed=1,
            players=[
                PlayerState(
                    name="player_1",
                    life=20,
                    hand=[fire],
                    mana_pool=ManaPool(R=1),
                    library=[],
                    graveyard=[],
                    exile=[],
                    command_zone=[],
                    deck=[],
                ),
                PlayerState(
                    name="player_2",
                    life=20,
                    library=[],
                    graveyard=[],
                    exile=[],
                    command_zone=[],
                    deck=[],
                ),
            ],
            turn=1,
            phase=Phase.PRECOMBAT_MAIN,
            step=Step.MAIN,
            active_player="player_1",
            priority_holder="player_1",
            stack=[],
            battlefield=[],
            graveyards={"player_1": [], "player_2": []},
            exile_zone={},
            pending_triggers=[],
            pending_choices=[],
            is_game_over=False,
            winner=None,
            format="standard",
        )

        card_id = gs.players[0].hand[0].id
        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"R": 1},
        )

        gs = resolve_top(gs)

        assert len(gs.stack) == 0
        assert len(gs.players[0].graveyard) == 1
        assert gs.players[0].adventure_cards == []


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.61")
class TestAdventureCreatureFromExile:
    """Test casting the creature half from adventure exile."""

    def test_creature_cast_from_adventure_exile(self, adventure_card_game):
        """Scenario 3: After adventure resolves, creature half can be cast from exile."""
        gs = adventure_card_game
        card_id = gs.players[0].hand[0].id

        # Cast adventure half
        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        # Resolve adventure
        gs = resolve_top(gs)

        assert len(gs.players[0].adventure_cards) == 1
        adventure_card = gs.players[0].adventure_cards[0]

        # Add mana for creature half
        gs.players[0].mana_pool = ManaPool(B=1)

        # Cast creature half from adventure exile
        gs = cast_spell(
            gs, "player_1", adventure_card.id,
            targets=[],
            mana_payment={"B": 1},
            from_adventure_exile=True,
            face_index=0,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.is_adventure is False
        assert stack_obj.source_card.name == "Witch's Chain"
        assert stack_obj.source_card.type_line == "Creature - Spirit"

        # Card removed from adventure_cards
        assert len(gs.players[0].adventure_cards) == 0

    def test_creature_cast_from_adventure_exile_removes_from_list(self, adventure_card_game):
        """Creature cast from adventure exile removes card from adventure_cards."""
        gs = adventure_card_game
        card_id = gs.players[0].hand[0].id

        # Cast and resolve adventure
        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )
        gs = resolve_top(gs)

        assert len(gs.players[0].adventure_cards) == 1
        adventure_card = gs.players[0].adventure_cards[0]

        gs.players[0].mana_pool = ManaPool(B=1)

        gs = cast_spell(
            gs, "player_1", adventure_card.id,
            targets=[],
            mana_payment={"B": 1},
            from_adventure_exile=True,
            face_index=0,
        )

        assert len(gs.players[0].adventure_cards) == 0
        # Creature should be on the stack now
        assert len(gs.stack) == 1
        assert gs.stack[0].source_card.name == "Witch's Chain"


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.61")
class TestAdventureCountered:
    """Test adventure spell countered behavior."""

    def test_countered_adventure_goes_to_graveyard(self, countered_adventure_game):
        """Scenario 4: Counter spell sends adventure to graveyard, not adventure_cards."""
        gs = countered_adventure_game

        player1 = gs.players[0]
        player2 = gs.players[1]
        adventure_id = player1.hand[0].id
        countermagic_id = player2.hand[0].id

        # Player 1 casts adventure half
        gs = cast_spell(
            gs, "player_1", adventure_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        stack_obj = gs.stack[0]

        # Grant priority to player_2 so they can respond
        gs.priority_holder = "player_2"

        # Player 2 counters the adventure spell
        gs = cast_spell(
            gs, "player_2", countermagic_id,
            targets=[stack_obj.id],
            mana_payment={"U": 2},
        )

        # Resolve countermagic first
        gs = resolve_top(gs)

        # Now the adventure spell is countered and should be in graveyard
        gs = resolve_top(gs)

        assert len(gs.players[0].graveyard) == 1
        assert gs.players[0].graveyard[0].name == "Chain of Vapor"
        assert len(gs.players[0].adventure_cards) == 0


    def test_countered_adventure_no_creature_available(self, countered_adventure_game):
        """Countered adventure does not make creature half available."""
        gs = countered_adventure_game

        player1 = gs.players[0]
        adventure_id = player1.hand[0].id

        # Player 1 casts adventure half
        gs = cast_spell(
            gs, "player_1", adventure_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        stack_obj = gs.stack[0]

        # Grant priority to player_2 so they can respond
        gs.priority_holder = "player_2"

        # Player 2 counters
        gs = cast_spell(
            gs, "player_2", gs.players[1].hand[0].id,
            targets=[stack_obj.id],
            mana_payment={"U": 2},
        )

        # Resolve countermagic first
        gs = resolve_top(gs)

        # Now the adventure spell is countered and should be in graveyard
        gs = resolve_top(gs)

        assert len(gs.players[0].graveyard) == 1
        assert gs.players[0].graveyard[0].name == "Chain of Vapor"
        assert len(gs.players[0].adventure_cards) == 0

    def test_countered_adventure_no_creature_available(self, countered_adventure_game):
        """Countered adventure does not make creature half available."""
        gs = countered_adventure_game

        player1 = gs.players[0]
        adventure_id = player1.hand[0].id

        # Player 1 casts adventure half
        gs = cast_spell(
            gs, "player_1", adventure_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )

        stack_obj = gs.stack[0]

        # Grant priority to player_2 so they can respond
        gs.priority_holder = "player_2"

        # Player 2 counters
        gs = cast_spell(
            gs, "player_2", gs.players[1].hand[0].id,
            targets=[stack_obj.id],
            mana_payment={"U": 2},
        )

        # Resolve countermagic
        gs = resolve_top(gs)

        # Resolve countered adventure (goes to graveyard)
        gs = resolve_top(gs)

        # No adventure_cards available
        assert len(gs.players[0].adventure_cards) == 0


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.61")
class TestAdventureLegalActions:
    """Test legal actions for adventure cards."""

    def test_legal_actions_include_adventure_creature_from_exile(self, adventure_card_game):
        """Scenario 5: After adventure resolves, legal actions include casting creature from exile."""
        gs = adventure_card_game
        card_id = gs.players[0].hand[0].id

        # Cast and resolve adventure half
        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"U": 2},
            face_index=1,
        )
        gs = resolve_top(gs)

        # Add mana for creature half
        gs.players[0].mana_pool = ManaPool(B=1)

        # Refresh state hash (required by _compute_legal_actions)
        gs = gs.refresh_hash()

        actions = _compute_legal_actions(gs)

        # Should include casting the creature half from adventure exile
        adventure_card = gs.players[0].adventure_cards[0]
        action_descriptions = [a.description for a in actions]
        creature_action = [
            a for a in actions
            if "creature half from adventure exile" in a.description
        ]
        assert len(creature_action) == 1
        assert creature_action[0].card_id == adventure_card.id

    def test_legal_actions_include_both_adventure_faces(self, adventure_card_game):
        """Adventure card in hand offers both creature and adventure cast options."""
        gs = adventure_card_game

        gs = gs.refresh_hash()
        actions = _compute_legal_actions(gs)

        action_descriptions = [a.description for a in actions]

        # Should include the base cast action (creature half, face_index=0)
        creature_actions = [a for a in actions if a.action_type == "cast" and a.card_id == gs.players[0].hand[0].id]
        assert len(creature_actions) >= 1

    def test_no_adventure_actions_before_adventure_resolves(self, adventure_card_game):
        """Before adventure resolves, no creature-from-exile actions available."""
        gs = adventure_card_game
        gs = gs.refresh_hash()
        actions = _compute_legal_actions(gs)

        adventure_exile_actions = [
            a for a in actions
            if "adventure exile" in a.description
        ]
        assert len(adventure_exile_actions) == 0
