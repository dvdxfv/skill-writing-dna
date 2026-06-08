#!/usr/bin/env python3
"""
Generate a human-readable comparison report from original draft, rewritten draft,
DNA profile, and debug artifacts.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_rewrite_against_dna import validate_rewrite


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_json_safe(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def build_report(original: str, rewritten: str, dna: dict, debug: dict) -> str:
    stats = debug.get("stats", {})
    slop = debug.get("ai_slop", {})
    changes = debug.get("changes", {})
    rules = debug.get("dna_rules_applied", [])
    skipped = debug.get("skipped_dna_rules", {})

    lines = []
    lines.append("# DNA 改写对比报告\n")
    lines.append(f"**DNA来源**: {dna.get('user_name') or dna.get('author', '未知')}\n")

    lines.append("## 📊 核心指标\n")
    lines.append("| 指标 | 改写前 | 改写后 |")
    lines.append("|:---|:---:|:---:|")
    lines.append(f"| 字数 | {stats.get('original_char_count', '?')} | {stats.get('rewritten_char_count', '?')} |")
    before_score = slop.get("before", {}).get("score", "?")
    after_score = slop.get("after", {}).get("score", "?")
    lines.append(f"| AI味分数 | {before_score} | {after_score} |")
    before_hits = slop.get("before", {}).get("hit_count", "?")
    after_hits = slop.get("after", {}).get("hit_count", "?")
    lines.append(f"| 套话命中数 | {before_hits} | {after_hits} |")
    ratio = stats.get("char_change_ratio", "?")
    lines.append(f"| 字数变化率 | — | {ratio}x |\n")

    removed_bl = changes.get("blacklist_phrases_removed", [])
    removed_conn = changes.get("ai_connectors_removed", [])
    matched_signatures = changes.get("signature_phrases_matched", changes.get("signature_phrases_injected", []))
    signature_suggestions = changes.get("signature_phrase_suggestions", [])

    lines.append("## ✏️ 改动明细\n")

    if removed_bl:
        lines.append("### 清除的黑名单词\n")
        for item in removed_bl[:20]:
            action = item.get("action", "deleted")
            if action == "replaced":
                lines.append(f"- **{item['phrase']}** (出现{item['removed_count']}次) → `{item.get('replacement', '')}`")
            elif action == "deferred":
                lines.append(f"- **{item['phrase']}** (出现{item['removed_count']}次) → 需语义改写，未机械删除")
            else:
                lines.append(f"- **{item['phrase']}** (出现{item['removed_count']}次)")
        lines.append("")

    if removed_conn:
        lines.append("### 替换的AI连接词\n")
        for c in removed_conn:
            lines.append(f"- `{c}` → 自然过渡")
        lines.append("")

    if matched_signatures:
        lines.append("### 自然命中的签名表达\n")
        for s in matched_signatures:
            lines.append(f"- `{s}`")
        lines.append("")
    if signature_suggestions:
        lines.append("### 可供二次改写参考的候选表达\n")
        for s in signature_suggestions:
            lines.append(f"- `{s}`")
        lines.append("")

    if rules:
        lines.append("## 📋 应用的DNA规则\n")
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. {rule}")
        lines.append("")

    validation = validate_rewrite(rewritten, dna, debug)
    sent = validation["sentence_alignment"]
    sig = validation["signature_alignment"]
    bl = validation["blacklist_residuals"]
    slop_residuals = validation["ai_slop_residuals"]
    opener = validation["opener_alignment"]
    lines.append("## 🧭 DNA 对齐验证\n")
    lines.append("| 指标 | 结果 |")
    lines.append("|:---|:---|")
    lines.append(
        f"| 句长偏差 | 平均 {sent['avg_length_chars']} 字 / 目标 {sent['target_avg_length_chars'] or '未知'} / 状态 {sent['status']} |"
    )
    lines.append(f"| 签名表达命中 | {len(sig['matched'])}/{sig['total']} |")
    lines.append(f"| 黑名单残留 | {bl['hit_count']} 处 |")
    lines.append(f"| AI 味残留 | 分数 {slop_residuals['score']} / 命中 {slop_residuals['hit_count']} |")
    lines.append(f"| 开头模式 | {opener['status']} / 匹配分 {opener['score'] if opener['score'] is not None else '未知'} |\n")

    downgraded = skipped.get("downgraded", [])
    not_applied = skipped.get("not_applied", [])
    applied_uncertain = skipped.get("applied_uncertain_candidates", [])
    if downgraded or not_applied or applied_uncertain:
        lines.append("## ⏭️ 跳过的规则 / 未应用 / 降权说明\n")
        if downgraded:
            lines.append("**降级特征（不稳定，仅作参考，不等同于本次规则没应用）:**\n")
            for d in downgraded:
                lines.append(f"- {d}")
            lines.append("")
        if not_applied:
            lines.append("**本次未应用的不确定候选（样本不足或不适合当前语境）:**\n")
            for n in not_applied:
                lines.append(f"- {n}")
            lines.append("")
        if applied_uncertain:
            lines.append("**已命中但仍需人工确认的候选:**\n")
            for n in applied_uncertain:
                lines.append(f"- {n}")
            lines.append("")

    lines.append("---\n")
    lines.append("## 📄 原文 vs 改写\n")
    lines.append("<details>")
    lines.append("<summary>点击展开原文</summary>\n")
    lines.append("```")
    lines.append(original[:3000])
    if len(original) > 3000:
        lines.append(f"\n... (共{len(original)}字，已截断)")
    lines.append("```\n")
    lines.append("</details>\n")

    lines.append("<details>")
    lines.append("<summary>点击展开改写结果</summary>\n")
    lines.append("```")
    lines.append(rewritten[:3000])
    if len(rewritten) > 3000:
        lines.append(f"\n... (共{len(rewritten)}字，已截断)")
    lines.append("```\n")
    lines.append("</details>")

    return "\n".join(lines)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Generate a human-readable rewrite report.")
    parser.add_argument("--original", required=True, help="Original draft path")
    parser.add_argument("--rewritten", required=True, help="Rewritten draft path")
    parser.add_argument("--dna", required=True, help="DNA profile path")
    parser.add_argument("--debug-json", help="Debug JSON path (optional)")
    parser.add_argument("--output-md", required=True, help="Report markdown output path")
    args = parser.parse_args()

    original = load_text(args.original)
    rewritten = load_text(args.rewritten)
    dna = load_json_safe(args.dna)
    debug = load_json_safe(args.debug_json) if args.debug_json else {}

    report = build_report(original, rewritten, dna, debug)

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(report, encoding="utf-8")
    print(f"✅ 对比报告已生成: {output_md}")


if __name__ == "__main__":
    main()
