"""
T1 验收层 · #5 DNA 版本管理 + 回滚。

现在应 RED（scripts/dna_versioning.py 尚未实现）。实现后应 GREEN。

定义的目标契约（实现可调整 import 路径，但行为必须满足）：
  scripts/dna_versioning.py 提供
    save_new_version(profiles_dir, user, dna_dict) -> Path   # 写 <user>-dna-vN.json 并更新 <user>-dna.json 指针
    list_versions(profiles_dir, user) -> list[int]
    rollback(profiles_dir, user, n) -> Path                  # 把 vN 内容写回 <user>-dna.json 指针
    diff_versions(profiles_dir, user, a, b) -> dict          # 版本对比

关键护栏：版本快照用 <user>-dna-vN.json 命名，当前版指针固定 <user>-dna.json，
这样 run.py 的 `*-dna.json` 发现 glob 只会命中指针（见 test_regression_existing
中 test_visible_files_glob_ignores_versioned_dna）。
"""

import json
from pathlib import Path

import pytest

dna_versioning = pytest.importorskip(
    "dna_versioning",
    reason="#5 未实现：scripts/dna_versioning.py 不存在（预期 RED）",
)


def _dna(**over):
    base = {"user_name": "tester", "schema_version": "1.0", "signature_phrases": ["说真的"]}
    base.update(over)
    return base


def test_save_creates_versioned_snapshot_and_pointer(tmp_path):
    v1 = dna_versioning.save_new_version(tmp_path, "tester", _dna(note="第一次"))
    assert v1.name == "tester-dna-v1.json"
    pointer = tmp_path / "tester-dna.json"
    assert pointer.exists(), "应同时维护当前版指针 tester-dna.json"


def test_second_save_increments_version(tmp_path):
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["A"]))
    v2 = dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["B"]))
    assert v2.name == "tester-dna-v2.json"
    assert sorted(dna_versioning.list_versions(tmp_path, "tester")) == [1, 2]


def test_pointer_reflects_latest(tmp_path):
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["A"]))
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["B"]))
    pointer = json.loads((tmp_path / "tester-dna.json").read_text(encoding="utf-8"))
    assert pointer["signature_phrases"] == ["B"], "指针应指向最新版"


def test_rollback_restores_old_version(tmp_path):
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["A"]))
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["B"]))
    dna_versioning.rollback(tmp_path, "tester", 1)
    pointer = json.loads((tmp_path / "tester-dna.json").read_text(encoding="utf-8"))
    assert pointer["signature_phrases"] == ["A"], "回滚后指针应等于 v1 内容"
    # 回滚不删历史快照
    assert (tmp_path / "tester-dna-v1.json").exists()
    assert (tmp_path / "tester-dna-v2.json").exists()


def test_diff_versions_reports_change(tmp_path):
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["A"]))
    dna_versioning.save_new_version(tmp_path, "tester", _dna(signature_phrases=["A", "B"]))
    diff = dna_versioning.diff_versions(tmp_path, "tester", 1, 2)
    assert diff, "应返回非空差异"
    assert "signature_phrases" in json.dumps(diff, ensure_ascii=False)
