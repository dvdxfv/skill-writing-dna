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
