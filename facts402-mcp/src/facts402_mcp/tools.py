"""The facts402 utility tools: general-purpose fact checks at api.facts402.com, $0.01 each."""

from __future__ import annotations

from functools import cache

from .catalog import FACTS, Catalog, Entry, build_catalog

ENTRIES: tuple[Entry, ...] = (
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


@cache
def catalog() -> Catalog:
    return build_catalog(__package__, ENTRIES)
