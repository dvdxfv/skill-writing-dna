#!/usr/bin/env python3
"""
DNA 版本管理 + 回滚。

用户修正 DNA 后不该只覆盖旧文件——这里保留历史版本，并支持回滚 / 版本对比。

命名约定（关键护栏，见 PROJECT_STATUS 2026-05-24 #5）：
  <user>-dna.json        当前版本「指针」——run.py 的 `*-dna.json` 发现 glob 只命中它
  <user>-dna-vN.json     版本快照（`-vN` 后缀不会被 `*-dna.json` 匹配，故不污染发现逻辑）

回滚 = 把某个 vN 快照写回指针；快照本身永远保留，不删。

典型用法（由 SKILL.md 在对话中驱动）：
  - 用户确认 / 修正 DNA 后 → save_new_version(...)：自动 +1 版并更新指针
  - 用户说「用回上一版」 → rollback(..., n)
  - 用户说「跟上一版比比」 → diff_versions(..., a, b)
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_VERSION_RE = re.compile(r"-dna-v(\d+)\.json$")
_META_KEYS = {"version", "saved_at", "revision_note"}  # 版本元数据，不参与内容 diff


def _pointer_path(profiles_dir: Path | str, user: str) -> Path:
    return Path(profiles_dir) / f"{user}-dna.json"


def _version_path(profiles_dir: Path | str, user: str, n: int) -> Path:
    return Path(profiles_dir) / f"{user}-dna-v{n}.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_versions(profiles_dir: Path | str, user: str) -> list[int]:
    """返回已存在的版本号列表（升序）。"""
    profiles_dir = Path(profiles_dir)
    if not profiles_dir.exists():
        return []
    versions = []
    for p in profiles_dir.glob(f"{user}-dna-v*.json"):
        m = _VERSION_RE.search(p.name)
        if m:
            versions.append(int(m.group(1)))
    return sorted(versions)


def save_new_version(profiles_dir: Path | str, user: str, dna_dict: dict,
                     note: str | None = None) -> Path:
    """
    保存为新版本快照 <user>-dna-vN.json，并把当前版指针 <user>-dna.json 指向它。
    返回新版本快照的路径。
    """
    profiles_dir = Path(profiles_dir)
    existing = list_versions(profiles_dir, user)
    n = (max(existing) + 1) if existing else 1

    snapshot: dict[str, Any] = dict(dna_dict)
    snapshot["version"] = n
    snapshot["saved_at"] = datetime.now().isoformat(timespec="seconds")
    if note is not None:
        snapshot["revision_note"] = note

    vpath = _version_path(profiles_dir, user, n)
    _write_json(vpath, snapshot)
    _write_json(_pointer_path(profiles_dir, user), snapshot)  # 指针 = 最新版
    return vpath


def rollback(profiles_dir: Path | str, user: str, n: int) -> Path:
    """把版本 n 的快照写回当前版指针；不删任何快照。返回指针路径。"""
    vpath = _version_path(profiles_dir, user, n)
    if not vpath.exists():
        raise FileNotFoundError(f"版本不存在：{vpath}")
    data = json.loads(vpath.read_text(encoding="utf-8"))
    pointer = _pointer_path(profiles_dir, user)
    _write_json(pointer, data)
    return pointer


def diff_versions(profiles_dir: Path | str, user: str, a: int, b: int) -> dict:
    """对比版本 a 与 b 的内容差异（忽略版本元数据），返回 {字段: {from, to}}。"""
    da = json.loads(_version_path(profiles_dir, user, a).read_text(encoding="utf-8"))
    db = json.loads(_version_path(profiles_dir, user, b).read_text(encoding="utf-8"))
    diff: dict[str, dict] = {}
    for key in set(da) | set(db):
        if key in _META_KEYS:
            continue
        if da.get(key) != db.get(key):
            diff[key] = {"from": da.get(key), "to": db.get(key)}
    return diff
