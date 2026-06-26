# Living to Tell Preview 0.1.11

This update fixes the update-action buttons in the installed app and keeps the article page from falsely claiming the current article is missing.

## Download

- `LivingToTell_0.1.11_x64-setup.exe`
  - SHA256: `49D5FEC047A95CD4BC272A0AD36FBA295139C6E094C43F04E3307B5FE5365790`
- `LivingToTell_0.1.11_x64_zh-CN.msi`
  - SHA256: `C98A4B0BD52A6BA61DD7F0BD732208E3A8BB27BDE4E61EAFEF4CF4B24773B625`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's fixed

- The update notice buttons now open the system browser correctly from the installed desktop app.
- The article page no longer claims the current article is missing just because a side-panel request briefly returned `404`.
- Article-side note / collection actions now verify the article itself before showing a missing-article warning.
- The regression is covered with tests for both the update buttons and the disproved-`404` article scenario.

## Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

---

# 活着为了讲述 0.1.11 预览版

本次更新修复了安装版里更新按钮点了没反应的问题，也继续收紧了文章页误报“文章已不存在”的情况。

## 下载

- `LivingToTell_0.1.11_x64-setup.exe`
  - SHA256: `49D5FEC047A95CD4BC272A0AD36FBA295139C6E094C43F04E3307B5FE5365790`
- `LivingToTell_0.1.11_x64_zh-CN.msi`
  - SHA256: `C98A4B0BD52A6BA61DD7F0BD732208E3A8BB27BDE4E61EAFEF4CF4B24773B625`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 修复内容

- 更新提示里的“下载安装包”和“查看发布页”现在会正确调用系统默认浏览器。
- 文章页右侧附属请求短暂返回 `404` 时，不会再误报“这篇文章已不存在，已刷新文章列表。”。
- 文章便签 / 作品集相关操作在显示“文章不存在”之前，会先验证文章本身是否真的已经不存在。
- 增加了对应回归测试，覆盖更新按钮和“侧栏请求 404，但文章仍然存在”的场景。

## 验证

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`
