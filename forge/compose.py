#!/usr/bin/env python3
"""grokhack.com /forge: idea -> composed Grok app repo under github.com/Blockchains.

  python forge/compose.py --idea "..." --name my-app [--index DIR|URL] [--out DIR] [--create] [--owner Blockchains] [--wait]

1. Detect required capabilities from the idea (keyword rules, deterministic, printed in forge.json).
2. Pick an archetype: 'digest' (scheduled job + static report, Python xai-sdk) or 'chat' (browser app, Vercel AI SDK @ai-sdk/xai).
3. Pick integration parts from Blockchains/grokhack-index (parts.json + repos/*.json): the SDK package at the exact indexed
   commit, the default model (newest grok-N.M chat model found in the official SDK), and reference snippets that implement the
   needed capabilities (permissive licences first, ranked by stars).
4. Generate the repo from templates/<archetype> + glue config, PARTS.md (every part with commit-pinned URL) and forge.json.
5. --create: gitleaks scan, create the GitHub repo, push, enable Pages (Actions), optionally --wait for CI + Pages and print the URL.
Stdlib only."""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, shutil, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_INDEX = "https://raw.githubusercontent.com/Blockchains/grokhack-index/main/data"
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "CC0-1.0", "MPL-2.0"}
CAP_RULES = {
    "tool_calling": r"\btools?\b|function|calculat|agent|action|github|lookup|api call",
    "live_search": r"\bsearch|\bweb\b|news|latest|current|x posts|tweets?|twitter|trend",
    "structured_output": r"json|structured|extract|classif|score|rank|report|digest|summar|table",
    "streaming": r"\bchat|stream|assistant|convers|real-?time|copilot",
    "vision": r"image|photo|screenshot|vision|picture",
    "scheduled": r"daily|weekly|nightly|hourly|digest|monitor|radar|track|cron|schedul|release|newsletter|every (day|week|morning)",
}

def log(*a):
    print("[forge]", *a, file=sys.stderr, flush=True)

def load_json(base: str, rel: str):
    if base.startswith("http"):
        with urllib.request.urlopen(f"{base}/{rel}", timeout=60) as r:
            return json.loads(r.read().decode())
    return json.load(open(os.path.join(base, rel)))

def detect(idea: str) -> dict:
    low = idea.lower()
    caps = sorted(c for c, rx in CAP_RULES.items() if re.search(rx, low))
    archetype = "digest" if "scheduled" in caps else "chat"
    if archetype == "chat":
        caps = sorted(set(caps) | {"streaming"})
    return {"capabilities": caps, "archetype": archetype}

def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", s.lower())).strip("-")[:60] or "grok-app"

def model_key(m: str):
    # grok-4.20 is version 4.2 (older than grok-4.3); compare N.M as a decimal number
    v = re.match(r"grok-(\d+(?:\.\d+)?)", m)
    return float(v.group(1)) if v else 0.0

PREFERRED_LIVE = ("grok-4.7", "grok-4.5")

def live_models() -> list[str]:
    """GET https://api.x.ai/v1/models with XAI_API_KEY from the environment (never logged). [] without a key or on error."""
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        return []
    try:
        req = urllib.request.Request("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ids = [m.get("id") for m in json.loads(r.read().decode()).get("data", [])]
        log("live models:", ", ".join(i for i in ids if i))
        return [i for i in ids if i]
    except Exception as e:
        log("live model list unavailable:", type(e).__name__)
        return []

def pick_models(shard: dict) -> tuple[str, list[str]]:
    general = [m for m in shard.get("models", {}) if re.fullmatch(r"grok-\d+(\.\d+)?", m)]
    if not general:
        raise SystemExit("index has no grok-N.M models in the official SDK shard")
    general.sort(key=model_key, reverse=True)
    extra = [m for m in shard.get("models", {}) if re.fullmatch(r"grok-\d+(\.\d+)?-(fast|mini|fast-reasoning|fast-non-reasoning|non-reasoning|reasoning)", m)]
    extra.sort(key=model_key, reverse=True)
    return general[0], (general[:6] + extra[:4])

def raw_json(repo: str, commit: str, path: str):
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/{repo}/{commit}/{path}", timeout=60) as r:
        return json.loads(r.read().decode())

def choose_parts(index: str, plan: dict) -> dict:
    parts = load_json(index, "parts.json")
    stats = load_json(index, "stats.json")
    shard_of = lambda fork: load_json(index, f"repos/{fork.replace('/', '__')}.json")
    sdk_py = next(p for p in parts if p["type"] == "package" and p.get("name") == "xai-sdk")
    sdk_ts = next(p for p in parts if p["type"] == "package" and p.get("name") == "@ai-sdk/xai")
    official = shard_of(sdk_py["repo"])
    default_model, models = pick_models(official)
    live = live_models()
    if live:  # composer has a key: prefer the newest live model the account can use (grok-4.7, then grok-4.5)
        for m in PREFERRED_LIVE:
            if m in live:
                default_model = m; break
    lang = {"digest": "Python", "chat": "TypeScript"}[plan["archetype"]]
    need = set(plan["capabilities"]) - {"scheduled"}
    snippets = [p for p in parts if p["type"] == "code-snippet" and p.get("lang") in (lang, "JavaScript" if lang == "TypeScript" else lang)]
    def score(p):
        cov = len(need & set(p.get("capabilities", [])))
        return (cov, p.get("license") in PERMISSIVE, p.get("stars") or 0)
    refs, seen_repos = [], set()
    for p in sorted(snippets, key=score, reverse=True):
        if p["repo"] in seen_repos or not (need & set(p.get("capabilities", []))):
            continue
        refs.append(p); seen_repos.add(p["repo"])
        if len(refs) >= 6:
            break
    chosen = {"sdk": sdk_py if plan["archetype"] == "digest" else sdk_ts, "default_model": default_model, "index_models": models,
              "model_source": {"repo": official["fork"], "commit": official["commit"]}, "references": refs,
              "index_generated_at": stats.get("generated_at")}
    if plan["archetype"] == "chat":
        # pin `ai` to the version in the same vercel/ai fork commit as the indexed @ai-sdk/xai package
        ai_pkg = raw_json(sdk_ts["repo"], sdk_ts["commit"], "packages/ai/package.json")
        chosen["ai_version"] = ai_pkg["version"]
    return chosen

def render_tree(src: str, dst: str, subs: dict):
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for fn in files:
            s = open(os.path.join(root, fn), encoding="utf-8").read()
            for k, v in subs.items():
                s = s.replace(k, v)
            open(os.path.join(dst, rel, fn), "w", encoding="utf-8").write(s)

def compose(idea: str, name: str, index: str, out: str, owner: str, title: str | None = None) -> dict:
    plan = detect(idea)
    chosen = choose_parts(index, plan)
    name = slugify(name)
    repo_url = f"https://github.com/{owner}/{name}"
    title = title or name.replace("-", " ").title()
    feats = {c: (c in plan["capabilities"]) for c in CAP_RULES}
    if os.path.exists(out):
        shutil.rmtree(out)
    subs = {"__APP_NAME__": name, "__APP_TITLE__": title, "__IDEA_ESC__": idea.replace('"', "&quot;").replace("<", "&lt;"),
            "__REPO__": f"{owner}/{name}"}
    if plan["archetype"] == "chat":
        subs.update({"__AI_SDK_XAI_VERSION__": chosen["sdk"]["version"], "__AI_VERSION__": chosen["ai_version"]})
    else:
        subs.update({"__SDK_FORK__": chosen["sdk"]["repo"], "__SDK_COMMIT__": chosen["sdk"]["commit"], "__CRON__": "17 6 * * *"})
    system_prompt = (f"You are the engine of '{title}'. App idea: {idea}. Be accurate, cite sources when you use search, "
                     "and say clearly when you do not know.")
    if plan["archetype"] == "digest":
        cfg = {"title": title, "idea": idea, "repo_url": repo_url, "default_model": chosen["default_model"], "window_days": 7,
               "repo_list_url": "https://raw.githubusercontent.com/Blockchains/awesome-grokhack/main/grok-forge.json",
               "repos": [], "max_repos": 120, "features": feats, "system_prompt": system_prompt +
               " You write concise release digests for developers building on Grok and the xAI API."}
        subs["__FORGE_PY__"] = json.dumps(cfg, indent=2).replace(": true", ": True").replace(": false", ": False").replace(": null", ": None")
    render_tree(os.path.join(ROOT, "templates", plan["archetype"]), out, subs)
    if plan["archetype"] == "chat":
        cfg_ts = {"title": title, "idea": idea, "repoUrl": repo_url, "defaultModel": chosen["default_model"],
                  "indexModels": chosen["index_models"], "features": feats, "systemPrompt": system_prompt}
        open(os.path.join(out, "src", "forge.config.ts"), "w").write(
            "// Generated by grokhack.com /forge from Blockchains/grokhack-index. Edit freely.\n"
            f"export const FORGE = {json.dumps(cfg_ts, indent=2)} as const satisfies {{\n"
            "  title: string; idea: string; repoUrl: string; defaultModel: string; indexModels: readonly string[]\n"
            "  features: Record<string, boolean>; systemPrompt: string\n}\n")
    manifest = {"forge_version": 1, "composed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "idea": idea,
                "repo": f"{owner}/{name}", "archetype": plan["archetype"], "capabilities": plan["capabilities"],
                "default_model": chosen["default_model"], "model_source": chosen["model_source"],
                "sdk_part": chosen["sdk"]["id"], "sdk_commit": chosen["sdk"]["commit"], "index_generated_at": chosen["index_generated_at"],
                "reference_parts": [r["id"] for r in chosen["references"]]}
    json.dump(manifest, open(os.path.join(out, "forge.json"), "w"), indent=2)
    lines = [f"# Integration parts used by {title}", "", f"Composed by [grokhack-forge](https://github.com/Blockchains/grokhack-forge) from "
             f"[Blockchains/grokhack-index](https://github.com/Blockchains/grokhack-index) (index generated {chosen['index_generated_at']}).", "",
             f"**Idea:** {idea}", "", f"**Archetype:** `{plan['archetype']}` · **Capabilities detected:** {', '.join(plan['capabilities'])}", "",
             "## Runtime dependency (installed, pinned to the indexed fork commit)", "",
             f"- `{chosen['sdk']['name']}` {chosen['sdk'].get('version') or ''} from "
             f"[{chosen['sdk']['repo']}](https://github.com/{chosen['sdk']['repo']}/tree/{chosen['sdk']['commit']}/{os.path.dirname(chosen['sdk']['path'])}) "
             f"(upstream {chosen['sdk']['upstream']}, licence {chosen['sdk']['license']})", "",
             f"Default model `{chosen['default_model']}`" + (" (newest model live on the composer's xAI account via `GET /v1/models`; preference grok-4.7, then grok-4.5). Newest general `grok-N.M` model referenced in the index: " if chosen['default_model'] not in chosen['index_models'] else ": newest general `grok-N.M` model referenced in ") +
             f"[{chosen['model_source']['repo']}@{chosen['model_source']['commit'][:7]}](https://github.com/{chosen['model_source']['repo']}/tree/{chosen['model_source']['commit']}). "
             "Override with `XAI_MODEL` (digest) or the model picker (chat, live list from `GET /v1/language-models`).", "",
             "## Reference implementations consulted (not copied; links pinned to the indexed commit)", ""]
    for r in chosen["references"]:
        lines.append(f"- [{r['repo']} `{r['path']}` L{r['start']}-{r['end']}]({r['url']}) · {r.get('license')} · {r.get('stars')} stars · "
                     f"capabilities: {', '.join(r.get('capabilities', []))}")
    open(os.path.join(out, "PARTS.md"), "w").write("\n".join(lines) + "\n")
    if plan["archetype"] == "chat":  # CI uses `npm ci` + the npm cache, both need a real lockfile
        if not shutil.which("npm"): raise SystemExit("npm is required to lock the chat app's dependencies")
        sh(["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=out)
    run_cmds = ("npm ci && npm run build && npm test && npm run e2e" if plan["archetype"] == "chat"
                else "pip install -r requirements.txt && pytest -q && python -m app.e2e && python -m app.main")
    readme = f"""# {title}

{idea}

**Live:** https://{owner.lower()}.github.io/{name}/ · composed by [grokhack-forge](https://github.com/Blockchains/grokhack-forge) · parts: [PARTS.md](PARTS.md) · manifest: [forge.json](forge.json)

- Archetype: `{plan['archetype']}` · capabilities: {', '.join(plan['capabilities'])}
- Grok via {'Vercel AI SDK `@ai-sdk/xai` (browser, bring-your-own key; the key only goes to api.x.ai)' if plan['archetype']=='chat' else 'the official `xai-sdk` (gRPC) with structured output, run daily by GitHub Actions'}
- Default model `{chosen['default_model']}`

## Keys
If api.x.ai answers 403 because the xAI account is out of credits or over its spending limit, the app shows an **xAI credits needed** notice; outputs are never faked.

{'Visitors paste their own xAI API key in the page. CI runs an end-to-end request against api.x.ai: with the `XAI_API_KEY` repository secret it checks a live answer, without it it checks that api.x.ai rejects the unauthenticated call (needs key).' if plan['archetype']=='chat' else 'Add the `XAI_API_KEY` repository secret to enable Grok summaries. Without it the page still publishes the real GitHub release data and shows a clear "needs key" notice instead of a summary.'}

## Run locally
```bash
{run_cmds}
```
Never commit keys; use `.env` (git-ignored) or repository secrets.

## License
MIT for the generated glue code. Dependencies keep their own licences (see PARTS.md).
"""
    open(os.path.join(out, "README.md"), "w").write(readme)
    year = dt.date.today().year
    open(os.path.join(out, "LICENSE"), "w").write(f"""MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""")
    return manifest

def sh(cmd, cwd=None, check=True, inp=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, input=inp)
    if check and p.returncode:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{p.stdout[-800:]}\n{p.stderr[-800:]}")
    return p

def create_and_push(out: str, owner: str, name: str, desc: str, wait: bool) -> dict:
    sh(["git", "init", "-q", "-b", "main"], cwd=out)
    sh(["git", "add", "-A"], cwd=out)
    sh(["git", "-c", f"user.name={owner}", "-c", f"user.email={owner}@users.noreply.github.com", "commit", "-qm",
        "Compose app with grokhack.com /forge"], cwd=out)
    gl = shutil.which("gitleaks")
    if not gl:
        raise SystemExit("gitleaks not installed: refusing to push")
    sh([gl, "git", "--no-banner", "--redact", "."], cwd=out)
    exists = sh(["gh", "api", f"repos/{owner}/{name}"], check=False).returncode == 0
    if exists:
        raise SystemExit(f"{owner}/{name} already exists; choose another --name")
    sh(["gh", "repo", "create", f"{owner}/{name}", "--public", "--description", desc[:340], "--source", out, "--remote", "origin", "--push"])
    sh(["gh", "api", "-X", "PUT", f"repos/{owner}/{name}/topics", "-f", "names[]=grok", "-f", "names[]=xai", "-f", "names[]=grokhack", "-f", "names[]=grokhack-forge"], check=False)
    p = sh(["gh", "api", "-X", "POST", f"repos/{owner}/{name}/pages", "-f", "build_type=workflow"], check=False)
    log("pages enable:", "ok" if p.returncode == 0 else p.stdout[-200:] + p.stderr[-200:])
    sh(["gh", "api", "-X", "PATCH", f"repos/{owner}/{name}", "-f", f"homepage=https://{owner.lower()}.github.io/{name}/"], check=False)
    # the push happened before Pages was enabled: dispatch the Pages workflow once so the first deploy succeeds
    time.sleep(5)
    sh(["gh", "workflow", "run", "pages.yml", "-R", f"{owner}/{name}"], check=False)
    result = {"repo": f"https://github.com/{owner}/{name}", "pages": f"https://{owner.lower()}.github.io/{name}/"}
    if wait:
        result["runs"] = wait_runs(owner, name)
    return result

def wait_runs(owner, name, timeout=1500):
    t0 = time.time(); last = {}
    while time.time() - t0 < timeout:
        time.sleep(20)
        p = sh(["gh", "run", "list", "-R", f"{owner}/{name}", "--json", "workflowName,status,conclusion,event,databaseId,url", "-L", "20"], check=False)
        runs = json.loads(p.stdout or "[]")
        latest = {}
        for r in runs:
            latest.setdefault(r["workflowName"], r)
        last = latest
        if latest and all(r["status"] == "completed" for r in latest.values()) and len(latest) >= 2:
            break
    return {k: {"conclusion": v["conclusion"], "url": v["url"]} for k, v in last.items()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idea", required=True); ap.add_argument("--name", required=True); ap.add_argument("--title")
    ap.add_argument("--index", default=DEFAULT_INDEX); ap.add_argument("--out")
    ap.add_argument("--owner", default="Blockchains"); ap.add_argument("--create", action="store_true"); ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    name = slugify(a.name)
    out = a.out or os.path.join("/tmp", "forge-out", name)
    manifest = compose(a.idea, name, a.index, out, a.owner, a.title)
    res = {"manifest": manifest, "dir": out}
    if a.create:
        res.update(create_and_push(out, a.owner, name, f"{a.title or name}: {a.idea} (composed by grokhack.com /forge)", a.wait))
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
