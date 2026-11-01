"""The server packages in this folder, for the maintenance scripts. Imports straight from each src/."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

MCP_DIR = Path(__file__).resolve().parent.parent
PACKAGES = {"facts402-mcp": "facts402_mcp", "base-memecoin-guard-mcp": "base_memecoin_guard_mcp"}

for _dist in PACKAGES:
    sys.path.insert(0, str(MCP_DIR / _dist / "src"))


def package_dir(dist: str) -> Path:
    return MCP_DIR / dist


def module_dir(dist: str) -> Path:
    return package_dir(dist) / "src" / PACKAGES[dist]


def tools(dist: str) -> ModuleType:
    return importlib.import_module(f"{PACKAGES[dist]}.tools")


def server(dist: str) -> ModuleType:
    return importlib.import_module(f"{PACKAGES[dist]}.server")


def selected(argv: list[str]) -> list[str]:
    """Packages named on the command line, or all of them."""
    unknown = [a for a in argv if a not in PACKAGES]
    if unknown:
        raise SystemExit(f"unknown package(s) {unknown}; choose from {list(PACKAGES)}")
    return argv or list(PACKAGES)
