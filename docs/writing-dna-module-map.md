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

### 3.3 `scripts/extract_template_profile.py`

职责：

- 从多篇同类业务文档里提取重复模板结构
- 区分模板表达和个人表达

输入：

- `inputs/filtered_markdown/*.md`

输出：

- `outputs/template_profiles/template_profile.json`
- `outputs/template_profiles/template_profile.md`

### 3.4 `scripts/extract_dna.py`

职责：

- 只从过滤后、且尽量剥离模板后的正文里提取个人写作 DNA

输入：

- `inputs/filtered_markdown/*.md`
- 可选：`outputs/template_profiles/template_profile.json`

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
3. `extract_template_profile.py`
4. `extract_dna.py`
5. `detect_ai_slop.py`
6. `rewrite_with_dna.py`
7. `generate_report.py`

## 5. 当前结论

现在不做测试，先把模块边界锁住。

后续如果实现偏离这个模块图，必须先改文档，再改代码。
