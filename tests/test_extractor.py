import os
import unittest

from token_classifier.extractor import (
    load_libraries,
    find_evidence,
    scan_indicators,
)

_HERE = os.path.dirname(__file__)
_DEMO = os.path.join(_HERE, "..", "demo", "demo_security_token.md")


class TestLoadLibraries(unittest.TestCase):
    def setUp(self):
        self.libs = load_libraries()

    def test_counts(self):
        self.assertEqual(len(self.libs["howey"]), 4)
        self.assertEqual(len(self.libs["hk_sfc"]), 3)
        self.assertEqual(len(self.libs["sg_mas"]), 3)
        self.assertEqual(len(self.libs["token_types"]), 4)

    def test_howey_keys(self):
        f = self.libs["howey"][0]
        for k in ("factor", "name", "indicators", "source_url", "source_accessed_at"):
            self.assertIn(k, f)


class TestFindEvidence(unittest.TestCase):
    def test_found(self):
        text = "用户以 ETH 认购代币，单价递增"
        ev = find_evidence(text, "认购")
        self.assertIsNotNone(ev)
        self.assertIn("认购", ev)

    def test_missing(self):
        self.assertIsNone(find_evidence("无任何关键词", "认购"))


class TestScanIndicators(unittest.TestCase):
    def test_scan(self):
        indicators = [
            {"pattern": "购买", "weight": "strong"},
            {"pattern": "质押", "weight": "weak"},
            {"pattern": "分红", "weight": "strong"},
        ]
        text = "用户购买代币并可获得分红"
        matched = scan_indicators(text, indicators)
        patterns = {m["pattern"] for m in matched}
        self.assertEqual(patterns, {"购买", "分红"})
        self.assertTrue(all("evidence" in m for m in matched))


if __name__ == "__main__":
    unittest.main()
