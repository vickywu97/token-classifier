import unittest

from token_classifier.extractor import load_libraries
from token_classifier.engine import judge_factor, judge_jurisdiction

LIBS = load_libraries()


class TestJudgeFactor(unittest.TestCase):
    def setUp(self):
        self.inv = LIBS["howey"][0]  # investment_of_money

    def test_strong(self):
        r = judge_factor(self.inv, "用户以 ETH 购买代币")
        self.assertEqual(r["state"], "strong")

    def test_weak(self):
        r = judge_factor(self.inv, "用户质押代币获得奖励")
        self.assertEqual(r["state"], "weak")

    def test_absent(self):
        r = judge_factor(self.inv, "用户通过空投免费获得代币")
        self.assertEqual(r["state"], "absent")

    def test_unknown(self):
        r = judge_factor(self.inv, "此段落描述项目的技术架构与节点部署方案")
        self.assertEqual(r["state"], "unknown")

    def test_strong_dominates_absent(self):
        # 既有购买又有空投：strong 应优先于 absent
        r = judge_factor(self.inv, "用户先购买，后又获空投奖励")
        self.assertEqual(r["state"], "strong")

    def test_evidence_attributed(self):
        r = judge_factor(self.inv, "用户购买代币")
        self.assertTrue(r["matched"])
        self.assertIn("购买", r["matched"][0]["evidence"])


class TestJudgeJurisdiction(unittest.TestCase):
    def test_hk_security_hit(self):
        results = judge_jurisdiction(LIBS["hk_sfc"], "该代币赋予持有人股权与分红权")
        hits = [r for r in results if r["hit"]]
        self.assertTrue(any(r["signal"] == "security" for r in hits))

    def test_no_false_hit(self):
        results = judge_jurisdiction(LIBS["hk_sfc"], "这是一段无关描述")
        self.assertFalse(any(r["hit"] for r in results))


if __name__ == "__main__":
    unittest.main()
