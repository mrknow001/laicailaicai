# Delegate 机制总结

## 快速参考

### 何时 Delegate？

| 场景 | 阈值 | Agent 类型 | 后台运行 |
|------|------|-----------|---------|
| 大文件深度审计 | > 500KB | Explore | 否 |
| 大目录批量提取 | > 50 个文件 | Explore | 否 |
| 批量接口测试 | > 20 个接口 | general-purpose | 是 |
| 批量参数 fuzz | > 30 个参数 | general-purpose | 是 |
| 多目标并行测试 | > 2 个目标 | general-purpose | 是 |
| 耗时探测任务 | 预计 > 2 分钟 | general-purpose | 是 |

### 如何调用？

```javascript
// 阻塞式（等结果）
const result = agent(prompt, {
    subagent_type: "Explore",
    description: "任务描述"
});

// 后台式（不等待）
agent(prompt, {
    run_in_background: true,
    description: "任务描述"
});
// 完成后收到 <task-notification>
```

### Delegate Agent 清单

| Agent | 用途 | 位置 |
|-------|------|------|
| file-analyzer | 深度分析大文件/目录 | `.claude/agents/file-analyzer.md` |
| batch-tester | 批量重复测试任务 | `.claude/agents/batch-tester.md` |
| Explore（内置） | 深度搜索和探索 | Claude Code 内置 |

---

## 设计原则

1. **主 Loop 保持轻量**：随时响应人类，不被重活阻塞
2. **Delegate 做重活**：大文件、批量任务、耗时探测
3. **只返回结论**：不污染主上下文
4. **后台异步**：重复任务后台跑，主 loop 继续工作
5. **文件通信**：通过结构化文件交换信息

---

## 相关文档

- `Competence/workflow-and-verification.md`：Delegate 机制详细说明
- `Competence/delegate-examples.md`：实战案例
- `.claude/agents/file-analyzer.md`：大文件分析 agent
- `.claude/agents/batch-tester.md`：批量测试 agent
