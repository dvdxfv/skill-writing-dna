"""
pytest 公共配置 + 受控 fixture。

设计说明
--------
本套件分三层（详见 tests/ACCEPTANCE_CHECKLIST.md 与 PROJECT_STATUS.md 2026-05-24 段）：

- T1 代码行为：确定性，pytest 可测。新功能现在应 RED，回归应 GREEN。
- T2 静态一致性：grep/文本断言，确定性。已做的 GREEN，没做的 RED。
- T3 对话验收：prompt 层 LLM 行为，pytest 测不了，见 ACCEPTANCE_CHECKLIST.md 人工走。

fixture 一律用受控的小样本（在 tmp 里现造），不依赖 inputs/ 下的真实大文件，
保证测试确定、可重复。
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 让 import extract_dna / rewrite_with_dna / run 等脚本可用
for p in (str(PROJECT_ROOT), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


# ── 受控样本 ──────────────────────────────────────────────

def _write_docs(target: Path, docs: dict[str, str]) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    for name, content in docs.items():
        (target / name).write_text(content, encoding="utf-8")
    return target


# 三篇“非公文 / 口语随性”样本：用于验证去公文化（公文特征对它们应无意义）
_CASUAL_1 = """周末又去爬山了。说真的，山顶那阵风一吹，整个人都活过来了。
我一直觉得，与其在家刷手机，不如出门走走。哪怕只是小区楼下转一圈，心情也不一样。
这次带了相机，拍了几张云。云这东西，你越想拍好它越不配合，挺有意思的。
回来路上买了个烤红薯，烫手，但是真香。"""

_CASUAL_2 = """聊聊我最近在用的笔记法。以前我总想着把所有东西都记下来，结果什么都记不住。
后来想明白了：记笔记不是为了存档，是为了忘得安心。
所以现在我只记三种东西——让我兴奋的、让我困惑的、和我打算下周就动手的。
其它的，忘了就忘了吧，真重要的会自己回来找你。"""

_CASUAL_3 = """养了一只猫之后，我对“边界感”这个词有了新理解。
它想让你撸的时候，会主动凑过来；不想的时候，你伸手它就走。从不解释，也不内疚。
人要是能有它这份坦荡，估计能少很多内耗。
当然，它也会半夜两点在我脸上踩来踩去，所以也别太羡慕。"""


@pytest.fixture
def diverse_casual_dir(tmp_path) -> Path:
    """三篇主题各异的口语样本（健康样本集）。"""
    return _write_docs(tmp_path / "casual", {
        "a.md": _CASUAL_1,
        "b.md": _CASUAL_2,
        "c.md": _CASUAL_3,
    })


@pytest.fixture
def near_dup_dir(tmp_path) -> Path:
    """两篇近重复（初稿 vs 定稿）+ 一篇不同。用于近重复整篇检测。"""
    draft = _CASUAL_1
    final = _CASUAL_1.replace("挺有意思的", "还挺有意思的").replace("真香", "确实香")
    return _write_docs(tmp_path / "neardup", {
        "report_draft.md": draft,
        "report_final.md": final,
        "other.md": _CASUAL_2,
    })


@pytest.fixture
def has_short_doc_dir(tmp_path) -> Path:
    """含一篇超短文（远低于 800 字建议）。用于字数分布检测。"""
    return _write_docs(tmp_path / "short", {
        "long1.md": _CASUAL_1 * 6,
        "long2.md": _CASUAL_2 * 6,
        "tiny.md": "今天没空，改天再写。",
    })


@pytest.fixture
def extract_docs() -> list[dict[str, str]]:
    """给 extract_dna(docs, name) 直接调用的 docs；含跨两篇重复的标志短语。"""
    sig = "于是我决定先动手再说"
    return [
        {"filename": "d1.md", "content": f"{sig}。{_CASUAL_2}\n\n{sig}，反正想多了也没用。"},
        {"filename": "d2.md", "content": f"{_CASUAL_3}\n\n{sig}，结果还真成了。{sig}。"},
    ]


@pytest.fixture
def minimal_dna_file(tmp_path) -> Path:
    """一份最小可用 DNA JSON，给改写/报告/版本测试用。"""
    import json
    dna = {
        "user_name": "tester",
        "schema_version": "1.0",
        "signature_phrases": ["说真的", "先动手再说"],
        "blacklist_phrases": ["赋能", "综上所述", "一站式"],
        "sentence_features": {"avg_length_chars": 22, "short_sentence_ratio": 0.6},
        "paragraph_features": {"paragraph_lines_avg": 2},
        "openers": ["周末又"],
        "closers": ["也别太羡慕"],
        "emoji_policy": {"frequency": "none", "allowed": [], "blocked": []},
    }
    path = tmp_path / "tester-dna.json"
    path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def ai_draft_file(tmp_path) -> Path:
    """一段 AI 味很重的草稿，给改写测试用。"""
    text = (
        "在数字化转型的浪潮中，我们需要赋能业务，打造一站式解决方案。\n\n"
        "首先，要重塑生态。其次，要完善体系。综上所述，这是一个卓越的方案。\n"
    )
    path = tmp_path / "draft.md"
    path.write_text(text, encoding="utf-8")
    return path
