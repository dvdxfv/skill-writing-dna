# 项目进度状态

## 当前阶段

`文档与提示词生产就绪，待执行跨模型 Benchmark`

- ✅ 全链路闭环已跑通（5篇样本 → DNA提取 → 改写验证）
- ✅ README.md 去敏完毕，流程图/诊断路径/检查清单完整
- ✅ SKILL.md 提示词完善，两个强制停等节点（第4步DNA确认 + 第7步效果确认）已写入
- ✅ 样本充足性测试脚本输出一句话结论
- ⏳ **下一步：跨模型 Benchmark**（见文末）

---

## 今天完成的改动（按提交顺序）

### 安全脱敏（3个commit）

| commit | 内容 |
|:---|:---|
| `d47fd48` | 脱敏处理真实姓名"管航" |
| `bb7728b` | 文件名脱敏 guanhang→user、管航→某人 |

> 所有 git 跟踪文件中的真实姓名已替换为"某人"，文件名中的拼音已替换为"user"。本地 outputs 目录也做了批量替换。

### README.md 文档重构（6个commit）

| commit | 内容 |
|:---|:---|
| `fcdf443` | 流程图精简 + 诊断路径初版 + 模型矩阵标注 |
| `a7b6c04` | 流程图重新设计——突出人工介入点（蓝色菱形） |
| `46ddef3` | 恢复TD布局 + 精简到10节点 + 强化人工介入点样式 |
| `e8b9251` | 样本多样性章节重写——增加实操指导和诊断联动 |
| `de823dc` | **样本去敏**（去除绩效评价报告等具体案例→改为通用类型描述）+ **诊断路径完整重写**（4步决策树） |
| `82bee5e` | 第4步和第7步检查指引（对称的4项检查表 + 排查路径） |

**README.md 当前结构：**
```
1. 全流程总览（一句话流程 + 完整mermaid流程图）
2. 🔵 第4步：DNA准确吗？—— 5项检查清单（热词图排第1）
3. 🔵 第7步：效果满意吗？—— 4项检查清单 + 3步排查路径
4. 关于样本（数量建议 + 类型多样性 + 好坏组合示例）
5. 效果不好怎么办（4步诊断决策树 + 快速定位对照表）
6. 使用方式 / 文件说明 / 开发指南
```

### SKILL.md 提示词完善（3个commit）

| commit | 内容 |
|:---|:---|
| `82bee5e` | 流程A Step3：从"让用户确认"升级为"⏸️必须停下等用户确认"+ 4项检查清单 |
| `caacac8` | 热词图作为DNA检查第1依据 + 流程B Step4拆分为停等(Step4)+交付(Step5) + 改写效果检查清单 |
| `a63286e` | 明确要求模型用图片语法展示热词图 + 告知所有产出文件的完整路径 |

**SKILL.md 当前两个强制停等节点：**

| 节点 | 时机 | 检查项数 | 模型必须做的事 |
|:---|:---|:---:|:---|
| 🔵 第4步 | DNA提取完成后 | 5项（热词图/短语/句长/黑名单/开头结尾） | 展示热词图(PNG+路径) + 文字版DNA + 停下等回复 |
| 🔵 第7步 | 改写+报告生成后 | 4项（AI味/像不像/信息/可用性） | 展示报告结论+改写全文(均带路径) + 停下等回复 |

### 测试脚本改进（1个commit）

| commit | 内容 |
|:---|:---|
| `3c519ae` | `test_sample_sufficiency.py` 输出一句话结论 + argparse参数化 + 去硬编码路径 |

**测试脚本当前行为：**
```
运行: python scripts/test_sample_sufficiency.py

输出:
==================================================
  ✅ 样本基本够用    （或 ❌样本不足 / ⚠️接近但未饱和）
==================================================
  当前5篇的特征排序稳定、曲线已饱和，够用。...
==================================================
  文档数: 5 篇 | 总字数: 26,470 字
  留一法波动: 0.012
  饱和度增益(4→5篇): +0.0 特征
==================================================

产出:
  outputs/debug/sample_sufficiency_test.md   （详细报告，顶部有结论）
  outputs/debug/sample_sufficiency_test.json （结构化数据）
```

---

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
| DNA 提取 | `inputs/template_stripped_markdown/` | `outputs/dna_profiles/` | `scripts/extract_dna.py`（自动统计+热词图） |
| 样本测试 | `inputs/template_stripped_markdown/` | `outputs/debug/` | `scripts/test_sample_sufficiency.py`（留一法+饱和度曲线） |
| 改写验证 | `inputs/ai_drafts/new_ai_draft.docx` | `outputs/rewrite_runs/` | `scripts/rewrite_with_dna.py` |

## DNA 最终产物

| 文件 | 说明 |
|:---|:---|
| `outputs/dna_profiles/user_dna_profile.md` | 人工提取 + 复核后的写作DNA画像（**正式主输出**） |
| `outputs/dna_profiles/user_dna_evidence.md` | DNA 证据链说明 |
| `outputs/dna_profiles/user_dna_profile.json` | DNA 结构化版本（可程序读取） |
| `outputs/dna_profiles/user_dna_feature_cloud.png` | "DNA 特征云"可视化（特征云词云） |
| `<用户名>-dna_hotwords.png` | **热词条形图**（extract_dna.py每次自动生成，DNA检查第一依据）|

> `outputs/dna_profiles/某人-single-dna.json` 为早期单篇词频版，`user_auto_dna.json` 为自动统计版，均保留作历史参考，正式 DNA 以 `user_dna_profile.md` 为准。

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

| 脚本 | 状态 | 今日改动 |
|:---|:---|:---|:---|
| `scripts/docx_to_md.py` | ✅ 已实现 | — |
| `scripts/filter_non_prose.py` | ✅ 已实现 | — |
| `scripts/strip_template.py` | ✅ 已实现 | — |
| `scripts/render_dna_feature_cloud.py` | ✅ 已实现 | — |
| `scripts/detect_ai_slop.py` | ✅ 已实现 | — |
| `scripts/ai_slop_dict.py` | ✅ 已实现 | — |
| `scripts/extract_dna.py` | ✅ 已实现 | — |
| `scripts/extract_template_profile.py` | ✅ 已实现 | — |
| `scripts/rewrite_with_dna.py` | ✅ 已实现 | — |
| `scripts/generate_report.py` | ✅ 已实现 | — |
| `scripts/test_sample_sufficiency.py` | ✅ 已实现 | ✅ 新增一句话结论 + argparse + 去硬编码路径 |

## 核心文档

| 文件 | 角色 | 今日改动 |
|:---|:---|:---|:---|
| `README.md` | GitHub 面向用户的完整文档 | ✅ 大幅重写（去敏+流程图+双检查指引+诊断路径） |
| `SKILL.md` | 模型在对话框里的行为指令（核心提示词） | ✅ 大幅增强（双强制停等+检查清单+文件路径告知） |
| `config.yaml` | 用户可配置参数 | — |
| `.gitignore` | Git 忽略规则（排除敏感数据） | — |

## 项目文件分类速查

### 最终产物（交付用）
```
outputs/dna_profiles/user_dna_profile.md
outputs/dna_profiles/user_dna_evidence.md
outputs/dna_profiles/user_dna_profile.json
outputs/dna_profiles/user_dna_feature_cloud.png
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
outputs/debug/sample_sufficiency_test.md         ← 样本测试报告
outputs/debug/sample_sufficiency_test.json        ← 样本测试数据
```

### 参考留存（历史版本/外部样本）
```
outputs/dna_profiles/某人-single-dna.json       ← 早期单篇提取版
outputs/dna_profiles/某人-single-dna_hotwords.png  ← 早期词频图
outputs/dna_profiles/user_auto_dna.json      ← 自动统计版
outputs/dna_profiles/user_auto_dna_hotwords.png ← 自动统计词频图
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
| 8 | ✅ 最佳 | 不确定项收敛，大部分特征确认 |
| 12 | ✅ 上限 | 特征基本饱和，再增量边际收益极低 |

---

## ⏭ 明天任务：跨模型 Benchmark

> **打开此文件后直接从这里开始。**

### 目标

用同一份 DNA 和同一份 AI 草稿，让不同大模型分别执行改写，横向对比各模型对"写作 DNA 改写"任务的执行质量。

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

- **DNA**：`outputs/dna_profiles/user_dna_profile.md` 中的改写规则
- **改写对象**：`outputs/rewrite_runs/new_ai_draft_effective_input.md`（纯净正文输入稿）
- **提示词**：基于 `SKILL.md` 流程 B 的改写规则，统一 prompt

### 评测维度

| 维度 | 测量方式 |
|:---|:---|
| DNA 规则遵循度 | 人工逐条核验改写规则是否被落实 |
| AI 味残留 | `scripts/detect_ai_slop.py` 打分 |
| 信息完整性 | 原文关键事实保留率 |
| 风格相似度 | 与用户原笔的句长/连接词分布对比 |
| 可读性 | 人工盲评 |

### 预期产出

| 文件 | 说明 |
|:---|:---|
| `outputs/model_benchmarks/{model_name}_rewritten.md` | 各模型改写稿 |
| `outputs/model_benchmarks/benchmark_report.md` | 横向对比报告 |
| `outputs/model_benchmarks/benchmark_scores.json` | 结构化评分数据 |

### 完成后需更新

1. `PROJECT_STATUS.md` — benchmark 结果填入
2. `README.md` — 模型矩阵部分从占位改为实测数据
3. `SKILL.md` — 如发现某模型表现突出，可在推荐中标注

---

## 其他未完事项（优先级低于Benchmark）

- `outputs/template_profiles/` 与 `outputs/reports/` 正式路径未产出（debug 下已有中间结果）
- 未做多作者交叉验证
