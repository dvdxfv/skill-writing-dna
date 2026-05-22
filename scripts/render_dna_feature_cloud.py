#!/usr/bin/env python3
"""
Render a human-facing DNA feature cloud from a formal writing DNA JSON profile.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 980
TITLE_HEIGHT = 140
MARGIN = 48
BG_COLOR = "#ffffff"
TITLE_COLOR = "#222222"
SUBTITLE_COLOR = "#666666"
PALETTE = [
    "#2F5D9F",
    "#3A7CA5",
    "#3DBB9A",
    "#59C36A",
    "#A7D129",
    "#6C43A6",
    "#1D9BB5",
    "#274690",
]


def pick_cjk_font() -> str:
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
    raise FileNotFoundError("No CJK font found under C:/Windows/Fonts")


def normalize_label(text: str) -> str | None:
    rules = [
        (["一是", "二是", "枚举"], "一是…二是…三是…"),
        (["先判断后展开", "先给判断句", "先定性", "概括后举证"], "先判断后展开"),
        (["建议+主体+动作+内容"], "建议+主体+动作+内容"),
        (["建制式", "制度/机制/办法/流程", "制度", "机制", "流程", "权责"], "制度 / 机制 / 流程 / 权责"),
        (["事实支撑", "附事实", "数据支撑", "没有数据的判断"], "判断后接事实"),
        (["长句", "分号", "信息单元"], "长句高信息密度"),
        (["总分", "先总述", "总—分", "总-分"], "段内总分推进"),
        (["稳健", "规范", "建议''应''需'", "建议\"\"应\"\"需"], "稳健规范语气"),
        (["流程链", "协同机制", "各主体职责", "衔接关系"], "协同机制 / 流程链"),
        (["手段/方式", "实现/确保/达到"], "手段→动作→目的"),
        (["制度分析导向"], "制度分析导向"),
        (["审慎论述", "不武断"], "审慎判断"),
    ]
    for needles, label in rules:
        if any(needle in text for needle in needles):
            return label
    return None


def add_feature(store: dict[str, float], raw_text: str, weight: float) -> None:
    label = normalize_label(raw_text)
    if label:
        store[label] += weight


def collect_feature_weights(profile: dict[str, Any]) -> list[tuple[str, float]]:
    weights: dict[str, float] = defaultdict(float)

    add_feature(weights, str(profile.get("overall_assessment", "")), 1.8)

    for value in profile.get("structure_habits", {}).values():
        add_feature(weights, str(value), 1.6)

    for value in profile.get("argumentation_style", {}).values():
        add_feature(weights, str(value), 1.5)

    language_features = profile.get("language_features", {})
    for value in language_features.values():
        if isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, list):
                    add_feature(weights, " / ".join(str(x) for x in nested), 1.1)
                else:
                    add_feature(weights, str(nested), 1.1)
        else:
            add_feature(weights, str(value), 1.1)

    for rule in profile.get("rewrite_rules", []):
        add_feature(weights, str(rule), 1.9)

    if "transition_mode" in profile.get("structure_habits", {}):
        weights["一是…二是…三是…"] += 1.0
    if "within_section" in profile.get("structure_habits", {}):
        weights["先判断后展开"] += 1.0

    features = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return features[:12]


def intersects(box: tuple[int, int, int, int], others: list[tuple[int, int, int, int]], padding: int = 12) -> bool:
    x1, y1, x2, y2 = box
    for ox1, oy1, ox2, oy2 in others:
        if not (x2 + padding < ox1 or x1 - padding > ox2 or y2 + padding < oy1 or y1 - padding > oy2):
            return True
    return False


def fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, size: int) -> tuple[ImageFont.FreeTypeFont, tuple[int, int]]:
    font = ImageFont.truetype(font_path, size=size)
    bbox = draw.textbbox((0, 0), text, font=font)
    return font, (bbox[2] - bbox[0], bbox[3] - bbox[1])


def place_words(
    draw: ImageDraw.ImageDraw,
    features: list[tuple[str, float]],
    font_path: str,
) -> list[dict[str, Any]]:
    if not features:
        return []

    max_weight = max(weight for _, weight in features)
    min_weight = min(weight for _, weight in features)
    spread = max(max_weight - min_weight, 0.01)
    placed: list[dict[str, Any]] = []
    occupied: list[tuple[int, int, int, int]] = []
    random.seed(42)

    for idx, (label, weight) in enumerate(features):
        norm = (weight - min_weight) / spread
        font_size = int(38 + norm * 92)
        # Long labels need a smaller starting size.
        if len(label) >= 12:
            font_size -= 10
        if len(label) >= 18:
            font_size -= 14
        font_size = max(font_size, 28)

        color = PALETTE[idx % len(PALETTE)]
        placed_item = None
        current_size = font_size

        while current_size >= 24 and placed_item is None:
            font, (width, height) = fit_font(draw, label, font_path, current_size)
            max_x = CANVAS_WIDTH - MARGIN - width
            max_y = CANVAS_HEIGHT - MARGIN - height
            if max_x <= MARGIN or max_y <= TITLE_HEIGHT + 20:
                current_size -= 6
                continue

            for _ in range(320):
                x = random.randint(MARGIN, max_x)
                y = random.randint(TITLE_HEIGHT + 20, max_y)
                box = (x, y, x + width, y + height)
                if not intersects(box, occupied):
                    placed_item = {
                        "text": label,
                        "font": font,
                        "x": x,
                        "y": y,
                        "color": color,
                        "box": box,
                    }
                    occupied.append(box)
                    break
            current_size -= 6

        if placed_item is None:
            font, (width, height) = fit_font(draw, label, font_path, 24)
            x = MARGIN
            y = TITLE_HEIGHT + 20 + len(occupied) * (height + 8)
            box = (x, y, x + width, y + height)
            placed_item = {
                "text": label,
                "font": font,
                "x": x,
                "y": y,
                "color": color,
                "box": box,
            }
            occupied.append(box)

        placed.append(placed_item)

    return placed


def render_feature_cloud(profile: dict[str, Any], output_path: Path) -> list[tuple[str, float]]:
    author = str(profile.get("author") or profile.get("user_name") or "用户")
    features = collect_feature_weights(profile)
    font_path = pick_cjk_font()

    image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(font_path, size=54)
    subtitle_font = ImageFont.truetype(font_path, size=24)
    text_font = ImageFont.truetype(font_path, size=26)

    draw.text((MARGIN, 34), f"{author} 写作 DNA 特征云", fill=TITLE_COLOR, font=title_font)
    draw.text(
        (MARGIN, 98),
        "展示的是稳定写作资产，而不是普通高频词",
        fill=SUBTITLE_COLOR,
        font=subtitle_font,
    )

    words = place_words(draw, features, font_path)
    for item in words:
        draw.text((item["x"], item["y"]), item["text"], fill=item["color"], font=item["font"])

    footer = "Source: formal DNA profile JSON"
    footer_box = draw.textbbox((0, 0), footer, font=text_font)
    footer_width = footer_box[2] - footer_box[0]
    draw.text(
        (CANVAS_WIDTH - MARGIN - footer_width, CANVAS_HEIGHT - 42),
        footer,
        fill="#888888",
        font=text_font,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return features


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Render a visual DNA feature cloud from a formal DNA JSON.")
    parser.add_argument("--input", required=True, help="Formal DNA JSON path")
    parser.add_argument("--output", help="Output PNG path; defaults to <input-stem>_feature_cloud.png")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_feature_cloud.png")

    profile = json.loads(input_path.read_text(encoding="utf-8"))
    features = render_feature_cloud(profile, output_path)

    print(f"Feature cloud written to: {output_path}")
    print("Top features:")
    for label, weight in features:
        print(f"  - {label}: {weight:.1f}")


if __name__ == "__main__":
    main()
