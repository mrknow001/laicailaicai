---
name: mapp-code-error-leak-response-modes
description: 小程序 code 异常自检后，按 5 类后端响应决定深入与否；遇加密响应 / 网关401 的判断与停止。
type: experience
last-verified: 2026-06-04
source: mapp-bench 5-appid 批量自检
---
小程序 `code` 异常自检（空格 / 百分号变体）后，按响应归类决定是否深入：

- **框架默认错误**（404/405/500 `{timestamp,status,error}`）：无敏感字段，放过。
- **微信风格** `{code:400,msg:"invalid code..."}`：jscode2session 已调通、微信侧拒绝，无泄露。
- **报错回显内部 URL**（`Illegal/Malformed ... index N: .../sns/jscode2session?...`）：✅ Java IllegalArgumentException 把 appid+secret+access_token 全带出 → 命中即停、脱敏记录。
- **响应是长 hex / base64**（AES/SM2 加密）：看不到明文 ≠ 安全，但 code 已被加密层盖住、明文 fuzz 失效 → 标「加密通道未暴露」，不强解。
- **网关固定错误**（401 Unauthorized，或多变体响应字节级完全相同）：网关层拦截未派发下游 → 标无发现；除非能看出签名头（X-Auth-*）才值得自写客户端复现。

**别做**：不对加密响应连续突变碰运气；不先发合法 code 探正常路径（浪费配额、不提供异常信号）；网关绕过是另一条线，不在本特长内。
