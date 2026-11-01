"""facts402-mcp: the general-purpose fact-check tools (IBAN, VAT, sanctions, FX, ...)."""

from __future__ import annotations

from . import __version__
from .app import ServerInfo, run
from .tools import catalog

INFO = ServerInfo(
    package="facts402-mcp",
    version=__version__,
    name="facts402",
    title="facts402: fact checks for agents (IBAN, VAT, sanctions, FX)",
    description="Pay-per-call fact checks for agents: IBAN, EU VAT, OFAC sanctions, LEI, phone, email, FX",
    instructions=(
        "Verified fact checks at $0.01 per call (x402, USDC on Base), paid from the user's own wallet within a "
        "per-call cap and session budget: IBAN/BIC validation, EU VAT (VIES), OFAC sanctions screening, GLEIF LEI "
        "company lookup, phone and email validation, ECB FX conversion, domain age (RDAP/WHOIS), business days "
        "and holidays, weather, sunrise/sunset and Base token contract facts. Each tool states its price."
    ),
    keywords=("iban", "bic", "vat", "vies", "sanctions", "ofac", "aml", "kyc", "kyb", "lei", "fx",
              "phone", "email", "whois", "x402", "usdc"),
)


def main() -> None:
    run(INFO, catalog())
