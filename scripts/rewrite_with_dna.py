#!/usr/bin/env python3
"""
Rewrite a draft using a DNA profile and optional template profile.

读取DNA画像 → 检测AI套话 → 按个人风格规则改写 → 输出改写稿+调试信息

改写优先级（与 SKILL.md「改写规则（按优先级）」一致；多目标冲突时序号靠前者优先）：
  1. 信息无损  2. 黑名单硬清除  3. 签名短语自然植入  4. 句长/节奏对齐
本脚本是确定性辅助工具：执行顺序固定为 黑名单清除 → 连接词替换 → 签名植入 → 开头调整，
已先清黑名单后植签名，符合上述优先级；不要为植入签名而反序破坏信息。真正的语义级改写
由对话中的 LLM 按上述优先级完成。
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


try:
    from ai_slop_dict import ALL_SLOP, detect_slop
except ImportError:
    ALL_SLOP = {}
    def detect_slop(text):
        return {"hits": [], "score": 0}


BLACKLIST_SAFE_REPLACEMENTS = {
    "在数字化转型的浪潮中": "当前",
    "在数字化转型的大背景下": "当前",
    "数字化转型": "数字技术应用",
    "顶层设计": "统筹安排",
    "多元化": "多样",
    "多维度": "多角度",
    "构建": "建设",
    "赋能": "支持",
    "重塑": "调整",
    "生态": "体系",
    "卓越的": "较好的",
    "完善的": "较完整的",
    "一站式": "系统性",
    "综上所述": "总体来看",
    "总而言之": "整体来看",
}

BLACKLIST_SAFE_DELETIONS = {
    "首先",
    "其次",
    "再次",
    "最后",
    "首先，",
    "其次，",
    "再次，",
    "最后，",
}


def load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def get_blacklist(dna: dict) -> list[str]:
    if "blacklist_phrases" in dna:
        return dna["blacklist_phrases"]
    return []


def get_signatures(dna: dict) -> list[str]:
    if "signature_phrases" in dna:
        return dna["signature_phrases"][:15]
    return []


def get_rewrite_rules(dna: dict) -> list[str]:
    if "rewrite_rules" in dna:
        return dna["rewrite_rules"]
    return []


def get_sentence_config(dna: dict) -> dict[str, Any]:
    sf = dna.get("sentence_features", {})
    return {
        "avg_length": sf.get("avg_length_chars", 40),
        "short_ratio": sf.get("short_sentence_ratio", 0.5),
        "max_length": 50,
    }


def get_openers(dna: dict) -> list[str]:
    return dna.get("openers", [])


def get_closers(dna: dict) -> list[str]:
    return dna.get("closers", [])


def detect_ai_slop_in_text(text: str, blacklist: list[str]) -> dict[str, Any]:
    slop_result = detect_slop(text)
    extra_hits = []
    for phrase in blacklist:
        if phrase in text:
            positions = [m.start() for m in re.finditer(re.escape(phrase), text)]
            extra_hits.append({"phrase": phrase, "positions": positions})
    all_hits = slop_result["hits"] + extra_hits
    return {
        "score": slop_result["score"],
        "slop_hits": slop_result["hits"],
        "blacklist_hits": extra_hits,
        "total_hits_count": len(all_hits),
    }


def cleanup_punctuation(text: str) -> str:
    """Clean punctuation scars left by deterministic phrase replacement."""
    text = re.sub(r"^[，,、；;：:\s]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"([。！？；;])\s*[，,、；;：:]+", r"\1", text)
    text = re.sub(r"[，,、；;：:]{2,}", "，", text)
    text = re.sub(r"，[、，]+", "，", text)
    text = re.sub(r"，。", "。", text)
    text = re.sub(r"，([。！？])", r"\1", text)
    text = re.sub(r"\s+([，。！？；：])", r"\1", text)
    return text.strip()


def _safe_delete_phrase(text: str, phrase: str) -> tuple[str, bool]:
    pattern = re.compile(rf"(?<!\w){re.escape(phrase)}[，,、]?", re.MULTILINE)
    new_text = pattern.sub("", text)
    return cleanup_punctuation(new_text), new_text != text


def apply_blacklist_removal(text: str, blacklist: list[str]) -> tuple[str, list[dict]]:
    removed = []
    for phrase in sorted(blacklist, key=len, reverse=True):
        count = text.count(phrase)
        if count > 0:
            if phrase in BLACKLIST_SAFE_REPLACEMENTS:
                replacement = BLACKLIST_SAFE_REPLACEMENTS[phrase]
                text = text.replace(phrase, replacement)
                removed.append({
                    "phrase": phrase,
                    "removed_count": count,
                    "action": "replaced",
                    "replacement": replacement,
                })
            elif phrase in BLACKLIST_SAFE_DELETIONS:
                text, changed = _safe_delete_phrase(text, phrase)
                if changed:
                    removed.append({"phrase": phrase, "removed_count": count, "action": "deleted"})
            else:
                removed.append({
                    "phrase": phrase,
                    "removed_count": count,
                    "action": "deferred",
                    "reason": "需要语义改写，确定性删除可能破坏句子",
                })
    return cleanup_punctuation(text), removed


def remove_ai_connectors(text: str) -> tuple[str, list[str]]:
    connectors = [
        ("首先，", ""), ("其次，", ""), ("再次，", ""), ("最后，", ""),
        ("综上所述", "总体来看"), ("总而言之", "整体来看"),
        ("在...的浪潮中", ""), ("在...的大背景下", ""),
        ("赋能", "支撑"), ("重塑", "优化"), ("生态", "体系"),
        ("卓越的", "显著的"), ("完善的", "健全的"),
        ("一站式", "系统性"),
    ]
    removed = []
    for pattern, replacement in connectors:
        if pattern in text:
            text = text.replace(pattern, replacement)
            removed.append(pattern)
    return text, removed


def apply_signature_injection(text: str, signatures: list[str], rate_per_200chars: int = 1) -> tuple[str, list[str]]:
    """Return signature phrases that already appear naturally.

    This helper intentionally does not inject text. Mechanical insertion made
    earlier acceptance outputs less readable; semantic placement belongs to the
    conversation LLM and the post-rewrite validation report.
    """
    if not signatures or not text:
        return text, []
    matched = []
    for sig in signatures:
        if sig and sig in text and sig not in matched:
            matched.append(sig)
    return text, matched


def suggest_signature_candidates(text: str, signatures: list[str], limit: int = 5) -> list[str]:
    """List signature phrases that could be considered in a second LLM pass."""
    return [sig for sig in signatures if sig and sig not in text][:limit]


def analyze_opener_alignment(text: str, openers: list[str]) -> dict[str, Any]:
    first = next((s.strip() for s in re.split(r"[。！？!?\n]+", text) if s.strip()), "")
    openers = [o for o in openers if isinstance(o, str) and o.strip()]
    if not first or not openers:
        return {"status": "unknown", "first_sentence": first[:80], "best_match": None, "score": None}

    def prefix_score(a: str, b: str) -> float:
        limit = min(len(a), len(b), 20)
        if limit == 0:
            return 0.0
        same = 0
        for i in range(limit):
            if a[i] != b[i]:
                break
            same += 1
        return same / limit

    best = max(openers, key=lambda opener: prefix_score(first, opener))
    score = round(prefix_score(first, best), 3)
    return {
        "status": "ok" if score >= 0.35 else "review",
        "first_sentence": first[:80],
        "best_match": best[:80],
        "score": score,
    }


def adjust_opener(text: str, openers: list[str]) -> str:
    """Keep text unchanged; opener fit is reported via analyze_opener_alignment."""
    return text


def build_debug_info(
    original: str,
    rewritten: str,
    dna: dict,
    slop_before: dict,
    slop_after: dict,
    removed_blacklist: list[dict],
    removed_connectors: list[str],
    injected_signatures: list[str],
    signature_suggestions: list[str] | None = None,
    opener_alignment: dict[str, Any] | None = None,
) -> dict:
    uncertain = dna.get("uncertain_candidates", [])
    applied_uncertain = [
        item for item in uncertain
        if item in injected_signatures or (isinstance(item, str) and item in rewritten)
    ]
    not_applied_uncertain = [
        item for item in uncertain
        if item not in applied_uncertain
    ]
    return {
        "schema_version": "1.0",
        "status": "completed",
        "dna_source": dna.get("user_name") or dna.get("author", "unknown"),
        "stats": {
            "original_char_count": len(original),
            "rewritten_char_count": len(rewritten),
            "char_change_ratio": round(len(rewritten) / max(len(original), 1), 2),
        },
        "ai_slop": {
            "before": {"score": slop_before["score"], "hit_count": slop_before["total_hits_count"]},
            "after": {"score": slop_after["score"], "hit_count": slop_after["total_hits_count"]},
        },
        "changes": {
            "blacklist_phrases_removed": removed_blacklist,
            "ai_connectors_removed": removed_connectors,
            "signature_phrases_injected": injected_signatures,  # backward-compatible key
            "signature_phrases_matched": injected_signatures,
            "signature_phrase_suggestions": signature_suggestions or [],
            "opener_alignment": opener_alignment or {},
        },
        "dna_rules_applied": get_rewrite_rules(dna),
        "skipped_dna_rules": {
            "downgraded": list(dna.get("downgraded_features", {}).keys()) if "downgraded_features" in dna else [],
            "not_applied": not_applied_uncertain,
            "applied_uncertain_candidates": applied_uncertain,
        },
    }


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Rewrite a draft with a DNA profile.")
    parser.add_argument("--draft", required=True, help="Input draft markdown or text file")
    parser.add_argument("--dna", required=True, help="DNA profile JSON path")
    parser.add_argument("--template", help="Optional template profile JSON path")
    parser.add_argument("--output-md", required=True, help="Rewritten markdown output path")
    parser.add_argument("--output-json", required=True, help="Rewrite debug JSON output path")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    dna = load_json(args.dna)

    original_clean = clean_markdown(draft_text)
    blacklist = get_blacklist(dna)
    signatures = get_signatures(dna)
    sentence_cfg = get_sentence_config(dna)
    openers = get_openers(dna)
    closers = get_closers(dna)

    slop_before = detect_ai_slop_in_text(original_clean, blacklist)

    text = original_clean
    text, removed_bl = apply_blacklist_removal(text, blacklist)
    text, removed_conn = remove_ai_connectors(text)
    text, injected_sigs = apply_signature_injection(text, signatures)
    signature_suggestions = suggest_signature_candidates(text, signatures)
    text = adjust_opener(text, openers)
    opener_alignment = analyze_opener_alignment(text, openers)

    slop_after = detect_ai_slop_in_text(text, blacklist)

    debug = build_debug_info(
        original_clean, text, dna,
        slop_before, slop_after,
        removed_bl, removed_conn, injected_sigs,
        signature_suggestions=signature_suggestions,
        opener_alignment=opener_alignment,
    )

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    output_md.write_text(text, encoding="utf-8")
    output_json.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 改写完成:")
    print(f"   原文字数: {debug['stats']['original_char_count']}")
    print(f"   改写字数: {debug['stats']['rewritten_char_count']}")
    print(f"   AI味分数: {slop_before['score']} → {slop_after['score']}")
    print(f"   清除黑名单词: {len(removed_bl)} 个")
    print(f"   清除AI连接词: {len(removed_conn)} 个")
    print(f"   自然命中签名表达: {len(injected_sigs)} 个")
    print(f"   输出文件: {output_md}")
    print(f"   调试信息: {output_json}")


if __name__ == "__main__":
    main()
