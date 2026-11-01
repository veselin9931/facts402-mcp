# Directory submissions: Glama, Smithery, mcp.so, PulseMCP

Prepared on 2026-11-02. Nothing has been submitted.

| | Value |
|---|---|
| Public repo | https://github.com/veselin9931/facts402-mcp (this `mcp/` folder is the repo root) |
| PyPI | `base-memecoin-guard-mcp`, `facts402-mcp` |
| Official MCP Registry | `com.facts402/base-memecoin-guard` and `com.facts402/facts402-mcp`, both 0.1.0 and `active` |

**Release 0.1.1 first.** Submit the directories after it, so they index the version that includes `x402_recommend`. See PUBLISHING.md: build, twine upload (facts402-mcp first), then `mcp-publisher publish` in each package folder. Push this folder to the public repo at the same time.

| Directory | Login the owner needs | Cost | Effort |
|---|---|---|---|
| PulseMCP | none | free | nothing to do |
| mcp.so | probably a mcp.so sign-in (GitHub or Google). Not confirmed: the form page shows a "Sign In" link but does not say it is required | free, or $39 to skip review | 2 minutes per server |
| Glama | GitHub account `veselin9931` | free | about 15 minutes |
| Smithery | Smithery account (GitHub sign-in) | free | about 30 minutes, needs Node.js |

## 1. PulseMCP: nothing to do

The submission form at https://www.pulsemcp.com/submit says it is "not accepting new MCP server or client submissions right now". It recommends publishing to the official MCP Registry instead, and says PulseMCP will pick servers up from there automatically once it is back. Both servers are already in the registry, so no action is needed.

Check about a week later: https://www.pulsemcp.com/servers?q=facts402

## 2. mcp.so: one form per server

The form at https://mcp.so/submit has three fields: Type, Name and Repository URL.

**base-memecoin-guard-mcp**

| Field | Value |
|---|---|
| Type | MCP Server |
| Name | Base Memecoin Guard |
| Repository URL | https://github.com/veselin9931/facts402-mcp/tree/main/base-memecoin-guard-mcp |

**facts402-mcp**

| Field | Value |
|---|---|
| Type | MCP Server |
| Name | facts402: x402 API finder + fact checks |
| Repository URL | https://github.com/veselin9931/facts402-mcp/tree/main/facts402-mcp |

Notes:
- If the form rejects a `/tree/...` URL, submit the plain repo URL once, as "facts402 MCP servers".
- The optional $39 "Pay and submit automatically" publishes without review and adds a verified badge, featured placement and a dofollow link. It is a payment, so it is the owner's decision. The free route is fine.

## 3. Glama: index, claim, then release

How Glama works:
- Glama lists GitHub repositories, one listing per repo.
- The maintainers in the repo-root `glama.json` can claim the listing.
- After claiming, a Docker build spec lets Glama start the server and detect its tools. Without one, the listing shows no tools and a lower score.

Already prepared in this folder:
- `glama.json` at the repo root, with maintainer `veselin9931`. Change it if the GitHub username is different.
- A `Dockerfile` in each package folder. Each installs the PyPI release and carries the `io.modelcontextprotocol.server.name` label.

**Unverified:** Glama's own docs did not load (404), so steps 3 and 4 come from Glama's blog and from public PRs that add `glama.json`.

Steps:
1. Push this folder, including the root `glama.json`, to `veselin9931/facts402-mcp`.
2. Open https://glama.ai/mcp/servers, sign in with GitHub as `veselin9931`, and use **Add Server** with the repo URL. If https://glama.ai/mcp/servers?query=facts402 already shows the repo, skip this step.
3. On the server page, choose **Claim ownership**. Glama checks that the signed-in user is listed in `glama.json`. After any later change to `glama.json`, run the claim again so Glama re-reads it.
4. On the server's admin page (Dockerfile / build settings):
   - Build from `base-memecoin-guard-mcp/Dockerfile`, the flagship. It answers `tools/list` and the free tools without a wallet.
   - Deploy, then make a release.
   - Check that the score shows the tools, the license (MIT) and "claimed".
5. A repo maps to one Glama listing, so `facts402-mcp` gets no listing of its own from the same repo. If it should have one, the options are a second public repo containing only `facts402-mcp/`, or accepting one combined listing.

The awesome-mcp-servers PR comes after this, because its bot labels PRs that lack a Glama badge. The github-lists session already opened PR #2091.

## 4. Smithery: MCPB bundles

Smithery distributes local stdio servers as MCPB bundles. Publishing by URL would need a remote HTTP endpoint, which is a server change and out of scope. Each package has an up-to-date `manifest.json`.

Steps:
1. Sign in at https://smithery.ai with GitHub. The first sign-in creates the account and its namespace (the username).
2. Build and check each bundle from its package folder:

   ```bash
   cd base-memecoin-guard-mcp
   npx -y @anthropic-ai/mcpb validate manifest.json
   npx -y @anthropic-ai/mcpb pack . base-memecoin-guard-mcp.mcpb
   ```

   Repeat in `facts402-mcp`.
3. Test once before publishing:
   - Open each `.mcpb` with Claude Desktop (Settings > Extensions, or drag the file in).
   - Leave the key empty.
   - Call `guard_preview` for the guard bundle, or `x402_recommend_preview` for facts402. This shows that the `uv` server type starts on a normal machine.
4. Publish:

   ```bash
   npx -y @smithery/cli auth login
   npx -y @smithery/cli mcp publish ./base-memecoin-guard-mcp.mcpb -n <namespace>/base-memecoin-guard
   npx -y @smithery/cli mcp publish ./facts402-mcp.mcpb -n <namespace>/facts402
   ```

5. Check the server pages on smithery.ai. They should show the tools (22 and 14, with their prices) and the key as an optional, masked field.

The bundles (`*.mcpb`) are git-ignored. Rebuild them for every release.
