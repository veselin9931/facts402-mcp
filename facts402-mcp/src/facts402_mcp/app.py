"""Shared MCP server plumbing (stdio): one tool per catalog entry, paid through the user's own wallet."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import anyio
from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)

from .budget import Budget, usd_to_atomic
from .caller import Caller, Outcome
from .catalog import Catalog, ToolSpec, thaw
from .config import ConfigError, Settings
from .wallet import Wallet


@dataclass(frozen=True)
class ServerInfo:
    """Identity of one published server package."""

    package: str  # PyPI name and console script
    version: str
    name: str  # MCP server name in the initialize handshake
    title: str
    description: str  # <= 100 chars: registry listings
    instructions: str  # sent to the client at initialize
    keywords: tuple[str, ...]
    website_url: str = "https://api.facts402.com"
    has_free_tools: bool = False  # without a key, are any tools usable? (drives the listings' key wording)

    @property
    def key_note(self) -> str:
        if self.has_free_tools:
            return "Optional: without it only the free tools work."
        return "Needed to call the tools: without it they only report their price."


def tool_definition(spec: ToolSpec) -> Tool:
    # Paid calls spend money, so they are never advertised as read-only or idempotent (no blind retries).
    return Tool(
        name=spec.name,
        title=spec.title,
        description=spec.description,
        input_schema=thaw(spec.input_schema),
        annotations=ToolAnnotations(
            title=spec.title,
            read_only_hint=not spec.paid and spec.route.method == "GET",
            destructive_hint=spec.route.method == "DELETE",
            idempotent_hint=not spec.paid and spec.route.method in ("GET", "DELETE"),
            open_world_hint=True,
        ),
    )


def to_result(outcome: Outcome) -> CallToolResult:
    payload = outcome.payload
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload if isinstance(payload, dict) else None,
        is_error=outcome.is_error,
    )


def build_server(info: ServerInfo, catalog: Catalog, caller: Caller) -> Server[Any]:
    tools = [tool_definition(spec) for spec in catalog.values()]

    async def list_tools(ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    async def call_tool(ctx: ServerRequestContext[Any], params: CallToolRequestParams) -> CallToolResult:
        spec = catalog.get(params.name)
        if spec is None:
            raise MCPError(INVALID_PARAMS, f"unknown tool {params.name!r}")
        return to_result(await caller.call(spec, params.arguments or {}))

    return Server(
        info.name,
        version=info.version,
        title=info.title,
        instructions=info.instructions,
        website_url=info.website_url,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


def caller_from_settings(settings: Settings, catalog: Catalog) -> Caller:
    budget = Budget(usd_to_atomic(settings.max_per_call_usd), usd_to_atomic(settings.session_budget_usd))
    free = tuple(name for name, spec in catalog.items() if not spec.paid)
    if settings.private_key is None:
        return Caller(budget, wallet=None, free_tools=free)
    try:
        return Caller(budget, wallet=Wallet.from_key(settings.private_key), free_tools=free)
    except ValueError as exc:
        return Caller(budget, wallet=None, wallet_problem=str(exc), free_tools=free)


def banner(info: ServerInfo, settings: Settings, caller: Caller) -> str:
    """Startup line for stderr: payer address and limits, never the key."""
    payer = f"payer {caller.wallet.address}" if caller.wallet else (caller.wallet_problem or "payments off (no X402_PRIVATE_KEY)")
    return (f"{info.package} {info.version}: {payer}; "
            f"cap ${settings.max_per_call_usd}/call, ${settings.session_budget_usd}/session")


async def _serve(server: Server[Any]) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run(info: ServerInfo, catalog: Catalog, env: Mapping[str, str] = os.environ) -> None:
    try:
        settings = Settings.from_env(env)
    except ConfigError as exc:
        sys.exit(f"{info.package}: {exc}")
    caller = caller_from_settings(settings, catalog)
    print(banner(info, settings, caller), file=sys.stderr)
    anyio.run(_serve, build_server(info, catalog, caller))
