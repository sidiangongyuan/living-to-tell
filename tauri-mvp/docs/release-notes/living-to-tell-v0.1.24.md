# Living to Tell Preview 0.1.24

This release combines the planned 0.1.22, 0.1.23, and 0.1.24 work into one acceptance build: Export & Backup Center, long-form collection planning, and first-use sample project.

## Download

- `LivingToTell_0.1.24_x64-setup.exe`
  - SHA256: `CB38580324BD3FE6E6FBD0DAA52724B0E477AFE1858C3E55E861897A61CF70B2`
- `LivingToTell_0.1.24_x64_zh-CN.msi`
  - SHA256: `E82B6EF08907226C51AF53798903601255089F2C20AFBAF60EC70DFE00F3A3D1`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- Export & Backup now starts from recovery confidence: it shows a safety summary, latest restore-point age, backup/checkpoint counts, and a selected restore point before restore.
- Restore points combine named checkpoints and automatic backups in one planner. Restoring still uses the app-managed safe backend path, which backs up the current database before restore.
- Backup reminders can be adjusted locally, so the app can show when the newest restore point is becoming stale.
- Data paths are visible in the backup center, with copy/open actions for the database, backup directory, and checkpoint directory.
- Recent article and recent collection export shortcuts are available from the backup center.
- Collections now include a planning board that groups outline cards by idea, draft, revision, done, and parked status.
- The Date welcome checklist can explicitly create a disposable sample project with two articles, a collection outline, a reference passage, a writing note, and a scene AI Card.
- The sample project is never created automatically. Removing it deletes only the exact IDs recorded by the sample marker, not user content with matching titles or tags.

## Verification

- Focused backend sample-project and version tests.
- Full backend API / AI service test subset: `179 passed, 1 skipped` (the skipped case is gated live Gemini quota).
- Frontend unit tests: `58 passed`.
- Full Playwright E2E suite: `67 passed`.
- Production frontend build and Rust/Tauri `cargo check`.
- Release packaging through `build-release.ps1`.
- Final installer hashes were computed after packaging.

---

# 活着为了讲述 0.1.24 预览版

本次把原计划的 0.1.22、0.1.23、0.1.24 合并为一个验收版本：导出与备份中心、作品集长篇规划增强、首次使用示例项目。

## 下载

- `LivingToTell_0.1.24_x64-setup.exe`
  - SHA256：`CB38580324BD3FE6E6FBD0DAA52724B0E477AFE1858C3E55E861897A61CF70B2`
- `LivingToTell_0.1.24_x64_zh-CN.msi`
  - SHA256：`E82B6EF08907226C51AF53798903601255089F2C20AFBAF60EC70DFE00F3A3D1`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增内容

- 导出与备份中心现在优先回答“我能不能恢复”：显示安全摘要、最新恢复点距离现在多久、备份/检查点数量和当前选中的恢复点。
- 恢复点规划器把命名检查点和自动备份放在一起。恢复仍走应用管理的安全后端路径，恢复前会先备份当前数据库。
- 可设置本机备份提醒阈值，用来判断最新恢复点是否已经偏旧。
- 备份中心显示真实数据路径，并支持复制或打开数据库、备份目录和检查点目录。
- 备份中心增加最近文章和最近作品集导出快捷入口。
- 作品集增加“规划看板”，按构思、草稿、修订、完成、暂停分组查看大纲卡片。
- 日期页欢迎清单可以显式创建一个可删除的示例项目，包含两篇文章、一个作品集大纲、一个文脉标本、一条文章便签和一张场景 AI Card。
- 示例项目不会自动创建。删除示例项目时只删除 marker 记录的精确 ID，不会按标题或标签删除用户内容。

## 验证

- 已增加后端示例项目与版本能力测试。
- 后端 API / AI 服务测试子集：`179 passed, 1 skipped`（跳过项是需要真实 Gemini 额度的 gated 测试）。
- 前端单元测试：`58 passed`。
- 完整 Playwright E2E：`67 passed`。
- 已通过前端生产构建和 Rust/Tauri `cargo check`。
- 已通过 `build-release.ps1` 完成安装包打包。
- 已在最终打包后计算安装包哈希。
