---
description: 列出当前项目可用特长
argument-hint: ""
---

# /specialty-list

用途：列出 `.claude/skills/specialty-skills/` 下可用的特长。

执行规则：

1. 只检查 `.claude/skills/specialty-skills/`。
2. 只有该目录下包含 `SKILL.md` 的子目录才算特长。
3. 不要把 `.claude/skills/` 下的普通 skill 当成特长。
4. 不执行任何测试动作。
