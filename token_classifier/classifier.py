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


JURISDICTION_LABELS = {
    "HK_SFC": "香港 SFC",
    "SG_MAS": "新加坡 MAS",
}


def analyze(text, libs, jurisdictions=None):
    """顶层编排：逐要素判定 → Howey 综合定性 → 各法域判定。

    返回供报告生成器消费的结构化结果。
    """
    if jurisdictions is None:
        jurisdictions = ["HK_SFC", "SG_MAS"]

    factor_results = [judge_factor(f, text) for f in libs["howey"]]
    howey = classify_howey(factor_results)

    jurisdiction_results = {}
    for key in jurisdictions:
        entries = libs.get(key.lower(), [])
        if not entries:
            continue
        judged = judge_jurisdiction(entries, text)
        jurisdiction_results[key] = classify_jurisdiction(judged, JURISDICTION_LABELS.get(key, key))

    return {
        "howey_factors": factor_results,
        "howey_summary": howey,
        "jurisdictions": jurisdiction_results,
    }
