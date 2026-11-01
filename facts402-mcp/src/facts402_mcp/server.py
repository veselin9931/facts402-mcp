"""facts402-mcp: the general-purpose fact-check tools (IBAN, VAT, sanctions, FX, ...)."""

from __future__ import annotations

from . import __version__
from .app import ServerInfo, run
from .tools import catalog

INFO = ServerInfo(
    package="facts402-mcp",
    version=__version__,
    name="facts402",
    title="facts402: x402 API finder and fact checks (IBAN, VAT, sanctions, FX)",
    description="Find the right paid x402 API, plus fact checks: IBAN, EU VAT, OFAC sanctions, LEI, FX",
    instructions=(
        "Need a paid API for a task? x402_recommend ($0.005, or the free x402_recommend_preview) ranks x402 "
        "endpoints across the ecosystem by relevance, real on-chain buyers and liveness. "
        "Verified fact checks at $0.01 per call (x402, USDC on Base), paid from the user's own wallet within a "
        "per-call cap and session budget: IBAN/BIC validation, EU VAT (VIES), OFAC sanctions screening, GLEIF LEI "
        "company lookup, phone and email validation, ECB FX conversion, domain age (RDAP/WHOIS), business days "
        "and holidays, weather, sunrise/sunset and Base token contract facts. Each tool states its price."
    ),
    keywords=("x402", "api-discovery", "api-finder", "iban", "bic", "vat", "vies", "sanctions", "ofac", "aml", "kyc",
              "kyb", "lei", "fx", "phone", "email", "whois", "usdc"),
    has_free_tools=True,
)


def main() -> None:
    run(INFO, catalog())
