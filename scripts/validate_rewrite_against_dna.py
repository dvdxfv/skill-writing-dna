#!/usr/bin/env python3
"""
Validate a rewritten draft against a Writing DNA profile.

This script is a deterministic quality anchor for the third confirmation point.
It reports alignment signals only; it never rewrites the text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_slop_dict import detect_slop  # noqa: E402


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_json(path: str | Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?\n]+", clean_markdown(text))
    return [part.strip() for part in parts if len(part.strip()) > 3]


def sentence_alignment(text: str, dna: dict) -> dict[str, Any]:
    sentences = split_sentences(text)
    lengths = [len(s) for s in sentences]
    avg = round(sum(lengths) / len(lengths), 1) if lengths else 0.0
    short_ratio = round(sum(1 for n in lengths if n <= 15) / len(lengths), 3) if lengths else 0.0

    sf = dna.get("sentence_features", {}) if isinstance(dna, dict) else {}
    target = sf.get("avg_length_chars") or sf.get("avg_length") or 0
    deviation = None
    status = "unknown"
    if target:
        deviation = round((avg - float(target)) / max(float(target), 1.0), 3)
        status = "ok" if abs(deviation) <= 0.2 else "off"

    return {
        "sentence_count": len(sentences),
        "avg_length_chars": avg,
        "target_avg_length_chars": target or None,
        "avg_length_deviation_ratio": deviation,
        "short_sentence_ratio": short_ratio,
        "status": status,
    }


def signature_alignment(text: str, dna: dict) -> dict[str, Any]:
    signatures = dna.get("signature_phrases", []) if isinstance(dna, dict) else []
    signatures = [s for s in signatures if isinstance(s, str) and s.strip()]
    matched = [s for s in signatures if s in text]
    missing = [s for s in signatures if s not in matched]
    return {
        "total": len(signatures),
        "matched": matched,
        "missing": missing,
        "coverage_ratio": round(len(matched) / max(len(signatures), 1), 3) if signatures else None,
        "suggested_candidates": missing[:5],
    }


def blacklist_residuals(text: str, dna: dict) -> dict[str, Any]:
    blacklist = dna.get("blacklist_phrases", []) if isinstance(dna, dict) else []
    hits = []
    for phrase in blacklist:
        if not isinstance(phrase, str) or not phrase:
            continue
        count = text.count(phrase)
        if count:
            hits.append({"phrase": phrase, "count": count})
    return {"hit_count": sum(item["count"] for item in hits), "hits": hits}


def opener_alignment(text: str, dna: dict) -> dict[str, Any]:
    sentences = split_sentences(text)
    first = sentences[0] if sentences else ""
    openers = dna.get("openers", []) if isinstance(dna, dict) else []
    openers = [o for o in openers if isinstance(o, str) and o.strip()]
    if not first or not openers:
        return {"status": "unknown", "first_sentence": first, "best_match": None, "score": None}

    def prefix_score(a: str, b: str) -> float:
        limit = min(len(a), len(b), 20)
        if limit == 0:
            return 0.0
        same = 0
        for i in range(limit):
            if a[i] != b[i]:
                break
            same += 1
        return same / limit

    best = max(openers, key=lambda opener: prefix_score(first, opener))
    score = round(prefix_score(first, best), 3)
    return {
        "status": "ok" if score >= 0.35 else "review",
        "first_sentence": first[:80],
        "best_match": best[:80],
        "score": score,
    }


def skipped_rule_summary(debug: dict) -> dict[str, Any]:
    skipped = debug.get("skipped_dna_rules", {}) if isinstance(debug, dict) else {}
    return {
        "downgraded": skipped.get("downgraded", []),
        "not_applied": skipped.get("not_applied", []),
        "applied_uncertain_candidates": skipped.get("applied_uncertain_candidates", []),
    }


def validate_rewrite(rewritten: str, dna: dict, debug: dict | None = None) -> dict[str, Any]:
    debug = debug or {}
    slop = detect_slop(rewritten)
    slop_hit_count = len(slop.get("hits", [])) + len(slop.get("combo_hits", [])) + len(slop.get("pattern_hits", []))
    return {
        "schema_version": "1.0",
        "sentence_alignment": sentence_alignment(rewritten, dna),
        "signature_alignment": signature_alignment(rewritten, dna),
        "blacklist_residuals": blacklist_residuals(rewritten, dna),
        "ai_slop_residuals": {
            "score": slop["score"],
            "hit_count": slop.get("total_hits_count", slop_hit_count),
        },
        "opener_alignment": opener_alignment(rewritten, dna),
        "skipped_rules": skipped_rule_summary(debug),
    }


def build_markdown_report(validation: dict) -> str:
    sent = validation["sentence_alignment"]
    sig = validation["signature_alignment"]
    bl = validation["blacklist_residuals"]
    slop = validation["ai_slop_residuals"]
    opener = validation["opener_alignment"]
    skipped = validation["skipped_rules"]

    lines = ["# DNA 对齐验证报告\n"]
    lines.append("## 核心指标\n")
    lines.append("| 指标 | 结果 |")
    lines.append("|:---|:---|")
    lines.append(
        f"| 句长偏差 | 平均 {sent['avg_length_chars']} 字 / 目标 {sent['target_avg_length_chars'] or '未知'} / 状态 {sent['status']} |"
    )
    lines.append(f"| 签名表达命中 | {len(sig['matched'])}/{sig['total']} |")
    lines.append(f"| 黑名单残留 | {bl['hit_count']} 处 |")
    lines.append(f"| AI 味残留 | 分数 {slop['score']} / 命中 {slop['hit_count']} |")
    lines.append(f"| 开头模式 | {opener['status']} / 匹配分 {opener['score'] if opener['score'] is not None else '未知'} |\n")

    if sig["matched"]:
        lines.append("## 已自然命中的签名表达\n")
        lines.extend(f"- {item}" for item in sig["matched"])
        lines.append("")
    if sig["suggested_candidates"]:
        lines.append("## 可作为二次改写参考的候选表达\n")
        lines.extend(f"- {item}" for item in sig["suggested_candidates"])
        lines.append("")
    if bl["hits"]:
        lines.append("## 黑名单残留\n")
        lines.extend(f"- {item['phrase']}：{item['count']} 次" for item in bl["hits"])
        lines.append("")
    if skipped["downgraded"] or skipped["not_applied"] or skipped["applied_uncertain_candidates"]:
        lines.append("## 未应用 / 降权说明\n")
        if skipped["downgraded"]:
            lines.append(f"- 降权参考：{', '.join(map(str, skipped['downgraded']))}")
        if skipped["not_applied"]:
            lines.append(f"- 本次未应用：{', '.join(map(str, skipped['not_applied']))}")
        if skipped["applied_uncertain_candidates"]:
            lines.append(f"- 已命中但需人工确认：{', '.join(map(str, skipped['applied_uncertain_candidates']))}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate rewritten text against a DNA profile.")
    parser.add_argument("--rewritten", required=True, help="Rewritten markdown/text file")
    parser.add_argument("--dna", required=True, help="DNA profile JSON")
    parser.add_argument("--debug-json", help="Optional rewrite_debug.json")
    parser.add_argument("--output-json", required=True, help="Validation JSON output")
    parser.add_argument("--output-md", help="Optional Markdown report output")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    rewritten = load_text(args.rewritten)
    dna = load_json(args.dna)
    debug = load_json(args.debug_json)
    validation = validate_rewrite(rewritten, dna, debug)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(build_markdown_report(validation), encoding="utf-8")

    print(f"DNA alignment validation written to: {output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
