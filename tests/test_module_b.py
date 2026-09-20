"""模块 B 行为锁定测试。

这些测试编码「当前（模块 B 审计时）应有的正确行为」，兼作回归锁定：
- test_b2_consumption_downgrade_target_is_weak：纯消费购买降级目标应为 weak（设计决策，非 absent）。
- test_b4_substring_collision_no_false_downgrade：问题4 预期修复后的行为。
  当前（子串匹配未修复前）'购买服务器硬件' 会因 consumption_context 含 '购买服务'
  而被误降级 → 此测试按"修复后应不降级"编写，当前 FAIL，标 @expectedFailure 记录缺口。

运行方式（仅本文件）：
  python -m unittest tests.test_module_b -v
"""
import unittest

from token_classifier.extractor import load_libraries
from token_classifier.engine import judge_factor


class TestModuleBBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        libs = load_libraries()
        cls.iom = [f for f in libs["howey"] if f["factor"] == "investment_of_money"][0]

    def test_b2_consumption_downgrade_target_is_weak(self):
        # 补强1：纯消费购买（购买 + 消费语境 + 无投资反证）降级目标应为 weak，
        # 而非 absent。设计理由：代币购买确实发生（资金易手），只是主导语义为消费，
        # 故保守地保留 weak 信号（合规工具倾向 over-flag）。
        text = "用户可购买平台代币用于支付平台内的各项服务费，代币仅作消费抵扣用途。"
        r = judge_factor(self.iom, text)
        buy = [m for m in r["matched"] if m["pattern"] == "购买"]
        self.assertTrue(buy, "应命中 购买(strong)")
        buy = buy[0]
        self.assertTrue(buy.get("downgraded"), "消费语境应将 购买 降级")
        self.assertEqual(buy["weight"], "weak", "降级目标应为 weak（设计决策，非 absent）")
        self.assertEqual(r["state"], "weak", "invest 因子状态应为 weak，而非 absent")

    @unittest.expectedFailure
    def test_b4_substring_collision_no_false_downgrade(self):
        # 问题4（纠正3）：consumption_context 含 '购买服务'，经 _ci_in 子串匹配，
        # 会在 '购买服务器/购买服务协议' 等连续子串上误触发 cons_hit，
        # 进而把非代币的 '购买服务器硬件' 中 购买 误降级为 weak。
        # 修复后（消费词做词边界/语义匹配，或移除 '购买服务' 拼接词），
        # '购买服务器硬件'（购买-only、非代币语境）不应触发降级。
        text = "用户购买服务器硬件用于部署节点，不涉及任何代币发行或权益销售。"
        r = judge_factor(self.iom, text)
        buy = [m for m in r["matched"] if m["pattern"] == "购买"]
        self.assertTrue(buy, "应命中 购买(strong)")
        buy = buy[0]
        self.assertFalse(
            buy.get("downgraded"),
            "'购买服务器硬件' 中的 '购买服务' 子串不应触发消费降级",
        )


if __name__ == "__main__":
    unittest.main()


class TestModuleAGA1TwoDimensionFixGuard(unittest.TestCase):
    """G-A1 修复护栏（补强2 / 模块A 补强3 的完整表达）。

    G-A1 架构修复必须**同时**约束两个维度，否则引入回归：
    - 维度1（weight）：只对 absent 指标跳过 negation，避免 B7 的 strong 否定路径被吞。
    - 维度2（semantics）：absent 指标内部按 property / element 分别处理
      （呼应模块A补强3 的 6 property / 8 element 二分）。

    4 条路径锁定：
    A. absent + property + 否定语境（独立使用）→ 修复后跳过 negation → 判 absent（当前 bug，expectedFailure）
    B. absent + element + 否定语境（免费）→ 不跳过，否定后不作为 absent 证据（当前已正确，锁约束）
    C. strong + 否定语境（无需购买，B7）→ 保持现有 negation 逻辑 → absent（当前已正确，锁回归）
    D. absent + property + 无否定语境（独立使用）→ 判 absent（当前已正确，锁回归）
    """

    @classmethod
    def setUpClass(cls):
        libs = load_libraries()
        cls.iom = [f for f in libs["howey"] if f["factor"] == "investment_of_money"][0]
        cls.ce = [f for f in libs["howey"] if f["factor"] == "common_enterprise"][0]

    @unittest.expectedFailure
    def test_ga1_path_a_absent_property_negated_should_be_absent(self):
        # 路径A：absent+property（独立使用）邻句无关否定（无需团队维护）→ 当前被误吞→unknown。
        # 修复后（property 跳过 negation）应判 absent。
        text = "无需团队维护，用户独立使用代币获取服务。"
        r = judge_factor(self.ce, text)
        self.assertEqual(
            r["state"], "absent",
            "absent+property(独立使用) 遇否定语境应跳过 negation 判 absent（修复后行为）",
        )

    def test_ga1_path_b_absent_element_negated_not_absent(self):
        # 路径B：absent+element（免费）在「不免费」中被否定 → 不应被当作 absent 证据。
        # 修复后 element 不跳过 negation，免费否定的命中被丢弃，因子无投资信号 → unknown。
        # 关键护栏：naive「对所有 absent 跳过 negation」会让「我们不免费」误判 absent（免费），
        # 本测试锁死「element 否定不得产生 absent 证据」。
        text = "我们不是免费提供服务，用户需支付对价。"
        r = judge_factor(self.iom, text)
        self.assertEqual(
            r["state"], "unknown",
            "absent+element(免费) 在『不免费』中被否定后，不应作为 absent 证据（因子应 unknown）",
        )

    def test_ga1_path_c_strong_negated_stays_absent_b7(self):
        # 路径C：strong+否定语境（B7「无需购买」）→ 保持现有 negation → absent。
        # 此路径是 B7 依赖的正确行为，修复不得破坏（维度1 weight 约束）。
        text = "用户使用代币参与治理，无需购买即可获得治理权限。"
        r = judge_factor(self.iom, text)
        self.assertEqual(
            r["state"], "absent",
            "strong(购买) 被『无需』否定应维持 absent（B7 正确路径，回归护栏）",
        )

    def test_ga1_path_d_absent_property_no_negation_stays_absent(self):
        # 路径D（对照）：absent+property（独立使用）无否定上下文 → 应判 absent。
        # 确保修复不会破坏无否定语境的 property 判定。
        text = "用户独立使用代币获取服务。"
        r = judge_factor(self.ce, text)
        self.assertEqual(
            r["state"], "absent",
            "absent+property(独立使用) 无否定语境应判 absent（对照，回归护栏）",
        )


class TestModuleBProblem4Systemic(unittest.TestCase):
    """问题4 系统性缺陷锁定（强化1）：consumption_context 全词表子串匹配，无词边界。

    "消费者权益" 是电商/服务类文本高频词，凡 "购买" 与其共现即误触发降级。
    修复后（消费词做词边界/语义匹配，或移除拼接词）不应再误降级。
    """

    @classmethod
    def setUpClass(cls):
        libs = load_libraries()
        cls.iom = [f for f in libs["howey"] if f["factor"] == "investment_of_money"][0]

    @unittest.expectedFailure
    def test_b4_consumer_rights_no_false_downgrade(self):
        # "我们重视消费者权益" 中的 "消费" 子串不应触发消费降级。
        text = "用户购买平台代币，我们重视消费者权益，提供透明的服务。"
        r = judge_factor(self.iom, text)
        buy = [m for m in r["matched"] if m["pattern"] == "购买"]
        self.assertTrue(buy, "应命中 购买(strong)")
        buy = buy[0]
        self.assertFalse(
            buy.get("downgraded"),
            "『消费者权益』中的『消费』子串不应触发购买降级（系统性缺陷，修复后通过）",
        )
