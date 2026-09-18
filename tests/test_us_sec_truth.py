"""SEC 框架真值用例（true-value cases）。

针对 us_sec.jsonl 中落地的两条 SEC 2019 框架细则：
- US-SEC-004：发行时网络未功能完备（提示构成投资合同）
- US-SEC-005：发行时功能完备且可立即使用（倾向不构成投资合同）

每个用例都给出「已知正确结论」的具体场景，断言引擎命中/不命中相应条款，
并校验 Howey 综合定性方向与之一致，防止回归。
"""
import os
import unittest

from token_classifier.extractor import load_libraries
from token_classifier.classifier import analyze

_HERE = os.path.dirname(__file__)


def _us_hit_ids(text, libs):
    a = analyze(text, libs)
    return {h["id"] for h in a["jurisdictions"]["US_SEC"]["hits"]}


class TestUSSECTruthCases(unittest.TestCase):
    def setUp(self):
        self.libs = load_libraries()

    def test_sec004_prelaunch_raise_flags_security(self):
        """已知结论：预售且主网未上线、资金用于开发 → 应命中 US-SEC-004 且 Howey 综合为证券。"""
        text = (
            "投资者出资认购项目代币。该项目处于测试网阶段，主网尚未上线，"
            "本轮募集资金将全部用于建设主网与生态开发。代币发行时不可用于任何功能。"
            "团队将负责后续开发与运营，并承诺上线后向持有者进行收益分配、按持有比例分红。"
        )
        hits = _us_hit_ids(text, self.libs)
        self.assertIn("US-SEC-004", hits)
        a = analyze(text, self.libs)
        self.assertEqual(a["howey_summary"]["classification"], "likely_security")

    def test_sec004_not_flagged_when_live(self):
        """已知结论：已上线且可立即使用、完全去中心化 → 不应命中 US-SEC-004，应命中 US-SEC-005。"""
        text = (
            "代币已在主网上线，持有人可立即使用代币支付平台服务费，"
            "网络完全去中心化，不依赖团队持续开发。"
        )
        hits = _us_hit_ids(text, self.libs)
        self.assertNotIn("US-SEC-004", hits)
        self.assertIn("US-SEC-005", hits)

    def test_sec005_utility_scenario(self):
        """已知结论：已上线、可立即兑换使用、无利润承诺 → 命中 US-SEC-005、不命中 US-SEC-004，且 Howey 综合为非证券。"""
        text = (
            "本代币已在主网上线，用户可立即使用其兑换平台内的存储空间，"
            "网络完全去中心化，无利润承诺、无二级市场炒作叙事。"
        )
        hits = _us_hit_ids(text, self.libs)
        self.assertIn("US-SEC-005", hits)
        self.assertNotIn("US-SEC-004", hits)
        a = analyze(text, self.libs)
        self.assertEqual(a["howey_summary"]["classification"], "likely_not_security")

    def test_future_dividend_not_falsely_negated(self):
        """精度回归：『未来上线后按持有比例分红』中的『未来』不应触发否定，利润预期要素须命中（strong）。"""
        text = (
            "投资者出资认购项目代币。该项目处于测试网阶段，主网尚未上线，"
            "募集资金将全部用于建设主网。团队承诺未来上线后按持有比例向持有者分红。"
        )
        a = analyze(text, self.libs)
        states = {f["factor"]: f["state"] for f in a["howey_factors"]}
        # 关键断言：『未来分红』不得因「未」被误判为 absent
        self.assertEqual(states["expectation_of_profits"], "strong")


if __name__ == "__main__":
    unittest.main()
