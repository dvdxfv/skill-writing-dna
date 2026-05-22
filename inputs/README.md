# Inputs Directory

## Purpose

This directory stores source inputs and normalized intermediate markdown files.

## Subdirectories

- `raw_docx_articles/`
  - raw user-provided DOCX files
- `normalized_markdown/`
  - markdown converted from DOCX or copied from plain-text sources
- `filtered_markdown/`
  - markdown after removing tables, images, captions, and other non-prose content
- `template_stripped_markdown/`
  - markdown after template stripping via cross-document alignment（pipeline 第 3 步产物，`scripts/strip_template.py` 输出）
