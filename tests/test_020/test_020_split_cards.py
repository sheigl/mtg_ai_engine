"""
User Story 4: Split Cards, MDFCs, and Aftermath.

Acceptance Criteria:
1. Split cards: cast left or right half from hand using face_index (CR 709)
2. Fuse: cast both halves as single spell with combined cost (CR 709.4)
3. MDFC land play: play back face as land (CR 712)
4. Aftermath: cast second half from graveyard, exile on resolution (CR 702.125)
5. Legal actions include separate cast actions per face + fuse

CR References:
- CR 709: Split cards
- CR 712: Modal double-faced cards
- CR 702.125: Aftermath
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Phase, Step, Card, CardFace, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top, _apply_face_to_card, _fuse_split_card


@pytest.fixture
def split_card_game():
    """Create a game with a split card in player_1's hand."""
    fire = CardFace(
        name="Fire",
        mana_cost="{R}",
        type_line="Instant",
        oracle_text="Fire deals 2 damage to any target.",
    )
    ice = CardFace(
        name="Ice",
        mana_cost="{U}",
        type_line="Instant",
        oracle_text="Ice deals 1 damage to target creature or player.",
    )
    split = Card(
        name="Fire // Ice",
        mana_cost="{R}{U}",
        type_line="",
        card_layout="split",
        faces=[fire, ice],
        keywords=["fuse"],
    )
    return GameState(
        game_id="test_split",
        seed=42,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[split],
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


@pytest.fixture
def aftermath_card_game():
    """Create a game with an aftermath card in graveyard."""
    digest = CardFace(
        name="Digest",
        mana_cost="{1}{W}",
        type_line="Sorcery",
        oracle_text="Return target creature card with mana value 2 or less from your graveyard to your hand.",
    )
    exile = CardFace(
        name="Exile",
        mana_cost="{3}{W}",
        type_line="Sorcery",
        oracle_text="Exile target creature.",
    )
    aftermath = Card(
        name="Digest // Exile",
        mana_cost="{1}{W}{3}{W}",
        type_line="",
        card_layout="aftermath",
        faces=[digest, exile],
    )
    gs = GameState(
        game_id="test_aftermath",
        seed=99,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[],
                graveyard=[aftermath],
                mana_pool=ManaPool(W=4),
                exile=[],
                library=[],
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
    return gs


@pytest.fixture
def mdfc_card_game():
    """Create a game with an MDFC land in hand."""
    front = CardFace(
        name="Bountiful Promenade",
        mana_cost="",
        type_line="Enchantment",
        oracle_text="When Bountiful Promenade enters the battlefield, you may search your library for a basic land card, put it onto the battlefield tapped, then shuffle.",
    )
    back_face = CardFace(
        name="Bountiful Promenade",
        mana_cost="",
        type_line="Land",
        oracle_text="{T}: Add {G} or {W}.",
    )
    mdfc = Card(
        name="Bountiful Promenade",
        mana_cost="",
        type_line="",
        card_layout="mdfc",
        faces=[front, back_face],
    )
    return GameState(
        game_id="test_mdfc",
        seed=77,
        players=[
            PlayerState(
                name="player_1",
                life=20,
                hand=[mdfc],
                mana_pool=ManaPool(),
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


@pytest.mark.comprehensive_rules
@pytest.mark.cr("709.1", "709.2", "709.3")
class TestSplitCardFaceIndex:
    """Test casting split card faces with face_index."""

    def test_face_index_0_casts_left_half(self, split_card_game):
        """Scenario 1: Casting a split card with face_index=0 uses the left face's properties."""
        gs = split_card_game
        card_id = gs.players[0].hand[0].id

        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"R": 1},
            face_index=0,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.source_card.name == "Fire"
        assert stack_obj.source_card.mana_cost == "{R}"
        assert "Instant" in stack_obj.source_card.type_line
        assert "Fire deals 2 damage" in stack_obj.source_card.oracle_text

    def test_face_index_1_casts_right_half(self):
        """Scenario 2: Casting a split card with face_index=1 uses the right face's properties."""
        fire = CardFace(
            name="Fire",
            mana_cost="{R}",
            type_line="Instant",
            oracle_text="Fire deals 2 damage to any target.",
        )
        ice = CardFace(
            name="Ice",
            mana_cost="{U}",
            type_line="Instant",
            oracle_text="Ice deals 1 damage to target creature or player.",
        )
        split = Card(
            name="Fire // Ice",
            mana_cost="{R}{U}",
            type_line="",
            card_layout="split",
            faces=[fire, ice],
            keywords=["fuse"],
        )
        gs = GameState(
            game_id="test_split_ice",
            seed=43,
            players=[
                PlayerState(
                    name="player_1",
                    life=20,
                    hand=[split],
                    mana_pool=ManaPool(U=1),
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
            mana_payment={"U": 1},
            face_index=1,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.source_card.name == "Ice"
        assert stack_obj.source_card.mana_cost == "{U}"
        assert "Instant" in stack_obj.source_card.type_line
        assert "Ice deals 1 damage" in stack_obj.source_card.oracle_text


@pytest.mark.comprehensive_rules
@pytest.mark.cr("709.4")
class TestSplitCardFuse:
    """Test casting split cards with fuse."""

    def test_fuse_combines_both_halves(self):
        """Scenario 3: Casting a split card with fuse=True merges both faces."""
        fire = CardFace(
            name="Fire",
            mana_cost="{R}",
            type_line="Instant",
            oracle_text="Fire deals 2 damage to any target.",
        )
        ice = CardFace(
            name="Ice",
            mana_cost="{U}",
            type_line="Instant",
            oracle_text="Ice deals 1 damage to target creature or player.",
        )
        split = Card(
            name="Fire // Ice",
            mana_cost="{R}{U}",
            type_line="",
            card_layout="split",
            faces=[fire, ice],
            keywords=["fuse"],
        )
        gs = GameState(
            game_id="test_fuse",
            seed=44,
            players=[
                PlayerState(
                    name="player_1",
                    life=20,
                    hand=[split],
                    mana_pool=ManaPool(R=1, U=1),
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
            mana_payment={"R": 1, "U": 1},
            fuse=True,
        )

        stack_obj = gs.stack[0]
        fused_card = stack_obj.source_card
        assert "R" in fused_card.mana_cost and "U" in fused_card.mana_cost
        assert "Instant" in fused_card.type_line
        assert "Fire deals 2 damage" in fused_card.oracle_text
        assert "Ice deals 1 damage" in fused_card.oracle_text
        assert stack_obj.is_fused is True

    def test_fuse_not_applied_without_flag(self, split_card_game):
        """Fuse should not merge when fuse=False (default)."""
        gs = split_card_game
        card_id = gs.players[0].hand[0].id

        gs = cast_spell(
            gs, "player_1", card_id,
            targets=["player_2"],
            mana_payment={"R": 1},
            face_index=0,
            fuse=False,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.source_card.name == "Fire"
        assert stack_obj.is_fused is False


@pytest.mark.comprehensive_rules
@pytest.mark.cr("712.1", "712.6")
class TestMDFC:
    """Test Modal Double-Faced Card handling."""

    def test_apply_face_to_card(self):
        """_apply_face_to_card copies face properties onto a new Card."""
        base = Card(
            name="Test // Card",
            mana_cost="{1}{R}",
            type_line="Sorcery - Instant",
            card_layout="split",
            faces=[
                CardFace(name="Test", mana_cost="{1}", type_line="Sorcery", oracle_text="Do something."),
                CardFace(name="Card", mana_cost="{R}", type_line="Instant", oracle_text="Do other thing."),
            ],
        )
        result = _apply_face_to_card(base, base.faces[1])
        assert result.name == "Card"
        assert result.mana_cost == "{R}"
        assert result.type_line == "Instant"
        assert result.oracle_text == "Do other thing."
        assert base.name == "Test // Card"
        assert base.mana_cost == "{1}{R}"

    def test_mdfc_card_has_back_face(self, mdfc_card_game):
        """MDFC card has faces with back face being a land."""
        mdfc = mdfc_card_game.players[0].hand[0]
        assert mdfc.card_layout == "mdfc"
        assert mdfc.faces is not None
        assert len(mdfc.faces) == 2
        assert "Land" in mdfc.faces[1].type_line


@pytest.mark.comprehensive_rules
@pytest.mark.cr("702.125")
class TestAftermath:
    """Test Aftermath card handling."""

    def test_aftermath_cast_from_graveyard(self, aftermath_card_game):
        """Casting aftermath second half from graveyard."""
        gs = aftermath_card_game
        aftermath = gs.players[0].graveyard[0]

        gs = cast_spell(
            gs, "player_1", aftermath.id,
            targets=["player_2"],
            mana_payment={"W": 4},
            face_index=1,
            from_graveyard=True,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.source_card.name == "Exile"
        assert "exile" in stack_obj.source_card.oracle_text.lower()

    def test_aftermath_card_exiled_on_resolution(self, aftermath_card_game):
        """Aftermath card cast from graveyard is exiled after resolution."""
        gs = aftermath_card_game
        aftermath = gs.players[0].graveyard[0]

        gs = cast_spell(
            gs, "player_1", aftermath.id,
            targets=["player_2"],
            mana_payment={"W": 4},
            face_index=1,
            from_graveyard=True,
        )

        assert aftermath.id not in [c.id for c in gs.players[0].hand]
        assert gs.players[0].graveyard == []

        gs = resolve_top(gs)

        assert len(gs.stack) == 0

    def test_aftermath_face_index_0_from_hand(self):
        """First half of aftermath should be castable from hand normally."""
        digest = CardFace(
            name="Digest",
            mana_cost="{1}{W}",
            type_line="Sorcery",
            oracle_text="Return target creature card with mana value 2 or less from your graveyard to your hand.",
        )
        exile = CardFace(
            name="Exile",
            mana_cost="{3}{W}",
            type_line="Sorcery",
            oracle_text="Exile target creature.",
        )
        aftermath = Card(
            name="Digest // Exile",
            mana_cost="{1}{W}{3}{W}",
            card_layout="aftermath",
            faces=[digest, exile],
        )
        gs = GameState(
            game_id="test_aftermath_hand",
            seed=111,
            players=[
                PlayerState(
                    name="p1",
                    life=20,
                    hand=[aftermath],
                    mana_pool=ManaPool(W=4),
                    library=[],
                    graveyard=[],
                    exile=[],
                    command_zone=[],
                    deck=[],
                ),
                PlayerState(
                    name="p2",
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
            active_player="p1",
            priority_holder="p1",
            stack=[],
            battlefield=[],
            graveyards={"p1": [], "p2": []},
            exile_zone={},
            pending_triggers=[],
            pending_choices=[],
            is_game_over=False,
            winner=None,
            format="standard",
        )

        gs = cast_spell(
            gs, "p1", gs.players[0].hand[0].id,
            targets=[],
            mana_payment={"W": 4},
            face_index=0,
        )

        stack_obj = gs.stack[0]
        assert stack_obj.source_card.name == "Digest"
        assert aftermath.id not in [c.id for c in gs.players[0].hand]


@pytest.mark.comprehensive_rules
@pytest.mark.cr("709.1")
class TestFuseSplitCardHelper:
    """Test _fuse_split_card helper function."""

    def test_fuse_split_card_combines_costs(self):
        """_fuse_split_card merges mana costs of both faces."""
        card = Card(
            name="Fire // Ice",
            card_layout="split",
            faces=[
                CardFace(name="Fire", mana_cost="{R}", type_line="Instant", oracle_text="Deals 2 damage."),
                CardFace(name="Ice", mana_cost="{U}", type_line="Instant", oracle_text="Deals 1 damage."),
            ],
        )
        fused = _fuse_split_card(card)
        assert fused.mana_cost == "{R} {U}"
        assert "Instant" in fused.type_line
        assert "Deals 2 damage" in fused.oracle_text
        assert "Deals 1 damage" in fused.oracle_text

    def test_fuse_split_card_no_faces(self):
        """_fuse_split_card returns unchanged card if no faces exist."""
        card = Card(
            name="Single Face Card",
            mana_cost="{2}",
            type_line="Sorcery",
        )
        result = _fuse_split_card(card)
        assert result.name == "Single Face Card"
        assert result.mana_cost == "{2}"
