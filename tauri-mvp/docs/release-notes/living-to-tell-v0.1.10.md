# Living to Tell Preview 0.1.10

This update fixes a false “article missing” warning on the article page and keeps the update-check flow ready for real release testing.

## Download

- `LivingToTell_0.1.10_x64-setup.exe`
  - SHA256: `FC55CF8DAE97190224669D4852EEAA095CE6BAD837FA034E6B463CF346A2C01C`
- `LivingToTell_0.1.10_x64_zh-CN.msi`
  - SHA256: `1B0E81E6F5EB657B002F2A5B399FFF6CA9804F3FDD6FC08E3A6A77BE657B41C3`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's fixed

- The article page no longer claims the current article is missing just because a side-panel request briefly returned `404`.
- Article-side note / collection requests now verify the article itself before showing a missing-article warning.
- The bug shape is locked down with a regression test that reproduces a false `404` from the side panel while the article still exists.
- `0.1.9` users can use this release to test the current update-notice flow against a real newer public build.

## Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

---

# 活着为了讲述 0.1.10 预览版

本次更新修复了文章页误报“文章已不存在”的问题，也方便你直接测试当前的更新提示流程。

## 下载

- `LivingToTell_0.1.10_x64-setup.exe`
  - SHA256: `FC55CF8DAE97190224669D4852EEAA095CE6BAD837FA034E6B463CF346A2C01C`
- `LivingToTell_0.1.10_x64_zh-CN.msi`
  - SHA256: `1B0E81E6F5EB657B002F2A5B399FFF6CA9804F3FDD6FC08E3A6A77BE657B41C3`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 修复内容

- 文章页右侧附属请求短暂返回 `404` 时，不会再误报“这篇文章已不存在，已刷新文章列表。”。
- 文章便签 / 作品集相关请求在显示“文章不存在”之前，会先验证文章本身是否真的已经不存在。
- 增加了对应回归测试，专门覆盖“侧栏请求 404，但文章仍然存在”的误报场景。
- 当前 `0.1.9` 用户可以直接通过本次 `0.1.10` 公开发布测试更新提示是否正常。

## 验证

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`
