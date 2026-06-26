# Living to Tell Preview 0.1.12

This update adds article version history and a collection-level outline workspace for longer projects.

## Download

- `LivingToTell_0.1.12_x64-setup.exe`
  - SHA256: `8D5F15D102D12437EDEE06BF977E08FB864411E1BB7FDCD70EC1826B301D1E57`
- `LivingToTell_0.1.12_x64_zh-CN.msi`
  - SHA256: `0925169817F26B46986DBA8922621BF719FB548B85B1436417FFBFB51C6214C1`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## What's new

- Articles now have a version history panel in the right context area.
- You can save manual checkpoints with labels before major edits.
- AI write-back actions create an `AI before apply` snapshot before replacing article content.
- Restoring an old version first saves the current body as a rollback snapshot.
- Saved versions can be compared at paragraph level, restored, cloned as a new article, copied, or deleted.
- Collections now have `Manuscript / Outline` tabs.
- The outline tab supports part, chapter, scene, and note cards for long-form planning.
- Outline cards can track status, summary, point of view, timeline, setting, tags, target word count, and linked article.
- You can create a linked article from an outline card or connect an existing article.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

---

# 活着为了讲述 0.1.12 预览版

本次更新增加了文章历史版本和作品集层面的长篇项目大纲。

## 下载

- `LivingToTell_0.1.12_x64-setup.exe`
  - SHA256: `8D5F15D102D12437EDEE06BF977E08FB864411E1BB7FDCD70EC1826B301D1E57`
- `LivingToTell_0.1.12_x64_zh-CN.msi`
  - SHA256: `0925169817F26B46986DBA8922621BF719FB548B85B1436417FFBFB51C6214C1`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 新增内容

- 文章右侧上下文栏新增历史版本面板。
- 可以在重要修改前手动保存带标签的检查点。
- AI 写回正文前会自动保存 `AI 修改前` 快照。
- 恢复旧版本前会先保存当前正文，避免恢复后无法回退。
- 历史版本支持段落级对比、恢复、克隆为新文章、复制和删除。
- 作品集新增 `稿件 / 大纲` 标签。
- 大纲支持分部、章节、场景、笔记四类卡片，用于长篇规划。
- 大纲卡片可记录状态、摘要、视角、时间线、场景地点、标签、目标字数和关联文章。
- 可以从大纲卡片一键创建关联文章，也可以连接已有文章。

## 验证

- `D:\anaconda\envs\writer\python.exe -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`
