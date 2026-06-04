---
description: 使用指定特长进入单一挖掘方向
argument-hint: "<特长名称和目标范围>"
---

# /specialty-use

用途：使用 `.claude/skills/specialty-skills/<特长名>/SKILL.md` 中定义的特长，围绕某一种渗透测试思路或挖掘手法工作。

执行规则：

1. 用户必须指定特长名称。
2. 只读取 `.claude/skills/specialty-skills/<特长名>/SKILL.md`。
3. 特长必须服务于当前项目声明和渗透测试目标。
4. 启用特长后，暂时只做该特长相关方向；其他漏洞类型和泛化测试方向一律不展开。
5. 如果特长会触发目标访问、扫描、fuzz 或验证，必须先完成 scope check。
6. 如果特长与项目注意事项或补充说明冲突，必须停止并说明原因。
