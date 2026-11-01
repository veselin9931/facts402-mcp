# Changelog

## 0.1.1 (unreleased)

- Watch prices re-checked against the live service (halved on 2026-11-01; 0.1.0 already shipped them):
  `watch_24h` $0.12, `watch_72h` $0.30, `watch_7d` $0.60, `watch_extend_24h` $0.12. Only `watch_7d` needs
  `X402_MAX_PER_CALL_USD` above the $0.30 default.
- Requires facts402-mcp 0.1.1 (shared core).

## 0.1.0 (2026-11-01)

- First release: 22 tools for Base trading agents.
  - Guard: honeypot, rug pull and exit-liquidity checks.
  - Pulse: social attention and shill score.
  - Signals: smart money and copy trade.
  - Watch: position alerts.
  - 7 of the tools are free.
- x402 payments from the user's own wallet with a per-call cap and a session budget.
