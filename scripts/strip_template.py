#!/usr/bin/env python3
"""
Template stripping: remove templated/schematic prose from filtered markdown.

Input:  filtered_markdown  (table-free, image-free, attachment-free)
Output: template_stripped_markdown  (personal prose preserved, boilerplate removed)

This module strips:
  - Indicator-analysis blocks (A11/A12/B21/D31 ... 该指标主要考核 ... 得分率...)
  - Scoring-rule template paragraphs
  - Evaluation-methodology template sections
  - Project-regulation numbered lists
  - Self-evaluation template sections
  - Repetitive institutional boilerplate
  - Attachment-reference traces
"""

import argparse
import re
import sys
from pathlib import Path


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


# ── Section headings that trigger "strip entire section until next heading" ──
STRIP_SECTION_PATTERNS = [
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价工作开展情况\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?综合评价情况及评价结论\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价指标体系分析\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价指标分析\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?组织实施\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?组织.?实施\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?其他需说明的问题\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价结果应用建议\s*$"),
]

# ── Sub-headings inside KEPT sections that trigger strip-until-next-heading ──
STRIP_SUB_PATTERNS = [
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目立项依据\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价依据\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目绩效目标\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价目的.?对象.?[和与]范围\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价原则.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价方法\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价工作过程\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价总体思路.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?数据来源.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?数据收集\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价工作组人员.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?工作安排.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?质量控制.*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?阶段性目标\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?分值评级\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?综合评价情况\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价结论\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价依据\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效自评情况\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价原则及方法\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?数据来源和取数方式\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价原则及依据\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价原则及方法\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价原则\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价依据\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价方法\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?评价目的\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?绩效评价原则\s*$"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?组织机构及职责\s*$"),
]

# ── Paragraph-level template markers ──
# A paragraph that contains ANY of these is considered template and is stripped
TEMPLATE_PARAGRAPH_MARKERS = [
    re.compile(r"该指标主要考核"),
    re.compile(r"该指标满分\s*\d+\s*分"),
    re.compile(r"该指标权重\s*\d+\s*分"),
    re.compile(r"按5:5权重加权计算"),
    re.compile(r"得分率为?\s*\d+(\.\d+)?\s*%"),
    re.compile(r"指标得分情况如表"),
    re.compile(r"得分情况如下表"),
    re.compile(r"权重分\s*\d+\s*分.*实际得分"),
    re.compile(r"详见附件\s*\d+"),
    re.compile(r"如附件所示"),
    re.compile(r"见附件\s*\d+"),
]

TEMPLATE_PARAGRAPH_LINE_STARTS = [
    re.compile(r"^A\d{2}\s*[^\u4e00-\u9fff]"),
    re.compile(r"^B\d{2}\s*[^\u4e00-\u9fff]"),
    re.compile(r"^C\d{2}\s*[^\u4e00-\u9fff]"),
    re.compile(r"^D\d{2}\s*[^\u4e00-\u9fff]"),
    re.compile(r"^根据评分标准"),
    re.compile(r"^根据评分细则"),
    re.compile(r"^根据现场调研"),
    re.compile(r"^评价组根据"),
    re.compile(r"^评价组通过"),
    re.compile(r"^评价组查阅"),
    re.compile(r"^为了深入贯彻"),
    re.compile(r"^根据项目单位提供的绩效目标申报表"),
    re.compile(r"^根据相关文件.*如下表"),
    re.compile(r"^根据收支两条线原则.*全额上缴国库"),
    re.compile(r"^综合评价情况"),
]

TEMPLATE_PARAGRAPH_FULL_MATCH = [
    re.compile(r"^在园区既定的优惠政策与扶持举措的有力支撑下.*发挥作用。$"),
    re.compile(r"^绩效评价报告$"),
    re.compile(r"^支出绩效评价报告$"),
    re.compile(r"^.{0,5}项目支出绩效评价报告$"),
]

# ── Paragraphs that contain a template-marker paragraph ▶ strip as a whole ──
def is_template_paragraph(para_text: str) -> bool:
    stripped = para_text.strip()
    if not stripped:
        return False
    for marker in TEMPLATE_PARAGRAPH_MARKERS:
        if marker.search(stripped):
            return True
    for start_pat in TEMPLATE_PARAGRAPH_LINE_STARTS:
        if start_pat.match(stripped):
            return True
    for full_pat in TEMPLATE_PARAGRAPH_FULL_MATCH:
        if full_pat.match(stripped):
            return True
    return False

# ── Section heading detection ──
HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+"                          # markdown headings
    r"|^\s*(?:[一二三四五六七八九十\d]+[\.\、)]*\s*)"
    r"(?:[\(（](?:[一二三四五六七八九十\d]+)[\)）]\s*)?"
    r"[\u4e00-\u9fff]{3,30}\s*$"
)

def is_heading(line: str) -> bool:
    return bool(HEADING_RE.match(line))

def is_strip_section_heading(line: str) -> bool:
    stripped = line.strip().lstrip("#").strip()
    for pat in STRIP_SECTION_PATTERNS:
        if pat.match(stripped):
            return True
    return False

def is_strip_sub_heading(line: str) -> bool:
    stripped = line.strip().lstrip("#").strip()
    for pat in STRIP_SUB_PATTERNS:
        if pat.match(stripped):
            return True
    return False

# ── Keep-zone section headings (content under these is always kept) ──
KEEP_ZONE_PATTERNS = [
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?(?:项目)?主要绩效"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?经验做法"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?存在的问题"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?需关注的主要问题"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?原因分析"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?下一步改进"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?政策建议"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?下一步改进及政策建议"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?改进建议"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目政策背景"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目主要内容"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目内容"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?项目组织"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?利益相关方"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s*)?资金投入"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s+)?项目预算"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s+)?资金用途"),
    re.compile(r"^(?:[一二三四五六七八九十\d]+[\.\、]?\s+)?资金使用"),
]

def is_keep_zone_heading(line: str) -> bool:
    stripped = line.strip().lstrip("#").strip()
    for pat in KEEP_ZONE_PATTERNS:
        if pat.match(stripped):
            return True
    return False


# Numbered regulation list line
COURT_NO_LINE = re.compile(r"^[\s（(]*\d+[\s）)]*《")

def is_regulation_list_line(line: str) -> bool:
    return bool(COURT_NO_LINE.match(line.strip()))


def normalize_for_dedupe(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def strip_accidental_heading_marks(text: str) -> str:
    cleaned_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("#"):
            cleaned_lines.append(line)
            continue

        body = stripped.lstrip("#").strip()
        is_short_heading = len(body) <= 32 and not re.search(r"[，。；：、,;]", body)
        if is_short_heading:
            cleaned_lines.append(line)
        else:
            cleaned_lines.append(body)
    return "\n".join(cleaned_lines)


def dedupe_long_paragraphs(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    last_seen: dict[str, int] = {}

    for idx, para in enumerate(paras):
        plain = normalize_for_dedupe(para.lstrip("#").strip())
        if len(plain) >= 80:
            last_seen[plain] = idx

    kept = []
    for idx, para in enumerate(paras):
        plain = normalize_for_dedupe(para.lstrip("#").strip())
        if len(plain) >= 80 and last_seen.get(plain) != idx:
            continue
        kept.append(para)

    return "\n\n".join(kept)


def strip_template(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # ── Detect first meaningful line for body-restart detection ──
    first_title_line = ""
    for line in lines:
        s = line.strip()
        if s and len(s) >= 4:
            first_title_line = s
            break

    # ── Pass 1: section-level stripping ──
    i = 0
    result1: list[str] = []
    in_strip_zone = False
    in_keep_zone = False

    while i < len(lines):
        line = lines[i]

        if is_heading(line):
            if is_keep_zone_heading(line):
                if in_strip_zone:
                    in_strip_zone = False
                in_keep_zone = True
                result1.append(line)
                i += 1
                continue
            elif is_strip_section_heading(line):
                in_strip_zone = True
                in_keep_zone = False
                i += 1
                continue
            elif is_strip_sub_heading(line) and not in_keep_zone:
                # Strip the sub-heading AND all content until the next heading
                i += 1
                while i < len(lines) and not is_heading(lines[i]):
                    i += 1
                continue

        if in_strip_zone:
            i += 1
            continue

        if in_keep_zone:
            if is_heading(line):
                if is_strip_section_heading(line):
                    in_keep_zone = False
                    in_strip_zone = True
                    i += 1
                    continue
                elif is_strip_sub_heading(line):
                    # Strip the sub-heading AND all content until the next heading.
                    # These sub-headings (绩效评价依据, 项目立项依据, etc.) always
                    # contain regulatory boilerplate, even inside keep-zones.
                    i += 1
                    while i < len(lines) and not is_heading(lines[i]):
                        i += 1
                    continue
                elif is_keep_zone_heading(line):
                    result1.append(line)
                    i += 1
                    continue
                else:
                    in_keep_zone = False
                    result1.append(line)
                    i += 1
                    continue
            else:
                result1.append(line)
                i += 1
                continue

        result1.append(line)
        i += 1

    text1 = "\n".join(result1)

    # ── Pass 1.5: strip body-restart segment ──
    # After 摘要 content, the body restarts with the same title + boilerplate.
    # Detect: a paragraph that is just the first_title_line (repeated) followed
    # by "绩效评价报告" on the next line.
    if first_title_line:
        paras = re.split(r"\n\n+", text1)
        kept2 = []
        skip_until_heading = False
        for j, para in enumerate(paras):
            stripped = para.strip()
            if skip_until_heading:
                if is_heading(stripped):
                    skip_until_heading = False
                    kept2.append(stripped)
                continue
            # Check: this paragraph is just the title line, and next para is "绩效评价报告"
            if stripped == first_title_line and j > 10:
                next_para = paras[j + 1].strip() if j + 1 < len(paras) else ""
                if "绩效评价报告" in next_para or "支出绩效评价报告" in next_para:
                    skip_until_heading = True
                    continue
            kept2.append(stripped)
        text1 = "\n\n".join(kept2)

    # ── Pass 2: paragraph-level stripping ──
    paras = re.split(r"\n\n+", text1)
    kept_paras = []
    # Track if we're in a regulation-list stanza
    consecutive_reg_lines = 0

    for para in paras:
        para_stripped = para.strip()
        if not para_stripped:
            continue

        # Check if this paragraph is a regulation list block
        para_lines = para_stripped.split("\n")
        reg_count = sum(1 for l in para_lines if is_regulation_list_line(l))
        non_empty = [l for l in para_lines if l.strip()]
        if non_empty and reg_count >= 2 and reg_count / max(len(non_empty), 1) > 0.5:
            continue

        # Skip single regulation-list lines
        if len(non_empty) == 1 and is_regulation_list_line(non_empty[0]):
            continue

        # Skip template paragraphs
        if is_template_paragraph(para_stripped):
            continue

        kept_paras.append(para_stripped)

    text2 = "\n\n".join(kept_paras)
    text2 = dedupe_long_paragraphs(text2)
    text2 = strip_accidental_heading_marks(text2)

    # ── Pass 3: clean up ──
    # Strip stray regulation-numbered leftover lines
    text2 = re.sub(r"^\s*[（(]\d+[）)]\s*其他与本项目相关的政策文件和资料[。]?\s*$", "", text2, flags=re.MULTILINE)
    text2 = re.sub(r"\n{3,}", "\n\n", text2)
    text2 = text2.strip() + "\n"

    return text2


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Strip template content from filtered markdown.")
    parser.add_argument("--input", nargs="+", required=True, help="Filtered markdown input files or directories")
    parser.add_argument("--output-dir", required=True, help="Directory for template-stripped markdown")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_files = []
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

    for input_path in input_files:
        text = input_path.read_text(encoding="utf-8")
        stripped = strip_template(text)
        output_path = output_dir / input_path.name
        output_path.write_text(stripped, encoding="utf-8")
        print(f"Template-stripped markdown written to: {output_path}")


if __name__ == "__main__":
    main()
