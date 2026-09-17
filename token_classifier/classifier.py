"""综合定性：Howey 四要素聚合 + 分法域判定 + 顶层编排。

设计原则：只输出「分级定性 + 逐要素证据 + 置信度」，绝不输出二元法律结论。
多法域分别判定，不做统一全球结论。
"""
from .engine import judge_factor, judge_jurisdiction


def classify_howey(factor_results):
    states = [r["state"] for r in factor_results]
    strong = states.count("strong")
    weak = states.count("weak")
    unknown = states.count("unknown")
    absent = states.count("absent")

    if unknown >= 3:
        cls = "insufficient_info"
    elif strong >= 3:
        cls = "likely_security"
    elif strong == 2 and weak == 2:
        cls = "possibly_security"
    elif strong + weak <= 1:
        cls = "likely_not_security"
    else:
        cls = "possibly_security"

    if unknown == 0:
        confidence = "high" if (strong >= 3 or absent >= 3) else "medium"
    elif unknown == 1:
        confidence = "medium"
    else:
        confidence = "low"

    sufficiency = "full" if unknown == 0 else ("partial" if unknown <= 2 else "none")

    return {
        "classification": cls,
        "confidence": confidence,
        "evidence_sufficiency": sufficiency,
        "counts": {"strong": strong, "weak": weak, "absent": absent, "unknown": unknown},
    }


def classify_jurisdiction(entries_results, jurisdiction_name):
    signals = {"security": 0, "payment": 0, "utility": 0, "regime": 0}
    hits = [r for r in entries_results if r["hit"]]
    for r in hits:
        signals[r["signal"]] = signals.get(r["signal"], 0) + 1

    if signals["security"] > 0 and signals["utility"] == 0:
        verdict = "likely_security"
    elif signals["security"] > 0 and signals["utility"] > 0:
        verdict = "mixed"
    elif signals["payment"] > 0 and signals["security"] == 0:
        verdict = "payment_token"
    elif signals["utility"] > 0 and signals["security"] == 0 and signals["payment"] == 0:
        verdict = "utility_token"
    elif signals["regime"] > 0:
        verdict = "regulated_activity"
    else:
        verdict = "insufficient_info"

    return {
        "jurisdiction": jurisdiction_name,
        "verdict": verdict,
        "signals": signals,
        "hits": hits,
    }


def classify_mica(entries_results, jurisdiction_name):
    """EU MiCA 分类判定：证券型（MiFID II）/ EMT / ART / 实用型。

    优先级：证券特征 > 单币稳定币(EMT) > 多资产稳定币(ART) > 实用型。
    证券特征命中即落入 MiFID II，不在 MiCA 范围内。
    """
    signals = {"security": 0, "emt": 0, "art": 0, "utility": 0}
    hits = [r for r in entries_results if r["hit"]]
    for r in hits:
        s = r["signal"]
        signals[s] = signals.get(s, 0) + 1

    if signals["security"] > 0:
        verdict = "security_token_outside_miCA"
    elif signals["emt"] > 0:
        verdict = "e_money_token"
    elif signals["art"] > 0:
        verdict = "asset_referenced_token"
    elif signals["utility"] > 0:
        verdict = "utility_token"
    else:
        verdict = "insufficient_info"

    return {
        "jurisdiction": jurisdiction_name,
        "verdict": verdict,
        "method": "mica",
        "signals": signals,
        "hits": hits,
    }


def _howey_to_sec_verdict(howey_classification):
    """SEC 采用 Howey 测试，故美国法域的定性直接由 Howey 综合判定映射。"""
    mapping = {
        "likely_security": "likely_security",
        "possibly_security": "possibly_security",
        "likely_not_security": "likely_not_security",
        "insufficient_info": "insufficient_info",
    }
    return mapping.get(howey_classification, "insufficient_info")


def _signal_counts(entries_results):
    signals = {}
    for r in entries_results:
        if r["hit"]:
            signals[r["signal"]] = signals.get(r["signal"], 0) + 1
    return signals


JURISDICTION_LABELS = {
    "HK_SFC": "香港 SFC",
    "SG_MAS": "新加坡 MAS",
    "US_SEC": "美国 SEC",
    "EU_MICA": "欧盟 MiCA",
}


def analyze(text, libs, jurisdictions=None):
    """顶层编排：逐要素判定 → Howey 综合定性 → 各法域判定。

    返回供报告生成器消费的结构化结果。
    各法域支持三种判定方法（见数据文件 method 字段）：
    - "signal"：基于命中信号的规则（HK SFC / SG MAS 默认）；
    - "howey_derived"：判定由 Howey 综合定性映射（美国 SEC 采用 Howey 测试）；
    - "mica"：欧盟 MiCA 加密资产分类（证券/EMT/ART/实用型）。
    """
    if jurisdictions is None:
        jurisdictions = ["HK_SFC", "SG_MAS", "US_SEC", "EU_MICA"]

    factor_results = [judge_factor(f, text) for f in libs["howey"]]
    howey = classify_howey(factor_results)

    jurisdiction_results = {}
    for key in jurisdictions:
        entries = libs.get(key.lower(), [])
        if not entries:
            continue
        method = entries[0].get("method", "signal") if entries else "signal"
        judged = judge_jurisdiction(entries, text)
        label = JURISDICTION_LABELS.get(key, key)

        if method == "howey_derived":
            jurisdiction_results[key] = {
                "jurisdiction": label,
                "verdict": _howey_to_sec_verdict(howey["classification"]),
                "method": "howey_derived",
                "signals": _signal_counts(judged),
                "hits": [r for r in judged if r["hit"]],
            }
        elif method == "mica":
            jurisdiction_results[key] = classify_mica(judged, label)
        else:
            jurisdiction_results[key] = classify_jurisdiction(judged, label)

    return {
        "howey_factors": factor_results,
        "howey_summary": howey,
        "jurisdictions": jurisdiction_results,
    }
