# facts402-mcp

<!-- mcp-name: com.facts402/facts402-mcp -->

**Find the right paid API for a task, and verified fact checks for AI agents.** Before an agent pays an
unknown API, `x402_recommend` ranks the x402 endpoints that fit the task by relevance, real on-chain buyers and
liveness, for $0.005 (the preview is free). And at $0.01 per call: validate an IBAN before a payout. Check an EU VAT number
in VIES before invoicing. Screen a name against OFAC sanctions. Look up a company's LEI. Validate a phone number
or email before outreach. Convert currency at official ECB rates. Check how old a domain is. These are small,
exact answers an agent can rely on, with no API keys or sign-up.

Pay per call with [x402](https://x402.org): USDC on Base, from **your own wallet**, within a per-call cap and a
session budget you set.

## Tools

| Tool | Price (USDC) | Use it to |
|---|---|---|
| `x402_recommend` | $0.005 | Find the best paid x402 endpoints for a task: url, price, network, 30-day buyers, liveness, risk flags, score |
| `x402_recommend_preview` | free | See the single top pick (host, price, buyers) for a task |
| `iban_check` | $0.01 | Validate an IBAN and get bank name, BIC and SEPA membership |
| `eu_vat_check` | $0.01 | Check an EU VAT number in VIES: status, company name and address |
| `sanctions_screen` | $0.01 | Fuzzy-screen a person, company, vessel or aircraft against the OFAC SDN list |
| `lei_lookup` | $0.01 | Look up a company in the GLEIF LEI index, by LEI or by name |
| `phone_check` | $0.01 | Validate and normalise a phone number: E.164, line type, carrier, time zone |
| `email_check` | $0.01 | Check email syntax, MX, disposable and role-account flags |
| `fx_convert` | $0.01 | Convert currency at ECB reference rates, for the latest day or any of the last 90 |
| `domain_check` | $0.01 | Get a domain's age, registrar, status and DNSSEC via RDAP (WHOIS) |
| `business_days` | $0.01 | Count business days and list public holidays between two dates |
| `weather_forecast` | $0.01 | Get a forecast for any coordinates, up to 7 days |
| `sun_times` | $0.01 | Get sunrise, sunset, golden hour and day length |
| `base_token_check` | $0.01 | Get raw on-chain facts for a Base ERC-20 contract (owner, proxy, mint / pause / blacklist) |

The service charges only for a successful (2xx) answer: invalid input, upstream errors and a recommend query
with no match (404) are never charged. Recommendations use the [x402-list.com](https://x402-list.com) catalog
(CC BY 4.0) and sellers' own 402 quotes, filtered and re-scored by facts402; facts402's own APIs are ranked with
the same formula.
For Base memecoin trading safety (honeypot, rug pull, exit liquidity, smart money), see
[base-memecoin-guard-mcp](https://pypi.org/project/base-memecoin-guard-mcp/).

## Payments and limits

| Variable | Default | Meaning |
|---|---|---|
| `X402_PRIVATE_KEY` | (unset) | Private key of a Base mainnet wallet you control that holds some USDC. Without it, `x402_recommend_preview` works and the paid tools return their price and setup steps, paying nothing. |
| `X402_MAX_PER_CALL_USD` | `0.30` | The most one call may pay. |
| `X402_SESSION_BUDGET_USD` | `2.00` | The most the server may spend until it restarts. |

- Use a **dedicated hot wallet** with a small balance. One dollar of USDC buys 100 checks or 200 recommendations.
- No ETH is needed: x402 `exact` payments are gasless EIP-3009 USDC authorisations.
- The key stays on your machine. It is never logged or returned, and it signs only the one request you made.
- Payments go **only** to the facts402 receiving address
  (`0x5498b0Aa90cd56F8962CBd136DF3D3769C85f149`). A quote for any other payee, any other token or a Permit2
  approval is refused.
- Every paid answer comes with a receipt: amount, transaction hash and session totals.

## Install

The server runs with [uv](https://docs.astral.sh/uv/) (`uvx facts402-mcp`).

### Claude Desktop

Add this to `claude_desktop_config.json` (Settings > Developer > Edit Config):

```json
{
  "mcpServers": {
    "facts402": {
      "command": "uvx",
      "args": ["facts402-mcp"],
      "env": {
        "X402_PRIVATE_KEY": "0xYOUR_HOT_WALLET_KEY",
        "X402_MAX_PER_CALL_USD": "0.30",
        "X402_SESSION_BUDGET_USD": "2.00"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add facts402 --scope user -e X402_PRIVATE_KEY=0xYOUR_HOT_WALLET_KEY -- uvx facts402-mcp
```

### Cursor

Use `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project; keep the key out of version control):

```json
{
  "mcpServers": {
    "facts402": {
      "command": "uvx",
      "args": ["facts402-mcp"],
      "env": { "X402_PRIVATE_KEY": "0xYOUR_HOT_WALLET_KEY" }
    }
  }
}
```

### Windsurf

Use `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "facts402": {
      "command": "uvx",
      "args": ["facts402-mcp"],
      "env": { "X402_PRIVATE_KEY": "0xYOUR_HOT_WALLET_KEY" }
    }
  }
}
```

## Example prompts

- "Which paid API should I use for web search? Show me the cheapest live one with real buyers."
- "Validate IBAN DE89 3704 0044 0532 0130 00 and tell me the bank."
- "Is IE6388047V a valid VAT number? What company is it?"
- "Screen 'Banco Nacional de Cuba' against OFAC sanctions."
- "How many business days are there in Germany between 21 Dec 2026 and 8 Jan 2027?"

## Development (both servers)

This folder also holds the shared core used by `base-memecoin-guard-mcp`: the HTTP caller, the x402 wallet, the
budget and the server plumbing. From `A2A_MICROPAYMENTS_TRACK/mcp`:

```bash
python -m venv .venv
.venv/bin/pip install -e "./facts402-mcp[test]" -e "./base-memecoin-guard-mcp[test]"
.venv/bin/pytest facts402-mcp && .venv/bin/pytest base-memecoin-guard-mcp     # unit tests, mocked HTTP
.venv/bin/pytest -m live facts402-mcp && .venv/bin/pytest -m live base-memecoin-guard-mcp   # live, never pays
.venv/bin/python scripts/sync_schemas.py     # refresh input schemas and prices from the live /openapi.json
.venv/bin/python scripts/write_manifest.py   # refresh each manifest.json (MCPB) from the code
```
