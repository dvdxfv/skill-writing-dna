#!/usr/bin/env python3
"""
Markdown 转 DOCX，用于最终交付。

依赖 pandoc（需单独安装：https://pandoc.org/installing.html）
转换为 WPS / Word 可直接打开的 .docx，自动使用中文字体。

用法:
    python scripts/md_to_docx.py --input outputs/rewrite_runs/rewritten_draft.md
    python scripts/md_to_docx.py --input draft.md --output 最终稿.docx --reference 模板.docx
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check_pandoc() -> None:
    if not shutil.which("pandoc"):
        print("错误：未找到 pandoc，请先安装 https://pandoc.org/installing.html", file=sys.stderr)
        sys.exit(1)


def build_reference_docx(output_path: Path) -> None:
    """生成一份带中文字体的参考文档，供 pandoc --reference-doc 使用。"""
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("提示：未安装 python-docx，将使用 pandoc 默认字体", file=sys.stderr)
        return

    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "仿宋"
    font.size = Pt(14)
    style.element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", "仿宋")

    for level, (name, size, bold) in {
        1: ("黑体", 16, True),
        2: ("楷体", 14, True),
        3: ("楷体", 14, False),
    }.items():
        heading_style = doc.styles[f"Heading {level}"]
        heading_font = heading_style.font
        heading_font.name = name
        heading_font.size = Pt(size)
        heading_font.bold = bold
        heading_font.color.rgb = None
        heading_style.element.rPr.rFonts.set(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", name
        )

    doc.save(str(output_path))


def convert_md_to_docx(input_path: Path, output_path: Path, reference_path: Path | None) -> None:
    cmd = [
        "pandoc",
        str(input_path),
        "-f", "markdown-auto_identifiers",
        "-t", "docx",
        "-o", str(output_path),
    ]
    if reference_path and reference_path.exists():
        cmd.extend(["--reference-doc", str(reference_path)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"pandoc 转换失败：{result.stderr}", file=sys.stderr)
        sys.exit(1)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".docx")


def main():
    parser = argparse.ArgumentParser(description="Markdown 转 DOCX（中文友好）")
    parser.add_argument("--input", required=True, help="输入 Markdown 文件路径")
    parser.add_argument("--output", help="输出 DOCX 文件路径（默认与输入同名、改后缀为 .docx）")
    parser.add_argument("--reference", help="参考模板 DOCX（用于复制样式；不提供则自动生成基础中文模板）")
    args = parser.parse_args()

    check_pandoc()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：文件不存在 {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else default_output_path(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reference_path = Path(args.reference) if args.reference else None

    if reference_path is None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_path = Path(tmpdir) / "reference.docx"
            build_reference_docx(ref_path)
            if ref_path.exists():
                convert_md_to_docx(input_path, output_path, ref_path)
            else:
                convert_md_to_docx(input_path, output_path, None)
    else:
        convert_md_to_docx(input_path, output_path, reference_path)

    print(f"DOCX 已生成：{output_path}")


if __name__ == "__main__":
    main()