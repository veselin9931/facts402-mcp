"""Turns one tool call into one HTTP call: free routes directly, paid routes through x402 within budget."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients.httpx import PaymentError, x402AsyncTransport
from x402.http.utils import ResponseBodyTooLargeError

from . import __version__
from .budget import Budget, BudgetRefused, atomic_to_usd, usd_to_atomic
from .catalog import Style, ToolSpec, thaw, usd_text
from .config import ENV_MAX_PER_CALL, ENV_PRIVATE_KEY, ENV_SESSION_BUDGET
from .wallet import FACTS402_PAY_TO, Wallet

TIMEOUT_S = 60.0
USER_AGENT = f"facts402-mcp/{__version__}"
SUCCESS = range(200, 300)
CALL_FAILURES = (PaymentError, httpx.HTTPError, ResponseBodyTooLargeError)

TransportFactory = Callable[[], httpx.AsyncBaseTransport]


@dataclass(frozen=True)
class Outcome:
    """What a tool call returns: a JSON-able payload and whether it is an error."""

    payload: Any
    is_error: bool = False


@dataclass(frozen=True)
class _Request:
    method: str
    url: str
    params: dict[str, Any] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)


def _query_value(value: Any) -> Any:
    """JSON Schema counts 5.0 as an integer; send it as "5", which integer-only query patterns accept."""
    return int(value) if isinstance(value, float) and value.is_integer() else value


def build_request(spec: ToolSpec, args: Mapping[str, Any]) -> _Request:
    args = dict(args)
    if spec.style is Style.JSON_BODY:
        return _Request(spec.route.method, spec.route.url, body=args)
    if spec.style is Style.QUERY:
        return _Request(spec.route.method, spec.route.url, params={k: _query_value(v) for k, v in args.items()})
    watch_id, secret = args.pop("watch_id"), args.pop("watch_secret")
    url = spec.route.url.replace("{watch_id}", watch_id)
    params = {k: _query_value(v) for k, v in args.items()}
    return _Request(spec.route.method, url, params=params, headers={"Authorization": f"Bearer {secret}"})


_validators: dict[str, Draft202012Validator] = {}


def _validator(spec: ToolSpec) -> Draft202012Validator:
    if spec.route.key not in _validators:
        _validators[spec.route.key] = Draft202012Validator(thaw(spec.input_schema))
    return _validators[spec.route.key]


def argument_errors(spec: ToolSpec, args: Mapping[str, Any]) -> list[str]:
    errors = sorted(_validator(spec).iter_errors(dict(args)), key=str)
    return [f"{'/'.join(map(str, e.absolute_path)) or '(arguments)'}: {e.message}" for e in errors]


def _body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return response.text[:2000]


def _rejection_reason(response: httpx.Response) -> str | None:
    """Why a paid retry came back 402, from the PAYMENT-REQUIRED header (e.g. insufficient_funds)."""
    header = response.headers.get("payment-required")
    if not header:
        return None
    try:
        return decode_payment_required_header(header).error
    except Exception:  # a malformed header is reported as an unknown reason
        return None


def _settlement(response: httpx.Response) -> dict[str, Any]:
    """Transaction details for the receipt. Never used for accounting: the signed amount is what moves."""
    header = response.headers.get("payment-response") or response.headers.get("x-payment-response")
    if not header:
        return {}
    try:
        settle = decode_payment_response_header(header)
    except Exception:
        return {}
    return {"transaction": settle.transaction, "network": settle.network}


class Caller:
    def __init__(
        self,
        budget: Budget,
        wallet: Wallet | None,
        wallet_problem: str | None = None,
        free_tools: tuple[str, ...] = (),
        transport_factory: TransportFactory = httpx.AsyncHTTPTransport,
    ) -> None:
        self.budget = budget
        self.wallet = wallet
        self.wallet_problem = wallet_problem
        self.free_tools = free_tools
        self._transport_factory = transport_factory

    async def call(self, spec: ToolSpec, args: Mapping[str, Any]) -> Outcome:
        errors = argument_errors(spec, args)
        if errors:
            return Outcome({"error": "invalid arguments, nothing was sent or paid", "details": errors}, is_error=True)
        try:
            request = build_request(spec, args)
            return await (self._paid(spec, request) if spec.paid else self._free(request))
        except Exception as exc:  # last resort: a tool call reports, it never crashes the server
            return Outcome({"error": f"unexpected {type(exc).__name__} calling {spec.name}: {exc}"}, is_error=True)

    # --- free ---------------------------------------------------------------------------------------------
    async def _free(self, request: _Request) -> Outcome:
        try:
            async with self._http(self._transport_factory()) as http:
                response = await self._send(http, request)
        except CALL_FAILURES as exc:
            return Outcome({"error": f"network error calling {request.url}: {type(exc).__name__}: {exc}"}, is_error=True)
        if response.status_code in SUCCESS:
            return Outcome(_body(response))
        return Outcome({"error": f"HTTP {response.status_code}", "body": _body(response)}, is_error=True)

    # --- paid ---------------------------------------------------------------------------------------------
    async def _paid(self, spec: ToolSpec, request: _Request) -> Outcome:
        price = usd_to_atomic(spec.price_usd)
        if self.wallet is None:
            return Outcome(self._payments_off(spec), is_error=True)
        try:
            reservation = self.budget.reserve(price)
        except BudgetRefused as exc:
            return Outcome({"error": f"not called, nothing paid: {exc}", "price_usd": atomic_to_usd(price)}, is_error=True)

        signed: list[int] = []
        paid: int | None = None  # stays None if cancelled or interrupted: then assume the worst below
        try:
            client = self.wallet.x402_client(reservation.cap, signed.append)
            async with self._http(x402AsyncTransport(client, self._transport_factory())) as http:
                response = await self._send(http, request)
            paid = signed[-1] if signed and response.status_code in SUCCESS else 0  # services settle only on 2xx
            return self._paid_outcome(spec, response, paid)
        except Exception as exc:  # CALL_FAILURES and anything unexpected; cancellation still reaches `finally`
            # No answer. Unsigned: nothing paid (e.g. the live quote is above the cap or to another payee).
            # Signed: the payment may have settled before the failure, so it counts.
            paid = signed[-1] if signed else 0
            note = "a signed payment may have been charged" if signed else "payment not made, nothing was paid"
            error = {"error": f"{note}: {type(exc).__name__}: {exc}", "price_usd": atomic_to_usd(price)}
            if "filtered out by policies" in str(exc):
                error["hint"] = (f"the service asked for a payee other than {FACTS402_PAY_TO} or a Permit2 approval; "
                                 "this client pays facts402 only. Update the package if the receiving address changed.")
            return Outcome({**error, **self._session_totals(extra=paid)}, is_error=True)
        finally:
            self.budget.settle(reservation, paid if paid is not None else (signed[-1] if signed else 0))

    def _paid_outcome(self, spec: ToolSpec, response: httpx.Response, paid: int) -> Outcome:
        if response.status_code in SUCCESS:
            receipt = {"paid_usd": atomic_to_usd(paid), **_settlement(response), **self._session_totals(extra=paid)}
            return Outcome({"result": _body(response), "payment": receipt})
        error: dict[str, Any] = {"error": f"HTTP {response.status_code}, you were not charged", "body": _body(response)}
        if response.status_code == 402:
            reason = _rejection_reason(response) or "unknown"
            error["error"] = f"payment was not accepted ({reason}), you were not charged"
            if reason == "insufficient_funds":
                error["hint"] = f"fund {self.wallet.address} with at least ${usd_text(spec.price_usd)} USDC on Base mainnet"
        return Outcome({**error, **self._session_totals()}, is_error=True)

    # --- helpers ------------------------------------------------------------------------------------------
    def _session_totals(self, extra: int = 0) -> dict[str, str]:
        """Session totals; `extra` is a charge not yet recorded (the budget settles after the outcome is built)."""
        return {
            "session_spent_usd": atomic_to_usd(self.budget.spent + extra),
            "session_budget_usd": atomic_to_usd(self.budget.session_budget),
        }

    def _payments_off(self, spec: ToolSpec) -> dict[str, Any]:
        reason = self.wallet_problem or f"{ENV_PRIVATE_KEY} is not set"
        message = {
            "error": f"payments are off ({reason}); nothing was called or paid",
            "tool": spec.name,
            "price_usd": usd_text(spec.price_usd),
            "how_to_enable": (
                f"Set {ENV_PRIVATE_KEY} to the private key of a Base mainnet wallet you control that holds a little USDC "
                f"(no ETH needed: x402 'exact' payments are gasless EIP-3009 signatures). Optional limits: "
                f"{ENV_MAX_PER_CALL} (default 0.30) and {ENV_SESSION_BUDGET} (default 2.00). Use a dedicated hot "
                "wallet with a small balance."
            ),
        }
        if self.free_tools:
            message["free_tools"] = list(self.free_tools)
        return message

    @staticmethod
    def _http(transport: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT})

    @staticmethod
    async def _send(http: httpx.AsyncClient, request: _Request) -> httpx.Response:
        return await http.request(request.method, request.url, params=request.params or None,
                                  json=request.body, headers=request.headers)
