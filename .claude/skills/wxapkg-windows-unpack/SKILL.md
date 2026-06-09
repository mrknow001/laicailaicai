---
name: wxapkg-windows-unpack
description: 从 Windows 微信小程序缓存目录中按 appid 自动定位 wxapkg，解密 PC 加密包，解包主包与分包，并生成 packages 原始解包目录和 merged 微信开发者工具工程还原目录。
---

# Windows 小程序解密解包

本 skill 用于从 Windows 微信缓存中提取指定小程序的 `.wxapkg`，完成解密、解包、主包/分包合并和工程目录还原。它只处理本地文件，不访问目标服务。

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

```text
<输出目录>/
  decrypted/
  packages/
  merged/
  _conflicts/
  manifest.json
  unpack.log
```

`packages/` 是原始解包结果。每个 `.wxapkg` 独立输出，不做工程还原加工，用于溯源和对比。

`merged/` 是工程还原结果。脚本优先调用本机 `wuWxapkg` 对解密后的包做真实还原，生成 `app.json`、`app.js`、`.wxml`、`.wxss`、页面 `.json` 等文件；如果未检测到 Node 或 `wuWxapkg`，才退回基础结构还原。

`merged/restore-diagnostics.json` 是工程还原诊断结果。重点查看 `validation.issues`、`runtime_residue`、`sanitized_json_files`，用于判断通用修复是否完成，以及是否仍存在还原器无法自动处理的编译产物残留。

## 工作方式

1. 从 `.env` 读取 `WECHAT_APPLET_ROOT`。
2. 在缓存根目录下查找指定 appid 目录。
3. 如果缓存中存在多个版本目录，默认选择版本号最大的目录。
4. 收集该版本目录内所有 `.wxapkg`。
5. 对加密包执行 PC 微信小程序包解密；已解密包直接进入解包流程。
6. 解包所有主包和分包到 `packages/`，阻止路径穿越。
7. 识别主包和分包 root，生成基础合并目录。
8. 优先用 `wuWxapkg` 对解密包做真实工程还原，并覆盖生成最终 `merged/`。
9. 对 `merged/` 做通用工程修复：清理无效 JSON 字段、修正页面路径、补齐页面文件、修复简单 WXML 属性语法、识别并隔离常见运行态残留。
10. 输出 `manifest.json`、`restore-diagnostics.json` 和极简执行摘要。

## 注意事项

- 只处理本地微信缓存文件。
- 必须由用户提供 appid。
- 输出目录由执行时的 `--out` 指定，不写入 `.env`。
- 如果同名文件内容不同，保留主包优先结果，并把冲突文件写入 `_conflicts/`。
- `merged/` 是基于编译产物生成的工程目录，不保证等同于开发者上传前的原始源码。
- 默认自动探测 `D:\Tools\MiniSpy-last\WorkDir\wuWxapkg-2` 和 `D:\Tools\MiniSpy-last\WorkDir\wuWxapkg-1`。
- 如需指定其他还原器目录，可设置环境变量 `WUWXAPKG_DIR`。
- 如果 `wuWxapkg` 不可用，脚本会生成基础占位工程，保证项目结构完整，但不保证可编译运行。
