"""Integration tests for Miracle keyword (CR 702.93)."""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
from mtg_engine.ability.keywords.miracle import MiracleKeyword, MiracleKeyword as MK
from mtg_engine.engine.zones import draw_card, get_player
from mtg_engine.engine.stack import cast_spell


def _make_game(human_name="p1"):
    from mtg_engine.models.game import Phase, Step
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool(W=1, U=1, B=1, R=1, G=1, C=10), library=[], hand=[])
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    gs = GameState(
        game_id="t-miracle",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=human_name,
        cards_drawn_this_turn={},
    )
    return gs


def _miracle_card(name="Entreat the Angels", mana_cost="{4}{W}{W}", oracle_text="Miracle {2}{W}\nDraw three cards."):
    return Card(id="m1", name=name, mana_cost=mana_cost, type_line="Sorcery", oracle_text=oracle_text, keywords=["miracle"])


class TestMiracleDetection:
    def test_parse_miracle_cost(self):
        cost = MiracleKeyword.parse_miracle_cost("Miracle {2}{W}")
        assert cost == "{2}{W}"

    def test_from_oracle_text_true(self):
        assert MiracleKeyword.from_oracle_text("Miracle {1}{U}\n...") is True

    def test_from_oracle_text_false(self):
        assert MiracleKeyword.from_oracle_text("Draw a card.") is False


class TestFirstDrawTrigger:
    def test_miracle_queues_pending_for_human_first_draw(self):
        gs = _make_game(human_name="p1")
        card = _miracle_card()
        gs.players[0].library = [card]
        gs.players[0].hand = []
        gs, drawn = draw_card(gs, "p1")
        assert drawn.id == card.id
        assert gs.pending_miracle_choice is not None
        pending = gs.pending_miracle_choice
        assert pending["player"] == "p1"
        assert pending["card_name"] == "Entreat the Angels"
        assert pending["miracle_cost"] == "{2}{W}"
        assert pending["resolved"] is False

    def test_miracle_no_trigger_on_second_draw(self):
        gs = _make_game(human_name="p1")
        c1 = _miracle_card(name="Miracle One")
        c2 = Card(id="c2", name="Normal", mana_cost="{1}", type_line="Sorcery", oracle_text="Deal 1 damage.")
        gs.players[0].library = [c2, c1]  # c2 on top
        gs.players[0].hand = []
        # First draw: normal card, no miracle
        gs, _ = draw_card(gs, "p1")
        assert gs.pending_miracle_choice is None
        # Second draw: miracle card, but not first draw
        gs, drawn = draw_card(gs, "p1")
        assert drawn.id == c1.id
        assert gs.pending_miracle_choice is None  # No trigger

    def test_cards_drawn_counter_increments(self):
        gs = _make_game(human_name="p1")
        c1 = Card(id="c1", name="A", mana_cost="{1}", type_line="Sorcery", oracle_text="")
        c2 = Card(id="c2", name="B", mana_cost="{1}", type_line="Sorcery", oracle_text="")
        gs.players[0].library = [c1, c2]
        gs, _ = draw_card(gs, "p1")
        assert gs.cards_drawn_this_turn.get("p1") == 1
        gs, _ = draw_card(gs, "p1")
        assert gs.cards_drawn_this_turn.get("p1") == 2


class TestAIAutoResolve:
    def test_ai_auto_casts_when_affordable(self):
        gs = _make_game(human_name="p2")  # p1 is AI
        card = _miracle_card()
        gs.players[0].library = [card]
        gs.players[0].mana_pool = ManaPool(W=2, C=2)
        gs, drawn = draw_card(gs, "p1")
        # AI should have auto-cast the card; it should be on stack
        assert len(gs.stack) == 1
        assert gs.stack[0].source_card.id == card.id
        # Card should no longer be in hand
        player = get_player(gs, "p1")
        assert card.id not in [c.id for c in player.hand]

    def test_ai_does_not_cast_when_unaffordable(self):
        gs = _make_game(human_name="p2")
        card = _miracle_card()
        gs.players[0].library = [card]
        gs.players[0].mana_pool = ManaPool(W=0, C=0)
        gs, drawn = draw_card(gs, "p1")
        assert len(gs.stack) == 0
        player = get_player(gs, "p1")
        assert card.id in [c.id for c in player.hand]


class TestMiracleApplyMethod:
    def test_apply_queues_pending_for_human(self):
        gs = _make_game(human_name="p1")
        card = _miracle_card()
        kw = MiracleKeyword()
        gs2 = kw.apply(gs, card, "p1")
        assert gs2.pending_miracle_choice is not None
        assert gs2.pending_miracle_choice["resolved"] is False

    def test_apply_noop_second_draw(self):
        gs = _make_game(human_name="p1")
        gs.cards_drawn_this_turn = {"p1": 1}
        card = _miracle_card()
        kw = MiracleKeyword()
        gs2 = kw.apply(gs, card, "p1")
        assert gs2 is gs  # same object, no-op

    def test_apply_noop_non_miracle(self):
        gs = _make_game(human_name="p1")
        card = Card(id="c1", name="Normal", mana_cost="{1}", type_line="Sorcery", oracle_text="Deal 1 damage.")
        kw = MiracleKeyword()
        gs2 = kw.apply(gs, card, "p1")
        assert gs2 is gs


class TestAlternativeCost:
    def test_miracle_cost_replaces_base(self):
        gs = _make_game(human_name="p2")
        card = _miracle_card()
        gs.players[0].hand = [card]
        gs.players[0].mana_pool = ManaPool(W=2, C=2)
        gs2 = cast_spell(gs, "p1", card.id, targets=[], mana_payment={}, alternative_cost="{2}{W}")
        assert len(gs2.stack) == 1
        stack_obj = gs2.stack[0]
        assert stack_obj.alternative_cost == "{2}{W}"


class TestPureTransform:
    def test_draw_card_pure_transform_on_no_miracle(self):
        gs = _make_game(human_name="p1")
        card = Card(id="c1", name="Normal", mana_cost="{1}", type_line="Sorcery", oracle_text="")
        gs.players[0].library = [card]
        old_id = id(gs)
        gs2, _ = draw_card(gs, "p1")
        assert id(gs2) != old_id
        # No miracle pending
        assert gs2.pending_miracle_choice is None
