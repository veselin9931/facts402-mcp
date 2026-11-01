from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from base_memecoin_guard_mcp.tools import HAND_WRITTEN_SCHEMAS
from facts402_mcp.catalog import Style, thaw

PAID_TOOLS = {
    "guard_check", "guard_exit_liquidity", "guard_batch",
    "pulse_token", "pulse_trending", "pulse_search",
    "signals_feed", "signals_token", "signals_wallet", "signals_leaderboard", "signals_brief",
    "watch_24h", "watch_72h", "watch_7d", "watch_extend_24h",
}
FREE_TOOLS = {"guard_preview", "pulse_preview", "signals_preview", "signals_performance",
              "watch_status", "watch_events", "watch_stop"}


def test_every_trading_route_is_a_tool(catalog):
    assert {n for n, s in catalog.items() if s.paid} == PAID_TOOLS
    assert {n for n, s in catalog.items() if not s.paid} == FREE_TOOLS


@pytest.mark.parametrize(("name", "price"), [
    ("guard_check", "0.05"), ("guard_exit_liquidity", "0.02"), ("guard_batch", "0.30"), ("pulse_token", "0.04"),
    ("pulse_trending", "0.08"), ("signals_feed", "0.15"), ("signals_brief", "0.25"), ("watch_24h", "0.12"),
    ("watch_72h", "0.30"), ("watch_7d", "0.60"), ("watch_extend_24h", "0.12"),
])
def test_prices_come_from_the_snapshot(catalog, name, price):
    assert catalog[name].price_usd == Decimal(price)
    assert f"${price} USDC" in catalog[name].description


def test_free_tools_say_so(catalog):
    for name in FREE_TOOLS:
        assert catalog[name].price_usd is None and "FREE" in catalog[name].description


def test_schemas_are_valid_objects_without_top_level_combinators(catalog):
    for spec in catalog.values():
        schema = thaw(spec.input_schema)
        Draft202012Validator.check_schema(schema)
        assert schema["type"] == "object", spec.name
        assert not {"oneOf", "anyOf", "allOf"} & schema.keys(), spec.name


def test_combinator_constraints_survive_as_text(catalog):
    assert "exactly one of" in catalog["pulse_token"].input_schema["description"].lower()
    assert "include_x" not in catalog["pulse_token"].input_schema["properties"]
    assert "position_usd" in catalog["guard_exit_liquidity"].input_schema["description"]


def test_watch_bearer_tools_use_hand_written_schemas(catalog):
    for name in HAND_WRITTEN_SCHEMAS:
        assert catalog[name].style is Style.WATCH_BEARER
        assert set(catalog[name].input_schema["required"]) == {"watch_id", "watch_secret"}


@pytest.mark.parametrize("watch_id", ["w_" + "a" * 22 + "\n", "w_" + "a" * 21, "../" + "a" * 21])
def test_watch_id_cannot_smuggle_path_or_newline(catalog, watch_id):
    validator = Draft202012Validator(thaw(catalog["watch_status"].input_schema))
    assert not validator.is_valid({"watch_id": watch_id, "watch_secret": "s"})


def test_descriptions_carry_the_search_terms_trading_agents_use(catalog):
    text = " ".join(s.description for s in catalog.values()).lower()
    for term in ("honeypot", "rug pull", "exit liquidity", "insider", "sniper", "smart money", "copy trade",
                 "base", "memecoin", "whale", "webhook", "shill", "slippage", "tax"):
        assert term in text, term
