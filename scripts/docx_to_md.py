#!/usr/bin/env python3
"""
Convert DOCX files to readable Markdown.

Primary goal:
- produce human-readable Markdown
- preserve headings, paragraphs, bullets, and basic tables as much as possible
- create a stable intermediate artifact for later DNA extraction
"""

import argparse
import re
import sys
from pathlib import Path

import mammoth
from markdownify import markdownify as md


def _remove_toc_section(text: str) -> str:
    """删除自动目录区域（从'目 录'行开始到最后一个 TOC 链接行）。"""
    lines = text.split("\n")
    in_toc = False
    toc_start = -1
    toc_end = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "目 录":
            in_toc = True
            toc_start = i
            continue
        if in_toc:
            if re.match(r"\[.+\]\(#_Toc\d+\)", stripped):
                toc_end = i
            else:
                if toc_end >= 0:
                    break
                in_toc = False
                toc_start = -1
    if toc_start >= 0 and toc_end >= 0:
        del lines[toc_start:toc_end + 1]
    return "\n".join(lines)


def normalize_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _remove_toc_section(text)
    text = re.sub(r"\[([^\]]+)\]\(#_Toc\d+\)", r"\1", text)
    text = re.sub(r"\*{4}(.+?)\*{4}", r"\1", text)
    text = re.sub(r"!\[.*?\]\(data:.*?\)", "[图片]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def convert_docx_to_markdown(input_path: Path) -> tuple[str, list[str]]:
    with input_path.open("rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
    html = result.value
    messages = [f"{message.type}: {message.message}" for message in result.messages]

    markdown = md(
        html,
        heading_style="ATX",
        bullets="-",
        strong_em_symbol="**",
    )
    markdown = normalize_markdown(markdown)
    return markdown, messages


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".md")


def main():
    parser = argparse.ArgumentParser(description="Convert DOCX files to readable Markdown.")
    parser.add_argument("--input", nargs="+", required=True, help="DOCX file paths")
    parser.add_argument("--output-dir", help="Optional output directory for generated markdown files")
    parser.add_argument("--stdout", action="store_true", help="Print markdown to stdout for single-file usage")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for raw_path in args.input:
        input_path = Path(raw_path)
        if not input_path.exists():
            print(f"Error: file not found: {input_path}", file=sys.stderr)
            continue
        if input_path.suffix.lower() != ".docx":
            print(f"Error: only .docx is supported: {input_path}", file=sys.stderr)
            continue

        markdown, messages = convert_docx_to_markdown(input_path)

        if args.stdout and len(args.input) == 1:
            sys.stdout.write(markdown)
        else:
            if output_dir:
                output_path = output_dir / f"{input_path.stem}.md"
            else:
                output_path = default_output_path(input_path)
            output_path.write_text(markdown, encoding="utf-8")
            print(f"Markdown written to: {output_path}")

        if messages:
            print(f"Warnings for {input_path.name}:")
            for message in messages:
                print(f"  - {message}")


if __name__ == "__main__":
    main()
