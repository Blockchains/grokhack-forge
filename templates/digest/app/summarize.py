"""Grok summary via the official xai-sdk (gRPC) with structured output (chat.parse + pydantic)."""
from __future__ import annotations
import datetime as dt, json, os
from pydantic import BaseModel, Field

class ItemSummary(BaseModel):
    repo: str
    tag: str
    headline: str = Field(description="One line, plain English, what changed")
    impact: str = Field(description="Why a Grok/xAI builder should care, one or two sentences")
    tags: list[str] = Field(description="2-4 short tags, e.g. tool-calling, streaming, breaking-change")

class Digest(BaseModel):
    overview: str = Field(description="3-5 sentence overview of the week for Grok builders")
    items: list[ItemSummary]

def is_credits_error(msg: str) -> bool:
    m = msg.lower()
    return any(k in m for k in ("credits", "spending limit", "used all available", "insufficient_quota", "billing"))

def summarize(collected: dict, cfg: dict) -> dict:
    key = os.environ.get("XAI_API_KEY", "").strip()
    model = os.environ.get("XAI_MODEL", "").strip() or cfg["default_model"]
    base = {"generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": model}
    if not key:
        return {**base, "status": "needs_key", "message": "Set the XAI_API_KEY repository secret to enable Grok summaries."}
    if not collected["items"]:
        return {**base, "status": "empty", "message": "No releases in the window, nothing to summarise."}
    from xai_sdk import Client
    from xai_sdk.chat import system, user
    client = Client(api_key=key, timeout=180)
    chat = client.chat.create(model=model, messages=[system(cfg["system_prompt"])])
    payload = [{k: it[k] for k in ("repo", "tag", "name", "published_at", "body")} for it in collected["items"][:40]]
    chat.append(user("Summarise these releases. Return one item per release.\n" + json.dumps(payload)))
    try:
        response, digest = chat.parse(Digest)
    except Exception as e:  # grpc.RpcError etc. Never fake a summary: report the real reason.
        msg = f"{getattr(e, 'code', lambda: '')()} {getattr(e, 'details', lambda: str(e))()}".strip() or str(e)
        if is_credits_error(msg):
            return {**base, "status": "credits_needed", "message": "xAI credits needed: the API key is valid but the xAI account has no credits left or hit its monthly spending limit. Add credits at https://console.x.ai to enable Grok summaries.", "detail": msg[:300]}
        return {**base, "status": "error", "message": f"Grok request failed: {msg[:300]}"}
    usage = getattr(response, "usage", None)
    return {**base, "status": "ok", "digest": digest.model_dump(),
            "usage": {"prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None)}}
