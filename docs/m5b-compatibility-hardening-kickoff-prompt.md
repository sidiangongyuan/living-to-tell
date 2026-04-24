# Writer M5B Compatibility + Integrity Hardening Kickoff Prompt v0.1

下面这段提示词可以直接发给实现 agent，作为下一轮长任务包。

---

当前状态我这边已经核过：

- 统一使用 conda `writer` 环境：`D:\anaconda\envs\writer\python.exe`
- 当前全量测试通过：`99 passed`
- M5 主线功能已经基本完成：projects / chapters / Markdown / TXT export 都在
- 但是我这边审查时确认了两个真实问题，必须先修，再继续后续功能

这轮不要开新功能线，不要跳去 AI chat、packaging、DOCX/PDF。

这轮请连续完成一整段“兼容性 + 数据一致性 + 回归覆盖”工作，一次收口，至少包含这 3 个任务：

1. 修复旧数据库升级到 M5 时的 migration blocker
2. 修复 project / chapter assignment 的数据一致性漏洞
3. 补齐这两类问题的回归测试，并跑全量验证

不要重新规划产品，不要扩大范围。

## 开始前先读

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/m5-projects-and-export-kickoff-prompt.md](docs/m5-projects-and-export-kickoff-prompt.md)

然后直接看这些实现文件：

- `src/writer/storage/database.py`
- `src/writer/storage/schema.sql`
- `src/writer/storage/repositories/entry_repository.py`
- `src/writer/storage/repositories/project_repository.py`
- `src/writer/storage/repositories/chapter_repository.py`
- `src/writer/ui/dialogs/assign_fragment_dialog.py`
- `src/writer/ui/main_window.py`
- 以及 M5 相关测试文件

## 这轮不是“看看有没有问题”

下面这些问题我已经确认过了，把它们当成已验证 bug 处理，不要把时间花在是否存在上。

### 已确认问题 A：旧库升级 blocker

对一个旧版 `entries` 表（没有 `project_id` / `chapter_id` 列）的数据库执行初始化时，会报：

- `OperationalError: no such column: project_id`

原因我已经定位到：

- `src/writer/storage/schema.sql` 里会创建 `idx_entries_project` / `idx_entries_chapter`
- 但 `src/writer/storage/database.py` 里是先执行 schema，再在 `_migrate()` 中补 `ALTER TABLE ... ADD COLUMN`
- 对旧库来说，索引创建时列还不存在，所以启动就炸了

### 已确认问题 B：project / chapter 可进入不一致状态

我已经验证过当前实现允许下面两种错误状态：

1. entry 在 project A 下，但可以被直接挂到 project B 的 chapter 上
2. entry 原来在 project B / chapter B1，下次改成 project A 后，旧的 `chapter_id` 仍可能残留，变成跨项目脏数据

也就是说，目前系统没有真正保护这个不变量：

- 当 `chapter_id` 非空时，entry 的 `project_id` 必须等于该 chapter 的 `project_id`

这类约束不能只靠对话框 UI 兜底，数据层或一个集中协调点必须真正保证它。

## 本轮目标

把“老库可升级启动”与“project / chapter assignment 永远自洽”这两件事一次修干净。

要求：

- 不破坏 M5 已有主线功能
- 不引入大范围重构
- 不把业务规则散落到多个 UI 回调里
- 对 fresh DB 和 old DB 都要成立

## 任务 1：修复 migration blocker

你要保证：

- brand-new 数据库初始化仍然成功
- pre-M5 数据库升级初始化成功
- migration 是幂等的
- 不会丢失旧 entries 数据

### 这里的最低要求

1. 修复 `initialize_schema()` / `_migrate()` 与 `schema.sql` 的先后关系问题
2. 保证 `entries.project_id` / `entries.chapter_id` 相关索引，只会在列存在时创建
3. fresh DB 仍然能得到完整 schema 和索引
4. old DB 升级后，后续 project/chapter 分配与导出逻辑都能正常工作

### 可接受实现方式

你可以自由选择实现方式，但要满足上面的结果。比如：

- 把依赖新增列的索引创建移到 migration 步骤里
- 或者拆分 schema bootstrap 与 migration 逻辑
- 或者其他更简洁可靠的方案

但无论你怎么做，都要保持：

- 新库初始化路径简单
- 旧库升级路径安全
- schema / migration 职责清楚

### 任务 1 必须补的测试

至少增加这几类测试：

1. 手工构造一个 pre-M5 `entries` 表，只包含旧列，不含 `project_id` / `chapter_id`
2. 对这个旧库执行初始化 / migration，确认不会报错
3. 升级完成后，确认新列存在，且可以继续创建 project / chapter 并给 entry 赋值
4. 最好再补一个“部分升级态”的测试，例如只存在 `project_id` 不存在 `chapter_id`，确认迁移仍然安全

如果你认为第 4 条没有必要，也请在汇报里解释为什么。

## 任务 2：修复 project / chapter assignment 一致性

这轮要真正建立并保护这个规则：

- `chapter_id is not null` 时，chapter 必须属于 entry 当前所属 project

### 这轮至少要保证这些行为

1. 清空 project 时，chapter 也必须被清空
2. 从 project A 切到 project B 时，如果原 chapter 不属于 B，chapter 必须被清空
3. 不能把 entry 挂到别的 project 的 chapter 上
4. 正常的同项目 chapter assignment 仍然可用
5. UI 只是入口，真正的一致性保护必须在 repository 或一个集中协调的 service 中完成

### 实现建议

你可以二选一：

1. 强化现有 repository API，让 repository 自己校验并清理不一致状态
2. 增加一个很薄的 assignment / orchestration service，由它统一完成 project + chapter 的一致性写入

但不要做成：

- 只有 `AssignFragmentDialog` 知道规则
- 只有 `MainWindow` 回调里手工拼顺序
- repository 完全不校验，靠调用方“自觉正确”

### 这里请你明确选一个一致行为

关于“给 entry 指定一个 chapter，但当前 project 不匹配”这件事，你必须明确选一种行为并固定下来：

- 要么拒绝这次写入
- 要么自动把 entry 的 project 同步到该 chapter 的 project

两种都可以，但不要模糊，更不要不同入口行为不一致。

从当前 MVP 风格看，我更偏向：

- project 改变时清空不兼容 chapter
- chapter assignment 必须与 project 一致
- 不允许悄悄留下跨项目 chapter 脏引用

你如果采用别的方案，也可以，但要在汇报里说明理由。

### 任务 2 必须补的测试

至少增加：

1. entry 分配到 project A 后，尝试挂到 project B 的 chapter，应被拒绝或被一致地修正
2. entry 已在 project B / chapter B1，再改到 project A 后，不应残留旧 `chapter_id`
3. 清空 project 时，chapter 一并清空
4. 同 project 下分配 chapter 正常通过

如果你加了一个新的 service，请给它独立测试，不要只靠 UI 测试覆盖。

## 任务 3：最小 UI / 集成收口

这轮不要重做 UI，但要保证已有入口和新规则不打架。

至少确认：

- `AssignFragmentDialog` 的交互仍然成立
- `MainWindow` 调用 assignment 时不会再制造跨项目脏数据
- 旧数据库升级后，从 UI 打开并做一次 assignment 不会炸

### UI / 集成层建议

- 如果你引入新 service，就把 `MainWindow` 改成调用它
- 如果你强化 repository，就让 `MainWindow` 使用新的安全调用路径
- 不要把 migration、数据校验、Qt 控件状态混成一团

## 明确不做的内容

本轮严禁做：

- AI chat
- packaging
- DOCX / PDF export
- local model support
- multi-provider routing UI
- vector search
- 复杂 project planning 系统
- 任何与这轮 bug 修复无关的大重构

## 建议文件范围

本轮大概率会修改或新增这些文件：

修改：

- `src/writer/storage/database.py`
- `src/writer/storage/schema.sql`
- `src/writer/storage/repositories/entry_repository.py`
- `src/writer/ui/main_window.py`
- `src/writer/ui/dialogs/assign_fragment_dialog.py`（如果需要）
- `src/writer/app/container.py`（如果引入新 service）

新增或补充测试：

- `tests/storage/...` 下的 migration / repository regression tests
- `tests/ui/...` 下最小 assignment / startup integration tests

如果你决定加一个很薄的 service，也可以新增，例如：

- `src/writer/services/...`

但保持薄，别做成新的大子系统。

## 建议执行顺序

请按这个顺序做：

1. 先修 migration blocker
2. 先把 migration 回归测试补上并跑通
3. 再修 assignment 一致性规则
4. 再补 repository / service 层测试
5. 最后收 UI / integration 的最小改动
6. 跑全量测试

不要一上来同时改很多层，不要把两个问题混在一次大改里失去可验证性。

## 验证要求

完成后至少做这些验证：

- `pytest -v`
- 旧库升级测试明确通过
- project / chapter consistency 测试明确通过
- 如果有 UI 相关改动，offscreen GUI 最小验证通过

如果你能方便地补一个“旧库启动后完成一次 fragment assignment”的最小集成测试，会更好。

## 汇报格式

完成后继续按这个格式汇报：

- 新增 / 修改文件
- 任务 1 如何修
- 任务 2 如何修
- 验证结果
- 刻意未做

如果你在实现中必须二选一，比如：

- mismatch chapter assignment 是 reject 还是 auto-sync project

请在汇报里明确写出来，不要含糊一句“已处理”。

## 停止条件

这轮完成后停下，不要继续往后做新功能。

这轮目标是把 M5 从“主线基本可用，但对旧库和一致性有风险”推进到“可以继续往后走的稳定状态”。

---