"""逐要素判定引擎。

对每个 Howey 要素 / 每个法域检查项独立判定，产出四态结果
（strong / weak / absent / unknown）并附证据片段。
判定纯基于关键词命中，零外部依赖、可复现。
"""
from .extractor import scan_indicators


def judge_factor(factor_entry, text):
    """判定单个 Howey 要素，返回四态结果 + 命中证据。

    状态优先级：strong > weak > absent > unknown。
    absent 类指标（如「空投」「免费」）仅在该要素无任何 strong/weak 命中时生效，
    避免「既购买了又空投」这类混合文本被错误判为 absent。
    """
    matched = scan_indicators(text, factor_entry.get("indicators", []))
    # 否定语境命中的 strong/weak 不计入正面证据，仅负向（被明示否定的要素视为 absent）
    pos = [m for m in matched if not m.get("negated")]
    neg = [m for m in matched if m.get("negated")]
    has_strong = any(m["weight"] == "strong" for m in pos)
    has_weak = any(m["weight"] == "weak" for m in pos)
    has_absent = any(m["weight"] == "absent" for m in pos)
    has_negated_strong_weak = any(m["weight"] in ("strong", "weak") for m in neg)

    if has_strong:
        state = "strong"
    elif has_weak:
        state = "weak"
    elif has_negated_strong_weak or has_absent:
        state = "absent"
    else:
        state = "unknown"

    return {
        "factor": factor_entry["factor"],
        "name": factor_entry.get("name", ""),
        "name_en": factor_entry.get("name_en", ""),
        "question": factor_entry.get("question", ""),
        "state": state,
        "matched": matched,
        "dispute_note": factor_entry.get("dispute_note", ""),
    }


def judge_jurisdiction(entries, text):
    """判定一个法域的多个检查项，返回每项命中情况（含 signal 标签）。"""
    results = []
    for entry in entries:
        matched = scan_indicators(text, entry.get("indicators", []))
        results.append({
            "id": entry.get("id", ""),
            "topic": entry.get("topic", ""),
            "topic_en": entry.get("topic_en", ""),
            "framework": entry.get("framework", ""),
            "signal": entry.get("signal", ""),
            "criteria": entry.get("criteria", ""),
            "notes": entry.get("notes", ""),
            "source_url": entry.get("source_url", ""),
            "matched": matched,
            "hit": len(matched) > 0,
        })
    return results
