---
description: 编写或更新渗透测试报告、漏洞详情和项目记录
argument-hint: "<报告范围或漏洞编号>"
---

# /report

用途：编写或更新渗透测试报告、漏洞详情、测试记录、接口信息和未测试危险接口清单。

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

- 项目摘要：项目名称、资产范围、漏洞收录要求。
- 漏洞列表。
- 漏洞详情：漏洞名称、漏洞等级、漏洞描述、漏洞危害、漏洞数据包、漏洞复现步骤、修复建议。
- 必要时同步更新 `tests.md`、`findings.md`、`dangerous-untested.md`。
