"""Tests for mana pool enhancement (MANA-01)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.models.game import ManaPool
from mtg_engine.engine.mana import (
    get_mana_colors,
    pool_can_produce_color,
    add_split_mana,
)


def test_get_mana_colors_empty():
    """Empty pool has no colors."""
    pool = ManaPool()
    assert get_mana_colors(pool) == set()


def test_get_mana_colors_single():
    """Pool with only white mana."""
    pool = ManaPool(W=3)
    assert get_mana_colors(pool) == {"white"}


def test_get_mana_colors_multiple():
    """Pool with multiple colors."""
    pool = ManaPool(W=1, U=2, G=1)
    assert get_mana_colors(pool) == {"white", "blue", "green"}


def test_get_mana_colors_ignores_colorless():
    """Colorless mana does not count as a color."""
    pool = ManaPool(C=5, W=1)
    assert get_mana_colors(pool) == {"white"}


def test_pool_can_produce_color_symbol():
    """Check color by symbol."""
    pool = ManaPool(R=2)
    assert pool_can_produce_color(pool, "R") is True
    assert pool_can_produce_color(pool, "W") is False


def test_pool_can_produce_color_name():
    """Check color by name."""
    pool = ManaPool(G=1)
    assert pool_can_produce_color(pool, "green") is True
    assert pool_can_produce_color(pool, "red") is False


def test_pool_can_produce_color_no_mana():
    """Empty pool cannot produce any color."""
    pool = ManaPool()
    assert pool_can_produce_color(pool, "W") is False


def test_add_split_mana_both():
    """Split mana adds both symbols."""
    pool = ManaPool()
    new_pool = add_split_mana(pool, "W", "U", 1)
    assert new_pool.W == 1
    assert new_pool.U == 1


def test_add_split_mana_amount():
    """Split mana with amount > 1."""
    pool = ManaPool(W=1)
    new_pool = add_split_mana(pool, "W", "U", 2)
    assert new_pool.W == 3  # 1 + 2
    assert new_pool.U == 2


def test_add_split_mana_colorless():
    """Split mana with colorless."""
    pool = ManaPool()
    new_pool = add_split_mana(pool, "R", "C", 1)
    assert new_pool.R == 1
    assert new_pool.C == 1


def test_add_split_mana_original_unchanged():
    """Original pool is not mutated."""
    pool = ManaPool(W=1, U=0)
    _ = add_split_mana(pool, "W", "U", 1)
    assert pool.W == 1
    assert pool.U == 0
