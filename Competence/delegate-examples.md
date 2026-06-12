# Delegate 使用示例

本文档展示如何在实际渗透测试中使用 delegate agent。

## 场景1：分析大型 JS 文件

### 触发条件
```bash
# 发现 tmp-recruit-portal.js 有 2.7MB
ls -lh projects/xxx/tmp-recruit-portal.js
-rw-r--r-- 1 user user 2.7M Jun 12 10:00 tmp-recruit-portal.js
```

### 主 Loop 判断逻辑
```javascript
// 文件超过 500KB，创建 file-analyzer agent
const file_size = 2.7 * 1024 * 1024; // bytes
if (file_size > 500 * 1024) {
    // Delegate 给 Explore agent
    const analysis = agent(
        "深度分析 projects/xxx/tmp-recruit-portal.js，提取：\n" +
        "1. 所有 API 端点（方法 + 路径 + 参数）\n" +
        "2. 认证逻辑摘要（JWT/Session/OAuth）\n" +
        "3. 敏感配置（API Key、硬编码密钥）\n" +
        "4. 业务模块（支付/订单/用户/管理）\n" +
        "按 file-analyzer agent 的格式返回结构化结果。",
        {
            subagent_type: "Explore",
            description: "分析2.7MB JS文件"
        }
    );
    
    // analysis 只包含结构化结论，不包含完整代码
    // 主 loop 上下文保持清爽
}
```

### Delegate Agent 返回示例
```markdown
# 文件分析结果

## 元信息
- 分析文件：tmp-recruit-portal.js
- 文件大小：2.7MB
- 分析时间：2024-06-12

## API 端点（共 47 个）

### 高价值接口（5个）
| 方法 | 路径 | 功能 | 风险 | 理由 |
|------|------|------|------|------|
| POST | /api/admin/user/delete | 删除用户 | 危险 | 破坏性操作 |
| GET | /api/salary/export | 导出工资表 | 敏感 | 涉及敏感数据 |
| POST | /api/resume/upload | 上传简历 | 文件上传 | 可能文件上传漏洞 |

### 普通接口（42个）
（已记录到 interfaces.md）

## 认证逻辑
- 方式：JWT
- 存储：localStorage.getItem('hr_token')
- 刷新：/api/auth/refresh
- 客户端权限：检测到 role === 'admin' 的前端判断（不可信）

## 敏感配置
- API_BASE_URL: https://hr-api.jccfc.com
- RSA_PUBLIC_KEY: "MIIBIjANBgk..." （硬编码）
- THIRD_PARTY_OSS_KEY: "LTAI***" （阿里云 OSS，可能泄露）

## 推荐下一步
1. 优先测试 /api/salary/export 未授权访问（敏感数据）
2. 确认 /api/admin/user/delete 是否允许测试
3. 验证 RSA_PUBLIC_KEY 是否在多个系统复用
```

### 主 Loop 后续动作
```javascript
// 收到分析结果后
// 1. 更新 interfaces.md
// 2. 自动生成高优先级假设
// 3. 询问人类

询问用户："发现 5 个高价值接口，建议先测 /api/salary/export（敏感数据导出）。是否继续？"
```

---

## 场景2：批量接口存活检测

### 触发条件
```markdown
# interfaces.md 中有 50 个待测试接口
从 JS 提取到 50 个接口，需要批量检测存活性。
```

### 主 Loop 判断逻辑
```javascript
const interfaces_count = 50;
if (interfaces_count > 20) {
    // 后台执行，不阻塞主 loop
    agent(
        "批量测试 projects/xxx/interfaces.md 中标记为「待测试」的 50 个接口存活性。\n" +
        "按 batch-tester agent 的格式返回摘要结果。",
        {
            subagent_type: "general-purpose",
            run_in_background: true,  // 后台运行
            description: "批量接口存活检测"
        }
    );
    
    // 主 loop 立即返回
    console.log("后台任务已启动，你可以继续下其他指令。");
    // 完成后会收到 <task-notification>
}
```

### 人类此时可以插话
```
人类："先别管那 50 个接口了，帮我看看这个登录接口有没有 SQL 注入"
主 Loop："好的，立即分析登录接口..."
（后台的 batch-tester 继续跑，互不干扰）
```

### Delegate Agent 完成后通知
```markdown
<task-notification>
批量接口存活检测已完成。

# 接口存活检测结果

## 统计
- 总数：50
- 通过 scope check：48
- 跳过（禁止范围）：2
- 存活：35
- 需要认证：10
- 异常：3

## 存活接口（35个）
| 接口 | 状态码 | 是否需要认证 | 推荐优先级 |
|------|--------|------------|----------|
| GET /api/user/info | 401 | 是 | 高（可能IDOR） |
| GET /api/salary/list | 200 | 否 | 高（敏感数据） |
...

## 推荐下一步
1. 优先测试 /api/salary/list（未授权访问敏感数据）
2. 获取 token 后复测 10 个需认证接口
</task-notification>
```

---

## 场景3：多目标并行测试

### 触发条件
```bash
人类："帮我同时测试这 3 个目标"
- target-1.jccfc.com
- target-2.jccfc.com
- target-3.jccfc.com
```

### 主 Loop 策略
```javascript
const targets = ["target-1.jccfc.com", "target-2.jccfc.com", "target-3.jccfc.com"];

// 为每个目标创建独立的 worker（后台运行）
targets.forEach((target, index) => {
    agent(
        `测试目标 ${target}，按 L2 策略：\n` +
        `1. 提取接口\n` +
        `2. 建立假设\n` +
        `3. 最小验证\n` +
        `结果写入 projects/xxx/worker-${index}-result.md`,
        {
            run_in_background: true,
            description: `Worker ${index}: ${target}`
        }
    );
});

console.log("3 个 worker 已启动，你可以随时查看进度或下新指令。");
```

### 人类随时查看进度
```
人类："进度如何？"
主 Loop：
  - Worker 0 (target-1): 已完成，发现 2 个漏洞
  - Worker 1 (target-2): 进行中（正在测试接口）
  - Worker 2 (target-3): 排队中
```

---

## 场景4：深度目录审计

### 触发条件
```bash
# 用户提供了一个包含 120 个文件的源码目录
ls -l projects/xxx/source-code/ | wc -l
120
```

### 主 Loop 判断逻辑
```javascript
const files_count = 120;
if (files_count > 50) {
    const analysis = agent(
        "深度审计 projects/xxx/source-code/ 目录（120 个文件），重点关注：\n" +
        "1. 认证 / 权限相关代码\n" +
        "2. SQL 拼接（可能注入）\n" +
        "3. 文件操作（可能路径遍历）\n" +
        "4. 命令执行（可能 RCE）\n" +
        "按 file-analyzer 格式返回高价值发现。",
        {
            subagent_type: "Explore",
            description: "审计120个源码文件"
        }
    );
}
```

---

## 实际使用流程

### 步骤1：主 Loop 自动判断
```javascript
// 在 deep-l2 执行中
if (需要深度分析 && 文件 > 500KB) {
    创建 file-analyzer agent
} else if (需要批量测试 && 接口 > 20) {
    创建 batch-tester agent（后台）
} else {
    自己处理
}
```

### 步骤2：Delegate 执行
- Delegate agent 读取项目声明
- 执行具体任务
- 只返回结构化结论

### 步骤3：主 Loop 处理结果
- 合并结果到 interfaces.md / leads.md
- 更新 hypotheses.md
- 询问人类下一步

---

## Delegate 的价值

| 不使用 Delegate | 使用 Delegate |
|----------------|--------------|
| 读 2.7MB JS → 主上下文爆炸 | file-analyzer 返回结构化结论 |
| 测 50 个接口 → 主 loop 阻塞 5 分钟 | batch-tester 后台跑，主 loop 立即响应 |
| 多目标串行 → 1 小时测 1 个 | 多 worker 并行 → 1 小时测 3 个 |
| 人类想插话 → 必须等当前任务完成 | 人类随时插话 → 主 loop 立即响应 |

---

## 注意事项

1. **不是所有任务都需要 Delegate**：简单任务（< 10 个接口、< 100KB 文件）直接处理更快。
2. **Delegate 有成本**：创建 agent 有启动开销，只在收益明显时使用。
3. **状态同步**：Delegate 通过文件通信，避免多个 agent 同时写同一文件。
4. **人类随时能打断**：后台任务可用 TaskStop 工具停止。
