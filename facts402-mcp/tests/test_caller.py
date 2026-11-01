import json

import anyio
import httpx
import pytest

from facts402_mcp.app import caller_from_settings
from facts402_mcp.budget import usd_to_atomic
from facts402_mcp.caller import build_request
from facts402_mcp.catalog import Route, Style, ToolSpec
from facts402_mcp.config import Settings
from facts402_mcp.testing import (
    TX,
    FakeService,
    make_caller,
    never_called,
    paywall,
    quote_header,
    settled_header,
)

IBAN = {"iban": "DE89 3704 0044 0532 0130 00"}

FREE_GET = ToolSpec(
    name="demo_preview", title="Demo preview", route=Route("GET", "https://demo.test", "/preview"),
    summary="Demo.", paid=False, style=Style.QUERY, price_usd=None,
    input_schema={"type": "object", "properties": {"q": {"type": "string"}}, "additionalProperties": False},
)


def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"valid": True})


# --- free tools -----------------------------------------------------------------------------------------------
async def test_free_tool_needs_no_wallet():
    service = FakeService(lambda r: httpx.Response(200, json={"hello": "world"}))
    outcome = await make_caller(service, None).call(FREE_GET, {"q": "x"})
    assert (outcome.is_error, outcome.payload) == (False, {"hello": "world"})
    (request,) = service.requests
    assert str(request.url) == "https://demo.test/preview?q=x"
    assert "payment-signature" not in request.headers


async def test_free_tool_http_error_is_reported_not_raised():
    service = FakeService(lambda r: httpx.Response(503, json={"warming_up": True}))
    outcome = await make_caller(service, None).call(FREE_GET, {})
    assert outcome.is_error and outcome.payload == {"error": "HTTP 503", "body": {"warming_up": True}}


async def test_network_failure_is_reported_not_raised():
    def boom(request):
        raise httpx.ConnectError("refused")

    outcome = await make_caller(FakeService(boom), None).call(FREE_GET, {})
    assert outcome.is_error and "network error" in outcome.payload["error"]


async def test_unexpected_exception_is_reported_not_raised():
    def bug(request):
        raise RuntimeError("boom")

    outcome = await make_caller(FakeService(bug), None).call(FREE_GET, {})
    assert outcome.is_error and outcome.payload["error"].startswith("unexpected RuntimeError")


async def test_invalid_arguments_never_reach_the_network(catalog, wallet):
    outcome = await make_caller(FakeService(never_called), wallet).call(catalog["iban_check"], {"iban": "!"})
    assert outcome.is_error and "nothing was sent or paid" in outcome.payload["error"]
    assert outcome.payload["details"][0].startswith("iban: ")


# --- paid tools without a wallet --------------------------------------------------------------------------------
async def test_paid_tool_without_key_explains_price_and_setup(catalog):
    caller = make_caller(FakeService(never_called), None, free_tools=("demo_preview",))
    outcome = await caller.call(catalog["sanctions_screen"], {"name": "Banco Nacional de Cuba"})
    assert outcome.is_error
    assert outcome.payload["price_usd"] == "0.01"
    assert "X402_PRIVATE_KEY is not set" in outcome.payload["error"]
    assert "X402_PRIVATE_KEY" in outcome.payload["how_to_enable"]
    assert outcome.payload["free_tools"] == ["demo_preview"]


async def test_invalid_key_is_reported_without_echoing_it(catalog):
    key = "0x" + "zz" * 32
    caller = caller_from_settings(Settings.from_env({"X402_PRIVATE_KEY": key}), catalog)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "not a valid hex private key" in outcome.payload["error"]
    assert key not in json.dumps(outcome.payload)


# --- paid tools with a wallet -----------------------------------------------------------------------------------
async def test_paid_call_signs_pays_and_records_spend(catalog, wallet):
    def answer(request):
        return httpx.Response(200, json={"valid": True}, headers={"PAYMENT-RESPONSE": settled_header("10000", wallet.address)})

    service = FakeService(paywall("0.01", answer))
    caller = make_caller(service, wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert not outcome.is_error
    assert outcome.payload == {
        "result": {"valid": True},
        "payment": {"paid_usd": "0.01", "transaction": TX, "network": "eip155:8453",
                    "session_spent_usd": "0.01", "session_budget_usd": "2.00"},
    }
    assert caller.budget.spent == usd_to_atomic("0.01") and caller.budget.remaining == usd_to_atomic("1.99")
    unpaid, paid = service.requests
    assert json.loads(paid.content) == IBAN
    assert "payment-signature" in paid.headers and "payment-signature" not in unpaid.headers


@pytest.mark.parametrize("reported", ["0", "0.01", "not-a-number"])
async def test_spend_is_the_signed_amount_whatever_the_server_reports(catalog, wallet, reported):
    def answer(request):
        return httpx.Response(200, json={}, headers={"X-PAYMENT-RESPONSE": settled_header(reported, wallet.address)})

    caller = make_caller(FakeService(paywall("0.01", answer)), wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert not outcome.is_error
    assert outcome.payload["payment"]["transaction"] == TX  # legacy X-PAYMENT-RESPONSE header is read too
    assert caller.budget.spent == usd_to_atomic("0.01")


async def test_price_above_cap_is_refused_before_any_request(catalog, wallet):
    caller = make_caller(FakeService(never_called), wallet, per_call="0.005")
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error
    assert "per-call cap" in outcome.payload["error"] and "X402_MAX_PER_CALL_USD" in outcome.payload["error"]


async def test_session_budget_stops_further_calls(catalog, wallet):
    service = FakeService(paywall("0.01", ok))
    caller = make_caller(service, wallet, session="0.02")
    for _ in range(2):
        assert not (await caller.call(catalog["iban_check"], IBAN)).is_error
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "session budget" in outcome.payload["error"]
    assert len(service.requests) == 4


@pytest.mark.parametrize(("quote", "label"), [
    ({"price_usd": "0.50"}, "live quote above the per-call cap"),
    ({"price_usd": "0.01", "pay_to": "0x" + "11" * 20}, "another payee"),
    ({"price_usd": "0.01", "asset": "0x" + "22" * 20}, "a token other than USDC"),
    ({"price_usd": "0.01", "extra": {"name": "USD Coin", "version": "2", "assetTransferMethod": "permit2"}}, "permit2"),
])
async def test_unacceptable_quotes_are_never_signed(catalog, wallet, quote, label):
    price = quote.pop("price_usd")
    caller = make_caller(FakeService(paywall(price, never_called, **quote)), wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "payment not made" in outcome.payload["error"], label
    assert caller.budget.spent == 0 and caller.budget.remaining == caller.budget.session_budget
    if "pay_to" in quote:
        assert "pays facts402 only" in outcome.payload["hint"]


async def test_signing_cap_shrinks_to_what_is_left_of_the_budget(catalog, wallet):
    caller = make_caller(FakeService(paywall("0.25", never_called)), wallet, session="0.20")
    outcome = await caller.call(catalog["iban_check"], IBAN)  # catalog 0.01 fits; live quote 0.25 > 0.20 left
    assert outcome.is_error and "payment not made" in outcome.payload["error"]
    assert caller.budget.spent == 0


async def test_rejected_payment_reports_reason_and_costs_nothing(catalog, wallet):
    def reject(request):
        header = quote_header(str(request.url), "0.01", error="insufficient_funds")
        return httpx.Response(402, headers={"PAYMENT-REQUIRED": header}, json={})

    caller = make_caller(FakeService(paywall("0.01", reject)), wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.payload["error"] == "payment was not accepted (insufficient_funds), you were not charged"
    assert wallet.address in outcome.payload["hint"]
    assert caller.budget.spent == 0


async def test_server_error_after_payment_is_not_charged(catalog, wallet):
    caller = make_caller(FakeService(paywall("0.01", lambda r: httpx.Response(503, json={"charged": False}))), wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "not charged" in outcome.payload["error"]
    assert caller.budget.spent == 0


async def test_connection_lost_after_signing_counts_against_budget(catalog, wallet):
    def drop(request):
        raise httpx.ReadTimeout("timed out")

    caller = make_caller(FakeService(paywall("0.01", drop)), wallet)
    outcome = await caller.call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "may have been charged" in outcome.payload["error"]
    assert caller.budget.spent == usd_to_atomic("0.01")
    assert caller.budget.remaining == usd_to_atomic("1.99")  # reservation released


async def test_cancellation_after_signing_counts_against_budget(catalog, wallet):
    signed_and_sent = anyio.Event()

    class SlowTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            if "payment-signature" not in request.headers:
                return httpx.Response(402, headers={"PAYMENT-REQUIRED": quote_header(str(request.url), "0.01")})
            signed_and_sent.set()
            await anyio.sleep(60)

    caller = make_caller(FakeService(never_called), wallet)
    caller._transport_factory = SlowTransport
    async with anyio.create_task_group() as tg:
        tg.start_soon(caller.call, catalog["iban_check"], IBAN)
        await signed_and_sent.wait()
        tg.cancel_scope.cancel()
    assert caller.budget.spent == usd_to_atomic("0.01")
    assert caller.budget.remaining == usd_to_atomic("1.99")


async def test_oversized_quote_body_is_reported_not_raised(catalog, wallet):
    huge = httpx.Response(402, content=b"x" * ((1 << 20) + 1))
    outcome = await make_caller(FakeService(lambda r: huge), wallet).call(catalog["iban_check"], IBAN)
    assert outcome.is_error and "ResponseBodyTooLargeError" in outcome.payload["error"]


async def test_concurrent_calls_cannot_overspend(catalog, wallet):
    caller = make_caller(FakeService(paywall("0.01", ok)), wallet, per_call="0.30", session="0.50")
    results = []

    async def one():
        results.append(await caller.call(catalog["iban_check"], IBAN))

    async with anyio.create_task_group() as tg:
        for _ in range(3):
            tg.start_soon(one)
    # The first two reserve 0.30 + 0.20 (their caps); the third finds nothing left.
    assert sum(not r.is_error for r in results) == 2
    assert caller.budget.spent == usd_to_atomic("0.02")


async def test_recommend_sends_numbers_as_query_strings_and_pays_half_a_cent(catalog, wallet):
    service = FakeService(paywall("0.005", lambda r: httpx.Response(200, json={"picks": []})))
    caller = make_caller(service, wallet)
    outcome = await caller.call(catalog["x402_recommend"], {"need": "web search", "max_price": 0.05, "k": 3})
    assert outcome.payload["payment"]["paid_usd"] == "0.005"
    assert str(service.requests[-1].url) == "https://api.facts402.com/v1/recommend?need=web+search&max_price=0.05&k=3"
    assert caller.budget.spent == usd_to_atomic("0.005")


async def test_recommend_preview_is_free(catalog):
    service = FakeService(lambda r: httpx.Response(200, json={"top_pick": {"host": "example.com"}}))
    outcome = await make_caller(service, None).call(catalog["x402_recommend_preview"], {"need": "iban validation"})
    assert outcome.payload == {"top_pick": {"host": "example.com"}}
    assert str(service.requests[0].url) == "https://api.facts402.com/v1/recommend/preview?need=iban+validation"


async def test_paid_tool_without_key_shows_sub_cent_price(catalog):
    outcome = await make_caller(FakeService(never_called), None).call(catalog["x402_recommend"], {"need": "web search"})
    assert outcome.payload["price_usd"] == "0.005"


def test_integral_floats_go_out_as_integers(catalog):
    request = build_request(catalog["x402_recommend"], {"need": "web search", "k": 5.0, "max_price": 1.0})
    assert request.params == {"need": "web search", "k": 5, "max_price": 1}
