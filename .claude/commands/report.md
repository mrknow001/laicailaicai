---
description: 编写或更新渗透测试报告和漏洞记录
argument-hint: "<报告范围或漏洞编号>"
---

# /report

用途：编写或更新渗透测试报告、漏洞报告、测试记录、接口信息和未测试危险接口清单。

执行规则：

1. 先读取 `CLAUDE.md` 和 `.claude/skills/report-writer/SKILL.md`。
2. 优先读取当前项目：
   - `project.md`
   - `interfaces.md`
   - `tests.md`
   - `findings.md`
   - `dangerous-untested.md`
3. 报告只描述已最小化验证的影响，不推测未验证影响。
4. 敏感数据必须脱敏。
5. 危险接口即使未测试，也应说明发现但未测试的原因。

输出：

- 可提交漏洞报告
- 测试边界声明
- 修复建议
- 未测试危险接口清单
- 后续建议
