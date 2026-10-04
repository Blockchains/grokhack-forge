import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "forge"))
import compose  # noqa: E402

INDEX = os.environ.get("FORGE_INDEX", compose.DEFAULT_INDEX)

class ComposeTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(compose.detect("a daily digest of releases")["archetype"], "digest")
        d = compose.detect("chat assistant with tools and web search")
        self.assertEqual(d["archetype"], "chat")
        self.assertIn("tool_calling", d["capabilities"]); self.assertIn("live_search", d["capabilities"])

    def test_choose_parts_from_real_index(self):
        c = compose.choose_parts(INDEX, {"archetype": "chat", "capabilities": ["streaming", "tool_calling"]})
        self.assertEqual(c["sdk"]["name"], "@ai-sdk/xai")
        self.assertRegex(c["default_model"], r"^grok-\d")
        self.assertEqual(len(c["sdk"]["commit"]), 40)
        self.assertTrue(c["references"])

    def test_compose_digest_writes_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "app")
            m = compose.compose("A weekly report of Grok SDK releases", "test-digest", INDEX, out, "Blockchains")
            self.assertEqual(m["archetype"], "digest")
            req = open(os.path.join(out, "requirements.txt")).read()
            self.assertIn("git+https://github.com/Blockchains/xai-sdk-python@", req)
            self.assertTrue(json.load(open(os.path.join(out, "forge.json")))["reference_parts"])
            self.assertNotIn("__", open(os.path.join(out, "app", "forge_config.py")).read().replace("__init__", ""))

class AgentDocsTests(unittest.TestCase):
    """Composed apps ship AGENTS.md, llms.txt and a blocks.json that is schema-valid and matches the generated code."""
    def check(self, out, arch):
        import agentdocs
        for f in ("AGENTS.md", "llms.txt", "blocks.json"):
            self.assertTrue(os.path.getsize(os.path.join(out, f)) > 200, f)
        with open(os.path.join(out, "blocks.json")) as f: man = json.load(f)
        self.assertEqual(agentdocs.validate(man), [])
        with open(os.path.join(out, "AGENTS.md")) as f: agents = f.read()
        for s in ("## Setup", "## Build / test", "## Structure", "## Conventions", "## Extension points", "## Do / don't"):
            self.assertIn(s, agents)
        with open(os.path.join(out, "llms.txt")) as f: llms = f.read()
        self.assertRegex(llms, r"^# .+\n\n> ")   # llmstxt.org: H1 then blockquote summary
        for ep in man["entrypoints"]:
            if ep["type"] in ("file", "cli"):
                self.assertTrue(os.path.exists(os.path.join(out, ep["ref"])), ep["ref"])
        return man

    def test_digest_app_docs(self):
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "app")
            compose.compose("A weekly report of Grok SDK releases", "test-digest", INDEX, out, "Blockchains")
            man = self.check(out, "digest")
            self.assertEqual(man["kind"], ["automation", "web-app"])
            summ = next(e for e in man["entrypoints"] if e["ref"] == "app/summarize.py")
            self.assertIn("summarize", summ["exports"])

    def test_chat_app_docs(self):
        if not compose.shutil.which("npm"): self.skipTest("npm not installed")
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "app")
            compose.compose("A chat assistant that can look up GitHub repos and do maths with tools", "test-chat", INDEX, out, "Blockchains")
            man = self.check(out, "chat")
            tools = next(e for e in man["entrypoints"] if e["ref"] == "src/tools.ts")["exports"]
            self.assertEqual(tools, ["calculate", "current_time", "github_repo"])
            with open(os.path.join(out, "src", "tools.ts")) as f: src = f.read()
            for name in tools: self.assertIn(f"  {name}: tool(", src)

    def test_vendored_schema_matches_published(self):
        import agentdocs, urllib.request
        try:
            live = json.load(urllib.request.urlopen(agentdocs.SCHEMA_URL, timeout=20))
        except Exception as e:
            self.skipTest(f"schema not reachable: {e}")
        with open(agentdocs.SCHEMA_PATH) as f:
            self.assertEqual(json.load(f), live, "forge/blocks.schema.json is stale; copy Blockchains/.github docs/blocks.schema.json")

if __name__ == "__main__":
    unittest.main()
