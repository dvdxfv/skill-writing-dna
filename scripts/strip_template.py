#!/usr/bin/env python3
"""
跨文档对齐 · 通用模板剥离（PRD §8.1.3 · Layer 1）

PRD 核心原则:
    模板决定这类文档应该怎么写，DNA 决定你在这个模板里习惯怎么写。

本脚本只做"确定性"的 Layer 1 检测——通过跨文档字面重复识别明显的模板内容。
语义层的判断（"这段是论文摘要套话"、"那段是邮件客套话"）由 SKILL.md 引导 LLM
在对话中完成（Layer 2），最终由用户确认（Layer 3）。

不再针对任何特定文体（绩效报告 / 论文 / 邮件 / 公众号 / 合同……）硬编码规则；
所有模板特征都从样本本身的跨文档统计中浮现。

输入:
    --input <目录或多个 markdown 文件>
    --output-dir <剥离后输出目录>

输出:
    1. 剥离后的 markdown（每篇一个文件）
    2. strip_report.md（人类可读报告，列出剥离了什么）

算法（三个独立通道）:
    A. 整句对齐：跨 ≥threshold 文档中字面完全相同的整句 → 模板
    B. 章节标题对齐：跨 ≥threshold 文档重复的 markdown 标题 → 该标题及内容剥离
    C. 长 ngram 对齐：≥8 字 ngram 跨 ≥threshold 文档出现 → 包含该 ngram 的整句剥离
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENTENCE_END_RE = re.compile(r"(?<=[。！？!?])")
PURE_PUNCT_RE = re.compile(r"^[\s，。、；：！？,;:.!?\d\-—…·]+$")

LONG_NGRAM_MIN_LEN = 8
SHORT_SENTENCE_MIN_LEN = 4


def normalize_for_match(text: str) -> str:
    """去空白用于跨文档字面匹配——保留标点（避免误合并不同句）。"""
    return re.sub(r"\s+", "", text.strip())


def is_heading_line(line: str) -> bool:
    return bool(HEADING_RE.match(line))


def heading_body(line: str) -> str:
    m = HEADING_RE.match(line)
    return m.group(2).strip() if m else ""


def extract_sentences(text: str) -> list[str]:
    """把文档切成"句"——按句末标点+换行切分。
    跳过 markdown 标题行（标题由 extract_headings 单独处理）。
    """
    body_lines = [ln for ln in text.split("\n") if not is_heading_line(ln)]
    body = "\n".join(body_lines)
    paragraphs = re.split(r"\n{2,}", body)
    sentences: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        parts = SENTENCE_END_RE.split(para.replace("\n", ""))
        for part in parts:
            s = part.strip()
            if len(s) >= SHORT_SENTENCE_MIN_LEN and not PURE_PUNCT_RE.match(s):
                sentences.append(s)
    return sentences


def extract_headings(text: str) -> list[str]:
    return [heading_body(line) for line in text.split("\n") if is_heading_line(line)]


def extract_long_ngrams(text: str, n_min: int, n_max: int) -> set[str]:
    """提取长 ngram（按汉字字符滑窗）。仅保留含汉字、非纯标点的 ngram。"""
    normalized = re.sub(r"\s+", "", text)
    grams: set[str] = set()
    for n in range(n_min, n_max + 1):
        for i in range(len(normalized) - n + 1):
            g = normalized[i:i + n]
            if PURE_PUNCT_RE.match(g):
                continue
            if not re.search(r"[一-鿿]", g):
                continue
            grams.add(g)
    return grams


def find_features_above_threshold(
    per_doc_sets: list[set[str]],
    threshold: float,
) -> dict[str, int]:
    """返回 {feature: doc_count}，仅保留出现在 ≥ threshold 比例文档中的特征。"""
    counter: Counter = Counter()
    for s in per_doc_sets:
        for item in s:
            counter[item] += 1
    total_docs = len(per_doc_sets)
    min_count = max(2, int(total_docs * threshold + 0.5))
    return {item: count for item, count in counter.items() if count >= min_count}


def find_template_sentences(docs: list[dict[str, Any]], threshold: float) -> dict[str, int]:
    per_doc = [
        {normalize_for_match(s) for s in extract_sentences(d["content"])}
        for d in docs
    ]
    return find_features_above_threshold(per_doc, threshold)


def find_template_headings(docs: list[dict[str, Any]], threshold: float) -> dict[str, int]:
    per_doc = [
        {normalize_for_match(h) for h in extract_headings(d["content"])}
        for d in docs
    ]
    return find_features_above_threshold(per_doc, threshold)


def find_template_ngrams(
    docs: list[dict[str, Any]],
    threshold: float,
    n_min: int,
    n_max: int,
) -> dict[str, int]:
    per_doc = [extract_long_ngrams(d["content"], n_min, n_max) for d in docs]
    return find_features_above_threshold(per_doc, threshold)


def collapse_ngrams(ngrams: dict[str, int]) -> dict[str, int]:
    """合并被包含的 ngram，只保留极大子串——
    若 'ABCDEFGH' 在结果里，'ABCDEFG' 就没必要单独列出。
    """
    sorted_grams = sorted(ngrams.keys(), key=lambda g: -len(g))
    kept: dict[str, int] = {}
    for g in sorted_grams:
        if any(g != bigger and g in bigger for bigger in kept):
            continue
        kept[g] = ngrams[g]
    return kept


def strip_from_document(
    text: str,
    template_sentences: dict[str, int],
    template_headings: dict[str, int],
    template_ngrams: dict[str, int],
) -> tuple[str, list[str]]:
    """对单篇文档做剥离。返回 (剥离后文本, 剥离条目列表)。"""
    removed: list[str] = []
    lines = text.split("\n")
    output: list[str] = []
    skip_until_next_heading = False

    long_ngrams_sorted = sorted(template_ngrams.keys(), key=lambda g: -len(g))

    for line in lines:
        if is_heading_line(line):
            heading_norm = normalize_for_match(heading_body(line))
            if heading_norm in template_headings:
                removed.append(f"[模板标题区段] {line.strip()}")
                skip_until_next_heading = True
                continue
            else:
                skip_until_next_heading = False
                output.append(line)
                continue

        if skip_until_next_heading:
            removed.append(f"[在模板标题下] {line.strip()[:80]}")
            continue

        normalized = normalize_for_match(line)
        if not normalized:
            output.append(line)
            continue

        # A. 整句字面对齐
        line_sentences = []
        parts = SENTENCE_END_RE.split(line.replace("\n", ""))
        for part in parts:
            s = part.strip()
            if s:
                line_sentences.append(s)

        kept_sentences: list[str] = []
        for sent in line_sentences:
            sent_norm = normalize_for_match(sent)
            if sent_norm in template_sentences:
                removed.append(f"[整句重复] {sent[:80]}")
                continue
            # C. 长 ngram 检测：若整句被一个长 ngram 占据 ≥50%，剥离
            ngram_hit = None
            for g in long_ngrams_sorted:
                if g in sent_norm and len(g) / max(len(sent_norm), 1) >= 0.5:
                    ngram_hit = g
                    break
            if ngram_hit:
                removed.append(f"[模板短语 '{ngram_hit}'] {sent[:80]}")
                continue
            kept_sentences.append(sent)

        if not kept_sentences:
            continue
        if len(kept_sentences) == len(line_sentences):
            output.append(line)
        else:
            output.append("".join(kept_sentences))

    rebuilt = "\n".join(output)
    rebuilt = re.sub(r"\n{3,}", "\n\n", rebuilt).strip() + "\n"
    return rebuilt, removed


def write_report(
    report_path: Path,
    docs: list[dict[str, Any]],
    template_sentences: dict[str, int],
    template_headings: dict[str, int],
    template_ngrams: dict[str, int],
    per_doc_removals: dict[str, list[str]],
    threshold: float,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    total_docs = len(docs)
    min_count = max(2, int(total_docs * threshold + 0.5))

    out: list[str] = []
    out.append("# 模板剥离报告（PRD §8.1.3 · Layer 1）")
    out.append("")
    out.append(f"- 文档总数: **{total_docs}**")
    out.append(f"- 跨文档重复阈值: **≥ {threshold * 100:.0f}%**（即 ≥ {min_count}/{total_docs} 个文档中出现才算模板）")
    out.append(f"- 长 ngram 最小长度: **{LONG_NGRAM_MIN_LEN}** 字")
    out.append("")
    out.append('> 本报告由跨文档对齐算法自动生成。该算法不依赖任何文体先验——任何在多数样本里字面重复出现的内容都会被识别为"模板"。语义层的判断（"这段是论文摘要套话"、"那段是邮件客套话"）由 SKILL.md 引导 LLM 在对话中识别，并由用户确认。')
    out.append("")

    out.append(f"## A. 重复的章节标题（{len(template_headings)} 个）")
    out.append("")
    if template_headings:
        out.append("跨多篇文档使用相同章节标题 → 这些章节及其内容已被剥离。")
        out.append("")
        for h, count in sorted(template_headings.items(), key=lambda x: (-x[1], x[0]))[:40]:
            out.append(f"- `{h}` — {count}/{total_docs} 篇")
    else:
        out.append("（无）")
    out.append("")

    out.append(f"## B. 字面完全相同的整句（{len(template_sentences)} 个）")
    out.append("")
    if template_sentences:
        out.append("跨多篇出现完全相同的整句 → 这些句子已被剥离。")
        out.append("")
        for s, count in sorted(template_sentences.items(), key=lambda x: (-len(x[0]), -x[1]))[:40]:
            preview = s if len(s) <= 100 else s[:100] + "…"
            out.append(f"- `{preview}` — {count}/{total_docs} 篇")
    else:
        out.append("（无）")
    out.append("")

    collapsed = collapse_ngrams(template_ngrams)
    out.append(f"## C. 跨文档高频长短语（≥ {LONG_NGRAM_MIN_LEN} 字，{len(collapsed)} 个）")
    out.append("")
    if collapsed:
        out.append(f"长度 ≥ {LONG_NGRAM_MIN_LEN} 字、跨 ≥ {min_count} 篇出现的短语 → 含该短语且短语占整句 ≥ 50% 的句子已被剥离。")
        out.append("")
        for g, count in sorted(collapsed.items(), key=lambda x: (-x[1], -len(x[0])))[:40]:
            out.append(f"- `{g}` — {count}/{total_docs} 篇")
    else:
        out.append("（无）")
    out.append("")

    out.append("## 每篇剥离样例")
    out.append("")
    for doc in docs:
        removals = per_doc_removals.get(doc["filename"], [])
        out.append(f"### {doc['filename']}（剥离 {len(removals)} 处）")
        out.append("")
        if removals:
            for r in removals[:12]:
                preview = r if len(r) <= 140 else r[:140] + "…"
                out.append(f"- {preview}")
            if len(removals) > 12:
                out.append(f"- *...共 {len(removals)} 处，仅展示前 12*")
        else:
            out.append("（无剥离）")
        out.append("")

    out.append("---")
    out.append("")
    out.append("## 下一步")
    out.append("")
    out.append('Layer 1 只能剥离字面重复模板。如果你的样本里还有"结构相同但内容不同"的模板（比如每篇报告都有"摘要"段，但每篇摘要内容不一样），需要让 LLM 在对话中进一步识别——这是 Layer 2/3 的工作。')
    out.append("")
    out.append("调阈值：")
    out.append('- 报告里识别的"模板"误伤了你的个人风格 → 把 `--doc-ratio-threshold` 调高（如 0.8）')
    out.append("- 报告里模板检测得不够多、个人 DNA 仍混入模板 → 把阈值调低（如 0.5），或在 SKILL.md 对话中由 LLM 进一步识别 Layer 2 模板")
    out.append("")

    report_path.write_text("\n".join(out), encoding="utf-8")


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Cross-document alignment template stripping (PRD §8.1.3 Layer 1)."
    )
    parser.add_argument("--input", nargs="+", required=True,
                        help="Markdown input files or directories")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for template-stripped markdown")
    parser.add_argument("--report",
                        default="outputs/template_profiles/strip_report.md",
                        help="Path to write the strip report (default: outputs/template_profiles/strip_report.md)")
    parser.add_argument("--doc-ratio-threshold", type=float, default=0.6,
                        help="Min ratio of docs a feature must appear in to count as template (default: 0.6)")
    parser.add_argument("--min-ngram", type=int, default=LONG_NGRAM_MIN_LEN,
                        help=f"Min ngram length for cross-doc detection (default: {LONG_NGRAM_MIN_LEN})")
    parser.add_argument("--max-ngram", type=int, default=20,
                        help="Max ngram length (default: 20)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report)

    # Resolve input files
    input_files: list[Path] = []
    for raw_path in args.input:
        input_path = Path(raw_path)
        if input_path.is_dir():
            input_files.extend(sorted(input_path.glob("*.md")))
        elif input_path.exists():
            input_files.append(input_path)
        else:
            print(f"Error: path not found: {input_path}", file=sys.stderr)

    if not input_files:
        print("Error: no valid input files found", file=sys.stderr)
        sys.exit(1)

    docs: list[dict[str, Any]] = []
    for f in input_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: failed to read {f}: {e}", file=sys.stderr)
            continue
        docs.append({"filename": f.name, "path": f, "content": content})

    if not docs:
        print("Error: no readable documents", file=sys.stderr)
        sys.exit(1)

    if len(docs) < 2:
        print(f"⚠️  Only {len(docs)} doc loaded — cross-document detection needs ≥ 2 docs to work.")
        print("    Will write empty strip report and copy file through unchanged.")

    print(f"Loaded {len(docs)} documents; threshold = {args.doc_ratio_threshold * 100:.0f}%")

    template_headings = find_template_headings(docs, args.doc_ratio_threshold)
    template_sentences = find_template_sentences(docs, args.doc_ratio_threshold)
    template_ngrams = find_template_ngrams(docs, args.doc_ratio_threshold,
                                            args.min_ngram, args.max_ngram)

    print(f"  Detected: {len(template_headings)} template headings, "
          f"{len(template_sentences)} template sentences, "
          f"{len(template_ngrams)} template ngrams")

    per_doc_removals: dict[str, list[str]] = {}
    for doc in docs:
        stripped, removed = strip_from_document(
            doc["content"], template_sentences, template_headings, template_ngrams
        )
        per_doc_removals[doc["filename"]] = removed
        out_path = output_dir / doc["filename"]
        out_path.write_text(stripped, encoding="utf-8")
        print(f"  {doc['filename']} -> {out_path} ({len(removed)} removals)")

    write_report(report_path, docs, template_sentences, template_headings,
                 template_ngrams, per_doc_removals, args.doc_ratio_threshold)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
