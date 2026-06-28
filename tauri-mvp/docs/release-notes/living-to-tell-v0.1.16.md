# Living to Tell Preview 0.1.16

This update smooths the AI profile workflow after the 0.1.15 profile-discovery release. It focuses on Settings layout, local discovery control, OpenCode credential diagnostics, and more reliable model comparison profile refresh.

## Download

- `LivingToTell_0.1.16_x64-setup.exe`
  - SHA256: `94649DE2A466D32DE287DB2F71180990B06D95E31E9FE2515F805C0583F11B88`
- `LivingToTell_0.1.16_x64_zh-CN.msi`
  - SHA256: `FA13E700542BDE741E3B1DBE6020EA0630D4E3E9443289A8A8448CFD304521F2`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's changed

- Settings no longer scans local AI configurations automatically when opening the page. Click **Scan Local Configs** when you want a fresh local discovery pass.
- New/edit AI profile now opens in a separate dialog with a clear cancel path instead of expanding an inline form at the bottom of Settings.
- Discovered local AI profile candidates can be removed from the current scan results one by one, or cleared together. This only changes the app UI list; it does not delete local OpenCode, Codex, Gemini, or environment configuration files.
- AI Tools refresh saved profile choices when the page regains focus, so profiles edited in Settings appear more reliably in model comparison.
- The “AI profiles refreshed” message is now scoped to the model comparison section and clears itself.
- OpenCode local credential checks no longer show a hard `auth_list_failed` state when local auth exists and real OpenCode requests work.
- Gemini remains honestly reported as unavailable when the local or remote configuration cannot answer a real request.

## Verification

- Real local OpenCode probe with `opencode/deepseek-v4-flash-free`: success, `transport=opencode_cli`, `cost=0`.
- Real local Codex/OpenAI probe from local Codex config: success.
- Real local Gemini probe: unavailable; no fake success is reported.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\services\ai\test_opencode_cli_provider.py tests\services\ai\test_preflight.py tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_crud_and_validation tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_discover_and_import_local -q`
- `npm test -- --run`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

---

# 活着为了讲述 0.1.16 预览版

本次更新打磨 0.1.15 引入的 AI 配置档案流程，重点修复设置页布局、本机扫描控制、OpenCode 凭据状态显示，以及 AI 工具多模型对比里的配置刷新体验。

## 下载

- `LivingToTell_0.1.16_x64-setup.exe`
  - SHA256: `94649DE2A466D32DE287DB2F71180990B06D95E31E9FE2515F805C0583F11B88`
- `LivingToTell_0.1.16_x64_zh-CN.msi`
  - SHA256: `FA13E700542BDE741E3B1DBE6020EA0630D4E3E9443289A8A8448CFD304521F2`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 更新内容

- 设置页不再进入页面就自动扫描本机 AI 配置。需要时点击 **扫描本机配置** 才会执行。
- 新增 / 编辑 AI 配置档案改为独立弹窗，有明确取消入口，不再在页面底部展开长表单。
- 本机扫描出的 AI 配置候选项可以逐个移除，也可以一次清空当前扫描结果。这个操作只清理应用里的扫描列表，不删除本机 OpenCode、Codex、Gemini 或环境变量配置。
- AI 工具页在重新获得焦点时会刷新已保存配置档案，设置页改完后更容易在多模型对比里直接看到。
- “AI 配置档案已刷新”提示现在只显示在模型对比区域，并会自动消失。
- OpenCode 本地凭据检查不再因为 `opencode auth list` 临时失败而显示硬性 `auth_list_failed`，只要本地 auth 存在且真实请求可用，就按可用能力处理。
- Gemini 如果本机或远端配置确实不可用，仍然会如实显示不可用，不做假成功。

## 验证

- 本机 OpenCode 真实请求 `opencode/deepseek-v4-flash-free` 成功，`transport=opencode_cli`，`cost=0`。
- 本机 Codex/OpenAI 配置真实请求成功。
- 本机 Gemini 真实探测不可用，应用显示诊断，不伪装为成功。
- `D:\anaconda\envs\writer\python.exe -m pytest tests\services\ai\test_opencode_cli_provider.py tests\services\ai\test_preflight.py tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_crud_and_validation tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_discover_and_import_local -q`
- `npm test -- --run`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`
