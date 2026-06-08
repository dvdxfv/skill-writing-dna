#!/usr/bin/env python3
"""Check that public tool entrypoints keep critical Writing DNA instructions in sync."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ENTRYPOINTS = [
    "SKILL.md",
    "WRITING_DNA.md",
    ".github/copilot-instructions.md",
    ".claude/commands/writing-dna.md",
    ".cursor/commands/writing-dna.md",
    ".codex/prompts/writing-dna.md",
    ".trae/skills/writing-dna/SKILL.md",
]

REQUIRED_MARKERS = [
    "信息无损",
    "黑名单",
    "签名",
    "句长",
    "回上一版",
    "没应用",
    "按章节",
    "remove AI flavor",
    "make it sound like me",
    "personal writing style",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_sync(root: Path) -> dict:
    files = {}
    missing = {}
    for rel in ENTRYPOINTS:
        path = root / rel
        if not path.exists():
            missing[rel] = ["<file missing>"]
            continue
        text = path.read_text(encoding="utf-8")
        absent = [marker for marker in REQUIRED_MARKERS if marker not in text]
        files[rel] = {"missing_markers": absent}
        if absent:
            missing[rel] = absent
    return {
        "status": "ok" if not missing else "drift",
        "files": files,
        "missing": missing,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Writing DNA tool-entrypoint sync.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = check_sync(repo_root())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "ok":
        print("OK: tool entrypoints contain the required sync markers.")
    else:
        print("DRIFT: tool entrypoints are missing required markers.", file=sys.stderr)
        for rel, markers in result["missing"].items():
            print(f"- {rel}: {', '.join(markers)}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
