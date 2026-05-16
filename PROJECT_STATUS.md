# 项目进度状态

## 当前阶段

`全链路闭环比对完成，最小可交付产物就绪`

5 篇正式样本已走通完整链路，DNA 提取 + 改写验证已完成一轮闭环。

## 开发资源消耗

| 资源 | 用量 | Token 消耗（估算） | 费用（按 API 市价折算） |
|:---|:---|:---|:---|
| 开发时间 | 4 小时 | — | — |
| Claude（Codex 环境） | 5 小时用量 | ~350,000–700,000 | ~$5–$11 |
| ChatGPT（Codex 环境） | 5 小时用量 | ~225,000–1,125,000 | ~$2.5–$12.5 |
| DeepSeek（Flash + Pro 混用） | API 调用 | 22,498,980 | 2.95 元 |

> Claude 和 ChatGPT 为订阅制套餐（$20/月），表中费用按其 API 标准价格（Claude Sonnet 4.6: $3/$15 每百万 token；GPT-5.1 codex: $2.50/$20 每百万 token）对估算 token 消耗做的折算参考。DeepSeek 为实际 API 计费金额。

## 已完成的完整链路

```
raw_docx_articles (5 DOCX)
  → normalized_markdown (DOCX→MD 转换)
  → filtered_markdown (非正文过滤)
  → template_stripped_markdown (模板剥离)
  → dna_profiles (DNA 提取，人工+复核)
  → rewrite_runs (AI草稿按DNA改写)
```

### 各环节产物

| 环节 | 输入 | 输出 | 脚本 |
|:---|:---|:---|:---|
| DOCX→MD | `inputs/raw_docx_articles/` | `inputs/normalized_markdown/` | `scripts/docx_to_md.py` |
| 非正文过滤 | `inputs/normalized_markdown/` | `inputs/filtered_markdown/` | `scripts/filter_non_prose.py` |
| 模板剥离 | `inputs/filtered_markdown/` | `inputs/template_stripped_markdown/` | `scripts/strip_template.py` |
| DNA 提取 | `inputs/template_stripped_markdown/` | `outputs/dna_profiles/` | 人工分析 + 复核 |
| 改写验证 | `inputs/ai_drafts/new_ai_draft.docx` | `outputs/rewrite_runs/` | 人工操作（按 DNA） |

## DNA 最终产物

| 文件 | 说明 |
|:---|:---|
| `outputs/dna_profiles/guanhang_dna_profile.md` | 人工提取 + 复核后的写作DNA画像（**正式主输出**） |
| `outputs/dna_profiles/guanhang_dna_evidence.md` | DNA 证据链说明 |
| `outputs/dna_profiles/guanhang_dna_profile.json` | DNA 结构化版本（可程序读取） |
| `outputs/dna_profiles/guanhang_dna_feature_cloud.png` | "DNA 特征云"可视化 |

> `outputs/dna_profiles/管航-single-dna.json` 为早期单篇词频版，`guanhang_auto_dna.json` 为自动统计版，均保留作历史参考，正式 DNA 以 `guanhang_dna_profile.md` 为准。

## 改写验证产物

| 文件 | 说明 |
|:---|:---|
| `inputs/ai_drafts/new_ai_draft.docx` | AI 草稿原始输入（AI 味浓，用于对比） |
| `outputs/rewrite_runs/new_ai_draft_effective_input.md` | 定版后的纯净正文输入 |
| `outputs/rewrite_runs/rewritten_draft.md` | 按 DNA 改写后的成稿 |
| `outputs/rewrite_runs/rewrite_notes.md` | 改写过程说明 |
| `outputs/rewrite_runs/rewrite_debug.json` | 改写调试信息 |

> **参赛对比链：** `new_ai_draft.docx`（AI原稿）→ `effective_input.md`（定版输入）→ `rewritten_draft.md`（改写结果）三件套完整可展示。

## 脚本清单

| 脚本 | 状态 |
|:---|:---|
| `scripts/docx_to_md.py` | ✅ 已实现 |
| `scripts/filter_non_prose.py` | ✅ 已实现 |
| `scripts/strip_template.py` | ✅ 已实现（本项目中新增） |
| `scripts/render_dna_feature_cloud.py` | ✅ 已实现（本项目中新增） |
| `scripts/detect_ai_slop.py` | ✅ 已实现 |
| `scripts/ai_slop_dict.py` | ✅ 已实现 |
| `scripts/extract_dna.py` | ⚪ 占位骨架 |
| `scripts/extract_template_profile.py` | ⚪ 占位骨架 |
| `scripts/rewrite_with_dna.py` | ⚪ 占位骨架 |
| `scripts/generate_report.py` | ⚪ 占位骨架 |

## 项目文件分类速查

### 最终产物（交付用）
```
outputs/dna_profiles/guanhang_dna_profile.md
outputs/dna_profiles/guanhang_dna_evidence.md
outputs/dna_profiles/guanhang_dna_profile.json
outputs/dna_profiles/guanhang_dna_feature_cloud.png
outputs/rewrite_runs/rewritten_draft.md
outputs/rewrite_runs/rewrite_notes.md
outputs/rewrite_runs/rewrite_debug.json
```

### 对比链路（参赛展示用）
```
inputs/ai_drafts/new_ai_draft.docx          ← AI原稿
outputs/rewrite_runs/new_ai_draft_effective_input.md  ← 定版输入
outputs/rewrite_runs/rewritten_draft.md               ← 改写结果
```

### 中间产物（链路追踪用）
```
inputs/normalized_markdown/     ← DOCX→MD 转换结果
inputs/filtered_markdown/       ← 非正文过滤结果
inputs/template_stripped_markdown/  ← 模板剥离结果
outputs/rewrite_runs/new_ai_draft_extracted.md  ← AI草稿原始提取稿
```

### 参考留存（历史版本/外部样本）
```
outputs/dna_profiles/管航-single-dna.json       ← 早期单篇提取版
outputs/dna_profiles/管航-single-dna_hotwords.png  ← 早期词频图
outputs/dna_profiles/guanhang_auto_dna.json      ← 自动统计版
outputs/dna_profiles/guanhang_auto_dna_hotwords.png ← 自动统计词频图
outputs/老张-dna.json                ← 另一作者DNA参考
outputs/ai_score.json                ← AI味检测测试结果
outputs/debug/single_docx_chain_check.md ← 单篇链路调试记录
examples/                            ← 外部AI味检测样本
archive/duplicate_downloads/         ← 历史重复下载
docs/writing-dna-*.md               ← 项目设计文档
```

## 推荐样本量

基于当前 5 篇实测验证：

| 篇数 | 效果 | 说明 |
|:---:|:---|:---|
| 1-4 | ❌ 不足 | 无法区分单篇特有与跨篇稳定 |
| 5 | ⚠️ 下限 | 刚好让稳定特征浮现，不确定项偏多 |
| 8 | ✅ 甜点 | 不确定项收敛，大部分特征确认 |
| 12 | ✅ 上限 | 特征基本饱和，再增量边际收益极低 |

## 当前明确未完

- `extract_dna.py` / `rewrite_with_dna.py` / `extract_template_profile.py` / `generate_report.py` 仍为占位骨架，对应环节由人工完成
- `outputs/template_profiles/` 与 `outputs/reports/` 未产出内容（模板剥离已在 strip_template.py 完成，但未生成独立模板画像文件）
- 未做多作者交叉验证
- 留一法稳定性测试已完成（脚本见 `scripts/test_sample_sufficiency.py`，报告见 `outputs/debug/sample_sufficiency_test.md`）
- **跨模型 benchmark 未执行** — 设计方案如下

## 跨模型 Benchmark 设计（占位，未跑）

### 目标

用同一份 DNA（`guanhang_dna_profile.md`）和同一份 AI 草稿（`inputs/ai_drafts/new_ai_draft.docx`），让不同大模型分别执行改写，横向对比各模型对"写作 DNA 改写"任务的执行质量。

### 待测模型矩阵

| 厂商 | 模型 | 口径 |
|:---|:---|:---|
| DeepSeek | DeepSeek V4 Pro | 旗舰推理 |
| DeepSeek | DeepSeek V4 Flash | 轻量快速 |
| OpenAI | ChatGPT 5.4 | 上一代旗舰 |
| OpenAI | ChatGPT 5.5 | 最新旗舰 |
| Anthropic | Claude 4.6 | 上一代旗舰 |
| Anthropic | Claude 4.7 | 最新旗舰 |

### 统一输入

- **DNA**：`outputs/dna_profiles/guanhang_dna_profile.md` 中的 8 条改写规则
- **改写对象**：`outputs/rewrite_runs/new_ai_draft_effective_input.md`（纯净正文输入稿）
- **提示词**：统一 prompt，包含完整的 DNA 规则 + 改写边界约束

### 评测维度（计划）

| 维度 | 测量方式 |
|:---|:---|
| DNA 规则遵循度 | 人工逐条核验 8 条规则是否被落实 |
| AI 味残留 | `scripts/detect_ai_slop.py` 打分 |
| 信息完整性 | 原文关键事实（金额/人数/机构/政策）保留率 |
| 风格相似度 | 与管航原笔 5 篇的句长/连接词/制度词分布对比 |
| 可读性 | 人工盲评 |

### 预期产出

| 文件 | 说明 |
|:---|:---|
| `outputs/model_benchmarks/` | 各模型改写结果存放目录 |
| `outputs/model_benchmarks/{model_name}_rewritten.md` | 各模型改写稿 |
| `outputs/model_benchmarks/benchmark_report.md` | 横向对比报告 |
| `outputs/model_benchmarks/benchmark_scores.json` | 结构化评分数据 |

### 当前状态

⚪ 仅设计，未执行。所有脚本和 prompt 待明天实现。
