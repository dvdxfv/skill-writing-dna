"""
T1 验收层 · #2 把样本预检并入第一确认点。

现在应 RED（run.py 尚未提供预检 seam）。实现后应 GREEN。

目标契约（实现可调整函数名，但行为必须满足）：
  run._sample_precheck_summary(stripped_dir) -> str | None
    返回一行人话结论（含 ✅/⚠️/❌ 之一），供 cmd_pipeline 在「模板剥留确认」
    消息里一并展示。不新增第 4 个停等点，所以这是「附加到已有确认点」的取数口子。

注意：闸门是“提示/软阻断”，不是硬阻断；run.py extract 单独调用不被它拦——
该向后兼容性由 test_regression_existing.test_run_extract_without_samples_is_friendly 守。
对话层的软提示/触发词识别属 T3，见 ACCEPTANCE_CHECKLIST.md。
"""

from pathlib import Path

import pytest

import run


def test_precheck_seam_exists():
    assert hasattr(run, "_sample_precheck_summary"), \
        "#2 未实现：run.py 缺少 _sample_precheck_summary 取数口"


def test_precheck_seam_returns_one_line_verdict(diverse_casual_dir):
    summary = run._sample_precheck_summary(diverse_casual_dir)
    assert isinstance(summary, str) and summary.strip(), "应返回非空一行结论"
    assert any(mark in summary for mark in ("✅", "⚠️", "❌")), \
        "结论应带分级标记，便于用户一眼看懂"
    assert "\n" not in summary.strip(), "确认消息防臃肿：只给一行结论"


def test_precheck_seam_handles_empty_dir(tmp_path):
    """空目录不应抛异常（预检拿不到样本就返回 None，由调用方决定）。"""
    summary = run._sample_precheck_summary(tmp_path)
    assert summary is None or isinstance(summary, str)
