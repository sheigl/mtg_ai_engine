"""
Mana system. REQ-A07, mana cost validation and payment.
Supports W, U, B, R, G, C (colorless), and generic (number).
Also supports hybrid, Phyrexian, and snow mana symbols.
"""
import re

from mtg_engine.models.game import ManaPool


# Regex to parse mana symbols from a mana cost string like "{2}{R}{U}"
_SYMBOL_RE = re.compile(r"\{([^}]+)\}")


def parse_mana_cost(mana_cost: str) -> dict[str, int]:
    """
    Parse a mana cost string into a dict of {symbol: count}.

    Examples:
      "{2}{R}"   → {"generic": 2, "R": 1}
      "{U}{U}"   → {"U": 2}
      "{W/U}"    → {"W/U": 1}  (hybrid)
      "{2/B}"    → {"2/B": 1}  (hybrid generic)
      "{B/P}"    → {"B/P": 1}  (Phyrexian)
      "{S}"      → {"S": 1}    (snow)
      "{15}"     → {"generic": 15}
    """
    cost: dict[str, int] = {}
    for m in _SYMBOL_RE.finditer(mana_cost or ""):
        sym = m.group(1)
        if sym.isdigit():
            cost["generic"] = cost.get("generic", 0) + int(sym)
        elif sym == "X":
            cost["X"] = cost.get("X", 0) + 1
        elif sym == "C":
            # {C} means specifically colorless mana required
            cost["C"] = cost.get("C", 0) + 1
        elif sym == "S":
            cost["S"] = cost.get("S", 0) + 1  # snow mana
        elif "/" in sym:
            # Hybrid or Phyrexian mana symbols
            cost[sym] = cost.get(sym, 0) + 1
        elif sym in ("W", "U", "B", "R", "G"):
            cost[sym] = cost.get(sym, 0) + 1
        else:
            # Unknown symbol (e.g., large generic numbers like {15})
            try:
                cost["generic"] = cost.get("generic", 0) + int(sym)
            except ValueError:
                cost[sym] = cost.get(sym, 0) + 1
    return cost


def pool_total(pool: ManaPool) -> int:
    """Return the total mana available in the pool."""
    return pool.W + pool.U + pool.B + pool.R + pool.G + pool.C


def can_pay_cost(pool: ManaPool, mana_cost: str, payment: dict[str, int] | None = None) -> bool:
    """
    Check if the pool can pay the mana cost.
    If payment is provided, validate that specific payment dict against pool and cost.
    Otherwise perform a simplified sufficiency check.
    """
    cost = parse_mana_cost(mana_cost)
    if payment is not None:
        return _validate_payment(pool, cost, payment)
    return _can_pay_simple(pool, cost)


def _can_pay_simple(pool: ManaPool, cost: dict[str, int]) -> bool:
    """
    Simplified sufficiency check: enough colored mana exists + enough total for generic.
    Does not validate hybrid costs exhaustively (greedy approach).
    """
    temp = {
        "W": pool.W,
        "U": pool.U,
        "B": pool.B,
        "R": pool.R,
        "G": pool.G,
        "C": pool.C,
    }

    # Pay each required colored mana symbol first
    for color in ("W", "U", "B", "R", "G"):
        needed = cost.get(color, 0)
        if temp[color] < needed:
            return False
        temp[color] -= needed

    # Pay colorless-specific cost ({C}): can only be paid with colorless mana
    needed_c = cost.get("C", 0)
    if temp["C"] < needed_c:
        return False
    temp["C"] -= needed_c

    # Pay generic cost with any remaining mana
    generic = cost.get("generic", 0)
    remaining = sum(temp.values())
    return remaining >= generic


def _validate_payment(pool: ManaPool, cost: dict[str, int], payment: dict[str, int]) -> bool:
    """
    Validate an explicit payment dict against a pool and cost.
    Checks that:
    1. The payment does not exceed available mana in the pool.
    2. The payment satisfies all colored requirements.
    3. The remaining payment after colored requirements covers generic.
    """
    pool_dict = {
        "W": pool.W,
        "U": pool.U,
        "B": pool.B,
        "R": pool.R,
        "G": pool.G,
        "C": pool.C,
    }

    # Verify payment does not exceed pool amounts
    for color, amount in payment.items():
        if pool_dict.get(color, 0) < amount:
            return False

    # Verify colored requirements are satisfied by the payment
    temp_payment = dict(payment)
    for color in ("W", "U", "B", "R", "G"):
        needed = cost.get(color, 0)
        paid = temp_payment.get(color, 0)
        if paid < needed:
            return False
        temp_payment[color] = paid - needed

    # Verify colorless-specific requirement
    needed_c = cost.get("C", 0)
    if temp_payment.get("C", 0) < needed_c:
        return False
    temp_payment["C"] = temp_payment.get("C", 0) - needed_c

    # Verify generic requirement is covered by remaining payment
    generic = cost.get("generic", 0)
    remaining = sum(v for v in temp_payment.values() if v > 0)
    return remaining >= generic


def pay_cost(pool: ManaPool, mana_cost: str, payment: dict[str, int]) -> ManaPool:
    """
    Deduct payment from pool and return the new ManaPool.
    Raises ValueError if the payment is insufficient or invalid.
    """
    cost = parse_mana_cost(mana_cost)
    if not _validate_payment(pool, cost, payment):
        raise ValueError(
            f"Payment {payment} cannot satisfy cost {mana_cost!r} from pool {pool}"
        )
    new_pool = pool.model_copy()
    for color, amount in payment.items():
        current = getattr(new_pool, color, 0)
        setattr(new_pool, color, current - amount)
    return new_pool


def add_mana(pool: ManaPool, symbol: str, amount: int = 1) -> ManaPool:
    """
    Add mana to pool. symbol must be one of: W, U, B, R, G, C.
    Returns a new ManaPool with the added mana.
    """
    new_pool = pool.model_copy()
    if symbol in ("W", "U", "B", "R", "G", "C"):
        setattr(new_pool, symbol, getattr(new_pool, symbol) + amount)
    else:
        # Unknown symbol — log and ignore
        import logging
        logging.getLogger(__name__).warning("add_mana: unknown symbol %r", symbol)
    return new_pool


def empty_pool(pool: ManaPool) -> ManaPool:
    """Return an empty mana pool (all zeros)."""
    return ManaPool()
