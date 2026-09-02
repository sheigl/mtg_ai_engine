"""Unit tests for the Fortify keyword (CR 702.54a).

Real card fixtures: Darksteel Garrison ("Fortify {3}") and C.A.M.P.
("Fortify {2}{G}") — the only two Fortify cards in all of MTG.
"""
from mtg_engine.ability.keywords.fortify import (
    Fortify,
    _compute_payment,
    _strip_tap,
    apply_fortify,
    resolve_fortify_with_ai,
)
from mtg_engine.models.game import Card, GameState, ManaPool, Permanent, Phase, PlayerState, Step

GARRISON_ORACLE = (
    "Fortify {3} ({3}: Attach to target land you control. "
    "Fortify only as a sorcery. This card enters unattached and stays on the "
    "battlefield if the land leaves.)"
)
CAMP_ORACLE = (
    "Fortify {2}{G} ({2}{G}: Attach to target land you control. "
    "Fortify only as a sorcery. C.A.M.P. can't be attacked. As long as C.A.M.P. "
    "is attached, it doesn't have base abilities or rules text.)"
)

FORTIFICATION_TYPE = "Artifact Creature — Fortification"


def _garrison_card() -> Card:
    return Card(name="Darksteel Garrison", type_line=FORTIFICATION_TYPE, oracle_text=GARRISON_ORACLE)


def _camp_card() -> Card:
    return Card(name="C.A.M.P.", type_line=FORTIFICATION_TYPE, oracle_text=CAMP_ORACLE)


def _forest_card() -> Card:
    return Card(name="Forest", type_line="Basic Land — Forest")


def _make_gs(p1_pool: ManaPool | None = None, p2_pool: ManaPool | None = None,
             active: str = "p1", holder: str = "p1",
             phase: Phase = Phase.PRECOMBAT_MAIN, step: Step = Step.MAIN) -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=p1_pool or ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=p2_pool or ManaPool())
    return GameState(
        game_id="test", seed=1,
        active_player=active, priority_holder=holder,
        phase=phase, step=step,
        players=[p1, p2],
    )


def _perm(card: Card, controller: str = "p1") -> Permanent:
    return Permanent(card=card, controller=controller)


class TestParseFortifyCost:
    def test_parse_single_generic(self):
        assert Fortify.parse_fortify_cost(GARRISON_ORACLE) == "{3}"

    def test_parse_colored_multi(self):
        assert Fortify.parse_fortify_cost(CAMP_ORACLE) == "{2}{G}"

    def test_parse_dash_variant(self):
        assert Fortify.parse_fortify_cost("Fortify—{1}{G}") == "{1}{G}"

    def test_parse_no_cost(self):
        assert Fortify.parse_fortify_cost("Flying.") is None

    def test_parse_timing_text_is_not_a_cost(self):
        # "Fortify only as a sorcery" must not be parsed as a cost.
        assert Fortify.parse_fortify_cost("Fortify only as a sorcery.") is None

    def test_parse_empty(self):
        assert Fortify.parse_fortify_cost("") is None


class TestHasFortify:
    def test_via_keyword_list(self):
        card = Card(name="X", type_line=FORTIFICATION_TYPE, keywords=["fortify"])
        assert Fortify.has_fortify(card)

    def test_via_oracle_text(self):
        assert Fortify.has_fortify(_garrison_card())

    def test_case_insensitive_keyword(self):
        card = Card(name="X", type_line=FORTIFICATION_TYPE, keywords=["Fortify"])
        assert Fortify.has_fortify(card)

    def test_without_fortify(self):
        assert not Fortify.has_fortify(_forest_card())

    def test_plain_land_without_keyword(self):
        card = Card(name="Plains", type_line="Basic Land — Plains", oracle_text="")
        assert not Fortify.has_fortify(card)


class TestFromOracleText:
    def test_true(self):
        assert Fortify.from_oracle_text(GARRISON_ORACLE)

    def test_false(self):
        assert not Fortify.from_oracle_text("Flying.")

    def test_empty(self):
        assert not Fortify.from_oracle_text("")


class TestIsFortification:
    def test_garrison(self):
        assert Fortify.is_fortification(_garrison_card())

    def test_camp(self):
        assert Fortify.is_fortification(_camp_card())

    def test_plain_land(self):
        assert not Fortify.is_fortification(_forest_card())

    def test_creature(self):
        card = Card(name="Bear", type_line="Creature — Beast")
        assert not Fortify.is_fortification(card)


class TestIsLandCard:
    def test_fortification_is_a_land(self):
        assert Fortify.is_land_card(_garrison_card())

    def test_plain_land(self):
        assert Fortify.is_land_card(_forest_card())

    def test_non_land_creature(self):
        card = Card(name="Bear", type_line="Creature — Beast")
        assert not Fortify.is_land_card(card)

    def test_non_land_artifact(self):
        card = Card(name="Sword", type_line="Artifact")
        assert not Fortify.is_land_card(card)


class TestStripTap:
    def test_strips_tap(self):
        assert _strip_tap("{T}{3}") == "{3}"

    def test_no_tap(self):
        assert _strip_tap("{3}") == "{3}"

    def test_only_tap(self):
        assert _strip_tap("{T}") == ""


class TestComputePayment:
    def test_generic_from_colorless(self):
        pool = ManaPool(C=3)
        assert _compute_payment(pool, "{3}") == {"C": 3}

    def test_generic_falls_back_to_colors(self):
        pool = ManaPool(W=1, G=2)
        assert _compute_payment(pool, "{3}") == {"W": 1, "G": 2}

    def test_colored_then_generic(self):
        # Colored is paid first; generic comes from the colorless pool.
        pool = ManaPool(G=1, R=2, C=5)
        assert _compute_payment(pool, "{2}{R}") == {"R": 1, "C": 2}

    def test_generic_uses_colored_when_no_colorless(self):
        # R pays its own requirement first; remaining generic splits R then G.
        pool = ManaPool(G=1, R=2)
        assert _compute_payment(pool, "{2}{R}") == {"R": 2, "G": 1}


class TestApplySuccess:
    def _setup(self, pool: ManaPool | None = None):
        gs = _make_gs(p1_pool=pool or ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        return gs, garrison, forest

    def test_attach_pays_cost_and_attaches(self):
        gs, garrison, forest = self._setup()
        gs = apply_fortify(gs, garrison, forest.id)
        attached = next(p for p in gs.battlefield if p.id == garrison.id)
        host = next(p for p in gs.battlefield if p.id == forest.id)
        assert attached.attached_to == forest.id
        assert garrison.id in host.attachments
        # 3 generic paid from the colorless pool
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.C == 0

    def test_returns_new_object(self):
        gs, garrison, forest = self._setup()
        gs2 = apply_fortify(gs, garrison, forest.id)
        assert gs2 is not gs

    def test_pure_transform_original_unchanged(self):
        gs, garrison, forest = self._setup()
        old_pool_C = gs.players[0].mana_pool.C
        gs2 = apply_fortify(gs, garrison, forest.id)
        assert gs2 is not gs
        assert gs.players[0].mana_pool.C == old_pool_C
        orig = next(p for p in gs.battlefield if p.id == garrison.id)
        assert orig.attached_to is None

    def test_colored_cost_paid(self):
        gs = _make_gs(p1_pool=ManaPool(G=1, C=2))
        camp = _perm(_camp_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [camp, forest]
        gs = apply_fortify(gs, camp, forest.id)
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.G == 0
        assert p1.mana_pool.C == 0
        attached = next(p for p in gs.battlefield if p.id == camp.id)
        assert attached.attached_to == forest.id

    def test_fortification_can_target_fortification(self):
        """A Fortification is a land, so it is a legal Fortify target."""
        gs = _make_gs(p1_pool=ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        camp = _perm(_camp_card(), "p1")
        gs.battlefield = [garrison, camp]
        gs = apply_fortify(gs, garrison, camp.id)
        attached = next(p for p in gs.battlefield if p.id == garrison.id)
        assert attached.attached_to == camp.id


class TestApplyNoOps:
    """Each invalid condition returns the SAME object (no-op)."""

    def test_no_fortify_keyword(self):
        gs = _make_gs()
        forest = _perm(_forest_card(), "p1")
        other = _perm(Card(name="Plains", type_line="Basic Land — Plains"), "p1")
        gs.battlefield = [forest, other]
        assert apply_fortify(gs, forest, other.id) is gs

    def test_unparseable_cost(self):
        gs = _make_gs()
        card = Card(name="X", type_line=FORTIFICATION_TYPE, keywords=["fortify"], oracle_text="")
        perm = _perm(card, "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [perm, forest]
        assert apply_fortify(gs, perm, forest.id) is gs

    def test_source_not_controlled_by_acting_player(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p2")  # p2's garrison, p1 acting
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_source_not_on_battlefield(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")  # not in gs.battlefield
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_not_main_phase(self):
        gs = _make_gs(phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS)
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_stack_not_empty(self):
        from mtg_engine.models.game import StackObject
        gs = _make_gs()
        gs.stack = [StackObject(
            source_card=Card(name="Lightning Bolt", type_line="Instant"),
            controller="p1",
        )]
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_not_acting_player(self):
        # p2 has priority but it is p1's turn — no sorcery speed for p2.
        gs = _make_gs(active="p1", holder="p2", p2_pool=ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p2")
        forest = _perm(_forest_card(), "p2")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_no_target(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")
        gs.battlefield = [garrison]
        assert apply_fortify(gs, garrison, None) is gs
        assert apply_fortify(gs, garrison, "") is gs

    def test_target_not_on_battlefield(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")
        gs.battlefield = [garrison]
        assert apply_fortify(gs, garrison, "nonexistent-id") is gs

    def test_target_not_controlled(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p2")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs

    def test_target_not_a_land(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")
        bear = _perm(Card(name="Bear", type_line="Creature — Beast"), "p1")
        gs.battlefield = [garrison, bear]
        assert apply_fortify(gs, garrison, bear.id) is gs

    def test_target_is_source_itself(self):
        gs = _make_gs()
        garrison = _perm(_garrison_card(), "p1")
        gs.battlefield = [garrison]
        assert apply_fortify(gs, garrison, garrison.id) is gs

    def test_cost_unaffordable(self):
        gs = _make_gs(p1_pool=ManaPool(C=2))  # only 2, needs 3
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert apply_fortify(gs, garrison, forest.id) is gs


class TestResolveFortifyWithAI:
    def _setup(self, pool: ManaPool | None = None):
        gs = _make_gs(active="p1", holder="p1", p1_pool=pool or ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        plains = _perm(Card(name="Plains", type_line="Basic Land — Plains"), "p1")
        bear = _perm(Card(name="Bear", type_line="Creature — Beast"), "p1")
        gs.battlefield = [garrison, bear, forest, plains]
        return gs, garrison

    def test_ai_attaches_to_first_valid_land(self):
        gs, garrison = self._setup()
        gs = resolve_fortify_with_ai(gs, garrison.id)
        attached = next(p for p in gs.battlefield if p.id == garrison.id)
        # Deterministic: first land-like permanent in battlefield order = forest
        assert attached.attached_to == forest_id(gs, "Forest")
        p1 = next(p for p in gs.players if p.name == "p1")
        assert p1.mana_pool.C == 0

    def test_ai_excludes_self(self):
        gs = _make_gs(p1_pool=ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        gs.battlefield = [garrison]  # only land it controls is itself
        assert resolve_fortify_with_ai(gs, garrison.id) is gs

    def test_ai_no_target(self):
        gs = _make_gs(p1_pool=ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        bear = _perm(Card(name="Bear", type_line="Creature — Beast"), "p1")
        gs.battlefield = [garrison, bear]
        assert resolve_fortify_with_ai(gs, garrison.id) is gs

    def test_ai_unaffordable(self):
        gs = _make_gs(p1_pool=ManaPool(C=1))
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert resolve_fortify_with_ai(gs, garrison.id) is gs

    def test_ai_not_acting_player(self):
        gs = _make_gs(active="p2", holder="p1", p1_pool=ManaPool(C=3))
        garrison = _perm(_garrison_card(), "p1")
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [garrison, forest]
        assert resolve_fortify_with_ai(gs, garrison.id) is gs

    def test_ai_not_fortify_card(self):
        gs = _make_gs(p1_pool=ManaPool(C=3))
        forest = _perm(_forest_card(), "p1")
        gs.battlefield = [forest]
        assert resolve_fortify_with_ai(gs, forest.id) is gs

    def test_ai_missing_perm(self):
        gs = _make_gs()
        assert resolve_fortify_with_ai(gs, "missing-id") is gs

    def test_ai_returns_new_object_on_success(self):
        gs, garrison = self._setup()
        gs2 = resolve_fortify_with_ai(gs, garrison.id)
        assert gs2 is not gs


def forest_id(gs: GameState, name: str) -> str:
    return next(p.id for p in gs.battlefield if p.card.name == name)
