# 经验索引（召回入口）

> 这是智能体的**可移植**经验库索引，随仓库迁移。**开工前先读本文件**，按当前目标类型（小程序 / Java / 某框架 / 某业务）判断哪几条相关，再展开对应 `<name>.md`，不要全量读取。
> 每条经验是 `memory/` 下一个独立文件，带 frontmatter（`name` / `description` / `type` / `last-verified` / `source`）。

## 使用约定

- **召回**：先扫本索引的 `description` 钩子，只展开与当前目标相关的条目。
- **应用**：经验是判断先验和检查点提示，不取代现场判断；与项目声明红线冲突时红线优先。
- **修正**：展开某条时若 `last-verified` 已久或与现场冲突，先存疑、复核后更新该文件正文并刷新 `last-verified`，同步本索引钩子。
- **写入**：满足「可复用 + 非显然 + 可浓缩」三条才沉淀；精炼优先，言多必失；写入前脱敏；新建后在此登记一行，更新已有条目时刷新其钩子。
- **禁止写入**：真实用户数据、Token/Cookie/密钥/私钥、未脱敏请求响应、客户源码/配置、可直接复现未公开漏洞的目标细节、可用于未授权攻击的批量利用步骤。

## experience（方法论 / 判断模式 / 手法）

- [mapp-code-error-leak-response-modes](mapp-code-error-leak-response-modes.md) — 小程序 code 异常自检后按 5 类后端响应决定深入与否，及加密 / 网关响应的判断与停止。
- [mapp-js-endpoint-discovery](mapp-js-endpoint-discovery.md) — 解包小程序后快速定位 wx.request 真实接口 / BaseURL 的套路，及何时放弃静态枚举转抓包。

## mistake（误报 / 踩坑 / 风控触发 / 无效方向）

- （暂无）

## fingerprint（技术指纹 ↔ 高价值方向关联）

- （暂无）

## waf（WAF / 风控的低影响观察与避坑）

- （暂无）
