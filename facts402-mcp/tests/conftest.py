from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from eth_account import Account

from facts402_mcp.tools import catalog as utility_catalog
from facts402_mcp.wallet import Wallet

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load_script(name: str) -> ModuleType:
    """A maintenance script from the shared mcp/scripts folder (repo checkouts only)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def catalog():
    return utility_catalog()


@pytest.fixture
def wallet() -> Wallet:
    return Wallet(Account.create())
