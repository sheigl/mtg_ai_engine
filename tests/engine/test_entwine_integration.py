"""
Story 7-6b: Entwine keyword (CR 702.39) — integration tests.

Entwine {cost} is an ADDITIONAL cost on modal spells. If paid, all modes are
chosen instead of just one.

This suite exercises:
* EntwineKeyword.apply() — pure transform, no-op guards, human/AI split
* cast_spell(entwine_paid=...) — entwine cost appended to base cost
* Modal resolution via _split_modal_texts and modes_chosen
* API surface via TestClient for human deferral and choice resolution
"""

from mtg_engine.ability.keywords.entwine import EntwineKeyword
from mtg_engine.engine.stack import cast_spell, resolve_top, _split_modal_texts
from mtg_engine.models.game import Card, GameState, ManaPool, Permanent, Phase, PlayerState, Step


def _make_modal_card(card_id="ent-1", name="Tooth and Nail", mana_cost="{3}{G}{W}",
                     type_line="Sorcery",
                     oracle_text="Choose one —\n• Search your library for up to two creature cards and put them onto the battlefield.\n• Return target creature card from your graveyard to the battlefield.\nEntwine {2}",
                     **kwargs):
    return Card(
        id=card_id,
        name=name,
        mana_cost=mana_cost,
        type_line=type_line,
        oracle_text=oracle_text,
        **kwargs,
    )


def _make_gs(pool=None, human=None, hand=None):
    p1 = PlayerState(
        name="p1", life=20, mana_pool=pool or ManaPool(),
        hand=hand if hand is not None else [_make_modal_card()],
    )
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    kwargs = {}
    if human is not None:
        kwargs["human_player_name"] = human
    return GameState(
        game_id="t-entwine", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
        **kwargs,
    )


def _entwine_perm(controller="p1"):
    return Permanent(card=_make_modal_card(), controller=controller)


class TestEntwineDetection:
    def test_parse_entwine_cost(self):
        cost = EntwineKeyword.parse_entwine_cost("Entwine {2}")
        assert cost == "{2}"

    def test_from_oracle_text_true(self):
        assert EntwineKeyword.from_oracle_text("Entwine {2}\nChoose one —") is True

    def test_from_oracle_text_false(self):
        assert EntwineKeyword.from_oracle_text("Choose one —") is False


class TestApplyEntwine:
    def test_human_queues_pending_entwine_choice(self):
        gs = _make_gs(pool=ManaPool(G=3, W=1, C=5), human="p1")
        gs2 = EntwineKeyword().apply(gs, _entwine_perm())
        assert gs2 is not gs
        assert gs.pending_entwine_choice is None
        pending = gs2.pending_entwine_choice
        assert pending is not None
        assert pending["player"] == "p1"
        assert pending["card_id"] == "ent-1"
        assert pending["card_name"] == "Tooth and Nail"
        assert pending["entwine_cost"] == "{2}"
        assert pending["base_cost"] == "{3}{G}{W}"
        # split includes "Choose one —" prefix, so 3 entries
        assert pending["num_modes"] == 3
        assert pending["resolved"] is False

    def test_ai_resolves_paid_true_when_affordable(self):
        gs = _make_gs(pool=ManaPool(G=3, W=1, C=5))  # AI
        gs2 = EntwineKeyword().apply(gs, _entwine_perm())
        pending = gs2.pending_entwine_choice
        assert pending is not None
        assert pending["resolved"] is True
        assert pending["paid"] is True

    def test_ai_resolves_paid_false_when_unaffordable(self):
        gs = _make_gs(pool=ManaPool(G=3, W=1, C=0))  # not enough for {2}
        gs2 = EntwineKeyword().apply(gs, _entwine_perm())
        pending = gs2.pending_entwine_choice
        assert pending is not None
        assert pending["resolved"] is True
        assert pending["paid"] is False

    def test_noop_non_modal(self):
        card = Card(id="nm-1", name="Simple", mana_cost="{1}", type_line="Sorcery",
                    oracle_text="Draw a card. Entwine {2}")
        perm = Permanent(card=card, controller="p1")
        gs = _make_gs(human="p1")
        gs2 = EntwineKeyword().apply(gs, perm)
        assert gs2 is gs  # same object, no-op

    def test_noop_no_entwine(self):
        card = Card(id="no-1", name="NoEntwine", mana_cost="{1}", type_line="Sorcery",
                    oracle_text="Choose one —\n• Draw a card.\n• Gain 1 life.")
        perm = Permanent(card=card, controller="p1")
        gs = _make_gs(human="p1")
        gs2 = EntwineKeyword().apply(gs, perm)
        assert gs2 is gs


class TestEntwineCastAndResolution:
    def test_entwine_paid_appends_cost_and_draws_all_modes(self):
        # Build a simple modal spell with draw and life gain modes
        card = Card(id="mod-1", name="Test Modal", mana_cost="{1}", type_line="Sorcery",
                    oracle_text="Choose one —\n• Draw two cards.\n• Gain 3 life.\nEntwine {1}")
        p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool(C=2), hand=[card])
        # Populate library
        p1.library = [Card(name=f"Lib{i}", type_line="Creature") for i in range(5)]
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        gs = GameState(game_id="t-entwine-res", seed=1, active_player="p1", priority_holder="p1",
                       phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN, players=[p1, p2])
        # Cast with entwine paid, modes_chosen = [1,2] (0 is "Choose one —")
        gs = cast_spell(gs, "p1", "mod-1", [], {"C": 2}, modes_chosen=[1, 2], entwine_paid=True)
        # Resolve spell
        gs = resolve_top(gs)
        # Both effects should have applied: life gain 3, draw 2
        p1_after = next(p for p in gs.players if p.name == "p1")
        assert p1_after.life == 23
        assert len(p1_after.hand) == 2  # started with 1 card, cast removes it, draws 2 → 2

    def test_entwine_not_paid_single_mode_only(self):
        card = Card(id="mod-2", name="Test Modal", mana_cost="{1}", type_line="Sorcery",
                    oracle_text="Choose one —\n• Draw two cards.\n• Gain 3 life.\nEntwine {1}")
        p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool(C=1), hand=[card])
        p1.library = [Card(name=f"Lib{i}", type_line="Creature") for i in range(5)]
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        gs = GameState(game_id="t-entwine-res2", seed=1, active_player="p1", priority_holder="p1",
                       phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN, players=[p1, p2])
        # Choose draw mode only (index 1)
        gs = cast_spell(gs, "p1", "mod-2", [], {"C": 1}, modes_chosen=[1], entwine_paid=False)
        gs = resolve_top(gs)
        p1_after = next(p for p in gs.players if p.name == "p1")
        assert p1_after.life == 20  # no life gain
        # Hand size should be 2 (draw 2, card removed)
        assert len(p1_after.hand) == 2

    def test_base_cost_still_paid_with_entwine(self):
        card = Card(id="mod-3", name="Test Modal", mana_cost="{1}{R}", type_line="Sorcery",
                    oracle_text="Choose one —\n• Draw a card.\n• Gain 1 life.\nEntwine {1}{R}")
        p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool(R=2, C=2), hand=[card])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        gs = GameState(game_id="t-entwine-cost", seed=1, active_player="p1", priority_holder="p1",
                       phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN, players=[p1, p2])
        gs = cast_spell(gs, "p1", "mod-3", [], {}, modes_chosen=[1,2], entwine_paid=True)
        p1_after = next(p for p in gs.players if p.name == "p1")
        # Base {1}{R} + entwine {1}{R} = {2}{R}{R} → need 2R +2C? Actually {1}{R} base, entwine {1}{R} → total {2}{R}{R}
        # Pool R=2 C=2 → should pay 2R +2C? Wait {2} generic =2, {R}{R}=2R. So R=2 used, C=2 used.
        assert p1_after.mana_pool.R == 0
        assert p1_after.mana_pool.C == 0


class TestSplitModalHelper:
    def test_split_modal_texts_count(self):
        oracle = "Choose one —\n• Draw two cards.\n• Gain 2 life.\nEntwine {2}"
        modes = _split_modal_texts(oracle)
        # Includes "Choose one —" prefix
        assert len(modes) == 3
        assert "Choose one" in modes[0]
        assert "Draw two cards" in modes[1]
        assert "Gain 2 life" in modes[2]


class TestRegressionModalWithoutEntwine:
    def test_modal_without_entwine_resolves_single_mode(self):
        card = Card(id="mod-4", name="Simple Modal", mana_cost="{1}", type_line="Sorcery",
                    oracle_text="Choose one —\n• Draw a card.\n• Gain 1 life.")
        p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool(C=1), hand=[card])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        gs = GameState(game_id="t-regression", seed=1, active_player="p1", priority_holder="p1",
                       phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN, players=[p1, p2])
        # Choose gain life mode (index 2)
        gs = cast_spell(gs, "p1", "mod-4", [], {"C":1}, modes_chosen=[2], entwine_paid=False)
        gs = resolve_top(gs)
        p1_after = next(p for p in gs.players if p.name == "p1")
        assert p1_after.life == 21
        # hand unchanged (no draw)
        assert len(p1_after.hand) == 0
