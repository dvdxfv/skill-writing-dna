# Outputs Directory

## Purpose

This directory stores generated analysis artifacts and rewrite artifacts.

## Subdirectories

- `template_profiles/`
  - 模板剥离报告（`strip_report.md`），由 `scripts/strip_template.py` 跨文档对齐后生成
- `dna_profiles/`
  - DNA 画像产物：写作风格指纹（`user_dna_profile.md/.json`）、特征云图（`user_dna_feature_cloud.png`）
- `rewrite_runs/`
  - 改写交付物：改写后成稿（`rewritten_draft.md`）、对比报告（`report.md`）、调试指标（`rewrite_debug.json`）、可选 DOCX 版（`rewritten_draft.docx`）
- `reports/`
  - 分析报告：模型评审记录、交叉评测详细报告
- `debug/`
  - 调试/临时产物：样本充足性测试输出、链路调试记录等
