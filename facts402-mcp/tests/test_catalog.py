from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from facts402_mcp.catalog import FACTS, Entry, build_catalog, thaw, usd_text
from facts402_mcp.tools import ENTRIES

UTILITY_TOOLS = {"iban_check", "eu_vat_check", "sanctions_screen", "lei_lookup", "phone_check", "email_check",
                 "fx_convert", "domain_check", "business_days", "weather_forecast", "sun_times", "base_token_check"}


def test_twelve_paid_utility_tools_at_one_cent(catalog):
    assert set(catalog) == UTILITY_TOOLS | {"x402_recommend", "x402_recommend_preview"}
    for name in UTILITY_TOOLS:
        spec = catalog[name]
        assert spec.paid and spec.price_usd == Decimal("0.01"), name
        assert spec.route.origin == FACTS
        assert "Price: $0.01 USDC per call" in spec.description


def test_recommender_costs_half_a_cent_and_has_a_free_preview(catalog):
    assert catalog["x402_recommend"].price_usd == Decimal("0.005")
    assert "Price: $0.005 USDC per call" in catalog["x402_recommend"].description
    assert not catalog["x402_recommend_preview"].paid
    assert "FREE" in catalog["x402_recommend_preview"].description


def test_recommender_takes_numbers_not_the_specs_pattern_strings(catalog):
    props = catalog["x402_recommend"].input_schema["properties"]
    assert (props["max_price"]["type"], props["k"]["type"]) == ("number", "integer")


@pytest.mark.parametrize(("price", "text"), [("0.01", "0.01"), ("0.6", "0.60"), ("0.005", "0.005"), ("1", "1.00")])
def test_usd_text(price, text):
    assert usd_text(Decimal(price)) == text


def test_schemas_are_valid_objects_without_top_level_combinators(catalog):
    for spec in catalog.values():
        schema = thaw(spec.input_schema)
        Draft202012Validator.check_schema(schema)
        assert schema["type"] == "object", spec.name
        assert not {"oneOf", "anyOf", "allOf"} & schema.keys(), spec.name


def test_descriptions_carry_the_search_terms_agents_use(catalog):
    text = " ".join(s.description for s in catalog.values()).lower()
    for term in ("iban", "bic", "vat", "vies", "sanctions", "ofac", "aml", "kyc", "kyb", "lei", "exchange rate",
                 "phone", "email", "whois", "holidays", "weather", "which paid api", "x402"):
        assert term in text, term


def test_catalog_is_immutable(catalog):
    with pytest.raises(TypeError):
        catalog["iban_check"].input_schema["properties"]["iban"] = {}  # type: ignore[index]


def test_build_catalog_rejects_routes_missing_from_the_snapshot():
    ghost = Entry("ghost", "Ghost", "POST", FACTS, "/does-not-exist", "nothing")
    with pytest.raises(KeyError, match="sync_schemas"):
        build_catalog("facts402_mcp", (*ENTRIES, ghost))


def test_build_catalog_rejects_duplicate_names():
    with pytest.raises(ValueError, match="duplicate"):
        build_catalog("facts402_mcp", (ENTRIES[0], ENTRIES[0]))
