# facts402 MCP servers

Two MCP servers that give AI agents pay-per-call (x402, USDC on Base) access to facts402 APIs:

| Package | What | Install |
|---|---|---|
| [`base-memecoin-guard-mcp`](base-memecoin-guard-mcp) | Base memecoin safety and trading intel: honeypot / rug / insider and bundle forensics, exit liquidity at your size, social attention, smart-money signals, position watch | `uvx base-memecoin-guard-mcp` |
| [`facts402-mcp`](facts402-mcp) | Find the right paid x402 API for a task (`x402_recommend`, $0.005; free preview), plus 12 utility checks for agents: IBAN, EU VAT, phone, email, FX, LEI, OFAC sanctions, domain age, business days, weather, sun | `uvx facts402-mcp` |

Free preview tools work without a wallet. Paid tools need `X402_PRIVATE_KEY` (a wallet with USDC on Base) and enforce per-call and per-session spend caps. See each package's README.

APIs: https://api.facts402.com · https://guard.facts402.com · https://pulse.facts402.com · https://signals.facts402.com · https://watch.facts402.com

Automated on-chain facts and rules-based flags. Not investment advice.
