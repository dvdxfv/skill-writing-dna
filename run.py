#!/usr/bin/env python3
"""
Writing DNA · 统一CLI入口

用法：
  python run.py extract    -- 提取DNA
  python run.py rewrite     -- 按DNA改写
  python run.py pipeline    -- 全流程一键运行
  python run.py status      -- 查看项目状态
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent / "scripts"
INPUTS_DIR = Path(__file__).parent / "inputs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"


def _run_script(script_name: str, args: list[str]) -> int:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n▶ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def cmd_extract(args):
    input_dir = INPUTS_DIR / "template_stripped_markdown"
    md_files = sorted(input_dir.glob("*.md")) if input_dir.exists() else []
    if not md_files:
        print("❌ 未找到清洗后的文档，请先将原始文档放入 inputs/raw_docx_articles/ 并运行 pipeline")
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
    dna_files = list(dna_dir.glob("*-dna.json")) if dna_dir.exists() else []
    if not dna_files:
        print("❌ 未找到DNA文件，请先运行 extract 或 pipeline")
        return 1
    dna_path = args.dna or str(dna_files[0])
    draft_dir = INPUTS_DIR / "ai_drafts"
    drafts = sorted(draft_dir.glob("*")) if draft_dir.exists() else []
    if not drafts:
        print("❌ 未找到AI草稿，请将草稿放入 inputs/ai_drafts/")
        return 1
    draft_path = args.draft or str(drafts[0])
    out_dir = OUTPUTS_DIR / "rewrite_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "rewritten_draft.md"
    out_json = out_dir / "rewrite_debug.json"
    return _run_script(
        "rewrite_with_dna.py",
        ["--draft", draft_path, "--dna", dna_path,
         "--output-md", str(out_md), "--output-json", str(out_json)],
    )


def cmd_pipeline(args):
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
    print("\n接下来需要人工介入：")
    print("  1. 运行 `python run.py extract` 提取DNA")
    print("  2. 复核DNA画像，确认或修正")
    print("  3. 将AI草稿放入 inputs/ai_drafts/")
    print("  4. 运行 `python run.py rewrite` 进行改写")
    return 0


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
            count = len(list(path.iterdir())) - sum(1 for f in path.iterdir() if f.name.startswith("."))
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
    raw_count = len(list((INPUTS_DIR / "raw_docx_articles").glob("*"))) if (INPUTS_DIR / "raw_docx_articles").exists() else 0
    if raw_count == 0:
        print("  → 放入原始文档到 inputs/raw_docx_articles/ 后运行 `python run.py pipeline`")
    elif not (OUTPUTS_DIR / "dna_profiles").exists() or not list((OUTPUTS_DIR / "dna_profiles").glob("*-dna.json")):
        print("  → 运行 `python run.py extract` 提取DNA")
    else:
        print("  → 放入AI草稿到 inputs/ai_drafts/ 后运行 `python run.py rewrite`")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Writing DNA · 个人写作风格守护者 — 统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run.py status                    # 查看当前状态
  python run.py pipeline                  # 运行前置处理全链路
  python run.py extract --user-name 张三  # 提取张三的写作DNA
  python run.py rewrite                   # 用已有DNA改写AI草稿
        """,
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    sub.add_parser("status", help="查看项目状态和下一步建议")
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
        "pipeline": cmd_pipeline,
        "extract": cmd_extract,
        "rewrite": cmd_rewrite,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
