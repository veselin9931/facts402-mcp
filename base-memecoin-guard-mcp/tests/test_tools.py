"""Trading-specific request shapes and the MCP surface. The payment core is tested in facts402-mcp."""

import httpx
from mcp import Client

from base_memecoin_guard_mcp.server import INFO
from facts402_mcp.app import build_server
from facts402_mcp.testing import TOKEN, FakeService, make_caller, never_called, paywall

WATCH_ID = "w_" + "a" * 22


async def test_free_preview_is_a_plain_get(catalog):
    service = FakeService(lambda r: httpx.Response(200, json={"verdict": "CAUTION", "risk_score": 10}))
    outcome = await make_caller(service, None).call(catalog["guard_preview"], {"token": TOKEN})
    assert outcome.payload == {"verdict": "CAUTION", "risk_score": 10}
    assert str(service.requests[0].url) == f"https://guard.facts402.com/v1/guard/preview?token={TOKEN}"


async def test_watch_events_sends_bearer_secret_and_cursor(catalog):
    service = FakeService(lambda r: httpx.Response(200, json={"events": [], "next_cursor": 7}))
    args = {"watch_id": WATCH_ID, "watch_secret": "s3cret", "since": 7}
    outcome = await make_caller(service, None).call(catalog["watch_events"], args)
    assert not outcome.is_error
    (request,) = service.requests
    assert str(request.url) == f"https://watch.facts402.com/v1/watch/{WATCH_ID}/events?since=7"
    assert request.headers["authorization"] == "Bearer s3cret"


async def test_watch_stop_is_a_delete(catalog):
    service = FakeService(lambda r: httpx.Response(200, json={"deleted": True}))
    await make_caller(service, None).call(catalog["watch_stop"], {"watch_id": WATCH_ID, "watch_secret": "s"})
    assert service.requests[0].method == "DELETE"


async def test_paid_get_sends_query_and_pays(catalog, wallet):
    service = FakeService(paywall("0.08", lambda r: httpx.Response(200, json={"tokens": []})))
    caller = make_caller(service, wallet)
    outcome = await caller.call(catalog["pulse_trending"], {"window": "6h"})
    assert outcome.payload["payment"]["paid_usd"] == "0.08"
    assert str(service.requests[-1].url) == "https://pulse.facts402.com/v1/pulse/trending?window=6h"


async def test_long_watch_needs_a_higher_cap(catalog, wallet):
    outcome = await make_caller(FakeService(never_called), wallet).call(catalog["watch_7d"], {"token": TOKEN})
    assert outcome.is_error and "per-call cap" in outcome.payload["error"]
    service = FakeService(paywall("0.60", lambda r: httpx.Response(200, json={"watch_id": WATCH_ID})))
    outcome = await make_caller(service, wallet, per_call="0.60").call(catalog["watch_7d"], {"token": TOKEN})
    assert outcome.payload["payment"]["paid_usd"] == "0.60"


async def test_server_lists_the_trading_tools(catalog):
    caller = make_caller(FakeService(never_called), None, free_tools=("guard_preview",))
    async with Client(build_server(INFO, catalog, caller)) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        result = await client.call_tool("guard_check", {"token": TOKEN})
    assert set(tools) == set(catalog)
    assert tools["guard_preview"].annotations.read_only_hint is True
    assert tools["guard_check"].annotations.read_only_hint is False
    assert result.is_error and result.structured_content["free_tools"] == ["guard_preview"]
