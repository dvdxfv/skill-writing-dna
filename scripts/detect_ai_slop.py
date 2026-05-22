#!/usr/bin/env python3
"""
Standalone CLI for AI-slop detection.

Inputs:
- raw text via --text
- or a UTF-8 file via --text-file
- optional DNA json via --dna to extend the blacklist

Outputs:
- human-readable console summary
- optional JSON file via --output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_slop_dict import ALL_SLOP, detect_slop


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def render_hit_context(text: str, position: int, phrase: str, window: int = 15) -> str:
    """Return a compact context string with the hit highlighted."""
    start = max(0, position - window)
    end = min(len(text), position + len(phrase) + window)
    before = text[start:position].replace("\n", " ")
    matched = text[position:position + len(phrase)]
    after = text[position + len(phrase):end].replace("\n", " ")
    return f"...{before}[{matched}]{after}..."


def extend_with_user_blacklist(text: str, result: dict, dna_path: str) -> dict:
    """Add user-specific blacklist hits from the DNA profile."""
    dna = json.loads(Path(dna_path).read_text(encoding="utf-8"))
    user_blacklist = dna.get("blacklist_phrases", [])
    custom_blacklist = [phrase for phrase in user_blacklist if phrase not in ALL_SLOP]

    custom_hits = []
    for phrase in custom_blacklist:
        start = 0
        while True:
            idx = text.find(phrase, start)
            if idx == -1:
                break
            custom_hits.append(
                {
                    "phrase": phrase,
                    "weight": 3,
                    "position": idx,
                    "category": "USER_BLACKLIST",
                }
            )
            start = idx + len(phrase)

    result["hits"].extend(custom_hits)
    raw = sum(hit["weight"] for hit in result["hits"])
    raw += sum(combo["bonus"] for combo in result["combo_hits"])
    raw += sum(pattern["weight"] for pattern in result["pattern_hits"])
    result["raw_score"] = raw
    result["score"] = min(100, int(raw * 100 / (len(text) * 0.2)))
    return result


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Detect AI-slop phrases and patterns in text.")
    parser.add_argument("--text-file", help="Path to a UTF-8 text/markdown file.")
    parser.add_argument("--text", help="Raw text input for quick tests.")
    parser.add_argument("--dna", help="Optional DNA json used to extend the blacklist.")
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument("--quiet", action="store_true", help="Only write JSON output.")
    args = parser.parse_args()

    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        print("Error: provide --text-file or --text", file=sys.stderr)
        sys.exit(1)

    result = detect_slop(text)

    if args.dna:
        result = extend_with_user_blacklist(text, result, args.dna)

    for hit in result["hits"]:
        hit["context"] = render_hit_context(text, hit["position"], hit["phrase"])
    for combo in result["combo_hits"]:
        marker = combo["combo"][0] + "..." + combo["combo"][1]
        combo["context"] = render_hit_context(text, combo["position"], marker)
    for pattern in result["pattern_hits"]:
        pattern["context"] = render_hit_context(text, pattern["position"], pattern["match"])

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.quiet:
        print("\n=== AI Slop Report ===")
        print(f"Total score: {result['score']}/100")
        print(f"Raw weight: {result['raw_score']}")
        print(f"Text length: {result['text_length']}")
        print(
            "Hits: "
            f"{len(result['hits'])} phrase / "
            f"{len(result['combo_hits'])} combo / "
            f"{len(result['pattern_hits'])} pattern"
        )

        if result["hits"]:
            print("\n--- Phrase Hits ---")
            seen_phrases = set()
            for hit in sorted(result["hits"], key=lambda item: (-item["weight"], item["phrase"])):
                if hit["phrase"] in seen_phrases:
                    continue
                seen_phrases.add(hit["phrase"])
                count = sum(1 for item in result["hits"] if item["phrase"] == hit["phrase"])
                print(f"[{hit['category']:14s}] {hit['phrase']} x{count} weight={hit['weight']}")
                print(f"  {hit['context']}")

        if result["combo_hits"]:
            print("\n--- Combo Hits ---")
            for combo in result["combo_hits"]:
                print(f"{combo['combo'][0]} + {combo['combo'][1]} bonus={combo['bonus']}")
                print(f"  {combo['context']}")

        if result["pattern_hits"]:
            print("\n--- Pattern Hits ---")
            for pattern in result["pattern_hits"]:
                print(f"{pattern['match']} ({pattern['description']})")
                print(f"  {pattern['context']}")

    return result


if __name__ == "__main__":
    main()
