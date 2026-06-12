"""
CMD-01: Commander format tests.
"""
from mtg_engine.engine.formats.commander import (
    get_commander_tax,
    record_commander_cast,
    check_commander_damage_loss,
    get_color_identity,
    validate_deck_for_commander,
    add_commander_to_command_zone,
    get_commander_command_zone,
)
from mtg_engine.models.game import GameState, PlayerState
from mtg_engine.models.game import Card


def _make_card(name: str, mana_cost: str = "{0}", type_line: str = "Creature",
               oracle_text: str = "") -> Card:
    return Card(name=name, mana_cost=mana_cost, type_line=type_line,
                oracle_text=oracle_text)


def _commander_gs() -> GameState:
    p1 = PlayerState(name="p1", life=40)
    p2 = PlayerState(name="p2", life=40)
    return GameState(
        game_id="test-cmd", seed=1,
        active_player="p1", priority_holder="p1",
        players=[p1, p2],
        format="commander",
    )


class TestCommanderTax:
    def test_no_tax_on_first_cast(self):
        gs = _commander_gs()
        assert get_commander_tax(gs, "p1", "My Commander") == 0

    def test_tax_after_one_cast(self):
        gs = _commander_gs()
        gs = record_commander_cast(gs, "p1", "My Commander")
        assert get_commander_tax(gs, "p1", "My Commander") == 2

    def test_tax_after_multiple_casts(self):
        gs = _commander_gs()
        for _ in range(4):
            gs = record_commander_cast(gs, "p1", "My Commander")
        assert get_commander_tax(gs, "p1", "My Commander") == 8

    def test_partner_taxes_independent(self):
        gs = _commander_gs()
        gs = record_commander_cast(gs, "p1", "Commander A")
        gs = record_commander_cast(gs, "p1", "Commander A")
        gs = record_commander_cast(gs, "p1", "Commander B")
        assert get_commander_tax(gs, "p1", "Commander A") == 4
        assert get_commander_tax(gs, "p1", "Commander B") == 2

    def test_tax_per_player(self):
        gs = _commander_gs()
        gs = record_commander_cast(gs, "p1", "My Commander")
        gs = record_commander_cast(gs, "p1", "My Commander")
        assert get_commander_tax(gs, "p2", "My Commander") == 0


class TestCommanderDamageLoss:
    def test_no_loss_below_21(self):
        gs = _commander_gs()
        gs.commander_damage["perm_1"] = {"p1": 20}
        assert check_commander_damage_loss(gs) is None

    def test_loss_at_21(self):
        gs = _commander_gs()
        gs.commander_damage["perm_1"] = {"p1": 21}
        assert check_commander_damage_loss(gs) == "p1"

    def test_loss_above_21(self):
        gs = _commander_gs()
        gs.commander_damage["perm_1"] = {"p1": 25}
        assert check_commander_damage_loss(gs) == "p1"

    def test_no_loss_in_standard_format(self):
        gs = _commander_gs()
        gs.format = "standard"
        gs.commander_damage["perm_1"] = {"p1": 21}
        assert check_commander_damage_loss(gs) is None

    def test_multiple_players_tracked(self):
        gs = _commander_gs()
        gs.commander_damage["perm_1"] = {"p2": 21}
        assert check_commander_damage_loss(gs) == "p2"

    def test_two_commanders_below_21_each(self):
        gs = _commander_gs()
        gs.commander_damage["perm_a"] = {"p1": 20}
        gs.commander_damage["perm_b"] = {"p1": 20}
        assert check_commander_damage_loss(gs) is None


class TestColorIdentity:
    def test_single_color_mana_cost(self):
        card = _make_card("Elf", "{G}")
        assert get_color_identity(card) == ["G"]

    def test_multi_color_mana_cost(self):
        card = _make_card("Dragon", "{U}{B}{R}")
        assert get_color_identity(card) == sorted(["U", "B", "R"])

    def test_colorless_has_no_identity(self):
        card = _make_card("Artifact", "{3}")
        assert get_color_identity(card) == []

    def test_hybrid_symbols_in_oracle_text(self):
        card = _make_card("Test", "{U}", oracle_text="{B}")
        identity = get_color_identity(card)
        assert "U" in identity
        assert "B" in identity


class TestValidateDeck:
    def test_valid_deck(self):
        commander = _make_card("Greta", "{G}", type_line="Legendary Creature")
        # 99 other cards + commander in the deck = 100 total
        cards = [_make_card("Forest", "") for _ in range(99)] + [commander]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid is True
        assert violations == []

    def test_wrong_number_of_cards(self):
        commander = _make_card("Greta", "{G}", type_line="Legendary Creature")
        cards = [_make_card("Forest", "") for _ in range(50)]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid is False
        assert any("100" in v for v in violations)

    def test_no_commander(self):
        valid, violations = validate_deck_for_commander([], [])
        assert valid is False
        assert any("commander" in v.lower() for v in violations)

    def test_color_identity_violation(self):
        commander = _make_card("White", "{W}", type_line="Legendary Creature")
        black_card = _make_card("Black Spell", "{B}")
        cards = [black_card, commander] + [_make_card("Plains", "") for _ in range(98)]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid is False
        assert any("Black Spell" in v for v in violations)

    def test_singleton_allows_basic_lands(self):
        commander = _make_card("Greta", "{G}", type_line="Legendary Creature")
        cards = [commander] + \
                [_make_card("Forest", "") for _ in range(33)] + \
                [_make_card("Llanowar Elves", "{G}")] + \
                [_make_card("Island", "") for _ in range(65)]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid  # basic lands are OK

    def test_singleton_violation(self):
        commander = _make_card("Greta", "{G}", type_line="Legendary Creature")
        cards = [commander] + \
                [_make_card("Forest", "") for _ in range(97)] + \
                [_make_card("Llanowar Elves", "{G}"), _make_card("Llanowar Elves", "{G}")]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid is False
        assert any("Llanowar Elves" in v for v in violations)

    def test_commander_itself_exempt_from_color_identity(self):
        commander = _make_card("Greta", "{G}", type_line="Legendary Creature")
        cards = [_make_card("Forest", "") for _ in range(99)] + [commander]
        valid, violations = validate_deck_for_commander(cards, [commander])
        assert valid is True


class TestCommandZone:
    def test_get_command_zone(self):
        gs = _commander_gs()
        assert get_commander_command_zone(gs, "p1") == []

    def test_add_commander_to_command_zone(self):
        gs = _commander_gs()
        card = _make_card("My Commander", "{G}", type_line="Legendary Creature")
        gs = add_commander_to_command_zone(gs, "p1", card)
        zone = get_commander_command_zone(gs, "p1")
        assert len(zone) == 1
        assert zone[0].name == "My Commander"

    def test_add_commander_sets_commander_name(self):
        gs = _commander_gs()
        card = _make_card("Greta", "{G}", type_line="Legendary Creature")
        gs = add_commander_to_command_zone(gs, "p1", card)
        p1 = [p for p in gs.players if p.name == "p1"][0]
        assert p1.commander_name == "Greta"
