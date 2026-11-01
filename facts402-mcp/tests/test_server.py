from decimal import Decimal

import httpx
import pytest
from mcp import Client

from facts402_mcp.app import banner, build_server, caller_from_settings, tool_definition
from facts402_mcp.catalog import Route, Style, ToolSpec
from facts402_mcp.config import Settings
from facts402_mcp.server import INFO
from facts402_mcp.testing import FakeService, make_caller


def client_for(catalog, handler) -> Client:
    return Client(build_server(INFO, catalog, make_caller(FakeService(handler), None)))


async def test_lists_every_tool_with_schema(catalog):
    async with client_for(catalog, lambda r: httpx.Response(500)) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == set(catalog)
    assert tools["iban_check"].input_schema["required"] == ["iban"]
    assert "$0.01" in tools["iban_check"].description


async def test_paid_tool_without_wallet_is_a_tool_error(catalog):
    async with client_for(catalog, lambda r: httpx.Response(500)) as client:
        result = await client.call_tool("sanctions_screen", {"name": "Banco Nacional de Cuba"})
    assert result.is_error
    assert result.structured_content["price_usd"] == "0.01"


async def test_unknown_tool_is_a_protocol_error(catalog):
    async with client_for(catalog, lambda r: httpx.Response(500)) as client:
        with pytest.raises(Exception, match="unknown tool"):
            await client.call_tool("nope", {})


def _spec(method: str, paid: bool) -> ToolSpec:
    return ToolSpec(name="t", title="T", route=Route(method, "https://x.test", "/"), summary="s", paid=paid,
                    style=Style.QUERY, price_usd=Decimal("0.01") if paid else None,
                    input_schema={"type": "object"})


@pytest.mark.parametrize(("method", "paid", "read_only", "idempotent", "destructive"), [
    ("GET", False, True, True, False),
    ("GET", True, False, False, False),  # paid: spends money, never read-only or safe to retry blindly
    ("POST", True, False, False, False),
    ("DELETE", False, False, True, True),
])
def test_annotations(method, paid, read_only, idempotent, destructive):
    hints = tool_definition(_spec(method, paid)).annotations
    assert (hints.read_only_hint, hints.idempotent_hint, hints.destructive_hint) == (read_only, idempotent, destructive)


def test_banner_shows_address_and_limits_never_the_key(catalog):
    key = "0x" + "12" * 32
    settings = Settings.from_env({"X402_PRIVATE_KEY": key})
    caller = caller_from_settings(settings, catalog)
    line = banner(INFO, settings, caller)
    assert key not in line and key[2:] not in line
    assert caller.wallet.address in line and "$0.30/call" in line
