"""base-memecoin-guard-mcp: Guard, Pulse, Signals and Watch tools for Base trading agents."""

from __future__ import annotations

from facts402_mcp.app import ServerInfo, run

from . import __version__
from .tools import catalog

INFO = ServerInfo(
    package="base-memecoin-guard-mcp",
    version=__version__,
    name="base-memecoin-guard",
    title="Base Memecoin Guard: honeypot, rug pull, exit liquidity, smart money",
    description="Base memecoin safety for trading agents: honeypot, rug pull, exit liquidity, smart money",
    instructions=(
        "Safety and alpha for agents trading Base memecoins, paid per call (x402, USDC on Base) from the user's "
        "own wallet within a per-call cap and session budget. Before buying: guard_check (honeypot, rug pull, "
        "tax, exit liquidity at your size, insiders, snipers, deployer) or the free guard_preview. Attention: "
        "pulse_token / pulse_trending (shill score, velocity). Smart money and copy trade: signals_*. After "
        "buying: watch_24h / watch_72h / watch_7d alert on liquidity pulls, dev dumps and exit traps; read alerts "
        "free with watch_events. Each tool states its price; tools marked FREE need no wallet. Results are "
        "automated facts and flags, not investment advice."
    ),
    keywords=("base", "memecoin", "honeypot", "rug-pull", "exit-liquidity", "insider", "sniper", "smart-money",
              "copy-trade", "whale", "trading", "crypto", "x402", "usdc"),
    website_url="https://guard.facts402.com",
    has_free_tools=True,
)


def main() -> None:
    run(INFO, catalog())
