# grokhack-forge

The composer behind **[grokhack.com /forge](https://grokhack.com/forge)**: describe an app idea, get a working Grok app repo under
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
