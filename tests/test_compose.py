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

if __name__ == "__main__":
    unittest.main()
