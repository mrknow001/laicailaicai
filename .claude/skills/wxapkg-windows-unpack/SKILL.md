---
name: wxapkg-windows-unpack
description: 从 Windows 微信小程序缓存目录中按 appid 自动定位 wxapkg，解密 PC 加密包，解包主包与分包，并还原小程序代码工程。
---

# Windows 小程序解密解包

本 skill 用于从 Windows 微信缓存中提取指定小程序的 `.wxapkg`，完成解密、解包、主包/分包合并和小程序代码工程还原。它只处理本地文件，不访问目标服务。

## 使用前配置

在 `scripts/.env` 中配置微信小程序缓存根目录：

```env
WECHAT_APPLET_ROOT=D:\SoftWareInstall\WeChat\WeChatData\WeChat Files\Applet
```

如果没有 `.env`，先复制 `scripts/.env.example` 后按本机路径修改。

## 脚本用法

```bash
python .claude/skills/wxapkg-windows-unpack/scripts/wxapkg_unpack.py <appid> --out <输出目录>
```

示例：

```bash
python .claude/skills/wxapkg-windows-unpack/scripts/wxapkg_unpack.py wx1234567890abcdef --out projects/demo/artifacts/wxapkg/wx1234567890abcdef
```

## 输出结构

脚本会把还原后的代码工程写入 `--out` 指定目录，目录根部就是微信开发者工具可打开的工程：

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

脚本优先调用 skill 内置还原器对解密后的包做工程还原，生成 `app.json`、`app.js`、`.wxml`、`.wxss`、页面 `.json` 等文件；如果内置还原器不完整，才退回基础结构还原。

`restore-diagnostics.json` 是工程还原诊断结果。重点查看 `validation.issues`、`runtime_residue`、`sanitized_json_files`，用于判断通用修复是否完成，以及是否仍存在还原器无法自动处理的编译产物残留。

## 工作方式

1. 从 `.env` 读取 `WECHAT_APPLET_ROOT`。
2. 在缓存根目录下查找指定 appid 目录。
3. 如果缓存中存在多个版本目录，默认选择版本号最大的目录。
4. 收集该版本目录内所有 `.wxapkg`。
5. 对加密包执行 PC 微信小程序包解密；已解密包直接进入解包流程。
6. 解包所有主包和分包，阻止路径穿越。
7. 识别主包和分包 root，生成基础合并结果。
8. 优先用 skill 内置还原器对解密包做工程还原。
9. 对还原工程做通用修复：清理无效 JSON 字段、修正页面路径、补齐页面文件、修复简单 WXML 属性语法、识别并隔离常见运行态残留。
10. 输出还原后的代码工程和极简执行摘要。

## 注意事项

- 只处理本地微信缓存文件。
- 必须由用户提供 appid。
- 输出目录由执行时的 `--out` 指定，不写入 `.env`。
- 如果同名文件内容不同，优先保留主包结果。
- 还原工程基于编译产物生成，不保证等同于开发者上传前的原始源码。
- 内置 Node 运行时位于 `scripts/NodeJS/node.exe`。
- 内置还原器位于 `scripts/wuwxapkg/`。
- 不自动探测外部绝对路径；迁移时随 skill 目录一起迁移。
- 如果内置还原器不完整，脚本会生成基础占位工程，保证项目结构完整，但不保证可编译运行。
