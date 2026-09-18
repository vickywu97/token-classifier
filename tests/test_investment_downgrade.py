import unittest

from token_classifier.extractor import load_libraries
from token_classifier.classifier import analyze


class TestInvestmentConsumptionDowngrade(unittest.TestCase):
    """投资资金要素：消费语境自动降级逻辑回归测试（token 1.3）。

    规则：购买类 strong 指标（购买/buy/purchase）在「消费语境命中 且 无投资语境反证」
    时降为 weak；若消费语境与反证词同时命中，则保持 strong 并标注双重语境。
    """

    def setUp(self):
        self.libs = load_libraries()

    def _iom(self, text):
        res = analyze(text, self.libs)
        return next(r for r in res["howey_factors"] if r["factor"] == "investment_of_money")

    def test_pure_consumption_downgrade(self):
        # 购买用于支付平台服务费，且无投资语境反证词 → 降为 weak
        text = (
            "用户可购买平台积分，用于支付平台内的存储服务费，"
            "代币仅作为功能凭证，不赋予任何财务权利。"
        )
        r = self._iom(text)
        self.assertEqual(r["state"], "weak")
        self.assertTrue(any(m.get("downgraded") for m in r["matched"]))
        self.assertTrue(any("降级" in a for a in r["annotations"]))

    def test_dual_context_keeps_strong(self):
        # EcoToken 类：购买（消费）与分红/增值（投资反证）并存 → 保持 strong + 双重语境标注
        text = (
            "用户可购买 ECO 用于支付平台数据服务费；白皮书称持币享受生态增值红利，"
            "并赋予持有人对生态收益的分红权与投票权。"
        )
        r = self._iom(text)
        self.assertEqual(r["state"], "strong")
        self.assertTrue(any(m.get("dual_context") for m in r["matched"]))
        self.assertTrue(any("双重语境" in a for a in r["annotations"]))

    def test_pure_investment_keeps_strong(self):
        # 认购 + 分红，无「购买」类消费购买词 → 保持 strong，不降级、不标双重语境
        text = (
            "用户以 ETH 认购 XCT，白皮书承诺按持有比例年度分红，"
            "预期年化收益约 15%。"
        )
        r = self._iom(text)
        self.assertEqual(r["state"], "strong")
        self.assertFalse(any(m.get("downgraded") for m in r["matched"]))
        self.assertFalse(any(m.get("dual_context") for m in r["matched"]))


if __name__ == "__main__":
    unittest.main()
