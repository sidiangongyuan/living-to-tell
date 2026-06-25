# Living to Tell Preview 0.1.9

This update adds in-app update notifications and direct release links.

## Download

- `LivingToTell_0.1.9_x64-setup.exe`
  - SHA256: `C412C5610CE44BF57976018049EBD949899F1CCF8CA664037C328CCB3F65D5BC`
- `LivingToTell_0.1.9_x64_zh-CN.msi`
  - SHA256: `EDF3B001407AF8343F09427E013ECD856D8C19B842FCF9B0C8D00EF373710910`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- The app now checks GitHub Releases in the background after startup.
- When a newer public release is available, an update banner appears with direct links to the installer and release page.
- Settings now include a dedicated About and Updates section with manual checks, release notes, and the recommended installer name.
- Background update checks stay quiet on failures; manual checks show a clear status message instead of a raw error page.
- The public release flow still uses installers, but the app opens the correct download path for you.

## Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

---

# 活着为了讲述 0.1.9 预览版

本次更新加入了应用内更新提示和发布页直达入口。

## 下载

- `LivingToTell_0.1.9_x64-setup.exe`
  - SHA256: `C412C5610CE44BF57976018049EBD949899F1CCF8CA664037C328CCB3F65D5BC`
- `LivingToTell_0.1.9_x64_zh-CN.msi`
  - SHA256: `EDF3B001407AF8343F09427E013ECD856D8C19B842FCF9B0C8D00EF373710910`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增与修复

- 应用会在启动后后台检查 GitHub Releases。
- 发现更新时会显示顶部提示条，并提供安装包和发布页直达入口。
- 设置页新增“关于与更新”区块，可手动检查更新、查看发布说明和打开推荐安装包。
- 后台更新检查失败时保持安静；用户手动检查时才显示清晰状态文案，不直接暴露原始网页错误。
- 公开发布仍通过安装包更新，但应用会自动带你打开正确的下载路径。

## 验证

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`
