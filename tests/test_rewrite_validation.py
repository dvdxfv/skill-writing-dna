import json
import os
import subprocess
import sys
from pathlib import Path

import validate_rewrite_against_dna as validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = PROJECT_ROOT / "scripts" / "validate_rewrite_against_dna.py"


def _dna():
    return {
        "user_name": "tester",
        "signature_phrases": ["说真的", "先动手再说"],
        "blacklist_phrases": ["赋能", "重塑"],
        "sentence_features": {"avg_length_chars": 12, "short_sentence_ratio": 0.6},
        "openers": ["说真的，"],
    }


def test_validator_detects_blacklist_residuals():
    result = validator.validate_rewrite("说真的，这段仍然在赋能业务。", _dna())
    assert result["blacklist_residuals"]["hit_count"] == 1
    assert result["blacklist_residuals"]["hits"][0]["phrase"] == "赋能"


def test_validator_counts_matched_and_missing_signatures():
    result = validator.validate_rewrite("说真的，这件事可以先试。", _dna())
    sig = result["signature_alignment"]
    assert sig["matched"] == ["说真的"]
    assert sig["missing"] == ["先动手再说"]
    assert sig["suggested_candidates"] == ["先动手再说"]


def test_validator_reports_sentence_length_deviation():
    result = validator.validate_rewrite("这是一个非常非常非常非常非常长的句子，需要被标出来。", _dna())
    sent = result["sentence_alignment"]
    assert sent["target_avg_length_chars"] == 12
    assert sent["avg_length_deviation_ratio"] is not None
    assert sent["status"] == "off"


def test_validator_preserves_skipped_rule_categories():
    debug = {
        "skipped_dna_rules": {
            "downgraded": ["句长不稳"],
            "not_applied": ["先动手再说"],
            "applied_uncertain_candidates": ["说真的"],
        }
    }
    result = validator.validate_rewrite("说真的，这段可以。", _dna(), debug)
    skipped = result["skipped_rules"]
    assert skipped["downgraded"] == ["句长不稳"]
    assert skipped["not_applied"] == ["先动手再说"]
    assert skipped["applied_uncertain_candidates"] == ["说真的"]


def test_validator_cli_writes_json_and_markdown(tmp_path):
    dna_path = tmp_path / "dna.json"
    rewritten_path = tmp_path / "rewritten.md"
    out_json = tmp_path / "validation.json"
    out_md = tmp_path / "validation.md"
    dna_path.write_text(json.dumps(_dna(), ensure_ascii=False), encoding="utf-8")
    rewritten_path.write_text("说真的，这段仍然赋能业务。", encoding="utf-8")

    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--rewritten",
            str(rewritten_path),
            "--dna",
            str(dna_path),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert out_json.exists()
    assert out_md.exists()
    assert "DNA 对齐验证报告" in out_md.read_text(encoding="utf-8")
