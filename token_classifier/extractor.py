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
        "token_types": load_jsonl(os.path.join(data_dir, "token_types.jsonl")),
    }


def split_paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    if not parts:
        parts = [text.strip()] if text.strip() else []
    return parts


def find_evidence(text, pattern, window=20):
    """在文本中定位 pattern，返回带上下文的证据片段；未命中返回 None。

    改进点（v1.1，修复报告渲染 bug）：
    - 优先在「非 Markdown 标题」的段落中定位，避免把标题（如「发行与认购」）
      误当作证据片段来源；
    - 返回前将内部空白（含换行）压缩为单个空格，避免破坏 Markdown 表格渲染；
    - 片段长度由 window 控制（命中词前后各约 window 字），避免整段原文。
    """
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    # 优先选择非标题段落（标题以 # 开头）
    candidates = [p for p in paragraphs if pattern in p and not p.startswith("#")]
    target = candidates[0] if candidates else next(
        (p for p in paragraphs if pattern in p), None
    )
    if target is None:
        return None
    idx = target.find(pattern)
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
    """扫描一组指标，返回命中列表（pattern / weight / evidence）。

    兼容两种格式：字典 {"pattern", "weight"} 或纯字符串（视为 weight=strong）。
    """
    matched = []
    for ind in indicators:
        if isinstance(ind, str):
            pattern, weight = ind, "strong"
        else:
            pattern, weight = ind["pattern"], ind["weight"]
        ev = find_evidence(text, pattern)
        if ev is not None:
            matched.append({
                "pattern": pattern,
                "weight": weight,
                "evidence": ev,
            })
    return matched
