"""The facts402 utility tools: fact checks at api.facts402.com ($0.01 each) and the x402 API recommender."""

from __future__ import annotations

from functools import cache
from typing import Any

from .catalog import FACTS, Catalog, Entry, Style, build_catalog

ENTRIES: tuple[Entry, ...] = (
    Entry("x402_recommend", "Find the right paid x402 API", "GET", FACTS, "/v1/recommend",
          "Which paid API should I call for this task? Describe the need in plain words (e.g. 'web search', "
          "'honeypot check base token', 'IBAN validation') and get the top-k x402 endpoints across the ecosystem: "
          "url, method, price, payment network, 30-day on-chain buyers, live 402 probe, risk flags and score, "
          "ranked by relevance, real buyers, recency and liveness (x402-list.com catalog, CC BY 4.0, plus sellers' "
          "own 402 quotes). Use it before paying an unknown API. No match = 404, not charged.", style=Style.QUERY),
    Entry("x402_recommend_preview", "x402 API finder preview", "GET", FACTS, "/v1/recommend/preview",
          "Free teaser of x402_recommend: the single top pick (host, price, 30-day payers) for a need, without url, "
          "risk flags or ranking details.", paid=False, style=Style.QUERY),
    Entry("iban_check", "IBAN and BIC validation", "POST", FACTS, "/iban",
          "Validate an IBAN (structure, mod-97 and national BBAN checksum) and return country, bank code, "
          "account code, bank name, BIC/SWIFT and SEPA membership. Use before a payout, invoice or SEPA transfer."),
    Entry("eu_vat_check", "EU VAT number check (VIES)", "POST", FACTS, "/vat",
          "Validate an EU VAT number: offline format and check-digit test plus a live lookup in the European "
          "Commission VIES, returning registration status, company name and address. For B2B invoicing, reverse "
          "charge, KYB and onboarding."),
    Entry("sanctions_screen", "OFAC sanctions screening", "POST", FACTS, "/sanctions",
          "Fuzzy-screen a person, company, vessel or aircraft name against the US Treasury OFAC SDN sanctions "
          "list including aliases (refreshed every 6 h): matches with score, type, sanctions programs and "
          "remarks, plus the closest near-miss. AML / KYC / KYB compliance screening aid."),
    Entry("lei_lookup", "LEI company lookup (GLEIF)", "POST", FACTS, "/lei",
          "Look up a legal entity in the official GLEIF LEI index: by 20-character LEI get legal name, status, "
          "jurisdiction, addresses, registration dates and direct/ultimate parent; or search by company name "
          "for up to 5 candidates. For KYB, onboarding and finance agents."),
    Entry("phone_check", "Phone number validation", "POST", FACTS, "/phone",
          "Validate and normalise any phone number worldwide: valid/possible, E.164 and national formats, "
          "country, line type (mobile, fixed line, toll-free, VoIP), original carrier, location and time zones. "
          "For CRM, outreach, KYC and calling agents."),
    Entry("email_check", "Email address check", "POST", FACTS, "/email",
          "Check an email address before sending: RFC syntax and normalisation, live DNS and MX records, null MX, "
          "disposable/throwaway domain and role-account (info@, support@) flags. No SMTP probing. For lead-gen, "
          "signup and outreach agents."),
    Entry("fx_convert", "ECB currency conversion", "POST", FACTS, "/fx",
          "Convert an amount between ~30 currencies at official European Central Bank (ECB) reference exchange "
          "rates, latest or any day in the last 90 days, with the publication date used and exact decimal "
          "results. For pricing, invoicing, travel-budget and accounting agents."),
    Entry("domain_check", "Domain age and RDAP/WHOIS", "POST", FACTS, "/domain",
          "Registration facts for any domain via RDAP (the WHOIS successor): registered or not, creation and "
          "expiry dates, domain age in days, registrar, EPP status, nameservers and DNSSEC. For fraud, phishing "
          "link-safety, lead-qualification and KYB agents."),
    Entry("business_days", "Business days and public holidays", "POST", FACTS, "/business-days",
          "Count business days between two dates for a country (optionally a state/region) and list the public "
          "holidays and weekends in the range. For payment deadlines, SLAs, delivery dates and scheduling."),
    Entry("weather_forecast", "Weather forecast", "POST", FACTS, "/weather",
          "Weather forecast for any latitude/longitude: current conditions plus up to 7 local-day summaries "
          "(min/max temperature, precipitation, wind, weather symbol) in the place's own time zone. Data from "
          "MET Norway. For travel, events and logistics agents."),
    Entry("sun_times", "Sunrise and sunset times", "POST", FACTS, "/sun",
          "Sunrise, sunset, solar noon, civil dawn/dusk, golden hour and day length for any coordinates and "
          "date, in local time; polar day/night flagged. For travel, photography, events and outdoor planning."),
    Entry("base_token_check", "Base token contract facts", "POST", FACTS, "/check",
          "Raw on-chain facts for a Base mainnet ERC-20 token contract, read at one block: is it a contract, "
          "EIP-1967 proxy / implementation / admin, name, symbol, decimals, totalSupply, owner, and whether mint, "
          "pause or blacklist function selectors appear in the bytecode. Facts only, no rating."),
)


_NEED = {"type": "string", "minLength": 2, "maxLength": 200,
         "description": "what you want to do, in plain words, e.g. 'web search' or 'IBAN validation'"}

# The OpenAPI spec types max_price and k as pattern-checked strings; agents send numbers. httpx renders these
# numbers as the strings the route expects.
HAND_WRITTEN_SCHEMAS: dict[str, dict[str, Any]] = {
    "x402_recommend": {
        "type": "object",
        "properties": {
            "need": _NEED,
            "max_price": {"type": "number", "minimum": 0.001, "maximum": 100,
                          "description": "max price per call in USD (default 0.05)"},
            "k": {"type": "integer", "minimum": 1, "maximum": 10, "description": "number of picks (default 5)"},
            "network": {"type": "string", "pattern": "^([a-z0-9-]+:[A-Za-z0-9-]+|any)$",
                        "description": "CAIP-2 payment network (default eip155:8453 = Base) or 'any'"},
        },
        "required": ["need"],
        "additionalProperties": False,
    },
    "x402_recommend_preview": {
        "type": "object", "properties": {"need": _NEED}, "required": ["need"], "additionalProperties": False,
    },
}


@cache
def catalog() -> Catalog:
    return build_catalog(__package__, ENTRIES, HAND_WRITTEN_SCHEMAS)
