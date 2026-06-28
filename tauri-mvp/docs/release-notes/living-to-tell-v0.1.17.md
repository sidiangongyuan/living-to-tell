# Living to Tell Preview 0.1.17

This is a small reliability release for the AI profile workflow. It fixes a stale frontend request race that could make imported AI profiles appear empty after moving between Settings and AI Tools.

## Download

- `LivingToTell_0.1.17_x64-setup.exe`
  - SHA256: `6A4CCEA6EDEFADCF18BE2B1C6A831DD0BA03299FF6281E762C8635A41E67D5C7`
- `LivingToTell_0.1.17_x64_zh-CN.msi`
  - SHA256: `0023FA511DBBAA3496E6C7BD5A50830028F78C34E6E7C733E65AB0DC3672C46F`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's fixed

- Settings no longer lets an older `/api/settings/ai/profiles` response overwrite a newly imported local profile list.
- AI Tools now ignores stale AI profile refresh responses, so imported OpenCode, Codex/OpenAI, Gemini, or custom profiles remain visible after Settings -> AI Tools -> Manage Config -> AI Tools navigation.
- Added a browser regression test for the exact route round trip, including a delayed stale empty profile response after import.

## Verification

- `npm run test:e2e -- e2e/settings-actions.e2e.ts --workers=1`
- `npm test -- --run`
- `npm run build`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

---

# 活着为了讲述 0.1.17 预览版

这是一次 AI 配置档案流程的小型可靠性更新，修复导入本机配置后，设置页和 AI 工具页来回切换时配置档案偶发显示为空的问题。

## 下载

- `LivingToTell_0.1.17_x64-setup.exe`
  - SHA256: `6A4CCEA6EDEFADCF18BE2B1C6A831DD0BA03299FF6281E762C8635A41E67D5C7`
- `LivingToTell_0.1.17_x64_zh-CN.msi`
  - SHA256: `0023FA511DBBAA3496E6C7BD5A50830028F78C34E6E7C733E65AB0DC3672C46F`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 修复内容

- 设置页不再允许旧的 `/api/settings/ai/profiles` 响应把刚导入的本机 AI 配置档案覆盖成空列表。
- AI 工具页会忽略过期的配置档案刷新结果，Settings -> AI 工具 -> 管理配置 -> AI 工具 的来回切换后，OpenCode、Codex/OpenAI、Gemini 或自定义配置仍保持可见。
- 新增浏览器回归测试，覆盖导入后旧空响应延迟返回的场景，以及设置页 / AI 工具页的来回切换路径。

## 验证

- `npm run test:e2e -- e2e/settings-actions.e2e.ts --workers=1`
- `npm test -- --run`
- `npm run build`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`
