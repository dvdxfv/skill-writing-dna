# AI 安装代理说明

当用户在 Codex、Claude Code、Cursor、Trae / Trae Solo 或其他 AI 编程工具里说：

> 帮我安装这个 writing-dna skill：https://github.com/dvdxfv/skill-writing-dna.git。安装后我要能用 `/writing-dna` 调用。

你应该直接完成安装，不要把下面的命令原样丢给用户。

## 安装目标

安装完成后，用户应能在当前 AI 工具里通过 `/writing-dna` 或工具内 skill 入口调用 Writing DNA。

## 执行步骤

1. 克隆或下载仓库。
2. 进入仓库根目录。
3. 如当前环境支持 Python，安装依赖：

```bash
pip install -r requirements.txt
```

4. 自动注册各工具入口：

```bash
python scripts/install_ai_tool_commands.py
```

如果当前工具所在项目不是本仓库，并且需要把 Cursor / 项目级命令安装到用户正在工作的项目，传入目标项目路径：

```bash
python scripts/install_ai_tool_commands.py --project "目标项目路径"
```

5. 告诉用户重启对应 AI 工具，或重新打开项目窗口。

## 注册位置

| 工具 | 注册位置 | 调用方式 |
|:---|:---|:---|
| Codex | `~/.codex/prompts/writing-dna.md` | `/writing-dna` |
| Claude Code | `~/.claude/commands/writing-dna.md` | `/writing-dna` |
| Cursor | 目标项目 `.cursor/commands/writing-dna.md` | `/writing-dna` |
| Trae / Trae Solo | `~/.trae/skills/writing-dna/SKILL.md` + 目标项目 `.trae/skills/writing-dna/SKILL.md` | `/writing-dna` 或工具内 skill 入口 |

## 回答用户时

不要让用户记脚本命令。直接告诉用户：

- 已安装到哪些工具入口。
- 哪些工具需要重启或重新打开项目。
- 下一步可以输入 `/writing-dna` 试用。

如果某个工具的注册目录不可写，明确说明失败项和原因，再给出最短的人工补救方式。
