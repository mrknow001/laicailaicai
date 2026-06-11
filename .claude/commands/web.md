---
description: 将 Web 页面、前端源码或 JS 作为前端资产入口，提取后端接口、参数、认证逻辑和业务线索。
argument-hint: "<URL、前端源码目录、JS文件或Web分析说明>"
---

# /web

这是一个 Web 前端资产入口。Web 页面不是最终渗透对象，只是后端接口、参数、认证逻辑和业务流程的线索来源。

请按以下方式处理：

1. 读取 `CLAUDE.md` 和 `.claude/skills/interface-source/SKILL.md`。
2. 如果用户提供 URL，在项目声明范围内通过浏览器或只读请求快速了解页面用途、主要功能、登录入口、JS 资源和明显业务模块。
3. 如果用户提供前端源码目录、JS 文件或分析材料，直接以用户提供内容作为线索来源。
4. 使用 `info-find` 提取 URL、BaseURL、接口路径、参数、认证关键字和敏感配置摘要。
5. 按当前 L 档审计 JS 和页面逻辑：L1 只围绕 `info-find` 命中上下文快速审计；L2 / L3 必须全量审计 Web JS 或前端源码。
6. 将有效线索写入当前项目的 `leads.md`、`interfaces.md`，必要时补充 `hypotheses.md`。
7. 只把 scope check 通过的后端接口交给当前 L 档或特长继续渗透测试。

输出重点：

- 页面 / JS 来源位置
- API / BaseURL
- 参数和疑似功能
- 认证与业务逻辑线索
- 敏感配置脱敏摘要
- scope check 状态
- 后续漏洞假设
