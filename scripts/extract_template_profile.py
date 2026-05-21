#!/usr/bin/env python3
"""
Extract a repeatable template profile from filtered markdown articles.

分析多篇文档，识别哪些内容是"模板噪声"（跨文档重复出现的结构/段落），
哪些是"个人正文"（每篇独有的分析内容），输出一份模板画像报告。

用途：
  - 让用户直观看到"模板 vs 个人风格"的分界线
  - 理解 DNA 提取时哪些内容被排除了、为什么排除
  - 作为 strip_template.py 的配套诊断工具
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


from strip_template import (
    STRIP_SECTION_PATTERNS,
    STRIP_SUB_PATTERNS,
    TEMPLATE_PARAGRAPH_MARKERS,
    TEMPLATE_PARAGRAPH_LINE_STARTS,
    TEMPLATE_PARAGRAPH_FULL_MATCH,
    KEEP_ZONE_PATTERNS,
    is_heading,
    is_keep_zone_heading,
    is_strip_section_heading,
    is_strip_sub_heading,
    is_template_paragraph,
    strip_template,
)


def read_files(paths: list[str]) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for raw_path in paths:
        p = Path(raw_path)
        if not p.exists():
            print(f"Warning: skip missing file: {raw_path}", file=sys.stderr)
            continue
        if p.is_dir():
            for ext in ("*.md", "*.txt"):
                for fp in sorted(p.rglob(ext)):
                    docs.append({"filename": fp.name, "content": fp.read_text(encoding="utf-8")})
        else:
            docs.append({"filename": p.name, "content": p.read_text(encoding="utf-8")})
    return docs


def extract_headings(text: str) -> list[str]:
    headings = []
    for line in text.split("\n"):
        s = line.strip()
        if is_heading(s):
            clean = s.lstrip("#").strip()
            headings.append(clean)
    return headings


def extract_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\n+", text.strip())
    return [p.strip() for p in paras if p.strip()]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def find_repeated_headings(docs: list[dict[str, str]], min_repeat: int = 2) -> list[dict[str, Any]]:
    all_headings: Counter = Counter()
    per_doc_headings: list[set[str]] = []

    for doc in docs:
        h_set = set(extract_headings(doc["content"]))
        per_doc_headings.append(h_set)
        for h in h_set:
            all_headings[h] += 1

    results = []
    for heading, count in all_headings.items():
        if count >= min_repeat:
            doc_list = [d["filename"] for i, d in enumerate(docs) if heading in per_doc_headings[i]]
            category = _classify_heading(heading)
            results.append({
                "heading": heading,
                "repeat_count": count,
                "total_docs": len(docs),
                "repeat_ratio": round(count / len(docs), 2),
                "found_in": doc_list,
                "category": category,
            })

    results.sort(key=lambda x: (-x["repeat_count"], x["heading"]))
    return results


def _classify_heading(heading: str) -> str:
    stripped = heading.strip()
    if any(p.match(stripped) for p in STRIP_SECTION_PATTERNS):
        return "template_section"
    if any(p.match(stripped) for p in STRIP_SUB_PATTERNS):
        return "template_subsection"
    if any(p.match(stripped) for p in KEEP_ZONE_PATTERNS):
        return "personal_content"
    return "uncertain"


def find_repeated_phrases(docs: list[dict[str, str]], min_len: int = 10, min_repeat: int = 2) -> list[dict[str, Any]]:
    phrase_counter: Counter = Counter()
    phrase_doc_counter: Counter = Counter()

    for doc in docs:
        seen_in_doc: set[str] = set()
        paras = extract_paragraphs(doc["content"])
        for para in paras:
            if len(para) < min_len:
                continue
            normalized = normalize_text(para)
            if len(normalized) >= min_len * 0.8:
                phrase_counter[normalized] += 1
                if normalized not in seen_in_doc:
                    phrase_doc_counter[normalized] += 1
                    seen_in_doc.add(normalized)

    results = []
    for phrase, total in phrase_counter.most_common(50):
        doc_count = phrase_doc_counter.get(phrase, 0)
        if doc_count < min_repeat or total < min_repeat:
            continue
        original = None
        for doc in docs:
            for para in extract_paragraphs(doc["content"]):
                if normalize_text(para) == phrase:
                    original = para[:80] + ("..." if len(para) > 80 else "")
                    break
            if original:
                break
        if original:
            is_templ = any(
                m.search(original) for m in
                TEMPLATE_PARAGRAPH_MARKERS + TEMPLATE_PARAGRAPH_LINE_STARTS + TEMPLATE_PARAGRAPH_FULL_MATCH
            )
            results.append({
                "phrase_preview": original,
                "total_occurrences": total,
                "doc_count": doc_count,
                "char_length": len(phrase),
                "is_template_boilerplate": is_templ,
            })

    return results[:20]


def analyze_single_document(text: str, filename: str) -> dict[str, Any]:
    paras = extract_paragraphs(text)
    headings = extract_headings(text)

    template_paras = [p for p in paras if is_template_paragraph(p)]
    keep_zone_heads = [h for h in headings if is_keep_zone_heading(h)]
    strip_section_heads = [h for h in headings if is_strip_section_heading(h)]
    strip_sub_heads = [h for h in headings if is_strip_sub_heading(h)]

    stripped = strip_template(text)
    stripped_paras = extract_paragraphs(stripped)

    return {
        "filename": filename,
        "total_paragraphs": len(paras),
        "total_headings": len(headings),
        "template_paragraphs_detected": len(template_paras),
        "keep_zone_sections": keep_zone_heads,
        "strip_sections": strip_section_heads,
        "strip_subsections": strip_sub_heads,
        "paragraphs_after_stripping": len(stripped_paras),
        "chars_before": len(text),
        "chars_after": len(stripped),
        "stripping_ratio": round(len(stripped) / max(len(text), 1), 2),
    }


def build_profile(docs: list[dict[str, str]]) -> dict[str, Any]:
    repeated_headings = find_repeated_headings(docs)
    repeated_phrases = find_repeated_phrases(docs)
    per_doc_analysis = [analyze_single_document(d["content"], d["filename"]) for d in docs]

    template_sections = [h for h in repeated_headings if h["category"] == "template_section"]
    template_subsections = [h for h in repeated_headings if h["category"] == "template_subsection"]
    personal_sections = [h for h in repeated_headings if h["category"] == "personal_content"]

    avg_stripping = sum(d["stripping_ratio"] for d in per_doc_analysis) / max(len(per_doc_analysis), 1)
    avg_template_para_ratio = sum(d["template_paragraphs_detected"] for d in per_doc_analysis) / sum(d["total_paragraphs"] for d in per_doc_analysis) if per_doc_analysis else 0

    return {
        "schema_version": "1.0",
        "sample_count": len(docs),
        "files_analyzed": [d["filename"] for d in docs],
        "summary": {
            "avg_template_ratio": round(avg_stripping, 2),
            "avg_template_paragraph_pct": round(avg_template_para_ratio * 100, 1),
            "repeated_headings_total": len(repeated_headings),
            "template_headings": len(template_sections) + len(template_subsections),
            "personal_content_headings": len(personal_sections),
        },
        "repeated_headings": {
            "template_sections": template_sections[:15],
            "template_subsections": template_subsections[:20],
            "personal_content_sections": personal_sections[:10],
        },
        "repeated_phrases": repeated_phrases[:15],
        "per_document_analysis": per_doc_analysis,
        "excluded_from_dna": {
            "rationale": "以下内容被判定为文档模板结构或行业套话，在DNA提取阶段被排除，以避免将模板噪声误认为个人写作风格",
            "excluded_categories": [
                "绩效评价方法论说明（评价原则/方法/过程/数据来源）",
                "指标评分段（该指标主要考核...得分率...权重分）",
                "政策法规清单（编号+法规名列表）",
                "委托关系描述（受XX委托，对XX进行绩效评价）",
                "评分结论句式（总体得分XX分，评价等级为XX）",
                "通用开篇套话（为了深入贯彻落实...）",
                "附件引用（详见附件X）",
            ],
        },
    }


def build_markdown_report(profile: dict[str, Any]) -> str:
    lines = []
    summary = profile["summary"]

    lines.append("# 模板画像报告\n")
    lines.append(f"**样本数量**: {profile['sample_count']} 篇")
    lines.append(f"**分析文件**: {', '.join(profile['files_analyzed'])}\n")

    lines.append("## 📊 总体概况\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|:---|:---:|")
    lines.append(f"| 平均保留率（剥离后字数/原文） | {summary['avg_template_ratio']:.0%} |")
    lines.append(f"| 模板段落占比 | {summary['avg_template_paragraph_pct']}% |")
    lines.append(f"| 重复出现的小标题 | {summary['repeated_headings_total']} 个 |")
    lines.append(f"| 其中：模板类标题 | {summary['template_headings']} 个 |")
    lines.append(f"| 其中：个人正文标题 | {summary['personal_content_headings']} 个 |\n")

    rh = profile.get("repeated_headings", {})

    ts = rh.get("template_sections", [])
    if ts:
        lines.append("## 🚫 模板级标题（整段排除）\n")
        lines.append("以下标题及其下属全部内容被判定为模板结构，在模板剥离时整段删除：\n")
        for item in ts:
            lines.append(f"- **{item['heading']}** — 出现在 {item['repeat_count']}/{item['total_docs']} 篇中 ({item['repeat_ratio']:.0%})")
        lines.append("")

    tsub = rh.get("template_subsections", [])
    if tsub:
        lines.append("## 🚫 子级模板标题（子段排除）\n")
        lines.append("以下标题的内容被判定为模板说明，仅删除该子段：\n")
        for item in tsub[:15]:
            lines.append(f"- **{item['heading']}** — 出现在 {item['repeat_count']}/{item['total_docs']} 篇中")
        lines.append("")

    ps = rh.get("personal_content_sections", [])
    if ps:
        lines.append("## ✅ 个人正文标题（保留用于DNA提取）\n")
        lines.append("以下标题下的内容被判定为个人分析，完整保留：\n")
        for item in ps:
            lines.append(f"- **{item['heading']}** — 出现在 {item['repeat_count']}/{item['total_docs']} 篇中")
        lines.append("")

    rp = profile.get("repeated_phrases", [])
    if rp:
        lines.append("## 🔁 跨文档重复段落\n")
        lines.append("以下段落/句子在多篇文档中高度相似，被标记为模板套话：\n")
        for item in rp[:12]:
            tag = "🔴 模板套话" if item["is_template_boilerplate"] else "🟡 高度相似"
            lines.append(f"- [{tag}] `{item['phrase_preview'][:60]}...` （{item['doc_count']}篇中出现{item['total_occurrences']}次）")
        lines.append("")

    pda = profile.get("per_document_analysis", [])
    if pda:
        lines.append("## 📄 逐篇分析\n")
        for doc in pda:
            lines.append(f"### {doc['filename']}\n")
            lines.append(f"| 指标 | 数值 |")
            lines.append("|:---|:---:|")
            lines.append(f"| 原始段落数 | {doc['total_paragraphs']} |")
            lines.append(f"| 模板段落检出 | {doc['template_paragraphs_detected']} |")
            lines.append(f"| 剥离后段落数 | {doc['paragraphs_after_stripping']} |")
            lines.append(f"| 字数变化 | {doc['chars_before']} → {doc['chars_after']} ({doc['stripping_ratio']:.0%}) |")
            lines.append("")

    excl = profile.get("excluded_from_dna", {})
    if excl:
        lines.append("---\n")
        lines.append("## ℹ️ DNA 提取排除说明\n")
        lines.append(f"{excl['rationale']}\n")
        lines.append("**排除类别：**\n")
        for cat in excl.get("excluded_categories", []):
            lines.append(f"- {cat}")
        lines.append("")

    return "\n".join(lines)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Extract a template profile from filtered markdown files.")
    parser.add_argument("--input", nargs="+", required=True, help="Filtered markdown files")
    parser.add_argument("--output-json", required=True, help="Template profile JSON output path")
    parser.add_argument("--output-md", required=True, help="Human-readable report output path")
    args = parser.parse_args()

    docs = read_files(args.input)
    if not docs:
        print("Error: no readable input files found", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {docs} documents for template profiling")

    profile = build_profile(docs)
    md_report = build_markdown_report(profile)

    json_path = Path(args.output_json)
    md_path = Path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md_report, encoding="utf-8")

    s = profile["summary"]
    print(f"\n✅ 模板画像生成完成:")
    print(f"   分析文档: {profile['sample_count']} 篇")
    print(f"   平均保留率: {s['avg_template_ratio']:.0%}（即约{(1-s['avg_template_ratio'])*100:.0f}%是模板噪声）")
    print(f"   模板标题数: {s['template_headings']} 个")
    print(f"   个人正文标题: {s['personal_content_headings']} 个")
    print(f"   JSON 报告: {json_path}")
    print(f"   MD 报告: {md_path}")


if __name__ == "__main__":
    main()
