from __future__ import annotations
import json, sys
from app.forge_config import FORGE
from app.collect import collect
from app.summarize import summarize
from app.render import render

def main() -> int:
    collected = collect(FORGE)
    digest = summarize(collected, FORGE)
    path = render(collected, digest, FORGE)
    print(json.dumps({"items": len(collected["items"]), "repos_checked": collected["repos_checked"], "errors": len(collected["errors"]),
                      "digest_status": digest["status"], "page": path}))
    return 0 if collected["repos_checked"] and len(collected["errors"]) < collected["repos_checked"] else 1

if __name__ == "__main__":
    sys.exit(main())
