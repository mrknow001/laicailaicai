---
name: wxapkg-windows-unpack
description: 解包小程序、逆向小程序、反编译小程序、还原微信小程序 wxapkg 代码工程。使用时需要用户提供小程序 appid，脚本会从解包主包与分包，并合并还原代码。
---

# Windows 小程序解包还原

本 skill 用于根据小程序 appid，从 Windows 微信缓存中提取 `.wxapkg`，完成解密、解包、主包/分包合并和代码工程还原。它只处理本地文件，不访问目标服务。

## 使用前配置

在 `scripts/.env` 中配置微信小程序缓存根目录：

```env
WECHAT_APPLET_ROOT=D:\SoftWareInstall\WeChat\WeChatData\WeChat Files\Applet
```

如果没有 `.env`，先复制 `scripts/.env.example` 后按本机路径修改。`.env` 只配置微信小程序缓存目录，输出目录在执行脚本时通过 `--out` 指定。

## 脚本用法

必须提供小程序 appid，例如 `wx1234567890abcdef`。

```bash
python .claude/skills/wxapkg-windows-unpack/scripts/wxapkg_unpack.py <小程序appid> --out <输出目录>
```

示例：

```bash
python .claude/skills/wxapkg-windows-unpack/scripts/wxapkg_unpack.py wx1234567890abcdef --out projects/demo/artifacts/wxapkg/wx1234567890abcdef
```

脚本会自动查找 appid 对应缓存目录，选择最新版本，收集其中所有 `.wxapkg`，解密、解包并合并主包和分包。

## 正常输出与解包失败说明

正常情况下，脚本会把还原后的代码工程直接写入 `--out` 指定目录。目录根部就是还原工程：

```text
<输出目录>/
  app.json
  app.js
  app.wxss
  pages/
  project.config.json
  restore-diagnostics.json
  restore-report.json
```

`restore-report.json` 是执行摘要。`restore-diagnostics.json` 是还原诊断结果，重点看 `validation.issues`、`runtime_residue`、`sanitized_json_files`，用于判断是否还有无法自动处理的编译产物残留。

解包失败时，先按错误类型判断：

- 找不到 appid 目录：检查 appid 是否正确，以及 `.env` 中的 `WECHAT_APPLET_ROOT` 是否指向微信小程序缓存根目录。
- 找不到 `.wxapkg`：确认该小程序已在 Windows 微信中打开过，并且缓存目录未被清理。
- 解密失败：可能不是 PC 微信加密包、包不完整，或缓存文件损坏。
- 解包成功但工程无法运行：还原工程来自编译产物，不保证等同原始源码；优先查看 `restore-diagnostics.json` 中的诊断项。
