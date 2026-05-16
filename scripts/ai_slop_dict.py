"""
AI 套话词典 · ai_slop_dict.py

收集中文 AI 写作里高频出现的"AI 味"标记。
分四类：开篇套话、过渡套话、修饰套话、收尾套话。
每条带权重（1-5），权重越高扣分越多。

可由用户在 DNA 文件的 blacklist_phrases 中追加个人定制项。
"""

# ============== 开篇套话 (Opener AI Slop) ==============
# 这类是最重的 AI 味标记，几乎一眼识破
OPENER_SLOP = {
    "在数字化转型的浪潮中": 5,
    "在信息爆炸的时代": 5,
    "在人工智能飞速发展的今天": 5,
    "随着科技的不断进步": 4,
    "作为一名": 3,  # "作为一名资深从业者" 这种
    "众所周知": 4,
    "在当今社会": 4,
    "在快节奏的现代生活中": 5,
    "近年来": 2,
    "随着时代的发展": 4,
    "在这个": 2,  # 弱，但搭配"瞬息万变的时代"就重
    "本文将": 4,
    "本文旨在": 5,
    "下面让我们": 3,
    "让我们一起来": 3,
}

# ============== 过渡套话 (Transition AI Slop) ==============
# AI 最爱用的机械连接词
TRANSITION_SLOP = {
    "首先": 3,
    "其次": 3,
    "再次": 4,
    "最后": 2,  # 弱，因为人也会用
    "综上所述": 5,
    "综上": 4,
    "总而言之": 4,
    "总的来说": 3,
    "总结来说": 4,
    "由此可见": 4,
    "不难看出": 4,
    "值得一提的是": 4,
    "值得注意的是": 3,
    "需要指出的是": 4,
    "从某种意义上来说": 4,
    "从一定程度上": 4,
    "在一定程度上": 3,
    "从某个角度来看": 4,
    "在...方面": 2,
    "就...而言": 3,
}

# ============== 修饰套话 (Modifier AI Slop) ==============
# 空洞的形容词和动词，没有具体信息量
MODIFIER_SLOP = {
    "赋能": 5,
    "重塑": 4,
    "构建": 2,  # 弱，但和"生态"连用就重
    "打造": 3,
    "助力": 4,
    "颠覆": 4,
    "引领": 4,
    "驱动": 3,
    "释放": 3,
    "激活": 3,
    "深度": 2,  # 单字弱，"深度赋能"就重
    "全方位": 4,
    "全面": 2,
    "深入": 2,
    "深入浅出": 3,
    "面面俱到": 4,
    "卓越的": 4,
    "完善的": 3,
    "优质的": 3,
    "优秀的": 2,
    "出色的": 3,
    "强大的": 2,
    "先进的": 3,
    "智能的": 2,
    "高效的": 2,
    "极致的": 4,
    "无与伦比的": 5,
    "一站式": 4,
    "一体化": 3,
    "全链路": 4,
    "端到端": 3,
    "多维度": 3,
    "多元化": 3,
    "多样化": 3,
    "新一代": 3,
    "下一代": 3,
    "全新的": 2,
    "崭新的": 3,
    "革命性的": 4,
    "颠覆性的": 4,
    "突破性的": 4,
    "创新性的": 4,
    "前沿的": 3,
    "尖端的": 3,
}

# ============== 名词套话 (Noun AI Slop) ==============
# 高频虚词组合
NOUN_SLOP = {
    "生态": 3,
    "生态布局": 5,
    "生态系统": 3,
    "生态闭环": 4,
    "解决方案": 2,
    "一站式解决方案": 5,
    "数字化": 3,
    "数字化转型": 4,
    "智能化": 3,
    "信息化": 3,
    "现代化": 3,
    "国际化": 3,
    "全球化": 3,
    "产业链": 3,
    "价值链": 3,
    "护城河": 3,
    "蓝海": 3,
    "红海": 3,
    "赛道": 3,
    "天花板": 2,
    "用户痛点": 3,
    "用户体验": 2,  # 弱，但"极致的用户体验"重
    "用户粘性": 3,
    "用户旅程": 3,
    "用户画像": 3,
    "需求场景": 3,
    "应用场景": 2,
    "落地场景": 3,
    "底层逻辑": 3,
    "顶层设计": 4,
}

# ============== 收尾套话 (Closer AI Slop) ==============
# 文章结尾最爱用的虚话
CLOSER_SLOP = {
    "是值得": 3,  # "是值得各位创作者尝试与推荐的优质工具"
    "值得推荐": 2,
    "值得尝试": 2,
    "不容错过": 4,
    "强烈推荐": 3,
    "强烈安利": 3,
    "亲测有效": 3,
    "干货满满": 4,
    "满满的干货": 4,
    "全是干货": 3,
    "点赞收藏": 3,
    "关注我": 2,
    "评论区见": 2,
    "我们下期再见": 3,
    "敬请期待": 4,
    "拭目以待": 4,
    "前景广阔": 4,
    "未来可期": 4,
    "大有可为": 4,
    "充满无限可能": 4,
    "为...提供了": 3,
    "为...带来了": 3,
    "助你": 3,
    "让你": 2,
    "帮你": 1,  # 弱，太常用
    "成为...的不二之选": 5,
    "不二选择": 4,
}

# ============== 完整词典聚合 ==============
ALL_SLOP = {}
ALL_SLOP.update(OPENER_SLOP)
ALL_SLOP.update(TRANSITION_SLOP)
ALL_SLOP.update(MODIFIER_SLOP)
ALL_SLOP.update(NOUN_SLOP)
ALL_SLOP.update(CLOSER_SLOP)


# ============== 套话组合（更高权重） ==============
# 某些短语单独看权重不高，组合起来就是绝对 AI 标记
SLOP_COMBOS = [
    # (词A, 词B, 距离上限-字符数, 组合权重加成)
    ("赋能", "生态", 30, 5),       # "赋能生态" 几乎必是 AI
    ("打造", "生态", 30, 4),
    ("一站式", "解决方案", 20, 5),
    ("深度", "赋能", 10, 4),
    ("全方位", "覆盖", 20, 3),
    ("多维度", "分析", 20, 3),
    ("数字化", "转型", 10, 3),
    ("智能化", "升级", 20, 3),
    ("打造", "闭环", 30, 4),
    ("构建", "生态", 20, 4),
]


# ============== 句式套话 (正则模式) ==============
import re

SLOP_PATTERNS = [
    # (正则, 描述, 权重)
    (r"作为一名[\u4e00-\u9fa5]{2,8}", "作为一名X的开场白", 3),
    (r"在[\u4e00-\u9fa5]{2,10}的(浪潮|时代|今天|当下)", "在X的浪潮/时代套话", 5),
    (r"是一款[\u4e00-\u9fa5]{0,10}的[\u4e00-\u9fa5]{2,8}(平台|工具|产品|应用)", "是一款X的Y平台/工具", 4),
    (r"旨在通过[\u4e00-\u9fa5]{2,30}帮助", "旨在通过X帮助Y", 5),
    (r"本文将从[\u4e00-\u9fa5]{0,8}多个维度", "本文将从多个维度", 5),
    (r"凭借其[\u4e00-\u9fa5]{2,15}", "凭借其X", 3),
    (r"为[\u4e00-\u9fa5]{2,10}提供了[\u4e00-\u9fa5]{0,15}解决方案", "为X提供了解决方案", 4),
]


def detect_slop(text: str) -> dict:
    """
    检测一段文本里的 AI 套话。

    Returns:
        {
            "score": int (0-100, 越高越 AI),
            "hits": [{"phrase": str, "weight": int, "position": int, "category": str}, ...],
            "combo_hits": [{"combo": tuple, "bonus": int}, ...],
            "pattern_hits": [{"match": str, "description": str, "weight": int}, ...],
        }
    """
    hits = []

    # 单词检测
    categories = {
        "OPENER": OPENER_SLOP,
        "TRANSITION": TRANSITION_SLOP,
        "MODIFIER": MODIFIER_SLOP,
        "NOUN": NOUN_SLOP,
        "CLOSER": CLOSER_SLOP,
    }
    for cat_name, cat_dict in categories.items():
        for phrase, weight in cat_dict.items():
            start = 0
            while True:
                idx = text.find(phrase, start)
                if idx == -1:
                    break
                hits.append({
                    "phrase": phrase,
                    "weight": weight,
                    "position": idx,
                    "category": cat_name,
                })
                start = idx + len(phrase)

    # 组合检测
    combo_hits = []
    for word_a, word_b, max_dist, bonus in SLOP_COMBOS:
        idx_a = 0
        while True:
            idx_a = text.find(word_a, idx_a)
            if idx_a == -1:
                break
            idx_b = text.find(word_b, idx_a, idx_a + len(word_a) + max_dist)
            if idx_b != -1:
                combo_hits.append({
                    "combo": (word_a, word_b),
                    "bonus": bonus,
                    "position": idx_a,
                })
            idx_a += len(word_a)

    # 句式检测
    pattern_hits = []
    for pattern, description, weight in SLOP_PATTERNS:
        for m in re.finditer(pattern, text):
            pattern_hits.append({
                "match": m.group(0),
                "description": description,
                "weight": weight,
                "position": m.start(),
            })

    # 计算总分
    # 公式：基础分 = 所有 hits 的权重和，按文本长度归一化到 0-100
    # 假设每 100 字出现权重和为 20 算"重度 AI"，则得分 100
    raw_score = sum(h["weight"] for h in hits)
    raw_score += sum(c["bonus"] for c in combo_hits)
    raw_score += sum(p["weight"] for p in pattern_hits)

    text_len = max(len(text), 100)
    # 归一化：每 100 字权重和 20 = 100 分
    normalized = min(100, int(raw_score * 100 / (text_len * 0.2)))

    return {
        "score": normalized,
        "hits": hits,
        "combo_hits": combo_hits,
        "pattern_hits": pattern_hits,
        "raw_score": raw_score,
        "text_length": len(text),
    }


if __name__ == "__main__":
    # 自测
    sample = """在数字化转型的浪潮中，AI 编辑器作为新一代生产力工具，正在重塑内容创作行业的生态。
首先，从功能层面来看，它赋能创作者，提供一站式的解决方案。
综上所述，是值得推荐的优质工具。"""
    result = detect_slop(sample)
    print(f"AI 味分数: {result['score']}/100")
    print(f"原始权重和: {result['raw_score']}")
    print(f"命中: {len(result['hits'])} 个单词套话, {len(result['combo_hits'])} 个组合, {len(result['pattern_hits'])} 个句式")
    for h in result["hits"][:10]:
        print(f"  - [{h['category']}] {h['phrase']} (权重 {h['weight']})")
