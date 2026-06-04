---
name: info-find
description: 给定本地文件或目录，使用 skill 内置正则规则和脚本提取 URL、BaseURL、接口路径、参数、认证关键字、敏感配置关键字等信息线索。
---

# 信息提取

本 skill 用于对本地文件或目录做静态信息提取。它根据内置正则规则提取命中内容，不限定文件必须是 JS，也不主动访问目标。

## 适用场景

- 用户提供了任意本地文件或目录，需要从中提取信息。
- 已经下载了静态资源、源码、配置、日志、抓包文本或反编译结果。
- App / 小程序 / Web / 客户端产生的本地文本材料需要统一提取线索。
- 需要把 URL、BaseURL、接口路径、参数、认证关键字、敏感配置关键字整理到当前项目记录中。

## 边界

- 只分析本地文件或目录，不自动请求 URL。
- 不保存 Token、Cookie、密钥等敏感原文，只记录脱敏摘要、关键字和来源位置。

## 内置资源

- 规则文件：`rules/rule.yml`
- 提取脚本：`scripts/info_find.py`

默认规则包含：

- `http_url`：HTTP / HTTPS 链接。
- `base_url`：基础 URL 配置。
- `api_path`：常见 API 路径。
- `token_key`：认证相关关键字。
- `sensitive_keyword`：敏感配置关键字。

## 推荐流程

1. 读取 `CLAUDE.md` 和当前项目 `project.md`。
2. 确认输入是本地文件或目录。
3. 使用 `scripts/info_find.py` 对输入路径执行静态提取。
4. 对提取出的域名、IP、BaseURL 做 scope check。
5. 将结果整理到当前项目：
   - `leads.md`：线索记录。
   - `interfaces.md`：接口信息。
   - `scope.md`：待确认资产或 scope check 记录。
6. 基于结果提出漏洞假设，但不要直接测试。

## 脚本用法

```bash
python .claude/skills/info-find/scripts/info_find.py <文件或目录>
```

常用参数：

```bash
python .claude/skills/info-find/scripts/info_find.py <文件或目录> --format markdown
python .claude/skills/info-find/scripts/info_find.py <文件或目录> --output result.json
```

默认按规则名聚合，只输出 `count` 和 `data`，不输出文件、行号、上下文、统计摘要等冗余信息。

JSON 输出示例：

```json
{
  "http_url": {
    "count": "2",
    "data": [
      "https://example.com",
      "https://api.example.com"
    ]
  }
}
```

## 输出整理

每条结果整理为：

- 来源文件
- 行号
- 规则名
- 类型
- 严重度
- 命中内容
- 是否可能是后端接口
- scope check 状态
- 后续动作

后续动作只允许是：

- 写入接口清单。
- 写入待确认资产。
- 生成漏洞假设。
- 询问用户补充项目范围。
- 放弃低价值或越界目标。
