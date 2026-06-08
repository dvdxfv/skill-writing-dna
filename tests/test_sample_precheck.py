"""
T1 验收层 · #1 样本预检：去公文化 + 多维健康度。

现在应 RED（功能未实现）。实现后应 GREEN，证明优化真正落地：
- 去掉公文专用特征
- 新增字数分布 / 文档间相似度 / 重复内容（近重复整篇）维度
- 给出分级 severity（ok / light / serious）供闸门用

黑盒方式：跑脚本生成 JSON，对 JSON 断言（这正是 run.py 实际消费的契约），
不绑定内部函数名，给实现留空间。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRECHECK_SCRIPT = PROJECT_ROOT / "scripts" / "test_sample_sufficiency.py"

# 公文专用特征名——去公文化后不应再出现在产出 JSON 里
GONGWEN_FEATURE_TOKENS = [
    "enum_density", "institution_density", "suggest_density", "deficiency_density",
]


def _run_precheck(input_dir: Path, tmp_path: Path) -> dict:
    out_json = tmp_path / "precheck.json"
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    result = subprocess.run(
        [sys.executable, str(PRECHECK_SCRIPT),
         "--input", str(input_dir), "--output-json", str(out_json)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert result.returncode == 0, f"预检脚本异常退出:\n{result.stdout}\n{result.stderr}"
    assert out_json.exists(), "预检未产出 JSON"
    return json.loads(out_json.read_text(encoding="utf-8"))


def test_precheck_runs_on_non_gongwen_samples(diverse_casual_dir, tmp_path):
    """非公文样本也能跑出结论、不崩溃。"""
    data = _run_precheck(diverse_casual_dir, tmp_path)
    assert data, "应产出非空结果"


def test_precheck_output_has_no_gongwen_features(diverse_casual_dir, tmp_path):
    """去公文化：产出 JSON 不再含公文专用特征名。"""
    data = _run_precheck(diverse_casual_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    leaked = [t for t in GONGWEN_FEATURE_TOKENS if t in blob]
    assert not leaked, f"产出里仍有公文特征: {leaked}"


def test_precheck_reports_length_distribution(has_short_doc_dir, tmp_path):
    """新增维度：字数分布，并能标出超短篇。"""
    data = _run_precheck(has_short_doc_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    assert "length_distribution" in blob or "字数分布" in blob, "缺少字数分布维度"
    # 含一篇超短文，应被标记
    assert "short" in blob.lower() or "超短" in blob or "过短" in blob


def test_precheck_reports_inter_doc_similarity(diverse_casual_dir, tmp_path):
    """新增维度：文档间相似度。"""
    data = _run_precheck(diverse_casual_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    assert ("similarity" in blob.lower()) or ("相似度" in blob), "缺少相似度维度"


def test_precheck_detects_near_duplicate_docs(near_dup_dir, tmp_path):
    """新增维度：近重复整篇检测（strip_template 行级对齐抓不到的）。"""
    data = _run_precheck(near_dup_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    assert ("near_dup" in blob.lower()) or ("近重复" in blob) or ("duplicate" in blob.lower()), \
        "未体现近重复检测维度"
    # 近重复对应被实际标出（report_draft vs report_final）
    assert "report_draft.md" in blob and "report_final.md" in blob, "未指出哪两篇近重复"


def test_precheck_emits_severity_grade(diverse_casual_dir, tmp_path):
    """分级闸门依据：severity ∈ {ok, light, serious}。"""
    data = _run_precheck(diverse_casual_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    assert "severity" in blob, "缺少分级字段 severity（闸门分级依据）"


def test_precheck_near_dup_triggers_serious(near_dup_dir, tmp_path):
    """三篇里两篇近重复（等于只有 2 篇不同）→ 应判严重（软阻断档）。"""
    data = _run_precheck(near_dup_dir, tmp_path)
    blob = json.dumps(data, ensure_ascii=False)
    assert "serious" in blob, "多数近重复应触发 serious 分级"
