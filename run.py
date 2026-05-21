#!/usr/bin/env python3
"""
Writing DNA · 统一CLI入口

用法：
  python run.py extract    -- 提取DNA
  python run.py rewrite     -- 按DNA改写
  python run.py pipeline    -- 运行预处理链路
  python run.py status      -- 查看项目状态
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent / "scripts"
INPUTS_DIR = Path(__file__).parent / "inputs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"


def _configure_windows_utf8() -> None:
    """Keep Chinese CLI output readable on Windows terminals where possible."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def _visible_files(path: Path, patterns: tuple[str, ...] = ("*",)) -> list[Path]:
    if not path.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(p for p in path.glob(pattern) if p.is_file() and not p.name.startswith("."))
    return sorted(set(files))


def _print_empty_dir_help(label: str, path: Path, expected: str, next_action: str) -> None:
    print(f"❌ {label}为空：{path}")
    print(f"   请放入 {expected}")
    print(f"   然后运行：{next_action}")


def _run_script(script_name: str, args: list[str]) -> int:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n▶ {' '.join(cmd)}")
    result = subprocess.run(cmd, env=_subprocess_env())
    return result.returncode


def cmd_extract(args):
    input_dir = INPUTS_DIR / "template_stripped_markdown"
    md_files = _visible_files(input_dir, ("*.md",))
    if not md_files:
        _print_empty_dir_help(
            "未找到模板剥离后的文档",
            input_dir,
            "已完成预处理的 Markdown，或先把原始样本放到 inputs/raw_docx_articles/",
            "python run.py pipeline",
        )
        return 1
    print(f"📄 找到 {len(md_files)} 篇清洗后文档")
    extra = []
    if args.user_name:
        extra += ["--user-name", args.user_name]
    output_path = OUTPUTS_DIR / "dna_profiles"
    output_path.mkdir(parents=True, exist_ok=True)
    extra += ["--output", str(output_path / f"{args.user_name or 'user'}-dna.json")]
    return _run_script("extract_dna.py", [str(p) for p in md_files] + extra)


def cmd_rewrite(args):
    dna_dir = OUTPUTS_DIR / "dna_profiles"
    dna_files = _visible_files(dna_dir, ("*-dna.json",))
    if not dna_files:
        _print_empty_dir_help(
            "未找到DNA文件",
            dna_dir,
            "DNA JSON 文件",
            "python run.py extract",
        )
        return 1
    dna_path = args.dna or str(dna_files[0])
    draft_dir = INPUTS_DIR / "ai_drafts"
    drafts = _visible_files(draft_dir, ("*.md", "*.txt"))
    if not drafts:
        _print_empty_dir_help(
            "未找到AI草稿",
            draft_dir,
            "需要改写的 .md 或 .txt 草稿",
            "python run.py rewrite",
        )
        return 1
    draft_path = args.draft or str(drafts[0])
    out_dir = OUTPUTS_DIR / "rewrite_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "rewritten_draft.md"
    out_json = out_dir / "rewrite_debug.json"
    ret = _run_script(
        "rewrite_with_dna.py",
        ["--draft", draft_path, "--dna", dna_path,
         "--output-md", str(out_md), "--output-json", str(out_json)],
    )
    if ret != 0:
        return ret

    report_md = out_dir / "report.md"
    ret = _run_script(
        "generate_report.py",
        [
            "--original", draft_path,
            "--rewritten", str(out_md),
            "--dna", dna_path,
            "--debug-json", str(out_json),
            "--output-md", str(report_md),
        ],
    )
    if ret != 0:
        return ret

    print("\n✅ 已生成效果确认材料：")
    print(f"   改写稿: {out_md}")
    print(f"   对比报告: {report_md}")
    print(f"   调试数据: {out_json}")
    print("   请先人工确认改写效果；满意后如需 DOCX，再运行 md_to_docx。")
    return 0


def cmd_pipeline(args):
    raw_files = _visible_files(INPUTS_DIR / "raw_docx_articles", ("*.docx",))
    if not raw_files:
        _print_empty_dir_help(
            "原始样本目录",
            INPUTS_DIR / "raw_docx_articles",
            "5-12 篇 .docx 旧文样本",
            "python run.py pipeline",
        )
        return 1

    steps = [
        ("DOCX→MD转换", "docx_to_md.py", [
            "--input", str(INPUTS_DIR / "raw_docx_articles"),
            "--output-dir", str(INPUTS_DIR / "normalized_markdown"),
        ]),
        ("非正文过滤", "filter_non_prose.py", [
            "--input", str(INPUTS_DIR / "normalized_markdown"),
            "--output-dir", str(INPUTS_DIR / "filtered_markdown"),
        ]),
        ("模板剥离", "strip_template.py", [
            "--input", str(INPUTS_DIR / "filtered_markdown"),
            "--output-dir", str(INPUTS_DIR / "template_stripped_markdown"),
        ]),
    ]
    for name, script, s_args in steps:
        print(f"\n{'='*50}")
        print(f"📋 步骤: {name}")
        ret = _run_script(script, s_args)
        if ret != 0:
            print(f"⚠️  {name} 执行失败，停止后续步骤")
            return ret
    print("\n✅ 前置处理链路完成")
    print("\n接下来需要人工介入：运行 `python run.py extract` 提取 DNA，并复核画像。")
    return 0


def cmd_auto(args):
    """Run the next sensible stage and stop at the required human checkpoint."""
    stripped_files = _visible_files(INPUTS_DIR / "template_stripped_markdown", ("*.md",))
    dna_files = _visible_files(OUTPUTS_DIR / "dna_profiles", ("*-dna.json",))
    draft_files = _visible_files(INPUTS_DIR / "ai_drafts", ("*.md", "*.txt"))

    if not stripped_files:
        print("🔎 未发现模板剥离后的样本，先运行前置处理链路。")
        return cmd_pipeline(args)

    if not dna_files:
        print("🔎 已有清洗样本，开始提取 DNA。完成后请先人工确认 DNA 是否准确。")
        return cmd_extract(args)

    if not draft_files:
        print("✅ DNA 已存在，下一步请把需要改写的 .md 或 .txt 草稿放入 inputs/ai_drafts/")
        print("   放好后运行：python run.py auto")
        return 0

    print("🔎 已有 DNA 和 AI 草稿，开始改写。完成后请人工确认改写效果。")
    return cmd_rewrite(args)


def cmd_status(args):
    print("\n📊 Writing DNA 项目状态\n")

    sections = {
        "原始文档": INPUTS_DIR / "raw_docx_articles",
        "MD转换": INPUTS_DIR / "normalized_markdown",
        "过滤后": INPUTS_DIR / "filtered_markdown",
        "模板剥离后": INPUTS_DIR / "template_stripped_markdown",
        "AI草稿": INPUTS_DIR / "ai_drafts",
        "DNA画像": OUTPUTS_DIR / "dna_profiles",
        "改写结果": OUTPUTS_DIR / "rewrite_runs",
    }
    for name, path in sections.items():
        if path.exists():
            count = len(_visible_files(path))
            print(f"  ✅ {name}: {count} 个文件 — {path}")
        else:
            print(f"  ⬜ {name}: (空) — {path}")

    scripts_ok = []
    scripts_placeholder = []
    for s in ["docx_to_md.py", "filter_non_prose.py", "strip_template.py",
              "extract_dna.py", "rewrite_with_dna.py", "generate_report.py"]:
        p = SCRIPTS_DIR / s
        content = p.read_text(encoding="utf-8") if p.exists() else ""
        if "placeholder" in content.lower() and "not implemented" in content.lower():
            scripts_placeholder.append(s)
        elif p.exists():
            scripts_ok.append(s)

    print(f"\n🔧 脚本状态:")
    for s in scripts_ok:
        print(f"  ✅ {s}")
    for s in scripts_placeholder:
        print(f"  ⚠️  {s} (占位骨架)")

    print(f"\n💡 下一步:")
    raw_count = len(_visible_files(INPUTS_DIR / "raw_docx_articles"))
    dna_count = len(_visible_files(OUTPUTS_DIR / "dna_profiles", ("*-dna.json",)))
    draft_count = len(_visible_files(INPUTS_DIR / "ai_drafts", ("*.md", "*.txt")))
    if raw_count == 0:
        print("  → 放入原始文档到 inputs/raw_docx_articles/ 后运行 `python run.py pipeline`")
    elif dna_count == 0:
        print("  → 运行 `python run.py auto` 自动推进到下一个人工确认点")
    elif draft_count == 0:
        print("  → 放入AI草稿到 inputs/ai_drafts/ 后运行 `python run.py auto`")
    else:
        print("  → 运行 `python run.py auto` 开始改写，并在完成后人工确认效果")
    return 0


def main():
    _configure_windows_utf8()

    parser = argparse.ArgumentParser(
        description="Writing DNA · 个人写作风格守护者 — 统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run.py status                    # 查看当前状态
  python run.py auto                      # 智能推进到下一个人工确认点
  python run.py pipeline                  # 运行前置处理全链路
  python run.py extract --user-name 张三  # 提取张三的写作DNA
  python run.py rewrite                   # 用已有DNA改写AI草稿
        """,
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    sub.add_parser("status", help="查看项目状态和下一步建议")
    auto_p = sub.add_parser("auto", help="智能推进到下一个人工确认点")
    auto_p.add_argument("--user-name", default="user", help="用户名")
    sub.add_parser("pipeline", help="运行前置处理全链路（转换→过滤→模板剥离）")
    extract_p = sub.add_parser("extract", help="从清洗后的文档中提取写作DNA")
    extract_p.add_argument("--user-name", default="user", help="用户名")
    rewrite_p = sub.add_parser("rewrite", help="用DNA画像改写AI草稿")
    rewrite_p.add_argument("--dna", help="指定DNA文件路径")
    rewrite_p.add_argument("--draft", help="指定AI草稿路径")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    dispatch = {
        "status": cmd_status,
        "auto": cmd_auto,
        "pipeline": cmd_pipeline,
        "extract": cmd_extract,
        "rewrite": cmd_rewrite,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
