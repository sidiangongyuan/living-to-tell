# Living to Tell Preview 0.1.8

This update focuses on windowed-layout comfort and AI Card quality.

## Download

- `LivingToTell_0.1.8_x64-setup.exe`
  - SHA256: `2DB5EC63E7FE936F58E1ECC4586D03D173F5A74E83E470B34B8FF027103EE102`
- `LivingToTell_0.1.8_x64_zh-CN.msi`
  - SHA256: `E9387AE7A42CD0A1AB1F9427BD794D1CAAE7250E1892EB4388DA791A60671578`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- Main work surfaces now support user-adjustable pane widths, with sizes remembered locally.
- Articles, AI Workspace, AI Cards, Reference Library, Collections, and Motif Star Map layouts behave better in windowed mode.
- Delete actions that already existed in the UI now also support right-click context menus.
- AI Card tags are now persisted in the database and returned by the API.
- AI Card search includes saved tags.
- The public "restore samples" control has been removed from AI Cards.
- Built-in AI Card samples are no longer automatically recreated after users delete them.

## Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

---

# 活着为了讲述 0.1.8 预览版

本次更新重点是窗口化布局舒适度和 AI 卡片质量。

## 下载

- `LivingToTell_0.1.8_x64-setup.exe`
  - SHA256: `2DB5EC63E7FE936F58E1ECC4586D03D173F5A74E83E470B34B8FF027103EE102`
- `LivingToTell_0.1.8_x64_zh-CN.msi`
  - SHA256: `E9387AE7A42CD0A1AB1F9427BD794D1CAAE7250E1892EB4388DA791A60671578`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增与修复

- 主要工作区支持用户自行拖动调整面板宽度，并会在本机记住尺寸。
- 文章、AI 工作区、AI 卡片、文脉库、作品集和意象星图在窗口化模式下更不容易互相遮挡。
- 已经存在删除按钮的位置，现在也支持右键菜单删除。
- AI 卡片标签现在会真实保存到数据库，并通过 API 返回。
- AI 卡片搜索会匹配已保存标签。
- AI 卡片中的“恢复样例”入口已移除。
- 用户删除内置 AI 卡片样例后，系统不会再自动重新创建这些样例。

## 验证

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

