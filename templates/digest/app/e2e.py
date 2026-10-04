"""Real call to the xAI API through xai-sdk. With XAI_API_KEY: expects an answer. Without: expects UNAUTHENTICATED/permission
error from api.x.ai (proves the gRPC path works) and prints 'needs key'."""
import os, sys
from xai_sdk import Client
from xai_sdk.chat import user
from app.forge_config import FORGE
key = os.environ.get("XAI_API_KEY", "").strip()
model = os.environ.get("XAI_MODEL", "").strip() or FORGE["default_model"]
client = Client(api_key=key or "not-a-real-key", timeout=60)
chat = client.chat.create(model=model)
chat.append(user("Reply with exactly: pong"))
try:
    r = chat.sample()
except Exception as e:  # grpc.RpcError
    msg = f"{type(e).__name__}: {getattr(e, 'code', lambda: '')()} {getattr(e, 'details', lambda: str(e))()}"
    if key:
        print("FAIL (live):", msg[:300]); sys.exit(1)
    if any(s in msg for s in ("UNAUTHENTICATED", "PERMISSION_DENIED", "INVALID_ARGUMENT", "API key", "api key")):
        print("PASS (needs key): api.x.ai rejected the unauthenticated request as expected ->", msg[:160]); sys.exit(0)
    print("FAIL: unexpected error without key:", msg[:300]); sys.exit(1)
if not key:
    print("FAIL: request without a valid key unexpectedly succeeded"); sys.exit(1)
print(f"PASS (live): model={model} reply={r.content[:80]!r}")
