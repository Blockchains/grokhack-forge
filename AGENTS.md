# AGENTS.md: grokhack-forge

Instructions for AI coding agents (Grok, Cursor, Claude Code, Codex, Copilot and others) working **in** this repo or **using it as a building block**. Humans: see [README.md](README.md).

## What this is

Composer for Grok apps: turns an app idea into a working repo (archetype `chat`: Vite + Vercel AI SDK @ai-sdk/xai with streaming and tools; archetype `digest`: Python xai-sdk with structured output on a schedule) using parts from grokhack-index, with CI that makes a real api.x.ai request and a GitHub Pages deploy.

- Kind: cli, github-action, template · stability: `beta` · licence: MIT
- Machine-readable manifest: [`blocks.json`](blocks.json) (schema: [BLOCKS-SCHEMA](https://github.com/Blockchains/.github/blob/main/docs/BLOCKS-SCHEMA.md))
- How it fits with the other Blockchains repos: [Build with Blocks](https://github.com/Blockchains/.github/blob/main/docs/BUILD-WITH-BLOCKS.md)

## Setup

```bash
python3 --version   # stdlib only
```

## Build and test

```bash
python3 -m unittest discover -s tests -v   # runs against the real published index
```

Tests hit **live** public networks/APIs (the org rule is no mocks). A failure can be an upstream outage: re-run before changing code.

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `XAI_API_KEY` | no | generated apps' live e2e; without it the e2e checks api.x.ai rejects the unauthenticated call |
| `XAI_MODEL` | no | override the default model in digest apps |
| `FORGE_TOKEN` | no | repo secret; lets the Action create repos |

## Structure

| Path | What |
|---|---|
| `forge/compose.py` | composer + CLI |
| `templates/chat/` | Vite + TypeScript chat app (src/grok.ts streaming, src/tools.ts local tools) |
| `templates/digest/` | Python digest app (app/collect, summarize, render) |
| `tests/test_compose.py` | tests |
| `results/` | Action outputs |

## Conventions

- Templates use `__APP_NAME__`-style placeholders filled by compose.py.
- Keys only via env/secrets; the browser app sends the visitor's key only to api.x.ai.
- Every generated repo must pass a real api.x.ai e2e (live answer or proven 401/403).

## Extension points

- New tool in chat apps: add a `tool({...})` to `localTools` in `templates/chat/src/tools.ts` with a zod schema and a test.
- New archetype: `templates/<name>/` + capability rules in compose.py + a CI compose job.

## Do

- Compose without `--create` while iterating.

## Don't

- Ship code that fakes a Grok answer when the key is missing or credits are exhausted; show the 'needs key' / 'xAI credits needed' notice instead.
- Invent data, mock network responses in shipped code, or hard-code values that should come from the live source; every repo here is 'no mocks, real data'.
- Commit secrets, keys or `.env` files. Run `gitleaks` before pushing; CI and the org policy reject leaks.

## Using it from another project

- **forge/compose.py** (cli): `python3 forge/compose.py --idea "<idea>" --name <app> [--out DIR] [--index DIR|URL] [--create --wait]`
- **compose app** (github-action): `workflow_dispatch inputs: idea, name, request_id → results/<request_id>.json`
- **templates/chat, templates/digest** (file): `app templates the composer fills in`

See the README section [Use as a building block](README.md#use-as-a-building-block) for a copy-paste example.

## Related blocks

- [Blockchains/grokhack-index](https://github.com/Blockchains/grokhack-index): parts source: SDK package versions at indexed fork commits, default model, reference snippets
- [Blockchains/blockchainlab-mcp](https://github.com/Blockchains/blockchainlab-mcp): give the app's developer agent blockchain tools, or port tools into the app
- [Blockchains/blockchainlab-sdk](https://github.com/Blockchains/blockchainlab-sdk): typed data calls as Grok tools inside a chat app (Build with Blocks recipe 2)
- [Blockchains/grok-tools-chat](https://github.com/Blockchains/grok-tools-chat): reference chat output
- [Blockchains/grok-release-radar](https://github.com/Blockchains/grok-release-radar): reference digest output
- [Blockchains/awesome-grokhack](https://github.com/Blockchains/awesome-grokhack): the forks behind the index
