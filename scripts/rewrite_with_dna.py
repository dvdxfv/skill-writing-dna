#!/usr/bin/env python3
"""
Rewrite a draft using a DNA profile and optional template profile.

读取DNA画像 → 检测AI套话 → 按个人风格规则改写 → 输出改写稿+调试信息
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


def apply_blacklist_removal(text: str, blacklist: list[str]) -> tuple[str, list[dict]]:
    removed = []
    for phrase in sorted(blacklist, key=len, reverse=True):
        count = text.count(phrase)
        if count > 0:
            text = text.replace(phrase, "")
            removed.append({"phrase": phrase, "removed_count": count})
    return text, removed


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
    if not signatures or not text:
        return text, []
    chars = len(text)
    target_count = max(1, int(chars / 200 * rate_per_200chars))
    target_count = min(target_count, len(signatures), 4)

    paragraphs = text.split("\n\n")
    injected = []
    used = set()
    sig_idx = 0

    for i, para in enumerate(paragraphs):
        if len(injected) >= target_count:
            break
        if para.strip() and len(para) > 100:
            while sig_idx < len(signatures):
                sig = signatures[sig_idx]
                sig_idx += 1
                if sig not in used and sig in para:
                    continue
                if sig not in used:
                    sentences = para.split("。")
                    if len(sentences) > 2:
                        insert_pos = min(2, len(sentences) - 1)
                        sentences[insert_pos] = sentences[insert_pos].rstrip("，。") + f"，{sig}。"
                        paragraphs[i] = "。".join(sentences)
                        injected.append(sig)
                        used.add(sig)
                    break

    return "\n\n".join(paragraphs), injected


def adjust_opener(text: str, openers: list[str]) -> str:
    if not openers:
        return text
    first_para = text.split("\n\n")[0] if text else ""
    sentences = first_para.split("。")
    if sentences:
        opener_template = openers[0][:50]
        if opener_template and len(sentences[0]) > 10:
            sentences[0] = opener_template
            rest = "。".join(sentences[1:])
            text = sentences[0] + ("。" if rest else "") + rest + ("\n\n" + "\n\n".join(text.split("\n\n")[1:]) if len(text.split("\n\n")) > 1 else "")
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
) -> dict:
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
            "signature_phrases_injected": injected_signatures,
        },
        "dna_rules_applied": get_rewrite_rules(dna),
        "skipped_dna_rules": {
            "downgraded": list(dna.get("downgraded_features", {}).keys()) if "downgraded_features" in dna else [],
            "not_applied": dna.get("uncertain_candidates", []),
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
    text = adjust_opener(text, openers)

    slop_after = detect_ai_slop_in_text(text, blacklist)

    debug = build_debug_info(
        original_clean, text, dna,
        slop_before, slop_after,
        removed_bl, removed_conn, injected_sigs,
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
    print(f"   植入签名短语: {len(injected_sigs)} 个")
    print(f"   输出文件: {output_md}")
    print(f"   调试信息: {output_json}")


if __name__ == "__main__":
    main()
