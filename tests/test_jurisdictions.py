import os
import unittest

from token_classifier.extractor import load_libraries
from token_classifier.classifier import analyze

_HERE = os.path.dirname(__file__)
_DEMO = os.path.join(_HERE, "..", "demo")


def _read(name):
    with open(os.path.join(_DEMO, name), encoding="utf-8") as f:
        return f.read()


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.libs = load_libraries()

    def test_security_demo(self):
        a = analyze(_read("demo_security_token.md"), self.libs)
        self.assertEqual(a["howey_summary"]["classification"], "likely_security")
        # 港/新至少应能形成判定
        for key in ("HK_SFC", "SG_MAS"):
            self.assertNotEqual(a["jurisdictions"][key]["verdict"], "insufficient_info")

    def test_utility_demo(self):
        a = analyze(_read("demo_utility_token.md"), self.libs)
        self.assertEqual(a["howey_summary"]["classification"], "likely_not_security")
        self.assertEqual(a["jurisdictions"]["HK_SFC"]["verdict"], "utility_token")

    def test_ambiguous_demo(self):
        a = analyze(_read("demo_ambiguous_token.md"), self.libs)
        self.assertEqual(a["howey_summary"]["classification"], "possibly_security")
        # 兼具证券与实用特征 → 混合
        for key in ("HK_SFC", "SG_MAS"):
            self.assertEqual(a["jurisdictions"][key]["verdict"], "mixed")


if __name__ == "__main__":
    unittest.main()
