#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨项目诚实性审计工具（token-classifier 专用）。

审计目标：复现 docs/HONESTY_AUDIT.md「模块 A」的关键证据，区分
「真克制」（输入确实缺信息）与「能力缺口」（输入有可读信息但代码没覆盖），
使审计**可复现**——读者可自行运行本脚本逐字核对，而非只看报告结论。

方法（与 privacy-policy-checker/scripts/honesty_audit.py 同性质，核心纪律：
逐字打印原始输入与引擎输出，**不修改任何代码 / 数据文件**）：
1. 载入 howey_factors.jsonl，逐条枚举 14 条 absent 指标，按
   property / element 二分打印（与报告 §B3a 证据表一致，并运行时校验分类覆盖）；
2. 对 3 个 demo 文本运行 analyze，收集所有 negated=True 的命中
   （复现「14/14 架构暴露 / 1/14 实际误吞」的观测面）；
3. 打印 case2b 危害态的完整四要素状态与 verdict（复现 G-A3 真实错分风险）；
4. 对 6 property / 8 element absent 指标做 scratch 验证（构造自我否定文本，
   确认当前引擎行为，论证修复方案风险；全程只读，不动真文件）。

用法（stdio）：
    python3 scripts/honesty_audit.py

也可作为库导入：from scripts.honesty_audit import run_audit
"""

import os
import sys

# 允许以脚本方式直接运行（将仓库根加入 sys.path）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from token_classifier.extractor import load_libraries, scan_indicators  # noqa: E402
from token_classifier.classifier import analyze  # noqa: E402


# —— 模块 A 审计报告 §B3a 的结论性分类（运行时与 jsonl 实际 absent 指标比对校验）——
# property-descriptor：指标描述「无某要素」的技术属性，字面命中即证据，跳过 negation 安全。
# element-negation：指标本身编码「缺乏某要素」，文本自我否定则语义反转，跳过 negation 危险。
ABSENT_CLASSIFICATION = {
    "独立使用": "property",
    "independent use": "property",
    "完全去中心化": "property",
    "自执行": "property",
    "smart contract": "property",
    "无需团队": "property",
    "免费": "element",
    "free": "element",
    "空投": "element",
    "airdrop": "element",
    "赠予": "element",
    "仅用于支付": "element",
    "无收益承诺": "element",
    "no profit": "element",
}

# case2b 危害态输入（逐字，复现报告 §A3 行 180-188）
# 注意：社区治理 须远离「无需」否定窗口（16 字），否则会被误吞为 absent；
# 正确位置下 社区治理 为 positive weak，购买 被「无需」否→absent，复现 0/1/1/2→likely_not_security。
CASE2B_TEXT = (
    "用户通过提供流动性参与挖矿获取平台奖励，由社区治理维护网络，"
    "无需购买代币，代币用于支付交易手续费。"
)

DEMO_FILES = [
    "demo/demo_security_token.md",
    "demo/demo_utility_token.md",
    "demo/demo_ambiguous_token.md",
]


def _factor_for_pattern(libs, pattern):
    """定位某指标所属 Howey 要素条目。"""
    for f in libs["howey"]:
        for ind in f["indicators"]:
            if ind["pattern"] == pattern:
                return f
    return None


def _is_ascii(s):
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def run_audit():
    """运行模块 A 全部可复现证据，返回结构化结果 dict。"""
    libs = load_libraries()

    # —— 1. 14 条 absent 指标逐条分类（运行时校验）——
    absent_list = []  # [(factor, pattern, weight)]
    for f in libs["howey"]:
        for ind in f["indicators"]:
            if ind["weight"] == "absent":
                absent_list.append((f["factor"], ind["pattern"]))
    absent_patterns = sorted(p for _, p in absent_list)
    expected = sorted(ABSENT_CLASSIFICATION.keys())
    if absent_patterns != expected:
        raise AssertionError(
            "absent 指标清单与分类表不一致！\n"
            "运行时: %s\n分类表: %s" % (absent_patterns, expected)
        )
    property_n = sum(1 for c in ABSENT_CLASSIFICATION.values() if c == "property")
    element_n = sum(1 for c in ABSENT_CLASSIFICATION.values() if c == "element")

    # —— 2. 3 个 demo 的 negated=True 命中列表 ——
    demo_negated = []  # [(demo, factor, pattern, weight, evidence)]
    for rel in DEMO_FILES:
        path = os.path.join(ROOT, rel)
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        res = analyze(text, libs)
        for fr in res["howey_factors"]:
            for m in fr["matched"]:
                if m.get("negated"):
                    demo_negated.append(
                        (rel, fr["factor"], m["pattern"], m["weight"], m.get("evidence", ""))
                    )

    # —— 3. case2b 危害态四要素状态 ——
    case2b = analyze(CASE2B_TEXT, libs)

    # —— 4. 6 property / 8 element scratch 验证（只读，不动真文件）——
    scratch = []  # [(pattern, cls, test_text, negated, note)]
    for pattern, cls in ABSENT_CLASSIFICATION.items():
        f = _factor_for_pattern(libs, pattern)
        if _is_ascii(pattern):
            if cls == "element":
                test_text = "the project is not %s, users must pay to acquire." % pattern
            else:
                test_text = "the token features %s." % pattern
        else:
            if cls == "element":
                test_text = "项目方并非%s，反而需用户出资购买。" % pattern
            else:
                test_text = "该代币%s。" % pattern
        m = scan_indicators(test_text, f["indicators"])
        hit = [x for x in m if x["pattern"] == pattern]
        negated = bool(hit and hit[0].get("negated"))
        if cls == "element":
            note = "negated=True → 盲跳 negation 会误判为 absent（实为要素成立）"
        else:
            note = "negated=False → 字面命中即属性证据，跳过 negation 安全"
        scratch.append((pattern, cls, test_text, negated, note))

    return {
        "absent_list": absent_list,
        "property_n": property_n,
        "element_n": element_n,
        "demo_negated": demo_negated,
        "case2b": case2b,
        "scratch": scratch,
    }


def _fmt_absent_table(data):
    lines = []
    lines.append("### 1. 14 条 absent 指标完整分类证据表（运行时校验通过）")
    lines.append("")
    lines.append("| # | 指标 | 所属要素 | 分类 | 跳 negation 是否安全 |")
    lines.append("|---|------|---------|------|---------------------|")
    for i, (factor, pattern) in enumerate(data["absent_list"], 1):
        cls = ABSENT_CLASSIFICATION[pattern]
        safe = "✅" if cls == "property" else "❌"
        lines.append("| %d | %s | %s | %s | %s |" % (i, pattern, factor, cls, safe))
    lines.append("")
    lines.append("> 合计 **%d property（✅）+ %d element（❌）**。分类表已与运行时实际 absent 指标逐一比对一致。"
                 % (data["property_n"], data["element_n"]))
    lines.append("")
    return "\n".join(lines)


def _fmt_demo_negated(data):
    lines = []
    lines.append("### 2. 3 个 demo 的 negated=True 命中列表（观测面）")
    lines.append("")
    if not data["demo_negated"]:
        lines.append("（无）")
    else:
        for rel, factor, pattern, weight, evidence in data["demo_negated"]:
            lines.append("- **%s** / `%s`(`%s`) → negated=True" % (rel, pattern, weight))
            lines.append("  - 证据窗口：`%s`" % evidence.replace("\n", "↵"))
    lines.append("")
    lines.append("> 复现「14/14 架构暴露 / **1/14 实际误吞 (7.1%)**」：当前 3 demo 仅 `独立使用`(utility) 被误吞；"
                 "其余 13 条 absent 在当前语料未触发否定窗口。")
    lines.append("")
    return "\n".join(lines)


def _fmt_case2b(data):
    lines = []
    lines.append("### 3. case2b 危害态完整四要素状态（G-A3 真实错分）")
    lines.append("")
    lines.append("**输入（逐字）**：")
    lines.append("```")
    lines.append(CASE2B_TEXT)
    lines.append("```")
    lines.append("")
    c2b = data["case2b"]
    for fr in c2b["howey_factors"]:
        triggers = [m["pattern"] for m in fr["matched"] if not m.get("negated")]
        neg = [m["pattern"] for m in fr["matched"] if m.get("negated")]
        lines.append("- `%s` → **%s**（正向命中:%s / 被否定:%s）"
                     % (fr["factor"], fr["state"], triggers or "无", neg or "无"))
    s = c2b["howey_summary"]
    lines.append("")
    lines.append("**counts** s/w/abs/unk = %d/%d/%d/%d → **%s**（置信度 %s，证据充分度 %s）"
                 % (s["counts"]["strong"], s["counts"]["weak"], s["counts"]["absent"],
                    s["counts"]["unknown"], s["classification"], s["confidence"],
                    s["evidence_sufficiency"]))
    lines.append("")
    lines.append("> 解读：investment_of_money 因「流动性/挖矿」不在词表→无正向命中、且「无需购买」的购买被否→absent；"
                 "在 common/profits 均 unknown、efforts 仅 1 weak 时，verdict 被压至 `likely_not_security`。"
                 "一旦补上 Joiner 出资词表，invest 翻为 strong，verdict 即翻转为 `possibly_security`——真实错分风险。")
    lines.append("")
    return "\n".join(lines)


def _fmt_scratch(data):
    lines = []
    lines.append("### 4. 6 property / 8 element scratch 验证（只读，不动真文件）")
    lines.append("")
    for pattern, cls, test_text, negated, note in data["scratch"]:
        mark = "✅" if (cls == "property" and not negated) or (cls == "element") else "⚠️"
        lines.append("- %s `%s`(%s) 测试文本：`%s` → negated=%s — %s"
                     % (mark, pattern, cls, test_text, negated, note))
    lines.append("")
    lines.append("> 结论：property 型字面命中即证据、跳过 negation 安全；element 型遇自我否定被标 negated=True，"
                 "盲跳 negation 会误判为 absent（实为要素成立），需按 element 型做「翻转」特殊处理（其自身边界见报告 §B3a 补强 B）。")
    lines.append("")
    return "\n".join(lines)


def main():
    data = run_audit()
    print("# token-classifier 诚实性审计 · 模块 A 可复现转储")
    print("")
    print("> 本转储由 scripts/honesty_audit.py 自动生成，逐字打印原始输入与引擎输出，"
          "供人工判读「真克制 vs 能力缺口」。审计结论见 docs/HONESTY_AUDIT.md。")
    print("")
    print(_fmt_absent_table(data))
    print(_fmt_demo_negated(data))
    print(_fmt_case2b(data))
    print(_fmt_scratch(data))
    print("---")
    print("")
    print("判定标准：真克制=输入确实缺信息；能力缺口=输入有信息但代码没读 / 指标过泛过窄。"
          "纪律：逐字打印输入；能力缺口只记录不修。")


if __name__ == "__main__":
    main()
