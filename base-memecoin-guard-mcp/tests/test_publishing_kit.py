from pathlib import Path

from base_memecoin_guard_mcp.server import INFO
from facts402_mcp.testing import publishing_kit_problems

from .conftest import load_script

ROOT = Path(__file__).resolve().parent.parent


def test_publishing_files_agree_with_the_code(catalog):
    expected_manifest = load_script("write_manifest").render(INFO.package)
    assert publishing_kit_problems(ROOT, INFO, catalog, expected_manifest) == []
