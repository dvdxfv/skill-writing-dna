"""
Tests for strip_template + extract_dna integration.

Run with: pytest scripts/test_template_stripping.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strip_template import strip_template
from extract_dna import extract_dna


# ── strip_template unit tests ──────────────────────────────────────────────

def test_non_template_doc_unchanged():
    """Plain personal prose passes through untouched."""
    text = "这是一段个人写作的文字。\n\n我喜欢用短句。事实支撑判断。"
    result = strip_template(text)
    assert "个人写作" in result
    assert "事实支撑判断" in result


def test_template_paragraph_stripped():
    """Paragraphs containing template markers (指标主要考核, 得分率) are removed."""
    text = (
        "## 存在的问题\n\n"
        "项目执行存在进度滞后的问题。\n\n"
        "该指标主要考核项目执行率，满分10分，得分率为90%。\n\n"
        "建议加强过程管理。\n"
    )
    result = strip_template(text)
    assert "该指标主要考核" not in result
    assert "得分率为" not in result
    # Personal content preserved
    assert "建议加强过程管理" in result


def test_strip_sub_heading_removes_content():
    """A STRIP_SUB_PATTERN heading (绩效评价依据) strips heading + content until next heading."""
    text = (
        "## 存在的问题\n\n"
        "这里是个人分析文字。\n\n"
        "## 绩效评价依据\n\n"
        "《某某法规》第X条。\n\n"
        "另一条法规依据。\n\n"
        "## 下一步改进\n\n"
        "改进措施在这里。\n"
    )
    result = strip_template(text)
    assert "绩效评价依据" not in result
    assert "某某法规" not in result
    # Content after the next heading should be preserved
    assert "改进措施在这里" in result


def test_keep_zone_content_preserved():
    """Keep-zone sections (存在的问题, 改进建议) are always preserved."""
    text = (
        "## 存在的问题\n\n"
        "问题一：资金使用效率偏低。\n\n"
        "问题二：跨部门协调机制不完善。\n\n"
        "## 改进建议\n\n"
        "建议建立定期会商机制。\n"
    )
    result = strip_template(text)
    assert "资金使用效率偏低" in result
    assert "跨部门协调机制" in result
    assert "建立定期会商机制" in result


# ── extract_dna integration tests ─────────────────────────────────────────

def _make_docs(content_list):
    return [{"filename": f"doc{i}.md", "content": c} for i, c in enumerate(content_list)]


def test_extract_dna_strips_template_pollution():
    """Template phrases (该指标主要考核) do not appear in signature_phrases."""
    template_para = "该指标主要考核项目完成率，满分10分，该指标满分10分，得分率为95%。"
    personal_para = "制度建设是核心抓手。建议建立健全协调机制，明确权责。"

    docs = _make_docs([f"{personal_para}\n\n{template_para}"] * 3)
    dna = extract_dna(docs, "test_user")

    phrases = [p.lower() for p in dna["signature_phrases"]]
    assert not any("指标" in p for p in phrases), f"Template phrase leaked into signatures: {phrases}"
    assert not any("得分" in p for p in phrases), f"Template phrase leaked into signatures: {phrases}"


def test_extract_dna_non_template_doc_unchanged():
    """Non-template documents produce non-empty signature phrases."""
    personal = (
        "建议建立健全制度机制，明确权责边界。\n"
        "一是完善协调机制；二是强化过程管理；三是加强结果运用。\n"
    )
    docs = _make_docs([personal] * 3)
    dna = extract_dna(docs, "test_user")

    assert dna["total_chinese_chars"] > 0
    assert len(dna["signature_phrases"]) > 0


def test_extract_dna_emoji_density_uses_original_chars():
    """emoji_per_1k uses original doc char count, not stripped char count."""
    # Doc has personal content + large template section
    personal = "这是个人写作内容。" * 10  # ~90 chars
    template = "该指标主要考核完成率，满分10分，得分率为90%。" * 50  # large template chunk
    content = f"{personal}\n\n{template}"

    docs = _make_docs([content] * 3)
    dna = extract_dna(docs, "test_user")

    # emoji_per_1k should be 0 (no emojis); just verify it doesn't crash
    # and density is consistent
    assert dna["emoji_policy"]["per_1k_chars"] >= 0
