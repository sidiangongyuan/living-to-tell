# Living to Tell Preview 0.1.18

This update fixes the version mismatch seen after installing 0.1.17 and improves the public update flow. Living to Tell can now download the installer inside the app, verify the release hash when GitHub provides one, launch the installer, and exit.

## Download

- `LivingToTell_0.1.18_x64-setup.exe`
  - SHA256: `E60937E71DF462943B0AFC540A5A6BEDB617D0DEB929112EA7731911555E0BD6`
- `LivingToTell_0.1.18_x64_zh-CN.msi`
  - SHA256: `19159AFBDDF7355217E5CD62730A429555F6EB414AAEB6BFBEB8F955CE608362`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's fixed

- Fixed the About and Updates page showing `0.1.16` after installing 0.1.17. The app binary had been updated, but the bundled backend version constant was still stale.
- The Tauri app now passes its package version to the backend sidecar on startup, reducing the chance of future frontend/backend version drift.
- Update checks now fall back to GitHub's `/releases/latest` redirect when the GitHub Releases API fails.
- Update check diagnostics distinguish timeout, proxy, SSL/certificate, GitHub API, and generic network failures more clearly.

## What's changed

- **Download and Install** now downloads the installer inside Living to Tell, verifies SHA256 when available, starts the installer, and exits the app.
- Browser download remains available as a fallback.
- When a proxy is detected, the update screen shows a safe proxy summary such as `https=127.0.0.1:7890`; credentials are never displayed.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

---

# 活着为了讲述 0.1.18 预览版

本次更新修复 0.1.17 安装后“关于与更新”仍显示 `0.1.16` 的版本错位问题，并改进公开版更新流程。现在应用可以在内部下载安装包、在 GitHub 提供摘要时校验 SHA256、自动启动安装器并退出。

## 下载

- `LivingToTell_0.1.18_x64-setup.exe`
  - SHA256: `E60937E71DF462943B0AFC540A5A6BEDB617D0DEB929112EA7731911555E0BD6`
- `LivingToTell_0.1.18_x64_zh-CN.msi`
  - SHA256: `19159AFBDDF7355217E5CD62730A429555F6EB414AAEB6BFBEB8F955CE608362`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 修复内容

- 修复安装 0.1.17 后“关于与更新”仍显示 `0.1.16`：Tauri 外壳已经更新，但打包的后端版本常量没有同步。
- Tauri 启动后端 sidecar 时会传入当前应用包版本，降低未来前后端版本漂移的概率。
- GitHub Releases API 失败时，更新检查会退回到 GitHub `/releases/latest` 重定向路径。
- 更新检查失败文案会更清楚地区分超时、代理、SSL/证书、GitHub API 和普通网络失败。

## 改进内容

- **下载并安装** 会在应用内下载安装包，尽量校验 SHA256，启动安装器，然后退出应用。
- 仍保留浏览器下载作为备用路径。
- 如果检测到代理，更新页会显示安全摘要，例如 `https=127.0.0.1:7890`；不会显示代理凭据。

## 验证

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`
