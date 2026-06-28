# Living to Tell Preview 0.1.21

This update focuses on first-run clarity, AI diagnostics, command-palette speed, reference-library overview, and safer capture of AI chat output. It also updates the public screenshots for the current AI Workspace, Reference Library, and Settings surfaces.

## Download

- `LivingToTell_0.1.21_x64-setup.exe`
  - SHA256: `9F33EF9B784B79E7143C520BF29244EFA9FEA9533BF01D28295AD7FE9CE19DBD`
- `LivingToTell_0.1.21_x64_zh-CN.msi`
  - SHA256: `B0D745AB1800E623364DC0B500146D3A2D029EA67CC66DD7BE88D280C8DC7AFB`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- The Date view now includes a first-run checklist that reads local state without creating sample data.
- Settings now shows AI diagnostics for provider, model, transport, credential source, local checks, real request checks, and model-list source.
- AI Tools now shows request size diagnostics before running: characters, paragraphs, estimated tokens, and selected model count.
- Multi-model AI runs now show honest pending result cards while the request is still in flight.
- The command palette is grouped into commands and searchable writing content, including articles, collections, references, motifs, AI Cards, settings, backup, and common actions.
- The Reference Library now shows compact overview cards and current-group summaries for sources, possible duplicates, usage distribution, authors, and character totals.
- AI chat assistant replies can be reviewed and edited in a capture dialog before saving as reference material or a new article.

## What's changed

- AI chat message actions use a quieter action row. Saving as an article note remains direct; saving as reference material or a new article requires confirmation.
- Reference-library overview labels are kept compact in narrow panes so Chinese labels do not break awkwardly.
- Public screenshots for AI Workspace, Reference Library, and Settings were refreshed.

## Verification

- Visual browser screenshots were checked for Dates onboarding, Settings AI diagnostics, Reference Library overview, AI chat capture, AI Tools comparison, and the command palette.
- Real OpenCode smoke test: `opencode/deepseek-v4-flash-free` returned `OK`, `cost=0`.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`

---

# 活着为了讲述 0.1.21 预览版

本次更新重点改善首次使用清晰度、AI 诊断、命令面板效率、文脉库总览，以及 AI 对话内容保存的安全性。同时更新了当前 AI 工作区、文脉库和设置页截图。

## 下载

- `LivingToTell_0.1.21_x64-setup.exe`
  - SHA256: `9F33EF9B784B79E7143C520BF29244EFA9FEA9533BF01D28295AD7FE9CE19DBD`
- `LivingToTell_0.1.21_x64_zh-CN.msi`
  - SHA256: `B0D745AB1800E623364DC0B500146D3A2D029EA67CC66DD7BE88D280C8DC7AFB`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增内容

- 日期页增加首次使用清单，读取本机状态，不创建示例数据。
- 设置页增加 AI 诊断，显示 provider、model、transport、凭据来源、本地检查、真实请求和模型列表来源。
- AI 工具运行前显示请求规模：字数、段落、估算 token 和选中模型数量。
- 多模型 AI 运行时，在请求未完成前显示真实等待中的结果卡片。
- 命令面板改为分组结构，覆盖常用命令、文章、作品集、文脉、意象、AI 卡片、设置和备份。
- 文脉库增加总览卡片和当前分组摘要，显示来源数、疑似重复、用途分布、作者和字数。
- AI 对话助手回复可先在预览弹窗中编辑，再保存为文脉标本或新文章。

## 改进内容

- AI 对话消息操作条更克制。保存为文章便签仍可直接执行；保存为文脉标本或新文章需要确认。
- 文脉库总览标签在窄栏里保持紧凑，避免中文断字。
- 公开截图中的 AI 工作区、文脉库和设置页已更新。

## 验证

- 已用浏览器截图检查日期页首次使用清单、设置页 AI 诊断、文脉库总览、AI 对话保存弹窗、AI 工具对比结果和命令面板。
- OpenCode 真实 smoke test：`opencode/deepseek-v4-flash-free` 返回 `OK`，`cost=0`。
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
