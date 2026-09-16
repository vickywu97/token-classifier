import unittest

from token_classifier.classifier import classify_howey, classify_jurisdiction


def _factors(states):
    return [{"state": s} for s in states]


class TestClassifyHowey(unittest.TestCase):
    def test_likely_security(self):
        r = classify_howey(_factors(["strong", "strong", "strong", "weak"]))
        self.assertEqual(r["classification"], "likely_security")
        self.assertEqual(r["confidence"], "high")

    def test_possibly_security(self):
        r = classify_howey(_factors(["strong", "strong", "weak", "weak"]))
        self.assertEqual(r["classification"], "possibly_security")

    def test_likely_not_security(self):
        r = classify_howey(_factors(["absent", "absent", "absent", "absent"]))
        self.assertEqual(r["classification"], "likely_not_security")

    def test_insufficient_info(self):
        r = classify_howey(_factors(["unknown", "unknown", "unknown", "strong"]))
        self.assertEqual(r["classification"], "insufficient_info")
        self.assertEqual(r["confidence"], "low")

    def test_partial_sufficiency(self):
        r = classify_howey(_factors(["strong", "strong", "weak", "unknown"]))
        self.assertEqual(r["evidence_sufficiency"], "partial")


class TestClassifyJurisdiction(unittest.TestCase):
    def test_likely_security(self):
        entries = [{"signal": "security", "hit": True, "matched": []},
                   {"signal": "regime", "hit": True, "matched": []}]
        r = classify_jurisdiction(entries, "香港 SFC")
        self.assertEqual(r["verdict"], "likely_security")

    def test_mixed(self):
        entries = [{"signal": "security", "hit": True, "matched": []},
                   {"signal": "utility", "hit": True, "matched": []}]
        r = classify_jurisdiction(entries, "新加坡 MAS")
        self.assertEqual(r["verdict"], "mixed")

    def test_utility_token(self):
        entries = [{"signal": "utility", "hit": True, "matched": []}]
        r = classify_jurisdiction(entries, "香港 SFC")
        self.assertEqual(r["verdict"], "utility_token")

    def test_payment_token(self):
        entries = [{"signal": "payment", "hit": True, "matched": []}]
        r = classify_jurisdiction(entries, "新加坡 MAS")
        self.assertEqual(r["verdict"], "payment_token")

    def test_insufficient(self):
        entries = [{"signal": "security", "hit": False, "matched": []}]
        r = classify_jurisdiction(entries, "香港 SFC")
        self.assertEqual(r["verdict"], "insufficient_info")


if __name__ == "__main__":
    unittest.main()
