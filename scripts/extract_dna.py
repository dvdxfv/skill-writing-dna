#!/usr/bin/env python3
"""
Extract a reusable writing DNA profile from a user's past writing samples.
"""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

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
    top_n: int = 18,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font_path = pick_cjk_font()
    if not font_path:
        raise FileNotFoundError("No CJK font found under C:/Windows/Fonts")

    top_items = hotwords[:top_n]
    canvas_width = 1600
    canvas_height = 980
    margin = 48
    title_height = 150
    palette = [
        "#2F5D9F",
        "#3A7CA5",
        "#3DBB9A",
        "#59C36A",
        "#A7D129",
        "#6C43A6",
        "#1D9BB5",
        "#274690",
    ]

    image = Image.new("RGB", (canvas_width, canvas_height), "#ffffff")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(font_path, size=54)
    subtitle_font = ImageFont.truetype(font_path, size=24)
    footer_font = ImageFont.truetype(font_path, size=26)

    draw.text((margin, 34), f"{user_name} 写作 DNA 特征云", fill="#222222", font=title_font)
    draw.text(
        (margin, 98),
        "展示的是稳定写作资产，而不是普通高频词统计",
        fill="#666666",
        font=subtitle_font,
    )

    if not top_items:
        empty_font = ImageFont.truetype(font_path, size=42)
        message = "未提取到稳定写作特征"
        bbox = draw.textbbox((0, 0), message, font=empty_font)
        draw.text(
            ((canvas_width - (bbox[2] - bbox[0])) // 2, canvas_height // 2),
            message,
            fill="#666666",
            font=empty_font,
        )
        image.save(output_path)
        return

    scores = [float(item.get("score", 0)) for item in top_items]
    max_score = max(scores)
    min_score = min(scores)
    spread = max(max_score - min_score, 1.0)
    occupied: list[tuple[int, int, int, int]] = []
    random.seed(42)

    def intersects(box: tuple[int, int, int, int], padding: int = 14) -> bool:
        x1, y1, x2, y2 = box
        for ox1, oy1, ox2, oy2 in occupied:
            if not (x2 + padding < ox1 or x1 - padding > ox2 or y2 + padding < oy1 or y1 - padding > oy2):
                return True
        return False

    for idx, item in enumerate(top_items):
        word = str(item.get("phrase", "")).strip()
        if not word:
            continue

        score = float(item.get("score", 0))
        norm = (score - min_score) / spread
        font_size = int(42 + norm * 108)
        if len(word) >= 8:
            font_size -= 12
        if len(word) >= 14:
            font_size -= 18
        font_size = max(font_size, 30)
        color = palette[idx % len(palette)]
        placed = False

        while font_size >= 24 and not placed:
            font = ImageFont.truetype(font_path, size=font_size)
            bbox = draw.textbbox((0, 0), word, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            max_x = canvas_width - margin - width
            max_y = canvas_height - margin - height
            if max_x <= margin or max_y <= title_height:
                font_size -= 6
                continue

            for _ in range(360):
                x = random.randint(margin, max_x)
                y = random.randint(title_height, max_y)
                box = (x, y, x + width, y + height)
                if intersects(box):
                    continue
                draw.text((x, y), word, fill=color, font=font)
                occupied.append(box)
                placed = True
                break

            font_size -= 6

        if not placed:
            font = ImageFont.truetype(font_path, size=24)
            x = margin
            y = min(canvas_height - margin - 28, title_height + len(occupied) * 36)
            draw.text((x, y), word, fill=color, font=font)
            bbox = draw.textbbox((x, y), word, font=font)
            occupied.append(bbox)

    footer = "Source: statistical signature phrases"
    footer_bbox = draw.textbbox((0, 0), footer, font=footer_font)
    draw.text(
        (canvas_width - margin - (footer_bbox[2] - footer_bbox[0]), canvas_height - 42),
        footer,
        fill="#888888",
        font=footer_font,
    )
    image.save(output_path)


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
        help="Optional output PNG path for the statistical signature-phrase feature cloud; defaults to <json-output-stem>_hotwords.png",
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
    print(f"Feature cloud image written to: {hotwords_image_path}")
    print(f"  Chinese chars: {dna['total_chinese_chars']}")
    print(f"  Signature phrases: {len(dna['signature_phrases'])}")
    print(f"  Avg sentence length: {dna['sentence_features']['avg_length_chars']}")
    print(f"  Short sentence ratio: {dna['sentence_features']['short_sentence_ratio']*100:.0f}%")
    print(f"  Avg paragraph lines: {dna['paragraph_features']['paragraph_lines_avg']}")
    print(f"  Emoji frequency: {dna['emoji_policy']['frequency']} ({dna['emoji_policy']['per_1k_chars']}/1k chars)")


if __name__ == "__main__":
    main()
