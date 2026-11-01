"""Spend limits in USDC atomic units (6 decimals): a per-call cap and a per-session budget."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from .catalog import usd_text

USDC_DECIMALS = 6
_ATOMIC_PER_USD = Decimal(10) ** USDC_DECIMALS


def usd_to_atomic(usd: Decimal | str) -> int:
    return int((Decimal(usd) * _ATOMIC_PER_USD).to_integral_value(rounding=ROUND_DOWN))


def atomic_to_usd(atomic: int) -> str:
    """`50000 -> "0.05"`; always at least two decimals."""
    return usd_text(Decimal(atomic) / _ATOMIC_PER_USD)


class BudgetRefused(Exception):
    """A paid call was refused before any request went out."""


@dataclass(frozen=True)
class Reservation:
    cap: int  # the most this call may pay, atomic


class Budget:
    """Tracks session spend. A call reserves its cap up front so concurrent calls cannot overspend."""

    def __init__(self, max_per_call: int, session_budget: int) -> None:
        if max_per_call <= 0 or session_budget <= 0:
            raise ValueError("spend limits must be positive")
        self.max_per_call = max_per_call
        self.session_budget = session_budget
        self.spent = 0
        self._reserved = 0

    @property
    def remaining(self) -> int:
        return self.session_budget - self.spent - self._reserved

    def reserve(self, price: int) -> Reservation:
        if price > self.max_per_call:
            raise BudgetRefused(
                f"price ${atomic_to_usd(price)} is above your per-call cap ${atomic_to_usd(self.max_per_call)} "
                "(raise X402_MAX_PER_CALL_USD to allow it)"
            )
        if price > self.remaining:
            raise BudgetRefused(
                f"price ${atomic_to_usd(price)} is above what is left of your session budget "
                f"(${atomic_to_usd(max(self.remaining, 0))} of ${atomic_to_usd(self.session_budget)}, calls in "
                "flight hold up to their cap until they finish; "
                "raise X402_SESSION_BUDGET_USD or restart the server for a new session)"
            )
        reservation = Reservation(cap=min(self.max_per_call, self.remaining))
        self._reserved += reservation.cap
        return reservation

    def settle(self, reservation: Reservation, paid: int) -> None:
        """Release the reservation and record what was actually paid (0 when nothing was charged)."""
        self._reserved -= reservation.cap
        self.spent += paid
