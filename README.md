# grokhack-forge

The composer intended for a **grokhack.com /forge** page (not live yet; run it from the CLI or the workflow below): describe an app idea, get a working Grok app repo under
[github.com/Blockchains](https://github.com/Blockchains) with CI and a GitHub Pages deploy link.

```
idea ──► capabilities (deterministic rules) ──► archetype (chat | digest)
     ──► parts from Blockchains/grokhack-index (SDK package @ indexed fork commit, default model, reference snippets)
     ──► templates/<archetype> + generated glue (config, PARTS.md, forge.json, README, LICENSE)
     ──► gitleaks ──► gh repo create Blockchains/<name> ──► push ──► Pages (Actions) ──► wait for CI + Pages ──► URL
```

| Archetype | When | Grok integration | Deploy |
|---|---|---|---|
| `chat` | default | Vercel AI SDK `ai` + `@ai-sdk/xai` (version taken from the indexed `Blockchains/ai` fork commit), streaming, local tools (calculator, time, live GitHub lookup), xAI web search tool | Static Vite app on GitHub Pages; visitors bring their own xAI key (sent only to api.x.ai, which allows browser CORS) |
| `digest` | idea mentions daily/weekly/digest/monitor/track/release... | official `xai-sdk` installed from `Blockchains/xai-sdk-python` at the indexed commit, structured output (`chat.parse` + pydantic) | GitHub Actions cron builds a static report and deploys Pages; without `XAI_API_KEY` it publishes the real data plus a "needs key" notice |

Every generated repo runs a real end-to-end request against api.x.ai in CI: with the `XAI_API_KEY` secret it checks a live answer;
without it, it checks that api.x.ai rejects the unauthenticated request (proves the request path; prints `needs key`). No mocks.

## Use

```bash
python3 forge/compose.py --idea "A chat assistant that looks up GitHub repos with tools" --name my-grok-chat            # generate into /tmp/forge-out/my-grok-chat
python3 forge/compose.py --idea "..." --name my-app --create --wait                                                       # + create Blockchains/my-app, push, Pages, wait for CI
```
or run the **compose app** workflow (`.github/workflows/compose.yml`, inputs `idea`, `name`, `request_id`). grokhack.com dispatches it through the
Blockchains GitHub App and reads `results/<request_id>.json`. Repo creation in the Blockchains user account needs the `FORGE_TOKEN`
secret (fine-grained PAT owned by Blockchains); the workflow fails fast with a clear message until it exists.

## Proof apps composed with this tool
- [Blockchains/grok-release-radar](https://github.com/Blockchains/grok-release-radar) · https://blockchains.github.io/grok-release-radar/
- [Blockchains/grok-tools-chat](https://github.com/Blockchains/grok-tools-chat) · https://blockchains.github.io/grok-tools-chat/

## Layout
`forge/compose.py` (stdlib only) · `templates/chat`, `templates/digest` · `tests/` (run against the real published index) · `results/` (compose run outputs).
CI composes one app of each archetype, builds and tests them (including the api.x.ai e2e) and runs gitleaks.

MIT licence.

<!-- blocks:start -->
## Use as a building block

> **For AI agents and builders:** read [`AGENTS.md`](AGENTS.md) (setup, commands, structure, rules), [`llms.txt`](llms.txt) (doc map) and the machine-readable [`blocks.json`](blocks.json) ([schema](https://github.com/Blockchains/.github/blob/main/docs/BLOCKS-SCHEMA.md)). How all Blockchains blocks fit together: **[Build with Blocks](https://github.com/Blockchains/.github/blob/main/docs/BUILD-WITH-BLOCKS.md)** · org catalogue: [https://blockchains.github.io/blocks.json](https://blockchains.github.io/blocks.json).

**What it exports**

| Export | Type | Install / access |
|---|---|---|
| `forge/compose.py` | cli | `python3 forge/compose.py --idea "<idea>" --name <app> [--out DIR] [--index DIR|URL] [--create --wait]` |
| `compose app` | github-action | `workflow_dispatch inputs: idea, name, request_id → results/<request_id>.json` |
| `templates/chat, templates/digest` | file | `app templates the composer fills in` |

**Minimal example** (composed, built and tested locally on 2026-10-04)

```bash
git clone https://github.com/Blockchains/grokhack-forge && cd grokhack-forge
python3 forge/compose.py --idea "A chat assistant that answers DeFi questions with tools" --name defi-grok-chat --out /tmp/defi-grok-chat
cd /tmp/defi-grok-chat && npm ci && npm run build && npm test     # add tools in src/tools.ts (localTools)
```

**Inputs → outputs**

- In: `--idea` (string); `--name` (string); `--index` (dir or URL) grokhack-index data (published index by default)
- Out: `app repo` (directory) src/ (chat) or app/ (digest), tests, scripts/e2e, PARTS.md, forge.json, AGENTS.md, llms.txt, schema-valid blocks.json, CI, Pages workflow; `compose result` (JSON on stdout) parts used, archetype, dir/URL

**Composes with**

- [Blockchains/grokhack-index](https://github.com/Blockchains/grokhack-index): parts source: SDK package versions at indexed fork commits, default model, reference snippets
- [Blockchains/blockchainlab-mcp](https://github.com/Blockchains/blockchainlab-mcp): give the app's developer agent blockchain tools, or port tools into the app
- [Blockchains/blockchainlab-sdk](https://github.com/Blockchains/blockchainlab-sdk): typed data calls as Grok tools inside a chat app (Build with Blocks recipe 2)
- [Blockchains/grok-tools-chat](https://github.com/Blockchains/grok-tools-chat): reference chat output
- [Blockchains/grok-release-radar](https://github.com/Blockchains/grok-release-radar): reference digest output
- [Blockchains/awesome-grokhack](https://github.com/Blockchains/awesome-grokhack): the forks behind the index

**Versioning & stability:** `beta`. Generated apps pin `ai` / `@ai-sdk/xai` / `xai-sdk` to the versions found at the indexed fork commits and record them in `forge.json`. Archetypes and template file layout are stable; the default model follows the index.
<!-- blocks:end -->

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `XAI_API_KEY` | env / repo secret | Used by the generated apps' tests and live e2e against api.x.ai. Without it the e2e checks that api.x.ai rejects the unauthenticated call (`needs key`) |
| `XAI_MODEL` | env | Overrides the default model in generated digest apps |
| `GITHUB_TOKEN` | env | GitHub API access for the generated apps' GitHub lookups/tests |
| `FORGE_TOKEN` | repo secret | Fine-grained PAT owned by Blockchains; needed by the **compose app** workflow to create repos |
| `FORGE_INDEX` | env (tests) | Overrides the grokhack-index URL used by `tests/` |

`--create` needs `gh` authenticated as Blockchains; `gitleaks` runs before every push.

## Contributing

Issues and pull requests are welcome. Please read the [contributing guide](https://github.com/Blockchains/.github/blob/main/CONTRIBUTING.md), [code of conduct](https://github.com/Blockchains/.github/blob/main/CODE_OF_CONDUCT.md) and [security policy](https://github.com/Blockchains/.github/blob/main/SECURITY.md) first.

---
Built by Blockchain Lab — [blockchainlab.com](https://blockchainlab.com/?utm_source=github&utm_medium=readme&utm_campaign=grokhack-forge)
