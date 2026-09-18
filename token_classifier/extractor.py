"""事实提取器。

从代币机制描述（白皮书摘要 / 代币经济学 / 问卷填写）中提取关键事实，
对每条指标命中返回「证据片段」，供判定引擎与报告使用。
纯标准库实现，离线可用。
"""
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_libraries(data_dir=DATA_DIR):
    return {
        "howey": load_jsonl(os.path.join(data_dir, "howey_factors.jsonl")),
        "hk_sfc": load_jsonl(os.path.join(data_dir, "jurisdictions", "hk_sfc.jsonl")),
        "sg_mas": load_jsonl(os.path.join(data_dir, "jurisdictions", "sg_mas.jsonl")),
        "us_sec": load_jsonl(os.path.join(data_dir, "jurisdictions", "us_sec.jsonl")),
        "eu_mica": load_jsonl(os.path.join(data_dir, "jurisdictions", "eu_mica.jsonl")),
        "token_types": load_jsonl(os.path.join(data_dir, "token_types.jsonl")),
    }


def split_paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    if not parts:
        parts = [text.strip()] if text.strip() else []
    return parts


# 否定语境标记：命中词前一小窗内出现这些词，则该命中视为被否定（要素明示缺失）。
NEGATION_MARKERS_CN = [
    "不", "无", "没有", "未", "非", "并非", "不构成", "不提供", "不保证", "不用于",
    "不代表", "不视为", "不存在", "免", "禁止", "不会", "不得", "不承诺", "不向",
]
# 英文否定标记采用词边界正则，避免 "no" 误命中 "token" 之类。
NEGATION_MARKERS_EN = [
    r"\bno\b", r"\bnot\b", r"\bwithout\b", r"\bnever\b", r"\bfree of\b",
    r"\bdoesn'?t\b", r"\bdon'?t\b", r"\bisn'?t\b", r"\baren'?t\b", r"\bwon'?t\b",
    r"\bcannot\b", r"\bcan'?t\b", r"\bnor\b", r"\bexcept\b", r"\bexcluding\b",
    r"\babsent\b", r"\bno\b", r"\bnot\b",
]


def _is_ascii(s):
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _ci_in(haystack, needle):
    """ASCII 模式大小写不敏感匹配；中文/混合模式精确匹配。"""
    if _is_ascii(needle):
        return needle.lower() in haystack.lower()
    return needle in haystack


def _ci_find(haystack, needle):
    if _is_ascii(needle):
        return haystack.lower().find(needle.lower())
    return haystack.find(needle)


def in_negation_context(text, match_start, window=16):
    """判断 match_start 之前的 window 字内是否出现否定标记。"""
    left = text[max(0, match_start - window): match_start]
    for m in NEGATION_MARKERS_CN:
        if m in left:
            return True
    left_l = left.lower()
    for m in NEGATION_MARKERS_EN:
        if re.search(m, left_l):
            return True
    return False


def find_evidence(text, pattern, window=20):
    """在文本中定位 pattern，返回带上下文的证据片段；未命中返回 None。

    改进点（v1.2）：
    - 优先在「非 Markdown 标题」的段落中定位，避免把标题误当作证据片段来源；
    - ASCII 模式大小写不敏感（"Profits" / "profits" 均可命中）；
    - 返回前将内部空白（含换行）压缩为单个空格，避免破坏 Markdown 表格渲染；
    - 片段长度由 window 控制（命中词前后各约 window 字），避免整段原文。
    """
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    # 优先选择非标题段落（标题以 # 开头）
    candidates = [p for p in paragraphs if _ci_in(p, pattern) and not p.startswith("#")]
    target = candidates[0] if candidates else next(
        (p for p in paragraphs if _ci_in(p, pattern)), None
    )
    if target is None:
        return None
    idx = _ci_find(target, pattern)
    if idx < 0:
        return None
    start = max(0, idx - window)
    end = min(len(target), idx + len(pattern) + window)
    snippet = target[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(target):
        snippet = snippet + "…"
    # 压缩内部空白（含换行）为单空格，防止破坏 Markdown 表格
    snippet = " ".join(snippet.split())
    return snippet.strip()


def scan_indicators(text, indicators):
    """扫描一组指标，返回命中列表（pattern / weight / evidence / negated）。

    兼容两种格式：字典 {"pattern", "weight"} 或纯字符串（视为 weight=strong）。
    每个命中附带 negated 标记：若命中词前一小窗内出现否定语境（如「无收益承诺」
    「不构成投资」），则 negated=True，供判定引擎抑制该命中、避免误判 strong/weak。
    """
    matched = []
    for ind in indicators:
        if isinstance(ind, str):
            pattern, weight = ind, "strong"
        else:
            pattern, weight = ind["pattern"], ind["weight"]
        ev = find_evidence(text, pattern)
        if ev is None:
            continue
        # 重新定位命中在全文中的绝对偏移，用于否定语境检测
        abs_idx = text.find(pattern) if not _is_ascii(pattern) else text.lower().find(pattern.lower())
        if abs_idx < 0:
            # 退化为逐段定位
            for p in re.split(r"\n+", text):
                j = _ci_find(p, pattern)
                if j >= 0:
                    abs_idx = text.find(p) + j
                    break
        negated = abs_idx >= 0 and in_negation_context(text, abs_idx, window=16)
        matched.append({
            "pattern": pattern,
            "weight": weight,
            "evidence": ev,
            "negated": negated,
        })
    return matched
