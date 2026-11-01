from decimal import Decimal

import pytest

from facts402_mcp.budget import Budget, BudgetRefused, atomic_to_usd, usd_to_atomic
from facts402_mcp.config import ConfigError, Settings
from facts402_mcp.wallet import Wallet


@pytest.mark.parametrize(("atomic", "text"), [(10_000, "0.01"), (300_000, "0.30"), (1_200_000, "1.20"), (1_500, "0.0015")])
def test_usd_formatting(atomic, text):
    assert atomic_to_usd(atomic) == text
    assert usd_to_atomic(text) == atomic


def test_reserve_and_settle_track_spend():
    budget = Budget(usd_to_atomic("0.30"), usd_to_atomic("1.00"))
    reservation = budget.reserve(usd_to_atomic("0.05"))
    assert reservation.cap == usd_to_atomic("0.30")
    assert budget.remaining == usd_to_atomic("0.70")
    budget.settle(reservation, usd_to_atomic("0.05"))
    assert budget.spent == usd_to_atomic("0.05")
    assert budget.remaining == usd_to_atomic("0.95")


def test_price_above_per_call_cap_is_refused():
    budget = Budget(usd_to_atomic("0.30"), usd_to_atomic("2.00"))
    with pytest.raises(BudgetRefused, match="per-call cap"):
        budget.reserve(usd_to_atomic("0.60"))


def test_session_budget_is_enforced_including_in_flight_calls():
    budget = Budget(usd_to_atomic("0.30"), usd_to_atomic("0.50"))
    first = budget.reserve(usd_to_atomic("0.25"))  # reserves its 0.30 cap
    second = budget.reserve(usd_to_atomic("0.20"))  # 0.20 left, cap shrinks to it
    assert second.cap == usd_to_atomic("0.20")
    with pytest.raises(BudgetRefused, match="session budget"):
        budget.reserve(usd_to_atomic("0.01"))
    budget.settle(first, 0)  # nothing charged frees the reservation
    assert budget.reserve(usd_to_atomic("0.01")).cap == usd_to_atomic("0.30")
    assert budget.spent == 0


def test_settings_defaults_and_parsing():
    s = Settings.from_env({})
    assert (s.private_key, s.max_per_call_usd, s.session_budget_usd) == (None, Decimal("0.30"), Decimal("2.00"))
    s = Settings.from_env({"X402_MAX_PER_CALL_USD": "$1.20", "X402_SESSION_BUDGET_USD": " 5 ", "X402_PRIVATE_KEY": " "})
    assert (s.private_key, s.max_per_call_usd, s.session_budget_usd) == (None, Decimal("1.20"), Decimal("5"))


@pytest.mark.parametrize("value", ["abc", "0", "-1", "1000", "nan", "Infinity"])
def test_bad_limits_fail_fast(value):
    with pytest.raises(ConfigError, match="X402_SESSION_BUDGET_USD"):
        Settings.from_env({"X402_SESSION_BUDGET_USD": value})


def test_private_key_never_appears_in_reprs_or_errors():
    key = "0x" + "11" * 32
    assert key not in repr(Settings.from_env({"X402_PRIVATE_KEY": key}))
    assert key not in repr(Wallet.from_key(key))
    bad = "0x" + "zz" * 32
    with pytest.raises(ValueError) as info:
        Wallet.from_key(bad)
    assert bad not in str(info.value)


def test_unfilled_host_placeholders_count_as_unset():
    s = Settings.from_env({"X402_PRIVATE_KEY": "${user_config.x402_private_key}",
                           "X402_MAX_PER_CALL_USD": "${user_config.max_per_call_usd}"})
    assert s.private_key is None and s.max_per_call_usd == Decimal("0.30")
