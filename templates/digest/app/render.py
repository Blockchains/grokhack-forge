"""Render the static site (site/index.html + JSON) from collected data and the Grok digest."""
from __future__ import annotations
import html, json, os

def render(collected: dict, digest: dict, cfg: dict, out: str = "site") -> str:
    os.makedirs(out, exist_ok=True)
    json.dump(collected, open(f"{out}/releases.json", "w"), indent=1)
    json.dump(digest, open(f"{out}/digest.json", "w"), indent=1)
    e = html.escape
    summ = {(s["repo"], s["tag"]): s for s in (digest.get("digest") or {}).get("items", [])}
    if digest.get("status") == "ok":
        top = f'<section class="ok"><h2>Grok overview</h2><p>{e(digest["digest"]["overview"])}</p><p class="mut">model {e(digest["model"])} · {e(digest["generated_at"])}</p></section>'
    elif digest.get("status") == "needs_key":
        top = f'<section class="warn"><h2>AI summary: needs key</h2><p>{e(digest["message"])} The release list below is real GitHub data and refreshes daily without a key.</p></section>'
    elif digest.get("status") == "credits_needed":
        top = f'<section class="warn"><h2>AI summary: xAI credits needed</h2><p>{e(digest["message"])} The release list below is real GitHub data and refreshes daily.</p></section>'
    else:
        top = f'<section class="mut"><p>{e(digest.get("message", ""))}</p></section>'
    rows = []
    for it in collected["items"]:
        s = summ.get((it["repo"], it["tag"]))
        extra = (f'<div class="sum"><b>{e(s["headline"])}</b><br>{e(s["impact"])}<br><span class="tags">{" ".join("#" + e(t) for t in s["tags"])}</span></div>' if s else "")
        rows.append(f'<li><a href="{e(it["url"])}">{e(it["repo"])} {e(it["tag"])}</a>{" <em>pre-release</em>" if it["prerelease"] else ""}'
                    f' <span class="mut">{e(it["published_at"][:10])}</span>{extra}</li>')
    body = "\n".join(rows) or '<li class="mut">No releases in this window.</li>'
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(cfg["title"])}</title><meta name="description" content="{e(cfg["idea"])}">
<style>body{{font-family:system-ui,sans-serif;background:#0b0d10;color:#e8eaed;max-width:900px;margin:0 auto;padding:24px}}a{{color:#7cf0c5}}
.mut{{color:#9aa0a6}}section{{border:1px solid #2a2f36;border-radius:10px;padding:12px 16px;margin:16px 0}}.warn{{border-color:#c9a227}}.ok{{border-color:#2e7d5b}}
li{{margin:10px 0}}.sum{{margin:6px 0 0 12px;font-size:.92rem}}.tags{{color:#9aa0a6}}</style></head><body>
<h1>{e(cfg["title"])}</h1><p class="mut">{e(cfg["idea"])}</p>{top}
<h2>Releases in the last {collected["window_days"]} days ({len(collected["items"])} across {collected["repos_checked"]} repos)</h2><ul>{body}</ul>
<p class="mut">Data generated {e(collected["generated_at"])}. {len(collected["errors"])} repos could not be read. Raw JSON: <a href="releases.json">releases.json</a> · <a href="digest.json">digest.json</a>.<br>
Composed by <a href="https://github.com/Blockchains/grokhack-forge">grokhack-forge</a> from indexed Grok parts (<a href="{e(cfg["repo_url"])}/blob/main/PARTS.md">PARTS.md</a>).</p></body></html>"""
    open(f"{out}/index.html", "w").write(page)
    return f"{out}/index.html"
