---
description: 将 App 安装包、反编译目录或 App 分析材料作为前端资产入口，提取后端接口、参数、认证逻辑和业务线索。
argument-hint: "<APK路径、反编译目录或App分析说明>"
---

# /app

这是一个 App 前端资产入口。App 不是最终渗透对象，只是后端接口、参数、认证逻辑和业务流程的线索来源。

请按以下方式处理：

1. 读取 `CLAUDE.md` 和 `.claude/skills/interface-source/SKILL.md`。
2. 仅分析用户提供的 APK、反编译目录或 App 分析材料。
3. 使用 `info-find` 提取 URL、BaseURL、接口路径、参数、认证关键字和敏感配置摘要。
4. 按当前 L 档审计客户端代码和配置：L1 只围绕 `info-find` 命中上下文快速审计；L2 / L3 必须全量审计 App 源码或反编译代码。
5. 将有效线索写入当前项目的 `leads.md`、`interfaces.md`，必要时补充 `hypotheses.md`。
6. 只把 scope check 通过的后端接口交给当前 L 档或特长继续渗透测试。

输出重点：

- App 来源信息
- API / BaseURL / 参数
- 认证与业务逻辑线索
- 敏感配置脱敏摘要
- scope check 状态
- 后续漏洞假设
