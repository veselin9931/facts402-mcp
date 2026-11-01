"""Live checks against the real services. They never move money:

- the free preview routes need no wallet;
- the payment path uses a fresh `Account.create()` key holding no USDC, so the facilitator refuses the signed
  payment with `insufficient_funds` and nothing settles.

Run with:  pytest -m live
"""

import pytest
from eth_account import Account

from facts402_mcp.budget import Budget, usd_to_atomic
from facts402_mcp.caller import Caller
from facts402_mcp.testing import TOKEN
from facts402_mcp.wallet import Wallet

pytestmark = pytest.mark.live


def _caller(wallet: Wallet | None) -> Caller:
    return Caller(Budget(usd_to_atomic("0.30"), usd_to_atomic("2")), wallet)


@pytest.mark.parametrize(("tool", "args"), [
    ("guard_preview", {"token": TOKEN}),
    ("pulse_preview", {"token": TOKEN}),
    ("signals_performance", {}),
])
async def test_free_previews_answer(catalog, tool, args):
    outcome = await _caller(None).call(catalog[tool], args)
    assert not outcome.is_error, outcome.payload


async def test_signals_preview_answers_or_is_warming_up(catalog):
    outcome = await _caller(None).call(catalog["signals_preview"], {})
    if outcome.is_error:  # Signals answers 503 until its 72 h warm-up is over (about 2026-11-03)
        assert outcome.payload["body"].get("warming_up") is True, outcome.payload


@pytest.mark.parametrize(("tool", "args"), [
    ("guard_exit_liquidity", {"token": TOKEN, "position_usd": 500}),
    ("pulse_search", {"query": "degen"}),
    ("guard_check", {"token": TOKEN}),
    ("pulse_token", {"token": TOKEN}),
    ("watch_24h", {"token": TOKEN}),
])
async def test_unfunded_wallet_reaches_the_facilitator(catalog, tool, args):
    caller = _caller(Wallet(Account.create()))
    outcome = await caller.call(catalog[tool], args)
    assert outcome.is_error and caller.budget.spent == 0
    assert "insufficient_funds" in outcome.payload["error"], outcome.payload
