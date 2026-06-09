---
description: 从 APK 中提取后端接口和业务线索
argument-hint: "<APK路径或App分析说明>"
---

# /app

用途：从用户提供的安装包中提取后端接口、参数、配置和客户端逻辑线索。

执行规则：

1. 先读取 `CLAUDE.md` 和 `.claude/skills/interface-source/SKILL.md`。
2. App 不是最终测试对象，只是后端接口和业务线索来源。
3. 只分析用户提供的安装包。
4. 不保存真实密钥、Token、证书私钥等敏感原文，只记录脱敏摘要和来源位置。
5. 提取到的后端域名、IP、BaseURL 必须做 scope check。

输出字段：

- 包名 / 版本 / 来源
- API / BaseURL
- 参数和疑似功能
- 认证与客户端逻辑线索
- 敏感配置摘要
- scope check 状态
- 后续漏洞假设
