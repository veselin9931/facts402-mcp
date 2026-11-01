# Publishing the facts402 MCP servers

Two servers come from one codebase. Each is listed separately in every registry:

| Package (PyPI) | Registry name | Tools | Audience |
|---|---|---|---|
| `base-memecoin-guard-mcp` (flagship) | `com.facts402/base-memecoin-guard` | 22 (15 paid, 7 free): Guard, Pulse, Signals, Watch | Base trading agents |
| `facts402-mcp` | `com.facts402/facts402-mcp` | 12 paid utility checks at $0.01 | General agent builders |

`facts402-mcp` also contains the shared core (HTTP caller, x402 wallet, budget, server plumbing), and
`base-memecoin-guard-mcp` depends on it. So that is two PyPI uploads, and **`facts402-mcp` goes first**.

Nothing here has been run. Every step that creates an account, uploads a package or registers a name is for
the owner to do by hand. Checked on 2026-11-01:
- Both PyPI names are free.
- The MCP Registry has no `facts402` or `memecoin` server.
- `facts402.com` has no TXT record at its apex (and no A record, which is fine for DNS verification).

## 0. Decide before the first upload

| Decision | Default | Change it in |
|---|---|---|
| License | MIT | each package's `LICENSE` and `pyproject.toml`, and `scripts/write_manifest.py` |
| Flagship name | `base-memecoin-guard-mcp` / `com.facts402/base-memecoin-guard` | Package folder, `pyproject.toml`, `server.py` `INFO`, `server.json`, README marker, `Dockerfile`, `smithery.yaml`, `llms-install.md`, `scripts/_packages.py`. The kit test lists anything you missed. |
| Registry namespace | `com.facts402/*` (DNS) | `server.json` `name` and the `mcp-name:` comment at the top of the README, in both packages |
| Glama maintainer | `veselin9931` in `glama.json` | Use the owner's real GitHub username |
| Version | `0.1.0` | `pyproject.toml`, `__init__.py`, `server.json` (twice) and `Dockerfile`, then `python scripts/write_manifest.py` |

A PyPI version can be uploaded only once. Before uploading, from `A2A_MICROPAYMENTS_TRACK/mcp`:

```bash
.venv/bin/pytest facts402-mcp && .venv/bin/pytest base-memecoin-guard-mcp
.venv/bin/pytest -m live facts402-mcp && .venv/bin/pytest -m live base-memecoin-guard-mcp
```

The kit tests fail if `server.json`, `manifest.json`, the README marker, the `Dockerfile` or `smithery.yaml`
disagree with the code.

### Which registry namespace?

| Namespace | Proves ownership with | Needs |
|---|---|---|
| `com.facts402/*` (recommended: matches the brand and the API hosts) | A DNS TXT record at the apex of `facts402.com` | DNS access for facts402.com and an Ed25519 key pair. No GitHub account. (The HTTP alternative, `https://facts402.com/.well-known/mcp-registry-auth`, would need a server change.) |
| `io.github.<github-user>/*` | `mcp-publisher login github` (browser device flow) | A GitHub account. Organisation namespaces need the Owner role and a PAT; the interactive login cannot publish to them. |

The registry also checks that each PyPI package belongs to you. It looks for `mcp-name: <server name>` in the
PyPI description, which is the README.

## 1. Accounts the owner must create

1. **PyPI** (required): register at https://pypi.org/account/register/ and turn on 2FA. Then create an API
   token under Account settings > API tokens. The first token must be account-wide, because the projects do not
   exist yet. After the first uploads, replace it with tokens scoped to each project.
2. **GitHub** (recommended; required for the `io.github.*` namespace, Glama, awesome-mcp-servers and the Cline
   marketplace): create one public repository holding this `mcp/` folder, for example `facts402-mcp`. Then add
   `"repository": {"url": "https://github.com/<user>/facts402-mcp", "source": "github", "subfolder": "<package folder>"}`
   to each `server.json`, and `Repository = "..."` under `[project.urls]` in each `pyproject.toml`.
3. **Smithery** (optional): sign in at https://smithery.ai with GitHub and create an API key.

No wallet, payment or USDC is needed for any of this.

## 2. PyPI (facts402-mcp first)

From `A2A_MICROPAYMENTS_TRACK/mcp`:

```bash
python -m pip install --upgrade build twine
python -m build facts402-mcp --outdir dist/facts402-mcp
python -m twine check dist/facts402-mcp/*
python -m twine upload dist/facts402-mcp/*
python -m build base-memecoin-guard-mcp --outdir dist/base-memecoin-guard-mcp
python -m twine check dist/base-memecoin-guard-mcp/*
python -m twine upload dist/base-memecoin-guard-mcp/*
```

Twine asks for a username and a password. Enter `__token__` as the username and the API token as the password.

Check each package from a clean shell:

```bash
uvx base-memecoin-guard-mcp
uvx facts402-mcp
```

Each should print `<package> 0.1.0: payments off (no X402_PRIVATE_KEY); ...` on stderr and then wait for MCP
input (stop it with Ctrl+C). Then add it to Claude Desktop or Claude Code with the README snippet and call
`guard_preview`, which is free.

## 3. Official MCP Registry (registry.modelcontextprotocol.io)

Wait until the PyPI uploads are live: the registry reads the README marker from PyPI.

1. Install `mcp-publisher`. On Windows, download `mcp-publisher_windows_amd64.tar.gz` from
   https://github.com/modelcontextprotocol/registry/releases/latest, unpack it and put `mcp-publisher.exe` on
   PATH. On macOS, run `brew install mcp-publisher`.
2. Log in once for the namespace.

   **`com.facts402` via DNS** (needs OpenSSL 3 or newer):

   ```bash
   openssl genpkey -algorithm Ed25519 -out mcp-registry-key.pem
   echo "v=MCPv1; k=ed25519; p=$(openssl pkey -in mcp-registry-key.pem -pubout -outform DER | tail -c 32 | base64)"
   ```

   Add the printed line as a TXT record on the apex `facts402.com`, not on a subdomain. Wait until it shows in
   `nslookup -type=TXT facts402.com`, then log in:

   ```bash
   mcp-publisher login dns --domain facts402.com --private-key "$(openssl pkey -in mcp-registry-key.pem -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')"
   ```

   Keep `mcp-registry-key.pem` private and outside the repository: every later login needs it.

   **`io.github.<user>` via GitHub:** first change the names (section 0), release a new version to PyPI, then
   run `mcp-publisher login github`.

3. Publish each package from its own folder (`mcp-publisher` reads `./server.json`):

   ```bash
   cd base-memecoin-guard-mcp && mcp-publisher publish && cd ..
   cd facts402-mcp && mcp-publisher publish && cd ..
   curl "https://registry.modelcontextprotocol.io/v0/servers?search=facts402"
   ```

PulseMCP and the other registries that mirror the official one pick the servers up from there.

## 4. Smithery

Smithery now distributes local stdio servers as MCPB bundles. Each package's `manifest.json` is its bundle
manifest; regenerate it with `python scripts/write_manifest.py`. `smithery.yaml` keeps the classic
`startCommand` format for tools that still read it. Publishing to Smithery by URL needs a remote HTTP endpoint,
which is out of scope here because it would be a server change.

For each package folder:

```bash
npx @anthropic-ai/mcpb validate manifest.json
npx @anthropic-ai/mcpb pack . <package>.mcpb
```

Before publishing, check that the bundle installs. Double-click the `.mcpb`, or drag it into Claude Desktop >
Settings > Extensions, then call `guard_preview`. This confirms the `uv` server type starts. The utility server
has no free tool, so for it check that `iban_check` answers with its price. Then publish:

```bash
npx @smithery/cli auth login
npx @smithery/cli mcp publish ./<package>.mcpb -n <smithery-namespace>/<package>
```

The same `.mcpb` files can be offered as one-click Claude Desktop installs.

## 5. Glama, awesome-mcp-servers, Cline (need the public GitHub repo)

- **Glama:** each package folder has `glama.json` (maintainers) and a `Dockerfile` that installs the PyPI
  release and carries `LABEL io.modelcontextprotocol.server.name`. Add the repository on glama.ai, claim it,
  and point the Docker build at the package folder.
- **awesome-mcp-servers:** open the PR after the Glama listing exists, because their bot checks for the Glama
  badge.
- **Cline marketplace:** `llms-install.md` is in each package. Cline also needs a 400×400 PNG logo, which still
  has to be made.

## 6. Each later release

1. Bump the versions (section 0).
2. If a route changed, run `python scripts/sync_schemas.py`.
3. Run `python scripts/write_manifest.py`.
4. When the core's minor version changes (`facts402-mcp` 0.2), widen the guard's `facts402-mcp>=0.1.0,<0.2`
   dependency in `base-memecoin-guard-mcp/pyproject.toml` and release both.
5. If the services' receiving address ever changes, update `FACTS402_PAY_TO` in `facts402_mcp/wallet.py` and
   release first: installed clients pay that address only and will refuse quotes for any other.
6. Run both test suites, then repeat sections 2 to 4.

If a price changes on a server, re-run `scripts/sync_schemas.py` and release. Tool descriptions show the bundled
prices, but each payment is still capped by the user's own limits.
