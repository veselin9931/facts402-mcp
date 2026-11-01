"""Settings from environment variables. The private key is never logged, echoed or put in a repr."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

ENV_PRIVATE_KEY = "X402_PRIVATE_KEY"
ENV_MAX_PER_CALL = "X402_MAX_PER_CALL_USD"
ENV_SESSION_BUDGET = "X402_SESSION_BUDGET_USD"

DEFAULT_MAX_PER_CALL = Decimal("0.30")
DEFAULT_SESSION_BUDGET = Decimal("2.00")
HARD_CEILING_USD = Decimal("100")  # sanity bound against typos such as 200 instead of 2.00

# Hosts that template config (MCPB bundles) may pass an unfilled `${user_config.x}` through literally.
_UNFILLED_PLACEHOLDER = re.compile(r"^\$\{.*\}$")


class ConfigError(Exception):
    pass


def _value(env: Mapping[str, str], name: str) -> str:
    raw = env.get(name, "").strip()
    return "" if _UNFILLED_PLACEHOLDER.match(raw) else raw


def _usd(env: Mapping[str, str], name: str, default: Decimal) -> Decimal:
    raw = _value(env, name).lstrip("$")
    if not raw:
        return default
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ConfigError(f"{name} must be a USD amount such as 0.30, got {raw!r}") from None
    if not (value.is_finite() and 0 < value <= HARD_CEILING_USD):
        raise ConfigError(f"{name} must be above 0 and at most {HARD_CEILING_USD}, got {raw!r}")
    return value


@dataclass(frozen=True)
class Settings:
    private_key: str | None = field(repr=False)
    max_per_call_usd: Decimal
    session_budget_usd: Decimal

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        return cls(
            private_key=_value(env, ENV_PRIVATE_KEY) or None,
            max_per_call_usd=_usd(env, ENV_MAX_PER_CALL, DEFAULT_MAX_PER_CALL),
            session_budget_usd=_usd(env, ENV_SESSION_BUDGET, DEFAULT_SESSION_BUDGET),
        )
