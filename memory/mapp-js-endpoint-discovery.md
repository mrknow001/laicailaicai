---
name: mapp-js-endpoint-discovery
description: 解包小程序后快速定位 wx.request 真实接口 / BaseURL 的套路，及何时放弃静态枚举转抓包。
type: experience
last-verified: 2026-06-03
source: 多个 uni-app/taro 小程序静态分析
---
解包小程序找后端接口 / BaseURL：

- **先读 `app.js`（未压缩）**：常有明文 `"https://api.x.com/path"`。webpack 包（uni-app/taro/mpvue）把 env 内联成对象字面量，grep `API|HOST|URI|BASE` + `":"`（如 `KIP_API:"https://..."`）。
- **拼接型 URL**：`url:a+s`，base `a` 在模块 early 定义、path 在各调用处（`"/user/xxxLogin"`）；带版本段 `"/evo-tdas/"+a+"/..."` 若 404 先查版本段；按参数切前缀见 `switch(c)` → `/applet | /webapp`。
- **service 文件**：`services/*.js` 每个导出 `{name:fn}`，base `n` 来自 `config/index.js`（`apiUrl/mpUri/...`）。
- **加密信号**：响应体是 base64/hex 且代码含 `aesDecrypt`/SM2 → 线上看不到明文、需密钥；Bearer 来自 `getStorageSync(...)`，存储名各异。
- **何时放弃静态转抓包**：login URL 来自服务端动态配置、十几个常见路径全 404、或压缩文件无 path 字面量（查 `chunk_N.*.js`）→ 记「静态无法枚举，需运行时抓包」。
