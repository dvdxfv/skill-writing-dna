#!/usr/bin/env python3
"""
样本量充足性测试：留一法 + 同型异型拆分 + 特征饱和度曲线
"""

import json
import re
import itertools
from pathlib import Path
from collections import Counter

INPUT_DIR = Path(r"G:\开发项目\skill项目\inputs\template_stripped_markdown")
OUTPUT_JSON = Path(r"G:\开发项目\skill项目\outputs\debug\sample_sufficiency_test.json")
OUTPUT_MD = Path(r"G:\开发项目\skill项目\outputs\debug\sample_sufficiency_test.md")

# ── 文档标签（项目类型）──
DOC_TAGS = {
    "（某人）2023-2024年山西美好蕴育生物科技有限责任公司绩效评价报告（定稿）.md": "入园企业",
    "（某人）2023-2024年山西途悦选煤工程技术股份有限公司绩效评价报告（初稿）.md": "入园企业",
    "（某人）2024年保德县韩家川乡寨沟村壮大村集体经济项目绩效评价报告(2).md": "村集体",
    "（某人）2024年运城市财政局评审经费项目支出绩效评价报告.md": "财政评审",
    "（某人）2025年榆次区改制企业经费项目绩效评价报告(1).md": "改制经费",
}

# ── 提取可量化特征 ──
def extract_features(text: str) -> dict[str, float]:
    features = {}

    # 1. 枚举式并列展开
    enum_count = len(re.findall(r"(?:一是|二是|三是|四是|五是|六是)", text))
    features["enum_density"] = enum_count / max(len(text), 1) * 1000

    # 2. 建议密度（建议+应+需+可）
    suggest_count = len(re.findall(r"(?:建议|应当?|[应需可]以?)", text))
    features["suggest_density"] = suggest_count / max(len(text), 1) * 1000

    # 3. 制度名词密度
    institution_count = len(re.findall(r"(?:机制|制度|流程|体系|权责|职责|衔接|管理办法)", text))
    features["institution_density"] = institution_count / max(len(text), 1) * 1000

    # 4. 数字嵌入密度（非表格数字）
    number_count = len(re.findall(r"\d+\.?\d*万?元?人?家?个?次?%?", text))
    features["number_density"] = number_count / max(len(text), 1) * 1000

    # 5. 平均句长
    sentences = re.split(r"[。！？\n]+", text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
    if sentences:
        features["avg_sentence_len"] = sum(len(s) for s in sentences) / len(sentences)

    # 6. "先判断后展开" — 检测段落首句是否为判断句（含"是/为/存在/涉及/欠缺/不足"）
    paras = re.split(r"\n\n+", text)
    judgment_openers = 0
    for p in paras:
        p = p.strip()
        if not p or len(p) < 10:
            continue
        first_sent = re.split(r"[。！？]", p)[0]
        if re.search(r"(?:是|为|存在|涉及|欠缺|不足|不到位|不充分|有所)", first_sent) and len(first_sent) < 80:
            judgment_openers += 1
    features["judgment_opener_ratio"] = judgment_openers / max(len(paras), 1)

    # 7. 转折表达密度
    contrast_count = len(re.findall(r"(?:但|然而|不过|尽管|虽然)", text))
    features["contrast_density"] = contrast_count / max(len(text), 1) * 1000

    # 8. 消极/缺陷词密度
    deficiency_count = len(re.findall(r"(?:欠缺|不足|不到位|不充分|不完整|不规范|未\d)", text))
    features["deficiency_density"] = deficiency_count / max(len(text), 1) * 1000

    return features


def load_docs():
    docs = {}
    for f in sorted(INPUT_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        docs[f.name] = {"text": text, "tag": DOC_TAGS.get(f.name, "未知"), "chars": len(text)}
    return docs


def all_combinations(doc_names, min_n=1, max_n=None):
    if max_n is None:
        max_n = len(doc_names)
    result = []
    for n in range(min_n, max_n + 1):
        result.extend(itertools.combinations(doc_names, n))
    return result


def feature_ranking(feature_vec: dict[str, float]) -> list[str]:
    """返回特征按值的排序（从高到低），用于比较稳定性"""
    return sorted(feature_vec.keys(), key=lambda k: feature_vec.get(k, 0), reverse=True)


def rank_distance(rank1: list[str], rank2: list[str]) -> float:
    """计算两个排名的距离（0=完全相同, 1=完全不同）"""
    common = set(rank1) & set(rank2)
    if not common:
        return 1.0
    dist = 0.0
    for feat in common:
        dist += abs(rank1.index(feat) - rank2.index(feat))
    max_dist = len(common) * len(common)  # worst case
    return dist / max(max_dist, 1)


def avg_features(doc_list):
    """对多篇文档的特征取平均"""
    if not doc_list:
        return {}
    keys = doc_list[0].keys()
    avg = {}
    for k in keys:
        avg[k] = sum(d[k] for d in doc_list) / len(doc_list)
    return avg


# ══════════════════════════════════════════════════
#  TEST 1: 留一法稳定性
# ══════════════════════════════════════════════════
def test_leave_one_out(docs):
    """逐篇去掉，看特征排序是否稳定"""
    names = list(docs.keys())
    full_features = avg_features([extract_features(docs[n]["text"]) for n in names])
    full_rank = feature_ranking(full_features)

    results = []
    for i, name in enumerate(names):
        subset = [n for j, n in enumerate(names) if j != i]
        sub_features = avg_features([extract_features(docs[n]["text"]) for n in subset])
        sub_rank = feature_ranking(sub_features)
        dist = rank_distance(full_rank, sub_rank)
        results.append({
            "removed": name,
            "subset_n": len(subset),
            "rank_distance": round(dist, 3),
            "full_rank": full_rank[:6],
            "subset_rank": sub_rank[:6],
        })

    avg_dist = sum(r["rank_distance"] for r in results) / len(results)
    return {"per_doc": results, "avg_distance": round(avg_dist, 3), "stable": avg_dist < 0.25}


# ══════════════════════════════════════════════════
#  TEST 2: 同型 vs 异型拆分
# ══════════════════════════════════════════════════
def test_type_split(docs):
    """按项目类型分组，比较组间差异"""
    groups = {}
    for name, info in docs.items():
        tag = info["tag"]
        groups.setdefault(tag, []).append(name)

    # 同型组：入园企业2篇
    if "入园企业" in groups and len(groups["入园企业"]) >= 2:
        same_type_names = groups["入园企业"][:2]
        same_features = avg_features([extract_features(docs[n]["text"]) for n in same_type_names])
        same_rank = feature_ranking(same_features)
    else:
        same_rank = []

    # 异型组：取三种类型各1篇
    cross_type_names = []
    for tag, names in groups.items():
        if names:
            cross_type_names.append(names[0])
    cross_type_names = cross_type_names[:3]
    cross_features = avg_features([extract_features(docs[n]["text"]) for n in cross_type_names])
    cross_rank = feature_ranking(cross_features)

    # 全量5篇组
    all_names = list(docs.keys())
    all_features = avg_features([extract_features(docs[n]["text"]) for n in all_names])
    all_rank = feature_ranking(all_features)

    return {
        "same_type_2docs": {
            "documents": same_type_names,
            "rank_top6": same_rank[:6],
            "tag": "入园企业（共建园区系列，背景材料高度共用）",
        },
        "cross_type_3docs": {
            "documents": cross_type_names,
            "rank_top6": cross_rank[:6],
            "tag": "三种不同类型各1篇",
        },
        "all_5docs": {
            "rank_top6": all_rank[:6],
        },
        "same_vs_all_distance": round(rank_distance(same_rank, all_rank), 3),
        "cross_vs_all_distance": round(rank_distance(cross_rank, all_rank), 3),
    }


# ══════════════════════════════════════════════════
#  TEST 3: 特征饱和度曲线
# ══════════════════════════════════════════════════
def test_saturation_curve(docs):
    """对所有组合抽取特征，看稳定特征数随篇数变化"""
    names = list(docs.keys())
    all_combos = all_combinations(names, min_n=1, max_n=len(names))

    # 全量排名作为基准
    full_features = avg_features([extract_features(docs[n]["text"]) for n in names])
    full_rank = feature_ranking(full_features)

    # 按篇数分组统计
    by_n = {}
    for combo in all_combos:
        n = len(combo)
        feat = avg_features([extract_features(docs[n]["text"]) for n in combo])
        rk = feature_ranking(feat)
        dist = rank_distance(rk, full_rank)
        overlap = len(set(rk[:6]) & set(full_rank[:6]))
        by_n.setdefault(n, []).append({
            "combo": list(combo),
            "rank_distance": round(dist, 3),
            "top6_overlap": overlap,
        })

    curve = {}
    for n in sorted(by_n.keys()):
        entries = by_n[n]
        avg_dist = sum(e["rank_distance"] for e in entries) / len(entries)
        avg_overlap = sum(e["top6_overlap"] for e in entries) / len(entries)
        curve[n] = {
            "combinations": len(entries),
            "avg_rank_distance": round(avg_dist, 3),
            "avg_top6_overlap": round(avg_overlap, 1),
        }

    return curve


# ══════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════
def main():
    docs = load_docs()
    names = list(docs.keys())
    total_chars = sum(info["chars"] for info in docs.values())

    print(f"加载 {len(docs)} 篇文档，总字数 {total_chars} 字符")
    for n in names:
        print(f"  [{docs[n]['tag']}] {n[:40]}... ({docs[n]['chars']}字)")

    # Test 1
    print("\n=== TEST 1: 留一法稳定性 ===")
    t1 = test_leave_one_out(docs)
    for r in t1["per_doc"]:
        print(f"  去掉 '{r['removed'][:40]}...' → rank距离={r['rank_distance']}")
    print(f"  平均距离: {t1['avg_distance']}  {'✅ 稳定' if t1['stable'] else '❌ 不够稳'}")

    # Test 2
    print("\n=== TEST 2: 同型 vs 异型 ===")
    t2 = test_type_split(docs)
    print(f"  同型2篇 vs 全量5篇: 距离={t2['same_vs_all_distance']}")
    print(f"  异型3篇 vs 全量5篇: 距离={t2['cross_vs_all_distance']}")
    print(f"  同型 top6: {t2['same_type_2docs']['rank_top6']}")
    print(f"  异型 top6: {t2['cross_type_3docs']['rank_top6']}")
    print(f"  全量 top6: {t2['all_5docs']['rank_top6']}")

    # Test 3
    print("\n=== TEST 3: 特征饱和度 ===")
    t3 = test_saturation_curve(docs)
    for n in sorted(t3.keys()):
        v = t3[n]
        bar = "█" * int(v["avg_top6_overlap"] / 2)
        print(f"  {n}篇 ({v['combinations']:2d}组合) | 距离={v['avg_rank_distance']} | top6重叠={v['avg_top6_overlap']}/6 {bar}")

    # Save results
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    results = {
        "total_docs": len(docs),
        "total_chars": total_chars,
        "doc_list": {n: {"tag": docs[n]["tag"], "chars": docs[n]["chars"]} for n in names},
        "test1_leave_one_out": t1,
        "test2_type_split": {k: v for k, v in t2.items() if k != "same_type_2docs" and k != "cross_type_3docs" and k != "all_5docs"},
        "test2_detail": {
            "same_type_top6": t2["same_type_2docs"]["rank_top6"],
            "cross_type_top6": t2["cross_type_3docs"]["rank_top6"],
            "all_top6": t2["all_5docs"]["rank_top6"],
            "same_vs_all": t2["same_vs_all_distance"],
            "cross_vs_all": t2["cross_vs_all_distance"],
        },
        "test3_saturation": t3,
    }
    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generate markdown report
    md_lines = []
    md_lines.append("# 样本量充足性测试报告\n")
    md_lines.append(f"**输入**：{len(docs)} 篇文档，总字数 {total_chars} 字符\n")
    md_lines.append("| 编号 | 类型 | 文件 | 字数 |")
    md_lines.append("|:---:|:---|:---|:---:|")
    for i, n in enumerate(names, 1):
        md_lines.append(f"| {i} | {docs[n]['tag']} | {n[:30]}... | {docs[n]['chars']} |")
    md_lines.append("")

    md_lines.append("## Test 1: 留一法稳定性\n")
    md_lines.append("逐一去掉 1 篇，看剩余 4 篇的特征排序是否与全量 5 篇一致。距离越接近 0 越稳。\n")
    md_lines.append("| 去掉的文档 | 子集篇数 | 排名距离 | 判定 |")
    md_lines.append("|:---|:---:|:---:|:---:|")
    for r in t1["per_doc"]:
        flag = "✅" if r["rank_distance"] < 0.25 else "⚠️" if r["rank_distance"] < 0.4 else "❌"
        md_lines.append(f"| {r['removed'][:25]}... | 4 | {r['rank_distance']} | {flag} |")
    md_lines.append(f"\n**平均距离：{t1['avg_distance']}**")
    md_lines.append(f"**结论：{'✅ 5篇特征排序稳定' if t1['stable'] else '❌ 5篇不够稳，建议增加到8篇'}**\n")

    md_lines.append("## Test 2: 同型 vs 异型拆分\n")
    md_lines.append("比较同类型文档组（入园企业2篇，背景段高度共用）与跨类型文档组（3种不同类型各1篇）的特征排序差异。\n")
    md_lines.append(f"- 同型2篇 vs 全量5篇距离：**{t2['same_vs_all_distance']}**")
    md_lines.append(f"- 异型3篇 vs 全量5篇距离：**{t2['cross_vs_all_distance']}**")
    md_lines.append(f"\n| 组别 | Top-6 特征 |")
    md_lines.append("|:---|:---|")
    md_lines.append(f"| 同型2篇 | {', '.join(t2['same_type_2docs']['rank_top6'][:6])} |")
    md_lines.append(f"| 异型3篇 | {', '.join(t2['cross_type_3docs']['rank_top6'][:6])} |")
    md_lines.append(f"| 全量5篇 | {', '.join(t2['all_5docs']['rank_top6'][:6])} |")
    if t2['cross_vs_all_distance'] < t2['same_vs_all_distance']:
        md_lines.append(f"\n**结论：异型3篇比同型2篇更接近全量结果 → 类型多样性比篇数更重要。**\n")
    else:
        md_lines.append(f"\n**结论：同型与异型差距不大 → 当前5篇类型覆盖已基本够用。**\n")

    md_lines.append("## Test 3: 特征饱和度曲线\n")
    md_lines.append("对所有可能组合（1篇到5篇）抽取特征，看 top-6 特征与全量结果的重叠数随篇数变化。\n")
    md_lines.append("| 篇数 | 组合数 | 平均排名距离 | 平均 top6 重叠 | 趋势 |")
    md_lines.append("|:---:|:---:|:---:|:---:|:---:|")
    prev_overlap = 0
    for n in sorted(t3.keys()):
        v = t3[n]
        bar = "█" * int(v["avg_top6_overlap"] / 2)
        trend = ""
        if v["avg_top6_overlap"] > prev_overlap + 0.5:
            trend = "↑ 陡升"
        elif v["avg_top6_overlap"] > prev_overlap + 0.1:
            trend = "↗ 缓升"
        else:
            trend = "→ 平"
        md_lines.append(f"| {n} | {v['combinations']} | {v['avg_rank_distance']} | {v['avg_top6_overlap']}/6 {bar} | {trend} |")
        prev_overlap = v["avg_top6_overlap"]

    # 判断是否饱和
    if len(t3) >= 2:
        n4 = t3.get(4, {})
        n5 = t3.get(5, {})
        if n4 and n5:
            gain = n5["avg_top6_overlap"] - n4["avg_top6_overlap"]
            if gain < 0.5:
                md_lines.append(f"\n**结论：从4篇到5篇仅增加 {gain:.1f} 个重叠特征 → 曲线已趋平，5篇接近饱和。建议当前篇数可维持，如需扩展优先增加不同类型文档。**\n")
            else:
                md_lines.append(f"\n**结论：从4篇到5篇增加 {gain:.1f} 个重叠特征 → 曲线仍在上升，建议增加到8篇。**\n")

    md_lines.append("## 综合建议\n")
    md_lines.append("| 指标 | 数值 | 阈值 | 结论 |")
    md_lines.append("|:---|:---:|:---|:---|")
    stable = t1["avg_distance"] < 0.25
    md_lines.append(f"| 留一法稳定性 | {t1['avg_distance']} | <0.25 | {'✅ 通过' if stable else '❌ 不通过'} |")
    cross_better = t2['cross_vs_all_distance'] < t2['same_vs_all_distance']
    md_lines.append(f"| 类型多样性收益 | 异型距离{t2['cross_vs_all_distance']} vs 同型{t2['same_vs_all_distance']} | 异型更小 | {'✅ 多样性有效' if cross_better else '⚠️ 差异不大'} |")
    sat = n5["avg_top6_overlap"] - n4["avg_top6_overlap"] < 0.5
    md_lines.append(f"| 饱和度 | 4→5篇增益={n5['avg_top6_overlap'] - n4['avg_top6_overlap']:.1f} | <0.5 | {'✅ 接近饱和' if sat else '❌ 仍在上升'} |")

    if stable and cross_better and sat:
        md_lines.append(f"\n### 最终结论：✅ 当前 5 篇够用，无需追加。")
        md_lines.append(f"如果后续想增强，优先加不同类型的 2-3 篇，而非同类型堆量。")
    elif stable and not sat:
        md_lines.append(f"\n### 最终结论：⚠️ 5 篇可用但不稳，建议加到 8 篇。")
    else:
        md_lines.append(f"\n### 最终结论：❌ 5 篇偏少，留一法不稳定，建议加到 8 篇。")

    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n结果已保存：")
    print(f"  JSON: {OUTPUT_JSON}")
    print(f"  MD:   {OUTPUT_MD}")


if __name__ == "__main__":
    main()
