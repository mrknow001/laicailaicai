---
description: 从小程序包或源码中提取后端接口线索
argument-hint: "<小程序包、源码路径或分析说明>"
---

# /mapp

用途：从用户提供的小程序包或源码中提取后端接口、页面路由和业务线索。

执行规则：

1. 先读取 `CLAUDE.md` 和 `.claude/skills/interface-source/SKILL.md`。
2. 小程序不是最终测试对象，只是后端接口和业务线索来源。
3. 只分析用户提供的小程序包 / 源码。
4. 提取到的 API BaseURL、域名、IP 必须做 scope check。
5. 输出写入当前项目的 `leads.md` 和 `interfaces.md`。

输出字段：

- 页面路由
- API / BaseURL
- 参数和疑似功能
- 业务模块
- 敏感配置摘要
- scope check 状态
- 后续漏洞假设
