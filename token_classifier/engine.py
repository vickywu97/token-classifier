"""逐要素判定引擎。

对每个 Howey 要素 / 每个法域检查项独立判定，产出四态结果
（strong / weak / absent / unknown）并附证据片段。
判定纯基于关键词命中，零外部依赖、可复现。
"""
from .extractor import scan_indicators, _ci_in


def judge_factor(factor_entry, text):
    """判定单个 Howey 要素，返回四态结果 + 命中证据。

    状态优先级：strong > weak > absent > unknown。
    absent 类指标（如「空投」「免费」）仅在该要素无任何 strong/weak 命中时生效，
    避免「既购买了又空投」这类混合文本被错误判为 absent。

    投资资金要素（investment_of_money）附加「消费语境降级」逻辑：
    - 仅对购买类 strong 指标（购买/buy/purchase）生效；
    - 若全文同时命中消费语境词（支付/服务费/消费…）且**无**投资语境反证词
      （投资/认购/分红/收益…），则该命中降为 weak（消费对价 ≠ Howey 投资资金）；
    - 若消费语境词与反证词**同时**命中，则保持 strong 并标注「双重语境」，
      交人工结合全案事实判断，避免一刀切。
    """
    matched = scan_indicators(text, factor_entry.get("indicators", []))
    # 否定语境命中的 strong/weak 不计入正面证据，仅负向（被明示否定的要素视为 absent）
    pos = [m for m in matched if not m.get("negated")]
    neg = [m for m in matched if m.get("negated")]
    annotations = []

    if factor_entry.get("factor") == "investment_of_money":
        purchase_set = {p.lower() for p in factor_entry.get("purchase_indicators", [])}
        cons_words = factor_entry.get("consumption_context", [])
        rebut_words = factor_entry.get("investment_rebuttal", [])
        cons_hit = any(_ci_in(text, w) for w in cons_words)
        rebut_hit = any(_ci_in(text, w) for w in rebut_words)
        for m in pos:
            if m["weight"] == "strong" and m["pattern"].lower() in purchase_set:
                if cons_hit and not rebut_hit:
                    m["weight"] = "weak"
                    m["downgraded"] = True
                    annotations.append(
                        "（降级理由：该「%s」用于支付平台服务费/消费对价，属消费行为，"
                        "非 Howey 意义上的投资资金）" % m["pattern"]
                    )
                elif cons_hit and rebut_hit:
                    m["dual_context"] = True
                    annotations.append(
                        "（双重语境：该「%s」兼具消费支付与投资收益表述，保持 strong，"
                        "须结合全案事实判断）" % m["pattern"]
                    )

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
        "annotations": annotations,
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
