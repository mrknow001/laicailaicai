---
description: 将微信小程序 id、小程序包或源码作为前端资产入口，解包或读取后提取后端接口、页面路由、参数和业务线索。
argument-hint: "<小程序appid、小程序包、源码路径或分析说明>"
---

# /mapp

这是一个小程序前端资产入口。小程序不是最终渗透对象，只是后端接口、参数、页面流程、认证逻辑和业务线索来源。

请按以下方式处理：

1. 读取 `CLAUDE.md` 和 `.claude/skills/interface-source/SKILL.md`。
2. 如果参数是小程序 appid，使用 `.claude/skills/wxapkg-windows-unpack/SKILL.md` 解包还原代码。
3. 如果参数是小程序包、源码目录或分析材料，直接以用户提供内容作为线索来源。
4. 使用 `info-find` 提取 URL、BaseURL、接口路径、参数、认证关键字和敏感配置摘要。
5. 按当前 L 档审计 JS、页面路由和业务流程：L1 只围绕 `info-find` 命中上下文快速审计；L2 / L3 按价值分配审计深度——脚本定位后深读认证 / 权限 / 支付等高价值模块，不为「全量」逐行读完无关代码。
6. 将有效线索写入当前项目的 `leads.md`、`interfaces.md`，必要时补充 `hypotheses.md`。
7. 只把 scope check 通过的后端接口交给当前 L 档或特长继续渗透测试。

输出重点：

- 页面路由
- API / BaseURL
- 参数和疑似功能
- 认证与业务逻辑线索
- 敏感配置脱敏摘要
- scope check 状态
- 后续漏洞假设
