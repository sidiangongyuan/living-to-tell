# Living to Tell Preview 0.1.7

This release is the first major public preview under the **Living to Tell / 活着为了讲述** name.

> Writing, photography, singing, and speaking are all ways to tell. To live is to tell.

## Download

- `LivingToTell_0.1.7_x64-setup.exe`
- `LivingToTell_0.1.7_x64_zh-CN.msi`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- Public app name, installer, window title, documentation, and release copy now use Living to Tell / 活着为了讲述.
- The app now stores new data under `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`.
- First launch copies old Writer data from `%APPDATA%\Writer\Writer\writer.sqlite3` if it exists. The old database remains untouched.
- Settings now include a Data and Storage section for opening the data directory, inspecting the active SQLite database, and migrating to a custom location by copying data.
- Uninstalling the app does not delete the writing database, backups, or checkpoints.
- Startup now shows a light splash screen while the bundled backend sidecar starts.
- Article AI chat now focuses on the current article, supports standing instructions, and can save assistant replies as article notes.
- The new Motif Star Map lets users save selected article/reference text into motifs, revisit source anchors, and explore co-occurrence links.
- Motif excerpts now deduplicate and repair position drift, so a sentence that moved after editing reopens the existing motifs instead of creating repeated anchors.
- Public screenshots are generated with demo data, not real writing or local credential paths.
- The installer now closes both old Writer processes and new Living to Tell processes before copying files, reducing the chance of half-updated installs.

## Included recent fixes

- Article notes in the article context pane.
- Safer AI writeback with explicit replace, insert, and copy actions.
- Focused controls and personal presets for polish, rewrite, expand, and continue.
- Restored article editing position and improved long-document writing comfort.
- Date page start-writing action and reference quote deep links.
- Close-button behavior with ask / tray / exit choices.
- Reference-library usage/tag switching and paragraph-count wording.
- Backend capability checks and friendlier messages for backend version or connection problems.
- Motif star map visual density, label overlap, right-click attach flow, duplicate excerpt merging, and safe unlink behavior.

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

本次发布是 **活着为了讲述 / Living to Tell** 品牌下的第一个重要公开预览版。

> 写作、拍照、唱歌、讲话，都是为了讲述。活着，就是为了讲述。

## 下载

- `LivingToTell_0.1.7_x64-setup.exe`
- `LivingToTell_0.1.7_x64_zh-CN.msi`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增与调整

- 应用名称、安装器、窗口标题、文档和 Release 文案统一改为活着为了讲述 / Living to Tell。
- 新数据目录为 `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`。
- 首次启动时，如果存在旧 Writer 数据库 `%APPDATA%\Writer\Writer\writer.sqlite3`，会复制到新目录；旧数据库保留不删除。
- 设置页新增“数据与存储”，可打开数据目录、查看当前 SQLite 数据库，并用复制方式迁移到自定义位置。
- 卸载应用不会删除写作数据库、备份或检查点。
- 启动时增加浅色启动反馈窗口，后台服务启动期间不再黑屏等待。
- 文章 AI 对话聚焦当前文章，支持常驻指令，并可把 AI 回复保存为文章便签。
- 新增意象星图：可把文章 / 文脉中的选中文字保存为意象，回到原文锚点，并查看意象共现关系。
- 意象摘录现在会处理位置漂移和重复数据：文章修改后，同一句话会回填已有意象，而不是反复创建重复锚点。
- 公开截图改用演示数据生成，不包含真实写作内容或本地凭据路径。
- 安装器会在复制文件前结束旧 Writer 进程和新 Living to Tell 进程，降低半更新风险。

## 包含的近期修复

- 文章右侧栏便签。
- AI 写回需要明确选择替换、插入或复制。
- 润色、改写、扩写、续写拥有独立控件和个人预设。
- 文章上次编辑位置恢复，并优化长文文末写作体验。
- 日期页开始写作按钮和每日精句跳转。
- 关闭按钮支持询问、最小化到托盘或直接退出。
- 文脉库用途 / 标签切换和段落数统计文案。
- 后端能力检查与更友好的后台版本 / 连接问题提示。
- 意象星图密度、标签重叠、右键加入、重复摘录合并和安全解绑。

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
