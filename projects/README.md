# 项目目录

每个 SRC 或企业渗透测试项目在此目录下创建独立文件夹。

创建新项目时，必须复制 `projects/_template` 整个目录到 `projects/<项目标识>/`，再按项目声明填写内容。不要每次临时拼文件，避免记录风格和字段不统一。

标准结构：

- `project.md`：项目声明。
- `scope.md`：范围解析和 scope check 记录。
- `leads.md`：线索。
- `interfaces.md`：接口信息。
- `hypotheses.md`：漏洞假设。
- `tests.md`：测试记录。
- `findings.md`：漏洞记录。
- `dangerous-untested.md`：未测试危险接口清单。
- `report.md`：报告。
- `findings/`：单个漏洞详情。
- `evidence/`：脱敏证据。
