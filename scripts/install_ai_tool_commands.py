#!/usr/bin/env python3
"""Install Writing DNA command entrypoints for common AI coding tools."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallTarget:
    tool: str
    scope: str
    source: Path
    destination: Path
    note: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def home() -> Path:
    return Path.home()


def build_targets(root: Path, project: Path | None) -> list[InstallTarget]:
    user_home = home()
    project_root = project or root

    return [
        InstallTarget(
            "codex",
            "user",
            root / ".codex" / "prompts" / "writing-dna.md",
            user_home / ".codex" / "prompts" / "writing-dna.md",
            "Restart Codex after installing.",
        ),
        InstallTarget(
            "codex",
            "project",
            root / ".codex" / "prompts" / "writing-dna.md",
            project_root / ".codex" / "prompts" / "writing-dna.md",
        ),
        InstallTarget(
            "claude",
            "user",
            root / ".claude" / "commands" / "writing-dna.md",
            user_home / ".claude" / "commands" / "writing-dna.md",
        ),
        InstallTarget(
            "claude",
            "project",
            root / ".claude" / "commands" / "writing-dna.md",
            project_root / ".claude" / "commands" / "writing-dna.md",
        ),
        InstallTarget(
            "cursor",
            "project",
            root / ".cursor" / "commands" / "writing-dna.md",
            project_root / ".cursor" / "commands" / "writing-dna.md",
            "Cursor custom commands are project-scoped.",
        ),
        InstallTarget(
            "trae",
            "user",
            root / ".trae" / "skills" / "writing-dna" / "SKILL.md",
            user_home / ".trae" / "skills" / "writing-dna" / "SKILL.md",
            "Best-effort Trae/Solo user-level skill install path.",
        ),
        InstallTarget(
            "trae",
            "project",
            root / ".trae" / "skills" / "writing-dna" / "SKILL.md",
            project_root / ".trae" / "skills" / "writing-dna" / "SKILL.md",
        ),
    ]


def install(target: InstallTarget, dry_run: bool) -> str:
    if not target.source.exists():
        return f"MISS {target.tool}:{target.scope} source not found: {target.source}"

    if target.source.resolve() == target.destination.resolve():
        return f"SKIP {target.tool}:{target.scope} already in place: {target.destination}"

    if dry_run:
        return f"DRY  {target.tool}:{target.scope} {target.source} -> {target.destination}"

    target.destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target.source, target.destination)
    suffix = f" ({target.note})" if target.note else ""
    return f"OK   {target.tool}:{target.scope} -> {target.destination}{suffix}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register the Writing DNA slash command / skill entrypoints for AI tools."
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        choices=["all", "codex", "claude", "cursor", "trae"],
        default=["all"],
        help="Tools to install for. Default: all.",
    )
    parser.add_argument(
        "--scope",
        choices=["all", "user", "project"],
        default="all",
        help="Install user-level commands, project-level commands, or both. Default: all.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Target project root for project-scoped commands. Default: this repository.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    project = args.project.resolve() if args.project else None
    tools = {"codex", "claude", "cursor", "trae"} if "all" in args.tools else set(args.tools)

    targets = [
        target
        for target in build_targets(root, project)
        if target.tool in tools and (args.scope == "all" or target.scope == args.scope)
    ]

    for target in targets:
        print(install(target, args.dry_run))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
