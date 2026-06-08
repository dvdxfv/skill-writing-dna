"""
T1 回归层：锁住现有功能的契约。

这些测试现在就应该全部 GREEN（测的是已有行为）。实现 6 项优化后，它们必须
依然 GREEN——任何一条变红，就说明优化污染了原有功能。这是「保证其他功能不被
影响」的自动护栏。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

ALL_SCRIPTS = [
    "docx_to_md.py", "filter_non_prose.py", "strip_template.py",
    "extract_dna.py", "render_dna_feature_cloud.py", "detect_ai_slop.py",
    "ai_slop_dict.py", "test_sample_sufficiency.py", "rewrite_with_dna.py",
    "generate_report.py", "md_to_docx.py", "dna_versioning.py",
    "validate_rewrite_against_dna.py", "check_tool_config_sync.py",
]


# ── 所有脚本能编译 ─────────────────────────────────────────
@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_script_compiles(script):
    path = SCRIPTS_DIR / script
    if not path.exists():
        pytest.skip(f"脚本不存在: {script}")
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"{script} 编译失败:\n{result.stderr}"


# ── extract_dna 纯函数契约 ────────────────────────────────
def test_extract_dna_contract(extract_docs):
    import extract_dna as ed
    dna = ed.extract_dna(extract_docs, "tester")

    # 顶层必备字段（改写脚本依赖这些 key）
    for key in ("user_name", "schema_version", "signature_phrases",
                "blacklist_phrases", "sentence_features", "emoji_policy"):
        assert key in dna, f"DNA 缺少字段: {key}"

    assert dna["user_name"] == "tester"
    assert isinstance(dna["signature_phrases"], list)
    assert dna["sentence_features"]["avg_length_chars"] > 0


def test_extract_dna_blacklist_excludes_user_owned(extract_docs):
    """黑名单逻辑：用户常用的套话不进黑名单。"""
    import extract_dna as ed
    dna = ed.extract_dna(extract_docs, "tester")
    for owned in dna.get("user_owned_phrases", []):
        assert owned not in dna["blacklist_phrases"]


def test_extract_dna_emoji_density_nonnegative(extract_docs):
    """Bug 4 修复后：emoji 密度分母一致，恒非负、不崩溃。"""
    import extract_dna as ed
    dna = ed.extract_dna(extract_docs, "tester")
    assert dna["emoji_policy"]["per_1k_chars"] >= 0
    assert dna["emoji_policy"]["frequency"] in {"none", "rare", "moderate", "heavy"}


def test_extract_dna_raises_on_empty():
    """Bug 5 修复后：全空输入抛 ValueError，不静默。"""
    import extract_dna as ed
    with pytest.raises(ValueError):
        ed.extract_dna([{"filename": "x.md", "content": "   \n\n  "}], "tester")


# ── rewrite_with_dna 纯函数契约 ───────────────────────────
def test_rewrite_blacklist_removal():
    import rewrite_with_dna as rw
    text, removed = rw.apply_blacklist_removal("赋能业务，打造一站式方案。", ["赋能", "一站式"])
    assert "赋能" not in text and "一站式" not in text
    assert {r["phrase"] for r in removed} == {"赋能", "一站式"}


def test_rewrite_blacklist_removal_preserves_sentence_readability():
    import rewrite_with_dna as rw
    original = (
        "在数字化转型的浪潮中，教育领域正迎来变化。"
        "如何利用数字化转型赋能教育教学，重塑教育生态，成为关键问题。"
    )
    text, removed = rw.apply_blacklist_removal(
        original,
        ["在数字化转型的浪潮中", "数字化转型", "赋能", "重塑", "生态"],
    )
    assert text.startswith("当前，教育领域")
    assert not text.startswith("，")
    assert "，、" not in text
    for phrase in ("在数字化转型的浪潮中", "数字化转型", "赋能", "重塑", "生态"):
        assert phrase not in text
    assert all(item.get("action") != "deferred" for item in removed)


def test_signature_helper_does_not_hard_append_absent_formal_phrase():
    import rewrite_with_dna as rw
    text = "教育评价需要回到课堂过程本身，不能只看一次考试结果。"
    rewritten, injected = rw.apply_signature_injection(text, ["有所欠缺"])
    assert rewritten == text
    assert injected == []


def test_adjust_opener_does_not_replace_with_sample_sentence():
    import rewrite_with_dna as rw
    text = "当前，教育领域正在发生变化。需要结合课堂实际推进。"
    opener = ["2023-2024年某项目绩效评价报告。"]
    assert rw.adjust_opener(text, opener) == text


def test_rewrite_debug_info_has_skipped_rules_field():
    """debug 信息里保留 skipped_dna_rules（可见性自查依赖它露出跳过项）。"""
    import rewrite_with_dna as rw
    dna = {"user_name": "t", "downgraded_features": {"x": 1}, "uncertain_candidates": ["y"]}
    debug = rw.build_debug_info(
        "原文", "改写", dna,
        {"score": 5, "total_hits_count": 2}, {"score": 1, "total_hits_count": 0},
        [], [], [],
    )
    assert "skipped_dna_rules" in debug
    assert debug["skipped_dna_rules"]["downgraded"] == ["x"]
    assert debug["skipped_dna_rules"]["not_applied"] == ["y"]


def test_rewrite_debug_does_not_mark_applied_uncertain_as_not_applied():
    import rewrite_with_dna as rw
    dna = {"user_name": "t", "uncertain_candidates": ["有所欠缺", "基本达成预期目标"]}
    debug = rw.build_debug_info(
        "原文", "这里确实有所欠缺。", dna,
        {"score": 5, "total_hits_count": 2}, {"score": 1, "total_hits_count": 0},
        [], [], [],
    )
    skipped = debug["skipped_dna_rules"]
    assert "有所欠缺" not in skipped["not_applied"]
    assert "有所欠缺" in skipped["applied_uncertain_candidates"]
    assert "基本达成预期目标" in skipped["not_applied"]


def test_feature_cloud_excludes_template_only_enum_label():
    import render_dna_feature_cloud as cloud
    profile = {
        "structure_habits": {
            "transition_mode": "一是…二是…三是…",
            "within_section": "先判断后展开",
        },
        "excluded_as_template": ["一是 / 二是 / 三是 这种分点展开方式。"],
    }
    labels = {label for label, _ in cloud.collect_feature_weights(profile)}
    assert "一是…二是…三是…" not in labels
    assert "先判断后展开" in labels


# ── generate_report：已有的「跳过规则」展示要保留 ─────────
def test_report_surfaces_skipped_rules():
    """generate_report.py 已把跳过/降权规则写进 report.md——锁住别丢。"""
    import generate_report as gr
    debug = {
        "stats": {"original_char_count": 100, "rewritten_char_count": 90, "char_change_ratio": 0.9},
        "ai_slop": {"before": {"score": 5, "hit_count": 2}, "after": {"score": 1, "hit_count": 0}},
        "changes": {"blacklist_phrases_removed": [], "ai_connectors_removed": [], "signature_phrases_injected": []},
        "dna_rules_applied": [],
        "skipped_dna_rules": {"downgraded": ["句长不稳"], "not_applied": ["某候选短语"]},
    }
    report = gr.build_report("原文内容", "改写内容", {"user_name": "t"}, debug)
    assert "跳过的规则" in report
    assert "句长不稳" in report
    assert "某候选短语" in report


def test_report_uses_matched_signature_wording():
    import generate_report as gr
    debug = {
        "stats": {"original_char_count": 100, "rewritten_char_count": 100, "char_change_ratio": 1.0},
        "ai_slop": {"before": {"score": 1, "hit_count": 1}, "after": {"score": 0, "hit_count": 0}},
        "changes": {
            "blacklist_phrases_removed": [],
            "ai_connectors_removed": [],
            "signature_phrases_matched": ["说真的"],
            "signature_phrase_suggestions": ["先动手再说"],
        },
        "dna_rules_applied": [],
        "skipped_dna_rules": {},
    }
    report = gr.build_report(
        "原文内容",
        "说真的，这段已经比较自然。",
        {"user_name": "t", "signature_phrases": ["说真的", "先动手再说"]},
        debug,
    )
    assert "自然命中的签名表达" in report
    assert "可供二次改写参考的候选表达" in report
    assert "植入的签名短语" not in report
    assert "DNA 对齐验证" in report


# ── run.py 的 DNA 发现 glob 不变式（#5 版本管理的关键护栏）──
def test_visible_files_glob_ignores_versioned_dna(tmp_path):
    """
    run._visible_files(dir, ('*-dna.json',)) 只能发现当前指针 user-dna.json，
    绝不能把版本快照 *-dna-vN.json 也扫进来——否则改写会选错文件。
    这是 #5 DNA 版本命名方案能成立的前提，现在就锁死。
    """
    import run
    (tmp_path / "tester-dna.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tester-dna-v1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tester-dna-v2.json").write_text("{}", encoding="utf-8")

    found = run._visible_files(tmp_path, ("*-dna.json",))
    names = {p.name for p in found}
    assert names == {"tester-dna.json"}, f"glob 污染了：{names}"


# ── run.py CLI 向后兼容 ───────────────────────────────────
def _run_cli(*args, cwd):
    env = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    import os
    full_env = os.environ.copy()
    full_env.update(env)
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run.py"), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(cwd), env=full_env,
    )


def test_run_no_command_prints_help(tmp_path):
    result = _run_cli(cwd=tmp_path)
    assert result.returncode == 0
    assert "Writing DNA" in (result.stdout + result.stderr)


def test_run_status_runs(tmp_path):
    result = _run_cli("status", cwd=PROJECT_ROOT)
    assert result.returncode == 0
    assert "项目状态" in result.stdout


def test_run_extract_wires_input_flag(monkeypatch, tmp_path):
    """
    run.py extract 必须用 --input 把文件传给 extract_dna（否则 argparse 报错）。

    bug ①（已修）：cmd_extract 原本把文件当位置参数传，extract_dna argparse 要求
    --input，导致 `run.py extract` / `auto` 提取步骤报错退出。
    """
    import argparse

    import run
    fake = [tmp_path / "a.md", tmp_path / "b.md"]
    monkeypatch.setattr(run, "_visible_files", lambda p, patterns=("*",): fake)
    captured: dict = {}
    monkeypatch.setattr(run, "_run_script",
                        lambda script, args: captured.update(script=script, args=args) or 0)

    run.cmd_extract(argparse.Namespace(user_name="tester"))
    assert captured.get("script") == "extract_dna.py"
    assert "--input" in captured["args"], "cmd_extract 仍用位置参数传文件，会触发 extract_dna 的 argparse 错误"


def test_sample_sufficiency_survives_fewer_than_5_docs(diverse_casual_dir, tmp_path):
    """
    bug ②（已修）：test_sample_sufficiency.py 在样本 <5 篇时崩溃
    （KeyError: 'avg_top6_overlap'，综合建议表假设有 4/5 篇组合）。
    充足性检查器必须能处理“样本不充足”这一最该被检查的情形。
    """
    out_json = tmp_path / "suf.json"
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "test_sample_sufficiency.py"),
         "--input", str(diverse_casual_dir), "--output-json", str(out_json)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert result.returncode == 0, f"<5 篇样本不应崩溃:\n{result.stdout}\n{result.stderr}"
    assert out_json.exists()
