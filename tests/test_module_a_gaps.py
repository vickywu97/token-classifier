"""模块 A 能力缺口的目标行为测试（G-A1）。

这些测试编码「修复后应有的正确行为」，作为缺口的回归锁定。
- test_absent_independent_use_no_neg_context：控制用例，当前代码即通过。
- test_absent_independent_use_with_neg_context：目标用例，当前（架构修复前）代码
  会因 in_negation_context 把「独立使用」误吞（上一句「无需团队维护」里的「无」
  落在 16 字窗口内）→ 此测试在修复前 FAIL，记录 G-A1 缺口；
  架构修复（absent 指标跳过 negation 过滤）后应通过。

注意（Doubt 3 修正）：目标用例标 @unittest.expectedFailure —— 它记录的是
「修复前应 FAIL 的已知缺口」，不是真实失败。expectedFailure 下 CI 保持全绿；
架构修复后删除该装饰器，测试应转为正常通过。

运行方式（仅本文件，避免污染主套件）：
  python -m unittest tests.test_module_a_gaps -v
"""
import unittest

from token_classifier.extractor import load_libraries, scan_indicators


class TestModuleAGapAbsentNegation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        libs = load_libraries()
        cls.ce = [f for f in libs["howey"] if f["factor"] == "common_enterprise"][0]

    def test_absent_independent_use_no_neg_context(self):
        # 控制用例：独立使用 上方无否定词 → 应命中 absent（当前代码即通过）
        text = "用户独立使用代币获取服务。"
        m = scan_indicators(text, self.ce["indicators"])
        hit = [x for x in m if x["pattern"] == "独立使用" and x["weight"] == "absent"]
        self.assertTrue(hit, "独立使用 应被识别为 absent 命中")
        self.assertFalse(hit[0]["negated"], "无否定上文时不应误标 negated")

    @unittest.expectedFailure  # 记录 G-A1 已知缺口：修复前此用例应 FAIL；架构修复后删除装饰器
    def test_absent_independent_use_with_neg_context(self):
        # 目标用例：独立使用 上方有无关否定词（无需团队维护）亦应命中 absent。
        # 修复前 FAIL（记录 G-A1，故标 expectedFailure，不破坏 CI）；架构修复后通过。
        text = "无需团队维护，用户独立使用代币获取服务。"
        m = scan_indicators(text, self.ce["indicators"])
        hit = [x for x in m if x["pattern"] == "独立使用" and x["weight"] == "absent"]
        self.assertTrue(
            hit,
            "独立使用 即便上方有无关否定上下文，也应命中 absent（absent 指标应跳过 negation 过滤）",
        )
        if hit:
            self.assertFalse(
                hit[0]["negated"],
                "absent 指标不应被 negation 上下文误吞（架构修复后通过）",
            )


if __name__ == "__main__":
    unittest.main()
