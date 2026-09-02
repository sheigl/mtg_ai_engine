"""Integration tests for the Crew keyword (CR 702.147, story 7-5a).

Crew N means "Tap any number of untapped creatures you control with total
power N or more: This permanent becomes an artifact creature until end of
turn." These tests exercise the human path (queues a pending choice without
tapping), the AI auto-resolution path (greedy cheapest combination), choice
resolution, and end-of-turn expiration. Pure-transform guarantees (Q4) are
checked: meaningful changes return a new GameState, no-op paths return the
same object so repeated events cannot double-fire.

Because these transforms build a fresh ``battlefield`` list of copied
permanents on each meaningful change, tests read creature/vehicle status from
the *returned* GameState rather than stale local references.
"""
from mtg_engine.ability.keywords.crew import (
    Crew,
    apply_crew,
    resolve_crew_choice,
    handle_crew_expiration,
)
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(active: str = "p1", holder: str | None = None, human: str | None = None) -> GameState:
    gs = GameState(
        game_id="test-crew", seed=1,
        active_player=active, priority_holder=holder or active,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
    )
    if human is not None:
        gs.human_player_name = human  # type: ignore[attr-defined]
    return gs


def _vehicle(crew_value: int = 2, controller: str = "p1", tapped: bool = False) -> Permanent:
    card = Card(
        name="Smuggler's Copter",
        type_line="Artifact — Vehicle",
        oracle_text=f"Crew {crew_value}.",
        mana_cost="{2}",
    )
    return Permanent(card=card, controller=controller, tapped=tapped)


def _creature(power: str, toughness: str = "1", controller: str = "p1", tapped: bool = False) -> Permanent:
    card = Card(
        name="Goblin",
        type_line="Creature — Goblin",
        oracle_text="",
        mana_cost="{1}",
        power=power,
        toughness=toughness,
    )
    return Permanent(card=card, controller=controller, tapped=tapped)


def _place(gs: GameState, *perms: Permanent) -> None:
    gs.battlefield = list(perms)


def _vehicle_perm(gs: GameState) -> Permanent:
    return next(p for p in gs.battlefield if p.card.name == "Smuggler's Copter")


def _creatures_on_board(gs: GameState, power: str | None = None) -> list[Permanent]:
    return [p for p in gs.battlefield if p.card.name == "Goblin" and (power is None or p.card.power == power)]


# ---------------------------------------------------------------------------
# Detection helpers (Q1)
# ---------------------------------------------------------------------------

class TestCrewDetection:
    def test_from_oracle_text_true(self):
        assert Crew.from_oracle_text("Crew 2.") is True

    def test_from_oracle_text_case_insensitive(self):
        assert Crew.from_oracle_text("crew 3") is True

    def test_from_oracle_text_false(self):
        assert Crew.from_oracle_text("Flying.") is False

    def test_from_oracle_text_empty(self):
        assert Crew.from_oracle_text("") is False

    def test_parse_crew_value(self):
        assert Crew.parse_crew_value("Crew 5") == 5

    def test_parse_crew_value_default_one(self):
        assert Crew.parse_crew_value("Vehicle.") == 1


# ---------------------------------------------------------------------------
# Human path: queue choice, tap nothing yet (Q4 no-tap)
# ---------------------------------------------------------------------------

class TestHumanPath:
    def test_human_queues_choice_without_tapping(self):
        gs = _make_game(human="p1")
        vehicle = _vehicle(crew_value=2)
        creature = _creature("3")
        _place(gs, vehicle, creature)

        new_gs = apply_crew(gs, vehicle)

        # Pending choice queued with the right metadata (value from oracle).
        assert new_gs.pending_crew_choice is not None
        choice = new_gs.pending_crew_choice
        assert choice["player"] == "p1"
        assert choice["permanent_id"] == vehicle.id
        assert choice["card_name"] == "Smuggler's Copter"
        assert choice["crew_value"] == 2
        assert choice["resolved"] is False
        assert creature.id in choice["available_creatures"]

        # Nothing tapped yet; the vehicle is NOT crewed until the human decides.
        assert creature.tapped is False
        assert vehicle.crewed_until_end_of_turn is False
        assert "creature" not in vehicle.card.type_line.lower()

    def test_human_choice_available_excludes_vehicle(self):
        gs = _make_game(human="p1")
        vehicle = _vehicle(crew_value=1)
        creature = _creature("2")
        _place(gs, vehicle, creature)

        gs = apply_crew(gs, vehicle)  # returned state carries the pending choice
        available = gs.pending_crew_choice["available_creatures"]
        assert vehicle.id not in available
        assert creature.id in available


# ---------------------------------------------------------------------------
# AI path: greedy cheapest combination (Q4 pure transforms)
# ---------------------------------------------------------------------------

class TestAIPath:
    def test_ai_single_creature(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=2)
        creature = _creature("4")
        _place(gs, vehicle, creature)

        gs = apply_crew(gs, vehicle)  # AI resolves immediately (no queued choice)

        assert gs.pending_crew_choice is None  # AI does not queue a choice
        assert _creatures_on_board(gs)[0].tapped is True
        v = _vehicle_perm(gs)
        assert v.crewed_until_end_of_turn is True
        assert v.card.type_line == "Artifact Creature — Vehicle"
        assert gs.crewed_vehicles[v.id] == 2

    def test_ai_partial_tap_combo(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=5)
        _place(gs, vehicle, _creature("2"), _creature("3"))

        gs = apply_crew(gs, vehicle)

        # Both tapped because their summed power (5) meets the crew value.
        assert all(p.tapped for p in _creatures_on_board(gs))
        v = _vehicle_perm(gs)
        assert v.crewed_until_end_of_turn is True
        assert gs.crewed_vehicles[v.id] == 5

    def test_ai_no_valid_combination_returns_same_object(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=5)
        a = _creature("1")
        b = _creature("1")
        _place(gs, vehicle, a, b)

        result = apply_crew(gs, vehicle)

        # Total available power (2) is below the crew value (5): pure no-op.
        assert result is gs
        assert a.tapped is False
        assert b.tapped is False
        assert vehicle.crewed_until_end_of_turn is False

    def test_ai_no_creatures_returns_same_object(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=1)
        _place(gs, vehicle)

        result = apply_crew(gs, vehicle)

        assert result is gs

    def test_ai_ignores_opponent_creatures(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=1, controller="p1")
        opponent_creature = _creature("5", controller="p2")
        _place(gs, vehicle, opponent_creature)

        result = apply_crew(gs, vehicle)

        assert result is gs  # Cannot crew with an opponent's creature
        assert opponent_creature.tapped is False


# ---------------------------------------------------------------------------
# Negative / guard paths (Q1 + Q4)
# ---------------------------------------------------------------------------

class TestGuardPaths:
    def test_non_crew_card_is_noop_same_object(self):
        gs = _make_game(active="ai", holder="ai")
        plain_vehicle = Card(name="Iron Skiff", type_line="Artifact — Vehicle", oracle_text="", mana_cost="{2}")
        perm = Permanent(card=plain_vehicle, controller="p1")
        creature = _creature("3")
        _place(gs, perm, creature)

        result = apply_crew(gs, perm)

        # Card lacks Crew entirely: strict no-op, nothing tapped.
        assert result is gs
        assert creature.tapped is False

    def test_vehicle_not_on_battlefield_is_noop(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=2)
        creature = _creature("3")
        # Vehicle intentionally NOT placed on the battlefield.
        _place(gs, creature)

        result = apply_crew(gs, vehicle)

        assert result is gs

    def test_repeated_apply_does_not_double_fire(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=2)
        creature = _creature("4")
        _place(gs, vehicle, creature)

        gs = apply_crew(gs, vehicle)  # first crew: creature now tapped
        current_vehicle = _vehicle_perm(gs)
        second = apply_crew(gs, current_vehicle)  # no untapped creatures left

        # Applying again is a pure no-op (idempotent): one crewed entry.
        assert second is gs
        assert list(gs.crewed_vehicles.values()).count(2) == 1


# ---------------------------------------------------------------------------
# Pure transform guarantees
# ---------------------------------------------------------------------------

class TestPureTransform:
    def test_ai_returns_new_object_and_leaves_original(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=2)
        creature = _creature("4")
        _place(gs, vehicle, creature)

        new_gs = apply_crew(gs, vehicle)

        assert new_gs is not gs  # Meaningful change -> new object
        # The original GameState's creatures remain untapped (no mutation).
        orig_vehicle = next(p for p in gs.battlefield if p.card.name == "Smuggler's Copter")
        orig_creature = _creatures_on_board(gs)[0]
        assert orig_vehicle.crewed_until_end_of_turn is False
        assert orig_creature.tapped is False


# ---------------------------------------------------------------------------
# Human choice resolution
# ---------------------------------------------------------------------------

class TestResolveChoice:
    def _queued_human_state(self, crew_value: int, powers: list[str]) -> GameState:
        gs = _make_game(human="p1")
        vehicle = _vehicle(crew_value=crew_value)
        creatures = [_creature(p) for p in powers]
        _place(gs, vehicle, *creatures)
        return apply_crew(gs, vehicle)  # returned state carries the pending choice

    def test_resolve_all_available(self):
        gs = self._queued_human_state(3, ["2", "2"])

        new_gs = resolve_crew_choice(gs, "p1")  # No subset -> tap all available

        assert new_gs.pending_crew_choice is None
        v = next(p for p in new_gs.battlefield if p.card.name == "Smuggler's Copter")
        assert v.crewed_until_end_of_turn is True
        assert all(p.tapped for p in _creatures_on_board(new_gs))

    def test_resolve_valid_subset(self):
        gs = self._queued_human_state(2, ["2", "3"])
        small_id = next(p.id for p in gs.battlefield if p.card.power == "2")

        new_gs = resolve_crew_choice(gs, "p1", [small_id])

        assert new_gs.pending_crew_choice is None
        v = next(p for p in new_gs.battlefield if p.card.name == "Smuggler's Copter")
        assert v.crewed_until_end_of_turn is True
        by_power = {p.card.power: p for p in new_gs.battlefield}
        # Only the chosen creature was tapped; the other remains untapped.
        assert by_power["2"].tapped is True
        assert by_power["3"].tapped is False

    def test_resolve_insufficient_leaves_nothing_changed(self):
        gs = self._queued_human_state(5, ["1", "1"])

        new_gs = resolve_crew_choice(gs, "p1")

        # Total power (2) < crew value (5): pending cleared but nothing tapped.
        assert new_gs.pending_crew_choice is None
        v = next(p for p in new_gs.battlefield if p.card.name == "Smuggler's Copter")
        assert not v.crewed_until_end_of_turn
        assert all(not p.tapped for p in _creatures_on_board(new_gs))

    def test_resolve_wrong_player_is_noop(self):
        gs = self._queued_human_state(2, ["3"])
        result = resolve_crew_choice(gs, "p2")  # Not the choosing player
        assert result is gs


# ---------------------------------------------------------------------------
# End-of-turn expiration (CR 702.147b)
# ---------------------------------------------------------------------------

class TestExpiration:
    def test_expiration_reverts_vehicle_only(self):
        gs = _make_game(active="ai", holder="ai")
        vehicle = _vehicle(crew_value=2)
        _place(gs, vehicle, _creature("4"))

        gs = apply_crew(gs, vehicle)  # AI crew: builds copies on the returned state
        assert _vehicle_perm(gs).crewed_until_end_of_turn is True

        new_gs = handle_crew_expiration(gs)

        # Vehicle reverts to its non-vehicle artifact form; tracking cleared.
        v = next(p for p in new_gs.battlefield if p.card.name == "Smuggler's Copter")
        assert v.card.type_line == "Artifact — Vehicle"
        assert v.crewed_until_end_of_turn is False
        assert new_gs.crewed_vehicles == {}
        # The tapped creature stays tapped (expiration only reverts vehicles).
        assert all(p.tapped for p in _creatures_on_board(new_gs))

    def test_expiration_nothing_to_expire_returns_same_object(self):
        gs = _make_game(active="ai", holder="ai")
        result = handle_crew_expiration(gs)
        assert result is gs  # Empty crewed_vehicles dict -> pure no-op
