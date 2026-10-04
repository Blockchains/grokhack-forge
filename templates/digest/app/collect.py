"""Collect real activity from GitHub for the tracked repositories (releases in the window, else latest push)."""
from __future__ import annotations
import datetime as dt, json, os, urllib.request, urllib.error

API = "https://api.github.com"

def _get(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "grokhack-forge-app"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def tracked_repos(cfg: dict) -> list[str]:
    repos = list(cfg.get("repos") or [])
    url = cfg.get("repo_list_url")
    if url:
        data = _get(url) if url.startswith(API) else json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
        items = data.get("repos", data) if isinstance(data, dict) else data
        repos += [it["upstream"] if isinstance(it, dict) else it for it in items]
    seen, out = set(), []
    for r in repos:
        if r.lower() not in seen:
            seen.add(r.lower()); out.append(r)
    return out[: int(cfg.get("max_repos", 120))]

def collect(cfg: dict, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=int(cfg.get("window_days", 7)))
    items, errors = [], []
    for full in tracked_repos(cfg):
        try:
            rels = _get(f"{API}/repos/{full}/releases?per_page=10")
            recent = [r for r in rels if r.get("published_at") and not r.get("draft")
                      and dt.datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")) >= since]
            for r in recent:
                items.append({"repo": full, "kind": "release", "tag": r["tag_name"], "name": r.get("name") or r["tag_name"],
                              "url": r["html_url"], "published_at": r["published_at"], "prerelease": r.get("prerelease", False),
                              "body": (r.get("body") or "")[:4000]})
        except urllib.error.HTTPError as e:
            errors.append({"repo": full, "error": f"HTTP {e.code}"})
        except Exception as e:  # network etc.
            errors.append({"repo": full, "error": str(e)[:200]})
    items.sort(key=lambda x: x["published_at"], reverse=True)
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "window_days": int(cfg.get("window_days", 7)),
            "repos_checked": len(tracked_repos(cfg)), "items": items, "errors": errors}
