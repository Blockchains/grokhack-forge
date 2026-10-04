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
