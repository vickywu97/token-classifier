import unittest

from token_classifier.classifier import (
    analyze,
    classify_howey,
    classify_jurisdiction,
    classify_mica,
    _howey_to_sec_verdict,
)
from token_classifier.extractor import load_libraries


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


class TestClassifyMica(unittest.TestCase):
    def _e(self, signal, hit):
        return {"signal": signal, "hit": hit,
                "matched": [{"pattern": "x", "evidence": "y"}] if hit else []}

    def test_security_priority_over_others(self):
        r = classify_mica([self._e("utility", True), self._e("security", True)], "欧盟 MiCA")
        self.assertEqual(r["verdict"], "security_token_outside_miCA")

    def test_emt(self):
        r = classify_mica([self._e("emt", True)], "欧盟 MiCA")
        self.assertEqual(r["verdict"], "e_money_token")

    def test_art(self):
        r = classify_mica([self._e("art", True)], "欧盟 MiCA")
        self.assertEqual(r["verdict"], "asset_referenced_token")

    def test_utility(self):
        r = classify_mica([self._e("utility", True)], "欧盟 MiCA")
        self.assertEqual(r["verdict"], "utility_token")

    def test_insufficient(self):
        r = classify_mica([self._e("security", False)], "欧盟 MiCA")
        self.assertEqual(r["verdict"], "insufficient_info")


class TestHoweyToSec(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(_howey_to_sec_verdict("likely_security"), "likely_security")
        self.assertEqual(_howey_to_sec_verdict("possibly_security"), "possibly_security")
        self.assertEqual(_howey_to_sec_verdict("likely_not_security"), "likely_not_security")
        self.assertEqual(_howey_to_sec_verdict("insufficient_info"), "insufficient_info")
        self.assertEqual(_howey_to_sec_verdict("bogus"), "insufficient_info")


class TestAnalyzeJurisdictions(unittest.TestCase):
    def test_us_sec_and_mica_present(self):
        libs = load_libraries()
        text = "用户以 ETH 认购代币，承诺年化 15% 分红，核心团队负责开发运营，赋予投票权"
        res = analyze(text, libs, ["US_SEC", "EU_MICA", "HK_SFC", "SG_MAS"])
        self.assertIn("US_SEC", res["jurisdictions"])
        self.assertIn("EU_MICA", res["jurisdictions"])
        self.assertEqual(res["jurisdictions"]["US_SEC"]["verdict"], "likely_security")
        self.assertEqual(res["jurisdictions"]["EU_MICA"]["verdict"], "security_token_outside_miCA")

    def test_utility_maps_to_not_security_and_utility(self):
        libs = load_libraries()
        text = "代币完全免费获取，网络完全去中心化，由智能合约自动执行，仅用于支付平台内存储服务"
        res = analyze(text, libs, ["US_SEC", "EU_MICA"])
        self.assertEqual(res["jurisdictions"]["US_SEC"]["verdict"], "likely_not_security")
        self.assertEqual(res["jurisdictions"]["EU_MICA"]["verdict"], "utility_token")


if __name__ == "__main__":
    unittest.main()
