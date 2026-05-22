#!/usr/bin/env python3
"""
Filter non-prose content from normalized markdown before template and DNA analysis.

Removes:
  - Markdown tables (pipe-delimited)
  - Table/figure caption lines (表X-X / 图X-X)
  - Image references and [图片] placeholders
  - Table of Contents blocks (目 录 + page-number entries)
  - Attachment sections (十、附件 / 十一、附件 / # 附件 ...)
  - Quadruple-asterisk **** markers (residue from DOCX bold conversion)
  - Page-number noise
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


TABLE_BORDER_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*[:\- ]+\|[:\-| ]*$")
IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
IMAGE_PLACEHOLDER_RE = re.compile(r"\[图片\]")
FIGURE_LINE_RE = re.compile(r"^\s*(?:[图圖]|表)\s*\d+\s*[.\-_]?\s*\d+.*$", re.MULTILINE)
PAGE_NOISE_RE = re.compile(r"^\s*第\s*\d+\s*页\s*$", re.MULTILINE)
TOC_LINK_RE = re.compile(r"^\s*\[[^\]]+\]\(#_Toc\d+\)\s*$", re.MULTILINE)
STRIP_BOLD4_RE = re.compile(r"\*{4}")
ATTACHMENT_HEADING_RE = re.compile(
    r"(?m)^\s*#?\s*"
    r"(?:[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\s*[.\u3001、]?\s*)?"
    r"(?:相关\s*)?\u9644\u4ef6"           # 附件 or 相关附件
    r"(?:\s*[：:\d.、].*)?\s*$"            # optional ：number. title
)


def remove_markdown_tables(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    in_table = False
    for line in lines:
        is_table = bool(TABLE_BORDER_RE.match(line)) or bool(TABLE_SEPARATOR_RE.match(line))
        if is_table:
            in_table = True
            continue
        if in_table and not line.strip():
            in_table = False
            continue
        if in_table:
            continue
        kept.append(line)
    return "\n".join(kept)


def remove_toc_block(text: str) -> str:
    """Remove the table-of-contents block (目 录 + page-reference entries)."""
    lines = text.splitlines()
    kept: list[str] = []
    in_toc = False
    toc_end_markers = {"摘要", "正文"}
    for line in lines:
        stripped = line.strip().replace(" ", "")
        if stripped == "目录":
            in_toc = True
            continue
        if in_toc:
            if stripped in toc_end_markers or re.match(r"^[\u4e00-\u9fff]{2,8}$", stripped):
                in_toc = False
                kept.append(line)
            continue
        kept.append(line)
    return "\n".join(kept)


def remove_attachment_section(text: str) -> str:
    match = ATTACHMENT_HEADING_RE.search(text)
    if not match:
        return text
    return text[: match.start()].rstrip()


def filter_non_prose(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = IMAGE_MD_RE.sub("", text)
    text = IMAGE_PLACEHOLDER_RE.sub("", text)
    text = STRIP_BOLD4_RE.sub("", text)
    text = FIGURE_LINE_RE.sub("", text)
    text = PAGE_NOISE_RE.sub("", text)
    text = TOC_LINK_RE.sub("", text)
    text = remove_toc_block(text)
    text = remove_markdown_tables(text)
    text = remove_attachment_section(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Filter tables, images, and other non-prose content from markdown.")
    parser.add_argument("--input", nargs="+", required=True, help="Markdown input files or directories")
    parser.add_argument("--output-dir", required=True, help="Directory for filtered markdown output")
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
        filtered = filter_non_prose(text)
        output_path = output_dir / input_path.name
        output_path.write_text(filtered, encoding="utf-8")
        print(f"Filtered markdown written to: {output_path}")


if __name__ == "__main__":
    main()
