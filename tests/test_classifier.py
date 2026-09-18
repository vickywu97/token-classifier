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


class TestAccuracyHardening(unittest.TestCase):
    """回归测试：否定语境与英文大小写覆盖，防止误判证券。"""

    def test_negation_explicit_no_security(self):
        libs = load_libraries()
        text = ("本代币仅用于支付平台服务费。无收益承诺，不构成投资，"
                "不用于投资收益，发行方不保证任何回报。团队仅做基础运维。")
        res = analyze(text, libs)
        # 投资资金 / 利润预期 均被否定 → absent
        fac = {f["factor"]: f["state"] for f in res["howey_factors"]}
        self.assertEqual(fac["investment_of_money"], "absent")
        self.assertEqual(fac["expectation_of_profits"], "absent")
        self.assertEqual(res["howey_summary"]["classification"], "likely_not_security")
        self.assertEqual(res["jurisdictions"]["US_SEC"]["verdict"], "likely_not_security")

    def test_english_lowercase_matches(self):
        libs = load_libraries()
        text = "Investors purchase tokens. The Company will develop the ecosystem and investors expect profits."
        res = analyze(text, libs)
        fac = {f["factor"]: f["state"] for f in res["howey_factors"]}
        # purchase / invest 此前因大小写漏判，现已命中
        self.assertIn(fac["investment_of_money"], ("strong", "weak"))
        # 英文不应被否定语境误伤
        matched = [m for f in res["howey_factors"] for m in f["matched"]]
        self.assertFalse(any(m.get("negated") for m in matched))

    def test_negation_flag_attached(self):
        libs = load_libraries()
        text = "无收益承诺，不构成投资"
        res = analyze(text, libs)
        matched = [m for f in res["howey_factors"] for m in f["matched"]]
        negated = [m for m in matched if m.get("negated")]
        self.assertTrue(any(m["pattern"] in ("收益", "投资") for m in negated))


if __name__ == "__main__":
    unittest.main()
