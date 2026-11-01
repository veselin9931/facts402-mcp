"""Regenerate each package's schemas.json from the live services.

For every catalog route: the input schema from the origin's /openapi.json (request body for POST, query
parameters for GET) and the price from its `x-payment-info`. api.facts402.com publishes no
`x-payment-info`, so its prices come from the GET / listing instead.

Schemas are made safe for MCP clients and LLM tool APIs: local $refs inlined, top-level oneOf/anyOf/allOf
removed (the Claude API rejects them; the constraint is kept as text in the description) and properties
pinned to a single `const` value dropped.

Usage:  python scripts/sync_schemas.py [package ...]     (free GETs only, never pays; default: all packages)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _packages import module_dir, selected, tools  # noqa: E402
from facts402_mcp.catalog import FACTS, SNAPSHOT_FILE, Entry, Route  # noqa: E402
COMBINATORS = ("oneOf", "anyOf", "allOf")
PRICE_TEXT = re.compile(r"\$(\d+(?:\.\d+)?)")


def _resolve(node: Any, components: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            return _resolve(components[ref.rsplit("/", 1)[1]], components)
        return {k: _resolve(v, components) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, components) for v in node]
    return node


def _combinator_note(name: str, branches: list[dict[str, Any]]) -> str:
    groups = [", ".join(b.get("required", [])) for b in branches]
    if name == "oneOf" and all(len(b.get("required", [])) == 1 for b in branches):
        return f"Provide exactly one of: {', '.join(groups)}."
    return f"Constraint ({name}): " + " | ".join(groups)


def make_tool_safe(schema: dict[str, Any]) -> dict[str, Any]:
    schema = dict(schema)
    notes = [_combinator_note(c, schema.pop(c)) for c in COMBINATORS if c in schema]
    props = {k: v for k, v in schema.get("properties", {}).items() if "const" not in v}
    schema["properties"] = props
    if "required" in schema:
        schema["required"] = [r for r in schema["required"] if r in props]
    schema.pop("title", None)
    if notes and "one of" not in schema.get("description", "").lower():
        schema["description"] = " ".join([schema.get("description", ""), *notes]).strip()
    schema["type"] = "object"
    return schema


def _query_schema(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for p in parameters:
        if p.get("in") != "query":
            continue
        prop = {k: v for k, v in p.get("schema", {}).items() if k != "title"}
        if p.get("description"):
            prop.setdefault("description", p["description"])
        props[p["name"]] = prop
    required = [p["name"] for p in parameters if p.get("in") == "query" and p.get("required")]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def input_schema(spec: dict[str, Any], route: Route) -> dict[str, Any]:
    op = spec["paths"][route.path][route.method.lower()]
    components = spec.get("components", {}).get("schemas", {})
    body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    raw = _resolve(body, components) if body else _query_schema(op.get("parameters", []))
    return make_tool_safe(raw)


def openapi_price(spec: dict[str, Any], route: Route) -> str | None:
    info = spec["paths"][route.path][route.method.lower()].get("x-payment-info")
    if not info:
        return None
    return str(Decimal(info["price"]["amount"]).normalize())


def facts_listing_prices(listing: dict[str, Any]) -> dict[str, str]:
    """`"POST /iban" -> "0.01"` from the api.facts402.com GET / listing."""
    services = [listing, *listing.get("other_services", {}).values()]
    prices = {}
    for s in services:
        match = PRICE_TEXT.search(s.get("price", ""))
        if match:
            prices[s["endpoint"]] = str(Decimal(match.group(1)).normalize())
    return prices


def snapshot(entries: list[Entry], http: httpx.Client) -> dict[str, Any]:
    specs = {o: http.get(f"{o}/openapi.json").raise_for_status().json() for o in {e.origin for e in entries}}
    facts_prices = facts_listing_prices(http.get(f"{FACTS}/").raise_for_status().json()) if FACTS in specs else {}
    routes = {}
    for e in entries:
        route = e.route
        price = openapi_price(specs[e.origin], route) if e.paid else None
        if e.paid and price is None and e.origin == FACTS:
            price = facts_prices.get(f"{e.method} {e.path}")
        if e.paid and price is None:
            raise SystemExit(f"no price found for paid route {route.key}")
        routes[route.key] = {"price_usd": price, "input_schema": input_schema(specs[e.origin], route)}
    return {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "routes": routes}


def main(argv: list[str]) -> None:
    with httpx.Client(timeout=60, follow_redirects=False) as http:
        for dist in selected(argv):
            entries = list(tools(dist).ENTRIES)  # hand-written schemas override these at load time
            out = module_dir(dist) / SNAPSHOT_FILE
            text = json.dumps(snapshot(entries, http), indent=1, sort_keys=True, ensure_ascii=False)
            out.write_text(text + "\n", encoding="utf-8")
            print(f"{dist}: wrote {len(entries)} routes to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
