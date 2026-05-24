#!/usr/bin/env python3
"""
样本质量预检：多维健康度（文体无关）

从「公文专用诊断工具」升级为「通用样本预检闸门」。所有维度都不依赖任何文体先验，
公文 / 小红书 / 博客 / 邮件 / 论文 同样适用。

覆盖维度（见 PROJECT_STATUS.md 2026-05-24「样本预检覆盖维度」）：
  1. 数量          —— 篇数 vs 5-12 区间
  2. 字数分布      —— 每篇字数、超短篇、单篇是否过度主导
  3. 文档间相似度  —— 两两相似度，整体过高=类型单一/同质
  4. 重复内容      —— 近重复整篇（strip_template 行级对齐抓不到的）+ 文档内重复
  5. 稳定性/饱和度 —— 留一法 + 饱和度曲线，排序基于「通用特征向量」
并给出分级 severity（ok / light / serious）供 run.py 第一确认点做软阻断判断。

用法:
  python scripts/test_sample_sufficiency.py
  python scripts/test_sample_sufficiency.py --input <目录> --output-json <a.json> --output-md <b.md>
"""

import argparse
import itertools
import json
import re
import sys
from collections import Counter
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="样本质量预检：多维健康度（文体无关）")
    p.add_argument("--input", default=None, help="模板剥离后的 markdown 目录（默认自动检测）")
    p.add_argument("--output-json", default=None, help="JSON 输出路径")
    p.add_argument("--output-md", default=None, help="Markdown 报告输出路径")
    return p.parse_args()


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_ROOT / "inputs" / "template_stripped_markdown"
DEFAULT_JSON = PROJECT_ROOT / "outputs" / "debug" / "sample_sufficiency_test.json"
DEFAULT_MD = PROJECT_ROOT / "outputs" / "debug" / "sample_sufficiency_test.md"

SHORT_DOC_CHARS = 800        # 单篇低于此字数视为过短（与 SKILL.md 输入建议一致）
NEAR_DUP_THRESHOLD = 0.8     # 文档间相似度 ≥ 此值视为近重复整篇
HOMOGENEOUS_THRESHOLD = 0.5  # 平均两两相似度 ≥ 此值视为整体同质/类型单一


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


# ══════════════════════════════════════════════════
#  通用特征（文体无关）——用于留一法 / 饱和度排序
# ══════════════════════════════════════════════════
def extract_features(text: str) -> dict[str, float]:
    """只用文体无关的统计量，不含任何特定文体的词汇先验。"""
    features: dict[str, float] = {}
    chars = max(len(text), 1)

    sentences = [s.strip() for s in re.split(r"[。！？!?\n]+", text) if len(s.strip()) > 3]
    if sentences:
        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        features["avg_sentence_len"] = mean_len
        features["short_sentence_ratio"] = sum(1 for n in lengths if n <= 15) / len(lengths) * 100
        variance = sum((n - mean_len) ** 2 for n in lengths) / len(lengths)
        features["sentence_len_cv"] = (variance ** 0.5) / mean_len * 100 if mean_len else 0

    cjk = re.findall(r"[一-鿿]", text)
    features["vocab_richness"] = len(set(cjk)) / max(len(cjk), 1) * 100

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paragraphs:
        features["avg_paragraph_len"] = sum(len(p) for p in paragraphs) / len(paragraphs)

    features["comma_density"] = len(re.findall(r"[，,]", text)) / chars * 1000
    features["question_density"] = len(re.findall(r"[？?]", text)) / chars * 1000
    features["exclaim_density"] = len(re.findall(r"[！!]", text)) / chars * 1000
    return features


def chinese_char_count(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text))


def load_docs(input_dir: Path) -> dict:
    """加载样本。不再依赖任何硬编码文档标签——文体无关。"""
    docs = {}
    for f in sorted(input_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        docs[f.name] = {"text": text, "chars": chinese_char_count(text)}
    return docs


def feature_ranking(feature_vec: dict[str, float]) -> list[str]:
    return sorted(feature_vec.keys(), key=lambda k: feature_vec.get(k, 0), reverse=True)


def rank_distance(rank1: list[str], rank2: list[str]) -> float:
    common = set(rank1) & set(rank2)
    if not common:
        return 1.0
    dist = sum(abs(rank1.index(f) - rank2.index(f)) for f in common)
    return dist / max(len(common) * len(common), 1)


def avg_features(doc_list):
    if not doc_list:
        return {}
    keys = set().union(*(d.keys() for d in doc_list))
    return {k: sum(d.get(k, 0) for d in doc_list) / len(doc_list) for k in keys}


# ══════════════════════════════════════════════════
#  维度 2：字数分布
# ══════════════════════════════════════════════════
def length_distribution(docs: dict) -> dict:
    items = [(n, docs[n]["chars"]) for n in docs]
    lengths = sorted(c for _, c in items)
    total = sum(lengths) or 1
    short_docs = [n for n, c in items if c < SHORT_DOC_CHARS]
    return {
        "min": min(lengths),
        "max": max(lengths),
        "median": lengths[len(lengths) // 2],
        "mean": round(total / len(lengths), 1),
        "short_docs": short_docs,
        "has_short": bool(short_docs),
        "dominant_ratio": round(max(lengths) / total, 2),
    }


# ══════════════════════════════════════════════════
#  维度 3 + 4：文档间相似度 / 近重复整篇 / 文档内重复
# ══════════════════════════════════════════════════
def _shingles(text: str, n: int = 3) -> set:
    cjk = re.sub(r"[^一-鿿]", "", text)
    if len(cjk) < n:
        return {cjk} if cjk else set()
    return {cjk[i:i + n] for i in range(len(cjk) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def inter_doc_similarity(docs: dict) -> dict:
    names = list(docs)
    shingles = {n: _shingles(docs[n]["text"]) for n in names}
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sim = round(_jaccard(shingles[names[i]], shingles[names[j]]), 3)
            pairs.append([names[i], names[j], sim])
    sims = [p[2] for p in pairs] or [0.0]
    mean_sim = round(sum(sims) / len(sims), 3)
    return {
        "mean_pairwise": mean_sim,
        "max_pairwise": max(sims),
        "homogeneous": mean_sim >= HOMOGENEOUS_THRESHOLD,
        "pairs": pairs,
    }


def intra_doc_repetition(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[。！？!?\n]+", text) if len(s.strip()) > 5]
    if not sentences:
        return 0.0
    counts = Counter(sentences)
    duplicate = sum(v - 1 for v in counts.values() if v > 1)
    return round(duplicate / len(sentences), 3)


def duplication(docs: dict, sim_pairs: list) -> dict:
    near_dups = [[a, b] for a, b, s in sim_pairs if s >= NEAR_DUP_THRESHOLD]
    intra = {n: intra_doc_repetition(docs[n]["text"]) for n in docs}
    heavy_intra = [n for n, r in intra.items() if r >= 0.2]
    return {
        "near_duplicate_pairs": near_dups,
        "intra_doc_repetition": intra,
        "heavy_intra_repetition_docs": heavy_intra,
    }


# ══════════════════════════════════════════════════
#  维度 5：留一法稳定性 + 饱和度曲线（通用特征）
# ══════════════════════════════════════════════════
def test_leave_one_out(docs: dict) -> dict:
    names = list(docs)
    full_rank = feature_ranking(avg_features([extract_features(docs[n]["text"]) for n in names]))
    results = []
    for i, name in enumerate(names):
        subset = [n for j, n in enumerate(names) if j != i]
        sub_rank = feature_ranking(avg_features([extract_features(docs[n]["text"]) for n in subset]))
        results.append({"removed": name, "rank_distance": round(rank_distance(full_rank, sub_rank), 3)})
    avg_dist = sum(r["rank_distance"] for r in results) / len(results) if results else 1.0
    return {"per_doc": results, "avg_distance": round(avg_dist, 3), "stable": avg_dist < 0.25,
            "full_rank": full_rank[:6]}


def test_saturation_curve(docs: dict) -> dict:
    names = list(docs)
    full_rank = feature_ranking(avg_features([extract_features(docs[n]["text"]) for n in names]))
    by_n: dict[int, list] = {}
    for r in range(1, len(names) + 1):
        for combo in itertools.combinations(names, r):
            rank = feature_ranking(avg_features([extract_features(docs[n]["text"]) for n in combo]))
            overlap = len(set(rank[:6]) & set(full_rank[:6]))
            by_n.setdefault(r, []).append(overlap)
    curve = {}
    for r in sorted(by_n):
        entries = by_n[r]
        curve[r] = {"combinations": len(entries),
                    "avg_top6_overlap": round(sum(entries) / len(entries), 1)}
    return curve


# ══════════════════════════════════════════════════
#  分级 + 一句话结论
# ══════════════════════════════════════════════════
def assess(docs, length_dist, similarity, dup, leave_one_out) -> tuple[str, str, list[str], str]:
    n = len(docs)
    near_dups = dup["near_duplicate_pairs"]
    effective = n - len(near_dups)  # 近重复对折算成 1 篇有效样本

    reasons = []
    if near_dups:
        pretty = "、".join("/".join(pair) for pair in near_dups)
        reasons.append(f"{len(near_dups)} 对近重复整篇（{pretty}），等于只有 {effective} 篇不同的")
    if length_dist["has_short"]:
        reasons.append(f"{len(length_dist['short_docs'])} 篇过短（<{SHORT_DOC_CHARS}字）：{'、'.join(length_dist['short_docs'])}")
    if length_dist["dominant_ratio"] >= 0.5 and n >= 2:
        reasons.append(f"单篇字数占比 {int(length_dist['dominant_ratio'] * 100)}%，长文主导 DNA")
    if similarity["homogeneous"]:
        reasons.append(f"文档间相似度偏高（均值 {similarity['mean_pairwise']}），类型偏单一")
    if not leave_one_out["stable"]:
        reasons.append(f"留一法波动较大（{leave_one_out['avg_distance']}），特征不稳")

    if effective < 3 or len(near_dups) >= max(1, n // 2):
        severity = "serious"
    elif n < 5 or near_dups or length_dist["has_short"] or similarity["homogeneous"] or not leave_one_out["stable"]:
        severity = "light"
    else:
        severity = "ok"

    verdict = {"ok": "✅ 样本健康", "light": "⚠️ 样本可用但有提醒", "serious": "❌ 样本有严重问题"}[severity]
    if severity == "ok":
        one_line = f"✅ {n} 篇样本健康：字数均衡、无近重复、类型有区分，可直接提取。"
    else:
        head = {"light": "⚠️", "serious": "❌"}[severity]
        one_line = f"{head} {n} 篇样本：" + "；".join(reasons[:3]) + "。"
    return severity, verdict, reasons, one_line


def build_results(docs: dict) -> dict:
    names = list(docs)
    total_chars = sum(docs[n]["chars"] for n in names)

    length_dist = length_distribution(docs)
    similarity = inter_doc_similarity(docs)
    dup = duplication(docs, similarity["pairs"])
    loo = test_leave_one_out(docs)
    saturation = test_saturation_curve(docs)

    severity, verdict, reasons, one_line = assess(docs, length_dist, similarity, dup, loo)

    return {
        "total_docs": len(docs),
        "total_chars": total_chars,
        "severity": severity,
        "verdict": verdict,
        "one_line": one_line,
        "reasons": reasons,
        "doc_list": {n: docs[n]["chars"] for n in names},
        "dimensions": {
            "count": {"docs": len(docs), "recommended_min": 5, "recommended_best": 8},
            "length_distribution": length_dist,
            "inter_doc_similarity": {k: v for k, v in similarity.items() if k != "pairs"},
            "duplication": dup,
        },
        "similarity_pairs": similarity["pairs"],
        "test_leave_one_out": loo,
        "test_saturation": saturation,
    }


# ══════════════════════════════════════════════════
#  Markdown 报告（不依赖任何特定篇数，避免历史崩溃）
# ══════════════════════════════════════════════════
def build_md(results: dict) -> str:
    L = []
    L.append("# 样本质量预检报告\n")
    L.append(f"> **{results['verdict']}** — {results['one_line']}\n")
    L.append(f"**样本数**：{results['total_docs']} 篇 · **总字数**：{results['total_chars']:,} 字 · "
             f"**分级**：`{results['severity']}`\n")

    ld = results["dimensions"]["length_distribution"]
    sim = results["dimensions"]["inter_doc_similarity"]
    dup = results["dimensions"]["duplication"]

    L.append("## 字数分布\n")
    L.append(f"- 最短 {ld['min']} / 中位 {ld['median']} / 最长 {ld['max']} / 均值 {ld['mean']} 字")
    L.append(f"- 单篇最大占比：{int(ld['dominant_ratio'] * 100)}%")
    if ld["has_short"]:
        L.append(f"- ⚠️ 过短样本（<{SHORT_DOC_CHARS}字）：{'、'.join(ld['short_docs'])}")
    L.append("")

    L.append("## 文档间相似度\n")
    L.append(f"- 两两相似度均值 {sim['mean_pairwise']} / 最大 {sim['max_pairwise']}")
    L.append(f"- {'⚠️ 整体偏同质（类型单一）' if sim['homogeneous'] else '✅ 类型有区分'}")
    L.append("")

    L.append("## 重复内容\n")
    if dup["near_duplicate_pairs"]:
        for a, b in dup["near_duplicate_pairs"]:
            L.append(f"- ⚠️ 近重复整篇：`{a}` ↔ `{b}`")
    else:
        L.append("- ✅ 未发现近重复整篇")
    if dup["heavy_intra_repetition_docs"]:
        L.append(f"- ⚠️ 文档内大量重复：{'、'.join(dup['heavy_intra_repetition_docs'])}")
    L.append("")

    loo = results["test_leave_one_out"]
    L.append("## 留一法稳定性\n")
    L.append(f"- 平均排名距离 {loo['avg_distance']}（<0.25 为稳）→ {'✅ 稳定' if loo['stable'] else '❌ 不稳'}")
    L.append("")

    if results["reasons"]:
        L.append("## 提醒\n")
        for r in results["reasons"]:
            L.append(f"- {r}")
        L.append("")
    return "\n".join(L)


def main():
    configure_utf8_stdio()
    args = parse_args()
    input_dir = Path(args.input) if args.input else DEFAULT_INPUT
    output_json = Path(args.output_json) if args.output_json else DEFAULT_JSON
    output_md = Path(args.output_md) if args.output_md else DEFAULT_MD

    if not input_dir.exists():
        print(f"Error: 输入目录不存在: {input_dir}", file=sys.stderr)
        sys.exit(1)

    docs = load_docs(input_dir)
    if len(docs) < 2:
        print(f"Error: 至少需要 2 篇文档才能预检，当前只有 {len(docs)} 篇", file=sys.stderr)
        sys.exit(1)

    results = build_results(docs)

    print("=" * 50)
    print(f"  {results['verdict']}")
    print("=" * 50)
    print(f"  {results['one_line']}")
    print("=" * 50)
    print(f"  文档数: {results['total_docs']} 篇 | 总字数: {results['total_chars']:,} 字 | 分级: {results['severity']}")
    print("=" * 50)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_md(results), encoding="utf-8")

    print(f"\n报告已保存: {output_md}")
    print(f"详细数据:  {output_json}")


if __name__ == "__main__":
    main()
