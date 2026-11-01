"""Tool catalog building blocks, shared by every facts402 MCP server.

A server package lists its routes as `Entry` objects (route + hand-written description). Input schemas and
prices come from that package's `schemas.json`, a snapshot of each origin's live /openapi.json written by
`scripts/sync_schemas.py`. A hand-written schema replaces the snapshot's where the OpenAPI one is missing or
unfriendly to agents; the price still comes from the snapshot.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from importlib import resources
from types import MappingProxyType
from typing import Any

FACTS = "https://api.facts402.com"
GUARD = "https://guard.facts402.com"
PULSE = "https://pulse.facts402.com"
SIGNALS = "https://signals.facts402.com"
WATCH = "https://watch.facts402.com"

SNAPSHOT_FILE = "schemas.json"


class Style(Enum):
    """How a tool's arguments travel to its route."""

    JSON_BODY = "json"  # POST, arguments are the JSON body
    QUERY = "query"  # GET, arguments are query parameters
    WATCH_BEARER = "watch"  # watch_id in the path, watch_secret as bearer, the rest as query


@dataclass(frozen=True)
class Route:
    method: str
    origin: str
    path: str

    @property
    def key(self) -> str:
        return f"{self.method} {self.origin}{self.path}"

    @property
    def url(self) -> str:
        return f"{self.origin}{self.path}"


@dataclass(frozen=True)
class Entry:
    """One route as a package declares it."""

    name: str
    title: str
    method: str
    origin: str
    path: str
    summary: str
    paid: bool = True
    style: Style = Style.JSON_BODY

    @property
    def route(self) -> Route:
        return Route(self.method, self.origin, self.path)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    route: Route
    summary: str
    paid: bool
    style: Style
    price_usd: Decimal | None
    input_schema: Mapping[str, Any]

    @property
    def description(self) -> str:
        if not self.paid:
            return f"{self.summary} FREE: no wallet or payment needed."
        return (
            f"{self.summary} Price: ${usd_text(self.price_usd)} USDC per call via x402 on Base, paid from your own wallet "
            "(X402_PRIVATE_KEY) within your per-call cap and session budget; charged only for a successful answer."
        )


Catalog = Mapping[str, ToolSpec]


def usd_text(price: Decimal) -> str:
    """`0.05 -> "0.05"`, `0.6 -> "0.60"`, `0.005 -> "0.005"`: cents, or more digits when a price needs them."""
    cents = price.quantize(Decimal("0.01"))
    return str(cents) if cents == price else f"{price.normalize():f}"


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def thaw(value: Any) -> Any:
    """Plain dict/list copy of a frozen schema (for the MCP wire models and jsonschema)."""
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def load_snapshot(package: str) -> Mapping[str, Any]:
    text = resources.files(package).joinpath(SNAPSHOT_FILE).read_text(encoding="utf-8")
    return json.loads(text)["routes"]


def _spec(entry: Entry, snapshot: Mapping[str, Any], hand_written: Mapping[str, Any]) -> ToolSpec:
    route = entry.route
    if route.key not in snapshot:
        raise KeyError(f"{route.key} missing from {SNAPSHOT_FILE}; run scripts/sync_schemas.py")
    schema = hand_written.get(entry.name, snapshot[route.key]["input_schema"])
    price = snapshot[route.key]["price_usd"]
    if entry.paid and price is None:
        raise ValueError(f"paid tool {entry.name} has no price in {SNAPSHOT_FILE}")
    return ToolSpec(
        name=entry.name,
        title=entry.title,
        route=route,
        summary=entry.summary,
        paid=entry.paid,
        style=entry.style,
        price_usd=Decimal(price) if entry.paid else None,
        input_schema=_freeze(schema),
    )


def build_catalog(package: str, entries: tuple[Entry, ...], hand_written: Mapping[str, Any] | None = None) -> Catalog:
    """Immutable catalog for `package` (whose `schemas.json` holds the snapshot)."""
    hand_written = hand_written or {}
    if len({e.name for e in entries}) != len(entries):
        raise ValueError("duplicate tool names")
    snapshot = load_snapshot(package)
    return MappingProxyType({e.name: _spec(e, snapshot, hand_written) for e in entries})
