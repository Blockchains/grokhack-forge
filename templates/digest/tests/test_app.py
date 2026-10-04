import datetime as dt, json, os
from app.collect import collect
from app.render import render
from app.summarize import summarize
from app.forge_config import FORGE

def test_collect_reads_real_github_releases(tmp_path):
    cfg = {**FORGE, "repos": ["xai-org/xai-sdk-python"], "repo_list_url": None, "window_days": 3650}
    c = collect(cfg)
    assert c["repos_checked"] == 1 and not c["errors"]
    assert c["items"] and c["items"][0]["repo"] == "xai-org/xai-sdk-python"

def test_render_without_key_shows_needs_key(tmp_path, monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    cfg = {**FORGE, "repos": ["xai-org/xai-sdk-python"], "repo_list_url": None, "window_days": 3650}
    c = collect(cfg)
    d = summarize(c, cfg)
    assert d["status"] == "needs_key"
    p = render(c, d, cfg, out=str(tmp_path))
    html = open(p).read()
    assert "needs key" in html and "xai-org/xai-sdk-python" in html
    assert json.load(open(tmp_path / "releases.json"))["items"]

def test_credits_error_is_detected_and_rendered(tmp_path):
    from app.summarize import is_credits_error
    assert is_credits_error("PERMISSION_DENIED Your team has either used all available credits or reached its monthly spending limit")
    assert not is_credits_error("UNAUTHENTICATED Incorrect API key provided")
    c = {"items": [], "window_days": 7, "repos_checked": 0, "errors": [], "generated_at": "2026-10-04T00:00:00Z"}
    d = {"status": "credits_needed", "message": "xAI credits needed: add credits at https://console.x.ai", "model": "grok", "generated_at": "2026-10-04T00:00:00Z"}
    html = open(render(c, d, {**FORGE}, out=str(tmp_path))).read()
    assert "xAI credits needed" in html
