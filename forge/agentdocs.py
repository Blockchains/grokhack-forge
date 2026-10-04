"""AI-agent docs for apps composed by grokhack-forge: AGENTS.md, llms.txt and a blocks.json manifest (Blockchains blocks schema 1.0).

Derived from the generated app itself (tool names and exported functions are parsed from the files written to `out`),
so the manifest matches the code. Stdlib only; `validate()` needs `jsonschema` (tests/CI only).
Schema: https://github.com/Blockchains/.github/blob/main/docs/BLOCKS-SCHEMA.md (vendored copy: blocks.schema.json).
"""
from __future__ import annotations
import glob, json, os, re

SCHEMA_URL = "https://raw.githubusercontent.com/Blockchains/.github/main/docs/blocks.schema.json"
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocks.schema.json")
GUIDE = "https://github.com/Blockchains/.github/blob/main/docs/BUILD-WITH-BLOCKS.md"


def _read(out, rel):
    p = os.path.join(out, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def ts_exports(src: str) -> list[str]:
    return re.findall(r"^export (?:async )?function\*? ?(\w+)", src, re.M) + re.findall(r"^export const (\w+)", src, re.M)


def chat_tools(out: str) -> list[str]:
    src = _read(out, "src/tools.ts")
    block = src[src.find("export const localTools"):] if "export const localTools" in src else ""
    return re.findall(r"^\s{2}(\w+): tool\(", block, re.M)


def py_functions(out: str) -> dict[str, list[str]]:
    res = {}
    for p in sorted(glob.glob(os.path.join(out, "app", "*.py"))):
        names = [n for n in re.findall(r"^def (\w+)\(", open(p, encoding="utf-8").read(), re.M) if not n.startswith("_")]
        if names:
            res[os.path.relpath(p, out)] = names
    return res


def manifest(out: str, m: dict, title: str, owner: str, name: str) -> dict:
    arch, idea = m["archetype"], m["idea"]
    pages = f"https://{owner.lower()}.github.io/{name}/"
    common_compat = [{"repo": "Blockchains/grokhack-forge", "how": "the composer that generated this app (forge.json records the parts)"},
                     {"repo": "Blockchains/grokhack-index", "how": f"source of the SDK part ({m['sdk_part']}) and reference snippets (PARTS.md)"},
                     {"repo": "Blockchains/blockchainlab-mcp", "how": "give the developer agent blockchain tools while extending this app (stdio MCP server)"}]
    if arch == "chat":
        tools = chat_tools(out)
        eps = [{"type": "web", "name": title, "ref": pages, "usage": "open the page and paste your own xAI API key (it is only sent to api.x.ai)"},
               {"type": "file", "name": "src/tools.ts", "ref": "src/tools.ts", "usage": "local tools Grok can call (`localTools`); add a `tool({...})` entry to extend", "exports": tools},
               {"type": "file", "name": "src/grok.ts", "ref": "src/grok.ts", "usage": "streaming chat client over @ai-sdk/xai", "exports": ts_exports(_read(out, "src/grok.ts"))},
               {"type": "file", "name": "src/forge.config.ts", "ref": "src/forge.config.ts", "usage": "title, default model, enabled features, system prompt"}]
        kind, deps = ["web-app"], ["node>=20", "npm"]
        tests = {"command": "npm ci && npm run build && npm test && npm run e2e", "ci": ".github/workflows/ci.yml", "network": True}
        inputs = [{"name": "xAI API key", "type": "user input", "description": "pasted by the visitor; stored in the browser only"},
                  {"name": "chat messages", "type": "text"}]
        outputs = [{"name": "streamed Grok answers", "type": "text", "description": "with tool calls/results shown inline"},
                   {"name": "static site", "type": "GitHub Pages", "description": pages}]
        compat = common_compat + [{"repo": "Blockchains/blockchainlab-sdk", "how": "add blockchain data tools to localTools (npm i github:Blockchains/blockchainlab-sdk), as in Build with Blocks recipe 2"}]
        env = [{"name": "XAI_API_KEY", "required": False, "purpose": "CI e2e only (repository secret); visitors use their own key"}]
    else:
        fns = py_functions(out)
        eps = [{"type": "cli", "name": "python -m app.main", "ref": "app/main.py", "usage": "collect GitHub releases, summarise with Grok, render site/"},
               {"type": "web", "name": title, "ref": pages, "usage": "published daily by .github/workflows/pages.yml"},
               {"type": "file", "name": "app/forge_config.py", "ref": "app/forge_config.py", "usage": "repos to track, window, default model, prompt"}]
        eps += [{"type": "file", "name": p, "ref": p, "exports": names} for p, names in fns.items() if p not in ("app/main.py",)]
        kind, deps = ["automation", "web-app"], ["python>=3.10", "xai-sdk (pinned fork commit in requirements.txt)"]
        tests = {"command": "pip install -r requirements.txt && pytest -q && python -m app.e2e", "ci": ".github/workflows/ci.yml", "network": True}
        inputs = [{"name": "GitHub releases", "type": "network", "description": "repos from app/forge_config.py (default: awesome-grokhack grok-forge.json)"},
                  {"name": "XAI_API_KEY", "type": "env", "description": "optional; without it the page shows a 'needs key' notice instead of summaries"}]
        outputs = [{"name": "site/", "type": "static HTML", "description": "release digest published to GitHub Pages"}]
        compat = common_compat + [{"repo": "Blockchains/awesome-grokhack", "how": "default list of tracked repos (grok-forge.json)"}]
        env = [{"name": "XAI_API_KEY", "required": False, "purpose": "Grok summaries (repository secret)"},
               {"name": "GITHUB_TOKEN", "required": False, "purpose": "higher GitHub API rate limit"}]
    summary = f"Grok {arch} app composed by grokhack-forge: {idea.strip()}"
    summary = (summary[:396] + "…") if len(summary) > 397 else summary
    return {"$schema": SCHEMA_URL, "schema_version": "1.0", "name": name, "repo": f"{owner}/{name}", "summary": summary, "kind": kind,
            "stability": "experimental", "license": "MIT", "homepage": pages, "entrypoints": eps, "inputs": inputs, "outputs": outputs, "deps": deps,
            "compatible_with": compat, "tests": tests, "env": env,
            "docs": {"readme": "README.md", "agents": "AGENTS.md", "llms": "llms.txt", "extra": ["PARTS.md", "forge.json"]},
            "tags": ["grok", "xai", arch, "composed"] + list(m.get("capabilities", []))}


def agents_md(out: str, m: dict, title: str, owner: str, name: str) -> str:
    arch = m["archetype"]
    if arch == "chat":
        setup = "npm ci\nnpm run dev            # local dev server (paste an xAI key in the page)"
        test = "npm run build          # tsc --noEmit + vite build\nnpm test               # unit tests (tools, client)\nXAI_API_KEY=… npm run e2e   # real api.x.ai request (without a key it checks the 'needs key' path)"
        structure = [("src/main.ts", "UI wiring"), ("src/grok.ts", "streaming client over @ai-sdk/xai: " + ", ".join(ts_exports(_read(out, "src/grok.ts"))[:6])),
                     ("src/tools.ts", "local tools Grok can call: " + ", ".join(chat_tools(out))), ("src/forge.config.ts", "generated config (title, model, features, prompt)"),
                     ("tests/", "unit tests (node test runner via tsx)"), ("scripts/e2e.ts", "live api.x.ai check"), (".github/workflows/", "ci.yml (build/test/e2e), pages.yml (deploy)")]
        extend = ["New tool: add a `tool({ description, inputSchema: z.object(...), execute })` entry to `localTools` in `src/tools.ts` plus a test in `tests/`.",
                  "Blockchain data: `npm i github:Blockchains/blockchainlab-sdk` and call it from a tool (Build with Blocks recipe 2).",
                  "Model/prompt: edit `src/forge.config.ts`."]
    else:
        setup = "python -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt"
        test = "pytest -q              # unit tests\nXAI_API_KEY=… python -m app.e2e   # real api.x.ai request\npython -m app.main     # full run: collect → summarise → render site/"
        structure = [(p, "functions: " + ", ".join(n)) for p, n in py_functions(out).items()] + [
            ("app/forge_config.py", "generated config (repos, window, model, prompt)"), ("tests/", "pytest"), (".github/workflows/", "ci.yml (tests/e2e), pages.yml (daily run + deploy)")]
        extend = ["Track other repos: edit `repos` / `repo_list_url` in `app/forge_config.py`.", "New section: extend `app/summarize.py` (structured output) and `app/render.py`, with a test in `tests/`.",
                  "Schedule: change the cron in `.github/workflows/pages.yml`."]
    rows = "\n".join(f"| `{p}` | {d} |" for p, d in structure)
    return f"""# AGENTS.md: {name}

Instructions for AI coding agents working in this repository. Humans: see [README.md](README.md).

**What this is:** {m['idea'].strip()}
A Grok `{arch}` app composed by [grokhack-forge](https://github.com/Blockchains/grokhack-forge) (capabilities: {', '.join(m.get('capabilities', []))}; default model `{m['default_model']}`). Integration parts and pinned commits: [PARTS.md](PARTS.md), [forge.json](forge.json).

## Setup
```bash
{setup}
```

## Build / test
```bash
{test}
```
CI runs the same commands on every push; Pages deploys from `.github/workflows/pages.yml`.

## Structure
| Path | What |
|---|---|
{rows}
| `PARTS.md`, `forge.json` | composer provenance (SDK part + commit, reference snippets) |
| `blocks.json`, `llms.txt` | machine-readable block manifest and doc map |

## Conventions
- Real data only: never fake model output. On xAI 403 (no credits / spending limit) show the credits notice; without a key show "needs key".
- Keys never leave their place: visitor keys go only to api.x.ai; CI keys are repository secrets. `.env` is git-ignored.
- Keep `npm test` / `pytest` green and add a test with every change.

## Extension points
{chr(10).join('- ' + e for e in extend)}
- While coding, give your agent the Blockchain Lab MCP server: `{{"command":"npx","args":["-y","github:Blockchains/blockchainlab-mcp"]}}`. See [Build with Blocks]({GUIDE}).

## Do / don't
- Do keep `blocks.json` in sync when you add tools, entry points or env vars.
- Don't commit API keys, tokens or `.env` files; run `gitleaks git` before pushing.
- Don't remove the credits/needs-key notices or replace live calls with canned data.
"""


def llms_txt(out: str, m: dict, title: str, owner: str, name: str) -> str:
    raw = f"https://raw.githubusercontent.com/{owner}/{name}/main"
    idea = m["idea"].strip() + ("" if m["idea"].strip()[-1:] in ".!?" else ".")
    key = ([("src/tools.ts", "local tools: " + ", ".join(chat_tools(out))), ("src/grok.ts", "Grok streaming client"), ("src/forge.config.ts", "config")]
           if m["archetype"] == "chat" else [("app/main.py", "entry point"), ("app/forge_config.py", "config"), ("app/summarize.py", "Grok structured summary"), ("app/collect.py", "GitHub release collection")])
    lines = [f"# {title}", "", f"> {idea} Grok `{m['archetype']}` app composed by grokhack-forge (default model {m['default_model']}).", "",
             f"Live: https://{owner.lower()}.github.io/{name}/ . MIT. Parts and pinned commits in PARTS.md.", "", "## Docs",
             f"- [README]({raw}/README.md): what it does, keys, run locally", f"- [AGENTS.md]({raw}/AGENTS.md): setup, commands, structure, rules for AI agents",
             f"- [blocks.json]({raw}/blocks.json): machine-readable manifest", f"- [PARTS.md]({raw}/PARTS.md): integration parts from grokhack-index", "", "## Code"]
    lines += [f"- [{p}]({raw}/{p}): {d}" for p, d in key]
    lines += ["", "## Optional", f"- [forge.json]({raw}/forge.json): composition manifest", f"- [Build with Blocks]({GUIDE}): how Blockchains blocks fit together", ""]
    return "\n".join(lines)


def write(out: str, m: dict, title: str, owner: str, name: str) -> dict:
    man = manifest(out, m, title, owner, name)
    with open(os.path.join(out, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2, ensure_ascii=False); f.write("\n")
    with open(os.path.join(out, "AGENTS.md"), "w", encoding="utf-8") as f: f.write(agents_md(out, m, title, owner, name))
    with open(os.path.join(out, "llms.txt"), "w", encoding="utf-8") as f: f.write(llms_txt(out, m, title, owner, name))
    return man


def validate(manifest_obj: dict) -> list[str]:
    import jsonschema
    v = jsonschema.Draft202012Validator(json.load(open(SCHEMA_PATH)))
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(manifest_obj)]
