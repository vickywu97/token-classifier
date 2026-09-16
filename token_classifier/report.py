"""报告生成：Markdown（法务版）+ JSON（工程版）。

两份报告均含：分级定性、置信度、依据充分性、逐要素证据，以及
「工具层 + 数据层」双重免责声明。
"""
import json
from datetime import datetime, timezone

from .classifier import JURISDICTION_LABELS

FACTOR_EMOJI = {
    "strong": "✅ strong",
    "weak": "⚠️ weak",
    "absent": "🟢 absent",
    "unknown": "⚪ unknown",
}

VERDICT_LABELS = {
    "likely_security": "🔴 可能构成证券（受证券法规管）",
    "mixed": "🟡 混合信号（兼具证券与实用特征，需进一步事实判断）",
    "payment_token": "🟢 倾向数字支付代币（受支付/服务法规管）",
    "utility_token": "🟢 倾向实用/功能型代币（通常不适用证券法）",
    "regulated_activity": "🟡 涉及受规管活动（如交易所/托管须持牌）",
    "insufficient_info": "⚪ 信息不足无法判定",
}

TOOL_DISCLAIMER = (
    "本工具输出为自动化分析线索，不构成法律意见。最终定性须由执业律师"
    "结合完整事实（发行方式、营销话术、治理结构、实际用途、二级市场安排等）判断。"
)
DATA_DISCLAIMER = (
    "本工具引用的监管框架基于公开信息整理（各事实库附 source_accessed_at 核验日期），"
    "可能滞后于最新执法动态与监管指引，请以各监管机构官方最新发布为准。"
)


def _type_meta(libs, classification):
    for t in libs.get("token_types", []):
        if t["classification"] == classification:
            return t
    return {"label": classification, "emoji": "", "risk": "unknown", "description": ""}


def _factor_row(r):
    if r["matched"]:
        ev = "；".join(f"命中「{m['pattern']}」：{m['evidence']}" for m in r["matched"][:2])
    else:
        ev = "（未从输入中检得明确证据）"
    return f"| {r['name']}（{r['name_en']}） | {FACTOR_EMOJI[r['state']]} | {ev} |"


def build_markdown(token_name, analysis, libs, jurisdictions):
    howey = analysis["howey_summary"]
    meta = _type_meta(libs, howey["classification"])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    jnames = " + ".join(JURISDICTION_LABELS.get(k, k) for k in jurisdictions)

    lines = []
    lines.append(f"# 代币监管定性分析报告\n")
    lines.append(f"**代币名称**：{token_name}")
    lines.append(f"**分析时间**：{now}")
    lines.append(f"**适用法域**：{jnames}\n")

    lines.append("## 综合定性（Howey 视角）\n")
    lines.append(f"{meta.get('emoji','')} **{meta.get('label','')}** （{meta.get('label_en','')}）\n")
    lines.append(f"- 置信度：{howey['confidence']}")
    lines.append(f"- 依据充分性：{howey['evidence_sufficiency']}")
    lines.append(f"- 要素统计：strong {howey['counts']['strong']} / weak {howey['counts']['weak']} / absent {howey['counts']['absent']} / unknown {howey['counts']['unknown']}")
    lines.append(f"- 说明：{meta.get('description','')}\n")

    lines.append("## Howey Test 四要素分析\n")
    lines.append("| 要素 | 判定 | 证据 |")
    lines.append("|------|------|------|")
    for r in analysis["howey_factors"]:
        lines.append(_factor_row(r))
    lines.append("")

    for key in jurisdictions:
        jr = analysis["jurisdictions"].get(key)
        if not jr:
            continue
        lines.append(f"## {jr['jurisdiction']} 分析\n")
        lines.append(f"**判定**：{VERDICT_LABELS.get(jr['verdict'], jr['verdict'])}\n")
        if jr["hits"]:
            for h in jr["hits"]:
                ev = "；".join(f"「{m['pattern']}」：{m['evidence']}" for m in h["matched"][:1])
                lines.append(f"- **{h['topic']}**（{h['framework']}）：命中 {ev}")
                if h.get("notes"):
                    lines.append(f"  - 备注：{h['notes']}")
        else:
            lines.append("- 未检得明确指示性证据，无法形成判定。")
        lines.append("")

    lines.append("## 风险提示\n")
    lines.append(f"- {TOOL_DISCLAIMER}")
    lines.append(f"- {DATA_DISCLAIMER}\n")

    lines.append("## 免责声明\n")
    lines.append("本工具由法律+工程复合背景构建，用于辅助合规自检，不得替代执业律师意见，")
    lines.append("亦不得作为投资、发行或合规决策的唯一依据。")
    return "\n".join(lines)


def build_json(token_name, analysis, libs, jurisdictions):
    howey = analysis["howey_summary"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "token_name": token_name,
        "analyzed_at": now,
        "jurisdictions": jurisdictions,
        "overall": {
            "classification": howey["classification"],
            "confidence": howey["confidence"],
            "evidence_sufficiency": howey["evidence_sufficiency"],
            "counts": howey["counts"],
        },
        "howey_factors": [
            {
                "factor": r["factor"],
                "name": r["name"],
                "name_en": r["name_en"],
                "state": r["state"],
                "evidence": [m["evidence"] for m in r["matched"]],
            }
            for r in analysis["howey_factors"]
        ],
        "jurisdiction_analysis": {
            key: {
                "jurisdiction": jr["jurisdiction"],
                "verdict": jr["verdict"],
                "signals": jr["signals"],
                "hits": [
                    {"topic": h["topic"], "framework": h["framework"], "evidence": [m["evidence"] for m in h["matched"]]}
                    for h in jr["hits"]
                ],
            }
            for key, jr in analysis["jurisdictions"].items()
        },
        "disclaimers": {
            "tool": TOOL_DISCLAIMER,
            "data": DATA_DISCLAIMER,
        },
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
