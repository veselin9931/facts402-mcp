"""Live checks against the real services. They never move money: the recommender preview is free, and a
fresh `Account.create()` key holds no USDC, so the CDP facilitator refuses the signed payment with
`insufficient_funds` and nothing settles.

Run with:  pytest -m live
"""

import pytest
from eth_account import Account

from facts402_mcp.budget import Budget, usd_to_atomic
from facts402_mcp.caller import Caller
from facts402_mcp.wallet import Wallet

pytestmark = pytest.mark.live


@pytest.mark.parametrize(("tool", "args"), [
    ("iban_check", {"iban": "DE89 3704 0044 0532 0130 00"}),
    ("sanctions_screen", {"name": "Banco Nacional de Cuba"}),
    ("x402_recommend", {"need": "web search"}),
])
async def test_unfunded_wallet_reaches_the_facilitator(catalog, tool, args):
    caller = Caller(Budget(usd_to_atomic("0.30"), usd_to_atomic("2")), Wallet(Account.create()))
    outcome = await caller.call(catalog[tool], args)
    assert outcome.is_error and caller.budget.spent == 0
    assert "insufficient_funds" in outcome.payload["error"], outcome.payload


async def test_recommend_preview_answers_without_a_wallet(catalog):
    caller = Caller(Budget(usd_to_atomic("0.30"), usd_to_atomic("2")), None)
    outcome = await caller.call(catalog["x402_recommend_preview"], {"need": "iban validation"})
    assert not outcome.is_error and "top_pick" in outcome.payload, outcome.payload
