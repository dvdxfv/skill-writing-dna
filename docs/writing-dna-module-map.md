# Writing DNA 模块清单

## 1. 文档目的

这份文档用于把架构进一步落到“模块职责”。

约束规则：

- 后续新增代码，优先归入现有模块
- 如果现有模块无法承接，再先讨论是否新增模块
- 不允许在开发过程中把多个职责随意混到一个脚本里

## 2. 目录约定

### 输入目录

- `inputs/raw_docx_articles/`
  - 用户原始 DOCX 文章

### 中间产物目录

- `inputs/normalized_markdown/`
  - DOCX 转换后的 Markdown
- `inputs/filtered_markdown/`
  - 过滤掉表格、图片、图注等非正文后的 Markdown

### 分析产物目录

- `outputs/template_profiles/`
  - 模板识别产物
- `outputs/dna_profiles/`
  - 用户 DNA 产物
- `outputs/rewrite_runs/`
  - 草稿改写产物
- `outputs/reports/`
  - 人可读对比报告
- `outputs/debug/`
  - 调试和中间指标

## 3. 模块职责

### 3.1 `scripts/docx_to_md.py`

职责：

- 把 `.docx` 转成可读 Markdown
- 只负责标准化，不负责 DNA 提取

输入：

- `inputs/raw_docx_articles/*.docx`

输出：

- `inputs/normalized_markdown/*.md`

### 3.2 `scripts/filter_non_prose.py`

职责：

- 过滤表格、图片、图题、图注、附件说明、页眉页脚、目录等非正文内容
- 产出“可用于 DNA 提取”的正文 Markdown

输入：

- `inputs/normalized_markdown/*.md`

输出：

- `inputs/filtered_markdown/*.md`

### 3.3 `scripts/strip_template.py`

职责（PRD §8.1.3 · Layer 1）：

- 跨文档对齐检测，识别该文体的"模板内容"并剥离
- 三个并行通道：跨 ≥60% 文档重复的章节标题、字面整句、≥8 字长短语
- 不依赖任何文体先验——适用于任何文体（论文/邮件/公众号/政府报告/合同/新闻稿/小说/产品文档/...）
- Layer 2（语义模板识别）+ Layer 3（用户确认）由 SKILL.md 引导 LLM 在对话中完成，不在脚本里

输入：

- `inputs/filtered_markdown/*.md`

输出：

- `inputs/template_stripped_markdown/*.md`（剥离后的正文，作为 DNA 提取的真正输入）
- `outputs/template_profiles/strip_report.md`（剥离报告：列出每个被识别为模板的标题/整句/长短语）

### 3.3A `scripts/test_sample_sufficiency.py`

职责（样本质量预检 · DNA 提取前的闸门）：

- 多维样本健康度检查，文体无关（不含任何公文/特定文体先验）：篇数、字数分布、文档间相似度、近重复整篇、文档内重复、留一法稳定性 + 饱和度
- 输出分级 `severity`（ok / light / serious），供 `run.py` 在第一确认点做软阻断判断
- 从"事后诊断工具"前移为"提取前闸门"：`run.py pipeline` 在模板剥离后自动跑，结论并入第一确认点（见 SKILL.md Step 1.5d）
- 只产诊断材料，不喂给 `extract_dna.py`，故不影响 DNA 产物本身

输入：

- `inputs/template_stripped_markdown/*.md`

输出：

- `outputs/debug/sample_sufficiency_test.json`（结构化多维数据）
- `outputs/debug/sample_sufficiency_test.md`（人可读报告）

### 3.4 `scripts/extract_dna.py`

职责：

- 只从模板已剥离后的正文里提取个人写作 DNA

输入：

- `inputs/template_stripped_markdown/*.md`（必须是 strip_template.py 处理过的产物）

输出：

- `outputs/dna_profiles/<user>-dna.json`
- `outputs/dna_profiles/<user>-dna_hotwords.png`
- `outputs/dna_profiles/<user>-dna_feature_cloud.png`

### 3.4A `scripts/render_dna_feature_cloud.py`

职责：
- 从正式 DNA JSON 中提取“用户写作资产标签”
- 生成面向用户展示的 DNA 特征云图片

输入：
- `outputs/dna_profiles/<user>-dna.json` 或同结构正式 DNA JSON

输出：
- `outputs/dna_profiles/<user>-dna_feature_cloud.png`

### 3.4B `scripts/dna_versioning.py`

职责（DNA 版本管理 + 回滚）：

- 用户修正 DNA 后保留历史版本，不直接覆盖
- `save_new_version` 写 `<user>-dna-vN.json` 快照并更新当前版指针 `<user>-dna.json`
- `rollback` 把任一版写回指针；`diff_versions` 对比两版；`list_versions` 列版本
- 护栏：版本快照用 `-vN` 后缀，绝不与指针 `<user>-dna.json` 同名，避免污染 `run.py` 的 `*-dna.json` 发现 glob

输入 / 输出：

- `outputs/dna_profiles/<user>-dna.json`（当前版指针）+ `<user>-dna-vN.json`（版本快照）

### 3.5 `scripts/detect_ai_slop.py`

职责：

- 对新草稿做 AI 套话体检

输入：

- 一篇新草稿

输出：

- `outputs/debug/ai_score.json`

### 3.6 `scripts/rewrite_with_dna.py`

职责：

- 根据 DNA 和模板约束改写新草稿
- 只承担确定性辅助改写，不负责重排长文结构
- 长文“按章节改、合并后统一术语/数字/标题层级”的行为由 `SKILL.md` / live prompt 入口驱动

输入：

- 新草稿
- DNA 文件
- 可选模板画像

输出：

- `outputs/rewrite_runs/rewritten.md`
- `outputs/rewrite_runs/rewrite_debug.json`

### 3.7 `scripts/generate_report.py`

职责：

- 把原稿、改写稿、DNA、AI 检测结果组织成人可读报告

输入：

- 原稿
- 改写稿
- DNA
- 调试数据

输出：

- `outputs/reports/report.md`

## 4. 开发顺序

当前建议顺序：

1. `docx_to_md.py`
2. `filter_non_prose.py`
3. `strip_template.py`（跨文档对齐 · 通用模板剥离 · PRD §8.1.3 Layer 1）
4. `extract_dna.py`
5. `detect_ai_slop.py`
6. `rewrite_with_dna.py`
7. `generate_report.py`

## 5. 当前结论

现在不做测试，先把模块边界锁住。

后续如果实现偏离这个模块图，必须先改文档，再改代码。
