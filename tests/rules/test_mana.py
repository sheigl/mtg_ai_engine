import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import ManaPool
from mtg_engine.engine.mana import can_pay_cost, pay_cost, parse_mana_cost, add_mana, pool_total


def test_parse_lightning_bolt():
    cost = parse_mana_cost("{R}")
    assert cost == {"R": 1}


def test_parse_counterspell():
    cost = parse_mana_cost("{U}{U}")
    assert cost == {"U": 2}


def test_parse_emrakul():
    cost = parse_mana_cost("{15}")
    assert cost == {"generic": 15}


def test_parse_mixed():
    cost = parse_mana_cost("{2}{G}{G}")
    assert cost == {"generic": 2, "G": 2}


def test_parse_empty():
    cost = parse_mana_cost("")
    assert cost == {}


def test_parse_hybrid():
    cost = parse_mana_cost("{W/U}")
    assert cost == {"W/U": 1}


def test_parse_phyrexian():
    cost = parse_mana_cost("{B/P}")
    assert cost == {"B/P": 1}


def test_parse_colorless_specific():
    cost = parse_mana_cost("{C}")
    assert cost == {"C": 1}


def test_can_pay_lightning_bolt():
    pool = ManaPool(R=1)
    assert can_pay_cost(pool, "{R}") is True


def test_cannot_pay_wrong_color():
    pool = ManaPool(G=1)
    assert can_pay_cost(pool, "{R}") is False


def test_can_pay_counterspell():
    pool = ManaPool(U=2)
    assert can_pay_cost(pool, "{U}{U}") is True


def test_cannot_pay_counterspell_one_blue():
    pool = ManaPool(U=1)
    assert can_pay_cost(pool, "{U}{U}") is False


def test_can_pay_emrakul():
    pool = ManaPool(G=10, W=5)
    assert can_pay_cost(pool, "{15}") is True


def test_cannot_pay_emrakul_insufficient():
    pool = ManaPool(G=10)
    assert can_pay_cost(pool, "{15}") is False


def test_pay_cost_deducts():
    pool = ManaPool(R=2, G=1)
    new_pool = pay_cost(pool, "{R}", {"R": 1})
    assert new_pool.R == 1
    assert new_pool.G == 1


def test_pay_cost_raises_on_insufficient():
    pool = ManaPool(G=1)
    try:
        pay_cost(pool, "{R}", {"R": 1})
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_add_mana_white():
    pool = ManaPool()
    new_pool = add_mana(pool, "W", 2)
    assert new_pool.W == 2


def test_add_mana_does_not_mutate():
    pool = ManaPool(R=1)
    new_pool = add_mana(pool, "R", 1)
    assert pool.R == 1  # original unchanged
    assert new_pool.R == 2


def test_pool_total():
    pool = ManaPool(W=1, U=2, B=1, R=0, G=3, C=1)
    assert pool_total(pool) == 8


def test_can_pay_with_explicit_payment():
    pool = ManaPool(R=1, G=2)
    # Pay {R} with R=1
    assert can_pay_cost(pool, "{R}", {"R": 1}) is True


def test_cannot_pay_with_wrong_explicit_payment():
    pool = ManaPool(R=1, G=2)
    # Try to pay {R} with G=1 (invalid: colored cost requires matching color)
    assert can_pay_cost(pool, "{R}", {"G": 1}) is False


def test_pay_generic_with_any_color():
    pool = ManaPool(G=3)
    assert can_pay_cost(pool, "{2}") is True


def test_cannot_pay_generic_with_too_little():
    pool = ManaPool(G=1)
    assert can_pay_cost(pool, "{2}") is False
