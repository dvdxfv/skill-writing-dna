"""
T2 静态一致性层：确定性文本检查。

已做的应 GREEN，没做的应 RED。这层不证明「模型会照做」（那是 T3 人工验收），
只证明「该写进 prompt / 该删的代码」这些客观事实成立。
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# #3：被各指令文件同步的核心文件集
MIRROR_FILES = [
    "SKILL.md",
    "WRITING_DNA.md",
    ".github/copilot-instructions.md",
    ".claude/commands/writing-dna.md",
    ".cursor/commands/writing-dna.md",
    ".codex/prompts/writing-dna.md",
    ".trae/skills/writing-dna/SKILL.md",
]

# #4：英文自然语言触发词
ENGLISH_TRIGGERS = ["remove AI flavor", "make it sound like me", "personal writing style"]

# #1：去公文化后，预检脚本源码不应再出现的公文专用特征名
GONGWEN_TOKENS = ["enum_density", "institution_density", "suggest_density", "deficiency_density"]

# 可见性自查（必要条件，行为见 T3）：实现后这些指令应出现在 SKILL.md
VISIBILITY_MARKERS = [
    "回上一版",   # #5 DNA 版本回滚的对话入口
    "没应用",     # #3/可见性：Step4 露出被跳过/降权的规则
    "按章节",     # #6 长文档分段时主动告知
]


def _read(rel: str) -> str | None:
    p = PROJECT_ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


def _in_order(text: str, tokens: list[str]) -> bool:
    pos = 0
    for tok in tokens:
        idx = text.find(tok, pos)
        if idx < 0:
            return False
        pos = idx + len(tok)
    return True


# ── #3 约束优先级（顺序 + 同步）────────────────────────────
PRIORITY_TOKENS = ["信息无损", "黑名单", "签名", "句长"]


def test_priority_order_in_skill():
    text = _read("SKILL.md")
    assert text, "SKILL.md 不存在"
    assert _in_order(text, PRIORITY_TOKENS), "SKILL.md 未按 信息无损>黑名单>签名>句长 顺序写明优先级"


@pytest.mark.parametrize("rel", MIRROR_FILES)
def test_priority_order_synced_to_mirror(rel):
    text = _read(rel)
    if text is None:
        pytest.skip(f"镜像文件不存在: {rel}")
    assert _in_order(text, PRIORITY_TOKENS), f"{rel} 未同步同一份优先级顺序"


# ── #4 英文触发词 ─────────────────────────────────────────
@pytest.mark.parametrize("phrase", ENGLISH_TRIGGERS)
def test_english_trigger_present_somewhere(phrase):
    """至少在 SKILL.md / WRITING_DNA.md / README_EN.md 之一里出现。"""
    blob = "".join(_read(f) or "" for f in ("SKILL.md", "WRITING_DNA.md", "README_EN.md"))
    assert phrase in blob, f"缺少英文触发词: {phrase}"


# ── #1 去公文化（源码层）──────────────────────────────────
@pytest.mark.parametrize("token", GONGWEN_TOKENS)
def test_precheck_source_drops_gongwen_features(token):
    text = _read("scripts/test_sample_sufficiency.py")
    assert text, "预检脚本不存在"
    assert token not in text, f"预检脚本仍含公文专用特征: {token}（去公文化未完成）"


# ── 可见性自查：指令是否写入 SKILL.md（必要条件）──────────
@pytest.mark.parametrize("marker", VISIBILITY_MARKERS)
def test_visibility_instruction_in_skill(marker):
    text = _read("SKILL.md") or ""
    assert marker in text, (
        f"SKILL.md 未写入可见性指令「{marker}」——功能存在但交互无入口=白写。"
        f"（注：这是必要条件，模型实际行为见 T3 人工验收清单）"
    )
