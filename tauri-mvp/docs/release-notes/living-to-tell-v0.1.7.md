# Living to Tell Preview 0.1.7

This release renames the public Tauri preview to **Living to Tell / 活着为了讲述**.

> Writing, photography, singing, and speaking are all ways to tell. To live is to tell.

## Download

- `LivingToTell_0.1.7_x64-setup.exe`
- `LivingToTell_0.1.7_x64_zh-CN.msi`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- Public app name, installer, window title, documentation, and release copy now use Living to Tell / 活着为了讲述.
- The app now stores new data under `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`.
- First launch copies old Writer data from `%APPDATA%\Writer\Writer\writer.sqlite3` if it exists. The old database remains untouched.
- Public screenshots are generated with demo data, not real writing or local credential paths.
- The installer now closes both old Writer processes and new Living to Tell processes before copying files, reducing the chance of half-updated installs.

## Included recent fixes

- Article notes in the article context pane.
- Safer AI writeback with explicit replace, insert, and copy actions.
- Focused controls and personal presets for polish, rewrite, expand, and continue.
- Restored article editing position and improved long-document writing comfort.
- Date page start-writing action and reference quote deep links.
- Close-button behavior with ask / tray / exit choices.

## Privacy

- Writing data is local by default.
- AI providers receive text only when you run an AI tool or send a chat message.
- Settings store the selected AI provider and credential source, not raw API keys.
- This release does not include personal writing samples, local databases, API keys, OAuth tokens, account identifiers, or generated development logs.

## Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

---

# 活着为了讲述 0.1.7 预览版

本次发布把 Tauri 公开预览版改名为 **活着为了讲述 / Living to Tell**。

> 写作、拍照、唱歌、讲话，都是为了讲述。活着，就是为了讲述。

## 下载

- `LivingToTell_0.1.7_x64-setup.exe`
- `LivingToTell_0.1.7_x64_zh-CN.msi`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增与调整

- 应用名称、安装器、窗口标题、文档和 Release 文案统一改为活着为了讲述 / Living to Tell。
- 新数据目录为 `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`。
- 首次启动时，如果存在旧 Writer 数据库 `%APPDATA%\Writer\Writer\writer.sqlite3`，会复制到新目录；旧数据库保留不删除。
- 公开截图改用演示数据生成，不包含真实写作内容或本地凭据路径。
- 安装器会在复制文件前结束旧 Writer 进程和新 Living to Tell 进程，降低半更新风险。

## 包含的近期修复

- 文章右侧栏便签。
- AI 写回需要明确选择替换、插入或复制。
- 润色、改写、扩写、续写拥有独立控件和个人预设。
- 文章上次编辑位置恢复，并优化长文文末写作体验。
- 日期页开始写作按钮和每日精句跳转。
- 关闭按钮支持询问、最小化到托盘或直接退出。

## 隐私说明

- 写作数据默认保存在本机。
- 只有主动运行 AI 工具或发送对话时，文本才会发给对应 AI 提供方。
- 设置只保存 AI 提供方和凭据来源，不保存明文 API Key。
- 本次发布不包含私人写作样本、本地数据库、API key、OAuth token、账号标识或开发日志。

## 验证

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`
