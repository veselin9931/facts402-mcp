"""Regenerate each package's manifest.json (MCPB bundle: Smithery and one-click Claude Desktop installs).

Everything comes from the package's ServerInfo and catalog, so the manifest never drifts from the code.
Usage:  python scripts/write_manifest.py [package ...]      (default: all packages)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _packages import package_dir, selected, server, tools  # noqa: E402
from facts402_mcp.config import DEFAULT_MAX_PER_CALL, DEFAULT_SESSION_BUDGET  # noqa: E402

MANIFEST = "manifest.json"


def manifest(dist: str) -> dict[str, Any]:
    info = server(dist).INFO
    return {
        "manifest_version": "0.4",
        "name": info.package,
        "display_name": info.title,
        "version": info.version,
        "description": info.description,
        "long_description": info.instructions,
        "author": {"name": "facts402", "url": info.website_url},
        "homepage": info.website_url,
        "license": "MIT",
        "keywords": list(info.keywords),
        "server": {
            "type": "uv",
            "entry_point": f"src/{dist.replace('-', '_')}/__main__.py",
            "mcp_config": {
                "command": "uv",
                "args": ["run", "--directory", "${__dirname}", info.package],
                "env": {
                    "X402_PRIVATE_KEY": "${user_config.x402_private_key}",
                    "X402_MAX_PER_CALL_USD": "${user_config.max_per_call_usd}",
                    "X402_SESSION_BUDGET_USD": "${user_config.session_budget_usd}",
                },
            },
        },
        "user_config": {
            "x402_private_key": {
                "type": "string", "title": "Wallet private key", "sensitive": True, "required": not info.has_free_tools,
                "description": f"Private key of your own Base mainnet wallet holding a little USDC. {info.key_note}",
            },
            "max_per_call_usd": {
                "type": "string", "title": "Max USD per call", "required": False, "default": str(DEFAULT_MAX_PER_CALL),
                "description": "Most a single tool call may pay.",
            },
            "session_budget_usd": {
                "type": "string", "title": "Session budget USD", "required": False,
                "default": str(DEFAULT_SESSION_BUDGET), "description": "Most the server may spend until it restarts.",
            },
        },
        "tools": [{"name": s.name, "description": s.description} for s in tools(dist).catalog().values()],
        "compatibility": {"platforms": ["darwin", "win32", "linux"], "runtimes": {"python": ">=3.11"}},
    }


def render(dist: str) -> str:
    return json.dumps(manifest(dist), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    for dist in selected(sys.argv[1:]):
        (package_dir(dist) / MANIFEST).write_text(render(dist), encoding="utf-8")
        print(f"{dist}: wrote {MANIFEST}")
