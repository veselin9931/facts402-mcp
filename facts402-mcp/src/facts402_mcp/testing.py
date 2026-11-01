"""Test helpers shared by the facts402 MCP server packages: a fake x402 service and publishing-kit checks."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import httpx
from x402.http import encode_payment_required_header, encode_payment_response_header
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo, SettleResponse

from .app import ServerInfo
from .budget import Budget, usd_to_atomic
from .caller import Caller
from .catalog import Catalog
from .wallet import BASE_MAINNET, FACTS402_PAY_TO, Wallet

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TOKEN = "0x4ed4e862860bed51a9570b96d89af5e1b0efefed"
TX = "0x" + "ab" * 32

Handler = Callable[[httpx.Request], httpx.Response]


def quote_header(url: str, price_usd: str, *, error: str | None = None, pay_to: str = FACTS402_PAY_TO,
                 asset: str = USDC_BASE, extra: dict | None = None) -> str:
    """A PAYMENT-REQUIRED header as our services send it (USDC on Base, scheme exact)."""
    return encode_payment_required_header(
        PaymentRequired(
            x402_version=2,
            error=error,
            resource=ResourceInfo(url=url),
            accepts=[
                PaymentRequirements(
                    scheme="exact",
                    network=BASE_MAINNET,
                    asset=asset,
                    amount=str(usd_to_atomic(price_usd)),
                    pay_to=pay_to,
                    max_timeout_seconds=300,
                    extra=extra or {"name": "USD Coin", "version": "2"},
                )
            ],
        )
    )


def settled_header(amount: str, payer: str) -> str:
    """A PAYMENT-RESPONSE header; `amount` is passed through as the server would send it."""
    return encode_payment_response_header(
        SettleResponse(success=True, transaction=TX, network=BASE_MAINNET, payer=payer, amount=amount)
    )


class FakeService:
    """Records requests and answers them with `handler`."""

    def __init__(self, handler: Handler) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def record(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

        return httpx.MockTransport(record)


def paywall(price_usd: str, paid: Handler, **quote: object) -> Handler:
    """402 quote without a payment signature, `paid(request)` with one."""

    def handle(request: httpx.Request) -> httpx.Response:
        if "payment-signature" not in request.headers:
            header = quote_header(str(request.url), price_usd, **quote)  # type: ignore[arg-type]
            return httpx.Response(402, headers={"PAYMENT-REQUIRED": header}, json={})
        return paid(request)

    return handle


def never_called(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request {request.method} {request.url}")


def make_caller(service: FakeService, wallet: Wallet | None, *, per_call: str = "0.30", session: str = "2.00",
                free_tools: tuple[str, ...] = ()) -> Caller:
    budget = Budget(usd_to_atomic(Decimal(per_call)), usd_to_atomic(Decimal(session)))
    return Caller(budget, wallet, free_tools=free_tools, transport_factory=service.transport)


# --- publishing kit ---------------------------------------------------------------------------------------------
def publishing_kit_problems(root: Path, info: ServerInfo, catalog: Catalog, expected_manifest: str) -> list[str]:
    """Everything that disagrees between a package's publishing files and its code (empty when consistent)."""
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    server = json.loads((root / "server.json").read_text(encoding="utf-8"))
    readme = (root / "README.md").read_text(encoding="utf-8")
    package = server["packages"][0]
    checks = {
        "pyproject name": pyproject["name"] == info.package == package["identifier"],
        "console script": info.package in pyproject["scripts"],
        "versions": pyproject["version"] == info.version == server["version"] == package["version"],
        "server.json description": server["description"] == info.description and len(info.description) <= 100,
        "README mcp-name marker": re.search(rf"mcp-name: {re.escape(server['name'])}\b", readme) is not None,
        "README lists every tool": all(f"`{name}`" in readme for name in catalog),
        "manifest.json up to date": (root / "manifest.json").read_text(encoding="utf-8") == expected_manifest,
        "Dockerfile label and version": (
            f'LABEL io.modelcontextprotocol.server.name="{server["name"]}"' in (root / "Dockerfile").read_text()
            and f"{info.package}=={info.version}" in (root / "Dockerfile").read_text()
        ),
        "smithery.yaml command": f"args: ['{info.package}']" in (root / "smithery.yaml").read_text(encoding="utf-8"),
        "env vars in server.json": {e["name"] for e in package["environmentVariables"]}
        == {"X402_PRIVATE_KEY", "X402_MAX_PER_CALL_USD", "X402_SESSION_BUDGET_USD"},
        "llms-install.md": info.package in (root / "llms-install.md").read_text(encoding="utf-8"),
        "key wording": info.has_free_tools == any(not s.paid for s in catalog.values())
        and package["environmentVariables"][0]["isRequired"] is not info.has_free_tools
        and info.key_note in package["environmentVariables"][0]["description"]
        and info.key_note.split(":")[0] in (root / "smithery.yaml").read_text(encoding="utf-8"),
    }
    return [name for name, ok in checks.items() if not ok]
