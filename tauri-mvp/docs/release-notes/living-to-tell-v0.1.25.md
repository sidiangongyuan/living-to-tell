# Living to Tell Preview 0.1.25

This release adds AI-assisted concept enrichment to the Motif Star Map.

## Assets

- `LivingToTell_0.1.25_x64-setup.exe`
- `LivingToTell_0.1.25_x64-setup.exe.sha256`
- `LivingToTell_0.1.25_x64_zh-CN.msi`
- `LivingToTell_0.1.25_x64_zh-CN.msi.sha256`

## What's New

- Motif Star Map details now include **AI Enrich**. You can enrich an existing motif or type a new concept first, generate a draft, then decide whether to append, overwrite, or skip note content.
- The draft template is writing-oriented instead of encyclopedic: definition, core tension, writing function, scene triggers, character behavior, image translation, short example, related suggestions, misuse warning, micro exercise, and source hints.
- AI related suggestions remain suggestions only. The feature does not create automatic semantic nodes or edges; star-map links still come from real excerpt co-occurrence.

## Reliability

- The user's typed concept remains the authoritative motif name even if the AI model rewrites the returned JSON `concept` field.
- Motif detail refresh is now sequential after saving, avoiding intermittent SQLite contention between local-graph and excerpt requests.
- Duplicate excerpt repair keeps the row with the correct current source range before falling back to timestamp/id ordering.

## Verification

- Real OpenCode test with `opencode/deepseek-v4-flash-free`: create concept, generate AI enrichment, save as motif, verify the note template, delete the test motif.
- Backend motif/API tests, frontend unit tests, full E2E suite, production build, and Tauri/Rust check passed.

# 活着为了讲述 0.1.25 预览版

本次更新给意象星图加入 **AI 丰富意象**，重点服务抽象概念、哲学概念和写作技法的记忆与转译。

## 安装包

- `LivingToTell_0.1.25_x64-setup.exe`
- `LivingToTell_0.1.25_x64-setup.exe.sha256`
- `LivingToTell_0.1.25_x64_zh-CN.msi`
- `LivingToTell_0.1.25_x64_zh-CN.msi.sha256`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 更新内容

- 意象星图右侧详情新增 **AI 丰富**：可以对已有意象生成短卡，也可以先输入新概念，生成后再确认创建。
- 短卡模板面向写作调用：一句话定义、核心张力、写作功能、场景触发、人物表现、意象转译、短例子、关联建议、误用提醒、微练习和来源线索。
- 关联建议只作为 chip 提示，不会自动建节点或连边；星图关系仍只来自真实摘录共现。

## 稳定性

- 用户输入的概念名现在是权威值，即使 AI 返回 JSON 时改写 `concept` 字段，也不会污染意象节点名称。
- 保存后详情刷新改为顺序加载，避免局部星图和摘录请求同时访问共享 SQLite connection 时出现偶发错误。
- 摘录漂移自动合并时，优先保留当前位置已经正确的那条记录，再按时间和 id 兜底。

## 验收

- 使用真实 `opencode/deepseek-v4-flash-free` 跑通：新建概念、AI 生成短卡、保存为意象、API 验证笔记模板、删除测试意象。
- 后端意象/API 测试、前端单测、完整 E2E、生产构建和 Tauri/Rust 检查均已通过。
