#!/usr/bin/env python3
"""
Extract a reusable writing DNA profile from a user's past writing samples.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).parent))
from ai_slop_dict import ALL_SLOP, detect_slop


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U0001F1E0-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)

COMMON_PHRASES = {
    "一个",
    "一种",
    "一些",
    "什么",
    "我们",
    "你们",
    "他们",
    "自己",
    "如果",
    "但是",
    "不过",
    "所以",
    "因为",
    "其实",
    "可以",
    "应该",
    "没有",
    "需要",
    "问题",
    "东西",
    "事情",
    "产品",
    "工具",
    "用户",
    "时候",
    "就是",
    "不是",
}


def read_text_files(paths: list[str]) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"Warning: skip missing path: {raw_path}", file=sys.stderr)
            continue
        if path.is_dir():
            for ext in ("*.md", "*.txt"):
                for file_path in sorted(path.rglob(ext)):
                    docs.append({"filename": file_path.name, "content": file_path.read_text(encoding="utf-8")})
        else:
            docs.append({"filename": path.name, "content": path.read_text(encoding="utf-8")})
    return docs


def clean_markdown(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[。！？!?])", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def split_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    return [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]


def chinese_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def extract_emojis(text: str) -> list[str]:
    return EMOJI_RE.findall(text)


def extract_ngrams(text: str, n_min: int = 2, n_max: int = 6) -> Counter:
    cleaned = re.sub(r"[^\u4e00-\u9fff，。！？、：；…]", " ", text)
    counter: Counter = Counter()
    for chunk in cleaned.split():
        pure_chunk = re.sub(r"[，。！？、：；…]", "", chunk)
        for n in range(n_min, n_max + 1):
            if len(pure_chunk) < n:
                continue
            for i in range(len(pure_chunk) - n + 1):
                gram = pure_chunk[i : i + n]
                if re.fullmatch(r"[\u4e00-\u9fff]+", gram):
                    counter[gram] += 1
    return counter


def is_meaningful_signature(phrase: str) -> bool:
    if len(phrase) < 2:
        return False
    if phrase in COMMON_PHRASES:
        return False
    if phrase in ALL_SLOP:
        return False
    if re.fullmatch(r"[的了是我你他她它们在有和就都也很把被让给对与]", phrase):
        return False
    return True


def remove_redundant_phrases(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (-len(item["phrase"]), -item["score"])):
        phrase = candidate["phrase"]
        if any(phrase in kept_item["phrase"] for kept_item in kept):
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda item: -item["score"])


def find_signature_phrases(docs: list[dict[str, str]], min_doc_appearances: int = 2) -> list[dict[str, Any]]:
    per_doc_grams: list[set[str]] = []
    total_counter: Counter = Counter()

    for doc in docs:
        text = clean_markdown(doc["content"])
        grams = extract_ngrams(text, n_min=2, n_max=6)
        per_doc_grams.append(set(grams.keys()))
        total_counter.update(grams)

    doc_counter: Counter = Counter()
    for gram_set in per_doc_grams:
        for gram in gram_set:
            doc_counter[gram] += 1

    candidates: list[dict[str, Any]] = []
    for phrase, total_count in total_counter.items():
        if doc_counter[phrase] < min_doc_appearances:
            continue
        if total_count < 2:
            continue
        if not is_meaningful_signature(phrase):
            continue

        score = total_count * doc_counter[phrase] * (1.0 + 0.6 * (len(phrase) - 2))
        candidates.append(
            {
                "phrase": phrase,
                "total_count": total_count,
                "doc_count": doc_counter[phrase],
                "score": round(score, 1),
            }
        )

    return remove_redundant_phrases(candidates)[:20]


def extract_openers_closers(docs: list[dict[str, str]], top_n: int = 5) -> dict[str, list[str]]:
    openers: list[str] = []
    closers: list[str] = []
    for doc in docs:
        text = clean_markdown(doc["content"])
        paragraphs = split_paragraphs(text)
        if not paragraphs:
            continue
        first_sentences = split_sentences(paragraphs[0])
        last_sentences = split_sentences(paragraphs[-1])
        if first_sentences:
            openers.append(first_sentences[0][:60])
        if last_sentences:
            closers.append(last_sentences[-1][:60])
    return {"openers": openers[:top_n], "closers": closers[:top_n]}


def pick_cjk_font() -> str | None:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simkai.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def render_hotwords_image(
    hotwords: list[dict[str, Any]],
    output_path: str | Path,
    user_name: str,
    top_n: int = 12,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font_path = pick_cjk_font()
    font_props = font_manager.FontProperties(fname=font_path) if font_path else None
    plt.rcParams["axes.unicode_minus"] = False

    top_items = hotwords[:top_n]
    if not top_items:
        fig, ax = plt.subplots(figsize=(10, 4), dpi=180)
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            f"{user_name} 写作 DNA 热词图\n\n未提取到稳定热词",
            ha="center",
            va="center",
            fontsize=16,
            fontproperties=font_props,
        )
        fig.savefig(output_path, bbox_inches="tight", facecolor="#f7f3ea")
        plt.close(fig)
        return

    words = [item["phrase"] for item in reversed(top_items)]
    scores = [item["score"] for item in reversed(top_items)]
    counts = [item["total_count"] for item in reversed(top_items)]

    fig_height = max(5.5, 0.5 * len(words) + 2.4)
    fig, ax = plt.subplots(figsize=(11, fig_height), dpi=180)
    fig.patch.set_facecolor("#f7f3ea")
    ax.set_facecolor("#fffdf8")

    bars = ax.barh(
        range(len(words)),
        scores,
        color="#9c4f2e",
        edgecolor="#6d3218",
        height=0.68,
    )
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words, fontproperties=font_props, fontsize=11)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.set_axisbelow(True)
    ax.set_title(f"{user_name} 写作 DNA 热词图", fontproperties=font_props, fontsize=18, pad=18)
    fig.text(
        0.125,
        0.94,
        "基于多篇旧文提取的高频且跨文档复现短语",
        fontsize=10,
        color="#5e5e5e",
        fontproperties=font_props,
    )
    ax.set_xlabel("热词分数", fontproperties=font_props, fontsize=10)

    score_padding = max(scores) * 0.015 if scores else 0.2
    for bar, score, count in zip(bars, scores, counts):
        ax.text(
            bar.get_width() + score_padding,
            bar.get_y() + bar.get_height() / 2,
            f"score={score}  count={count}",
            va="center",
            fontsize=9,
            color="#333333",
        )

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def extract_dna(docs: list[dict[str, str]], user_name: str) -> dict[str, Any]:
    # Template stripping is now handled cross-document by scripts/strip_template.py
    # in the pipeline stage (PRD §8.1.3 Layer 1) and by SKILL.md prompt + user
    # confirmation (Layer 2/3). extract_dna assumes docs already have templates
    # stripped — the input directory should be inputs/template_stripped_markdown/.
    stripped_docs = docs  # alias preserved for downstream variable names
    cleaned_docs = [clean_markdown(doc["content"]) for doc in stripped_docs]
    all_text = "\n\n".join(cleaned_docs)

    if not all_text.strip():
        raise ValueError(
            "All input documents were fully stripped to empty content. "
            "Check that inputs contain personal prose, not only template boilerplate."
        )

    all_sentences = split_sentences(all_text)
    all_paragraphs = split_paragraphs(all_text)

    sentence_lengths = [chinese_char_count(sentence) for sentence in all_sentences if chinese_char_count(sentence) > 0]
    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    short_sentence_ratio = (
        sum(1 for count in sentence_lengths if count <= 15) / len(sentence_lengths) if sentence_lengths else 0
    )

    paragraph_lines = [paragraph.count("\n") + 1 for paragraph in all_paragraphs]
    avg_paragraph_lines = sum(paragraph_lines) / len(paragraph_lines) if paragraph_lines else 0

    emojis: list[str] = []
    for doc in stripped_docs:
        emojis.extend(extract_emojis(doc["content"]))
    emoji_counter = Counter(emojis)

    total_chars = chinese_char_count(all_text)
    emoji_per_1k = len(emojis) / max(total_chars, 1) * 1000
    if emoji_per_1k < 0.5:
        emoji_frequency = "none"
    elif emoji_per_1k < 3:
        emoji_frequency = "rare"
    elif emoji_per_1k < 10:
        emoji_frequency = "moderate"
    else:
        emoji_frequency = "heavy"

    min_signature_docs = 1 if len(stripped_docs) == 1 else 2
    signatures = find_signature_phrases(stripped_docs, min_doc_appearances=min_signature_docs)
    opener_closer = extract_openers_closers(stripped_docs)

    self_slop_hits: list[str] = []
    for text in cleaned_docs:
        detected = detect_slop(text)
        self_slop_hits.extend(hit["phrase"] for hit in detected["hits"])
    self_slop_counter = Counter(self_slop_hits)
    user_owned_phrases = sorted(phrase for phrase, count in self_slop_counter.items() if count >= 2)
    blacklist = sorted(set(ALL_SLOP.keys()) - set(user_owned_phrases))

    return {
        "user_name": user_name,
        "schema_version": "1.0",
        "sample_count": len(docs),
        "total_chinese_chars": total_chars,
        "sentence_features": {
            "avg_length_chars": round(avg_sentence_length, 1),
            "short_sentence_ratio": round(short_sentence_ratio, 2),
            "total_sentences": len(all_sentences),
        },
        "paragraph_features": {
            "paragraph_lines_avg": round(avg_paragraph_lines, 1),
            "total_paragraphs": len(all_paragraphs),
        },
        "signature_phrases": [item["phrase"] for item in signatures[:15]],
        "signature_phrases_detail": signatures[:15],
        "openers": opener_closer["openers"],
        "closers": opener_closer["closers"],
        "emoji_policy": {
            "frequency": emoji_frequency,
            "per_1k_chars": round(emoji_per_1k, 2),
            "allowed": [emoji for emoji, _ in emoji_counter.most_common(10)],
            "blocked": [],
        },
        "blacklist_phrases": blacklist,
        "user_owned_phrases": user_owned_phrases,
        "manual_corrections": [],
        "_meta": {
            "files_processed": [doc["filename"] for doc in docs],
        },
    }


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Extract a reusable writing DNA profile from past writing samples.")
    parser.add_argument("--input", nargs="+", required=True, help="Input file or directory paths")
    parser.add_argument("--user-name", default="user", help="User name used in the output DNA file")
    parser.add_argument("--output", help="Optional output JSON path; defaults to <user-name>-dna.json")
    parser.add_argument(
        "--hotwords-image",
        help="Optional output PNG path for the hotwords image; defaults to <json-output-stem>_hotwords.png",
    )
    args = parser.parse_args()

    docs = read_text_files(args.input)
    if not docs:
        print("Error: no readable input files found", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(docs)} documents")
    if len(docs) < 5:
        print(f"Warning: only {len(docs)} samples loaded; 5+ samples are recommended for a stable DNA profile")

    dna = extract_dna(docs, args.user_name)

    output_path = Path(args.output or f"{args.user_name}-dna.json")
    hotwords_image_path = (
        Path(args.hotwords_image)
        if args.hotwords_image
        else output_path.with_name(f"{output_path.stem}_hotwords.png")
    )

    render_hotwords_image(dna["signature_phrases_detail"], hotwords_image_path, args.user_name)
    dna["_meta"]["hotwords_image"] = str(hotwords_image_path)

    output_path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"DNA written to: {output_path}")
    print(f"Hotwords image written to: {hotwords_image_path}")
    print(f"  Chinese chars: {dna['total_chinese_chars']}")
    print(f"  Signature phrases: {len(dna['signature_phrases'])}")
    print(f"  Avg sentence length: {dna['sentence_features']['avg_length_chars']}")
    print(f"  Short sentence ratio: {dna['sentence_features']['short_sentence_ratio']*100:.0f}%")
    print(f"  Avg paragraph lines: {dna['paragraph_features']['paragraph_lines_avg']}")
    print(f"  Emoji frequency: {dna['emoji_policy']['frequency']} ({dna['emoji_policy']['per_1k_chars']}/1k chars)")


if __name__ == "__main__":
    main()
