# Installing base-memecoin-guard-mcp (for AI coding assistants such as Cline)

1. Make sure `uv` is installed (`uvx --version`). If not: https://docs.astral.sh/uv/getting-started/installation/
2. Add this server to the MCP settings file:

```json
{
  "mcpServers": {
    "base-memecoin-guard": {
      "command": "uvx",
      "args": ["base-memecoin-guard-mcp"],
      "env": {
        "X402_MAX_PER_CALL_USD": "0.30",
        "X402_SESSION_BUDGET_USD": "2.00"
      }
    }
  }
}
```

3. Payments are optional. Without `X402_PRIVATE_KEY`, the paid tools reply with their price and how to enable
   payments, and nothing is paid. To enable payments, ask the user for the private key of a **dedicated** Base
   mainnet hot wallet holding a little USDC. Add it as `"X402_PRIVATE_KEY"` in `env`. Never use or suggest
   the user's main wallet, and never print the key back.
4. Restart the MCP client and list the tools to check the server runs.
