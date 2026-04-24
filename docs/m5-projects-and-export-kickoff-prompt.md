# Writer M5 Projects + Export Kickoff Prompt v0.1

下面这段提示词可以直接发给实现 agent，作为下一轮长任务包。

---

当前状态我这边已经核过：

- 统一使用 conda `writer` 环境：`D:\anaconda\envs\writer\python.exe`
- 当前测试通过：`72 passed`
- M1、M2、M3、M4A 主线已经完成

你下一轮不要只做一个小点，也不要跳去 AI chat 或 packaging。

这轮请连续完成一整段：

1. Project accumulation
2. Lightweight chapter grouping
3. Markdown / TXT export

不要重新规划，不要扩大范围。

开始前先读这些文档：

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/initial-scaffold.md](docs/initial-scaffold.md)
- [docs/product-requirements.md](docs/product-requirements.md)

## 本轮目标

把“零散 fragment → project → lightweight chapter grouping → export accepted content”这条链路打通。

要求仍然保持 MVP 级别，不要做复杂写作平台。

## 本轮必须做的内容

### 1. Project 数据模型与持久化

新增：

- `src/writer/domain/models/project.py`
- `src/writer/domain/models/chapter.py`
- `src/writer/storage/repositories/project_repository.py`
- `src/writer/storage/repositories/chapter_repository.py`

修改：

- `src/writer/storage/schema.sql`
- `src/writer/app/container.py`
- 必要时 `src/writer/storage/repositories/entry_repository.py`
- 必要时 `src/writer/domain/models/entry.py`

最低要求：

- `projects` 表
- `chapters` 表
- entry 能关联到 project
- entry 能可选关联到 chapter
- project CRUD
- chapter CRUD
- chapter 在 project 内有稳定顺序

### 2. Project / Chapter 基础 UI

新增：

- `src/writer/ui/panels/project_panel.py`

如果需要一层薄 dialog 包裹，也可以新增轻量 dialog，但不要做复杂导航壳。

要求：

- 能创建、重命名、删除 project
- 能在 project 下创建、编辑、删除 chapter
- 能把当前 fragment 分配到某个 project
- 能把当前 fragment 可选分配到某个 chapter
- 界面保持轻量，不要做看板、卡片墙、复杂拖拽

建议交互：

- 用一个独立的 Projects 对话框或面板集中管理
- 在主窗口里提供进入 project 管理的入口
- 对当前 fragment 的 project/chapter 归属，可以用简单动作或选择框解决

### 3. Export 服务

新增：

- `src/writer/services/export/__init__.py`
- `src/writer/services/export/markdown_exporter.py`
- `src/writer/services/export/text_exporter.py`

要求：

- 只导出 accepted content，也就是当前 entries.body
- 不导出 AI 历史版本
- 先支持两种导出对象：
  - 当前 fragment
  - 当前 project

导出格式要求：

- Markdown：保留 project / chapter / entry 标题层级
- TXT：清晰可读、结构简单、无需复杂格式化

不要做：

- DOCX
- PDF
- 富样式导出
- 出版模板

### 4. 主窗口集成

修改：

- `src/writer/ui/main_window.py`

要求：

- 主窗口增加 Projects 入口
- 主窗口增加 Export 入口
- 当前 fragment 可以被归入 project/chapter
- 可以触发 export current fragment / export current project

实现方式要求：

- `MainWindow` 只做协调，不自己拼导出文本，不自己操作 SQL
- 持久化走 repository
- 导出走 export service

### 5. 导出顺序与边界

导出 current project 时，顺序必须明确。

推荐最小规则：

- chapter 按 `sort_order`
- 不在 chapter 下的 entry 先独立输出或集中在一个无章节区块
- 同章内 entry 按 `updated_at` 或明确的稳定顺序

你可以选一个简单稳定的方案，但必须在汇报里说明。

## 明确不做的内容

本轮严禁做：

- AI chat
- packaging
- multi-provider routing UI
- local model support
- vector search
- project analytics
- drag-and-drop plotting board
- cards/kanban 章节管理
- DOCX/PDF export
- sync

## 建议文件范围

本轮大概率会新增或修改这些文件：

新增：

- `src/writer/domain/models/project.py`
- `src/writer/domain/models/chapter.py`
- `src/writer/storage/repositories/project_repository.py`
- `src/writer/storage/repositories/chapter_repository.py`
- `src/writer/services/export/__init__.py`
- `src/writer/services/export/markdown_exporter.py`
- `src/writer/services/export/text_exporter.py`
- `src/writer/ui/panels/project_panel.py`
- 如果需要：一个薄的 project dialog
- `tests/storage/test_project_repository.py`
- `tests/storage/test_chapter_repository.py`
- `tests/services/test_exporters.py`
- `tests/ui/test_projects_and_export.py`

修改：

- `src/writer/storage/schema.sql`
- `src/writer/app/container.py`
- `src/writer/ui/main_window.py`
- `src/writer/domain/models/entry.py`（如果需要 project/chapter 字段）
- `src/writer/storage/repositories/entry_repository.py`（如果需要 assignment 方法）

## 建议执行顺序

请按这个顺序推进：

1. 扩 schema：projects / chapters / entry assignment
2. 做 `project.py` / `chapter.py`
3. 做 `project_repository.py` / `chapter_repository.py`
4. 补 repository 测试
5. 做 export services
6. 补 exporter 测试
7. 做 `project_panel.py` 和必要 UI 容器
8. 接入 `main_window.py`
9. 补 UI 测试
10. 跑全量测试

## 设计约束

继续保持当前分层，不要破坏：

- `app`
- `domain`
- `services`
- `storage`
- `ui`

要求：

- 项目/章节逻辑不要塞进 `MainWindow`
- 不要让导出逻辑知道 Qt 控件细节
- repository 负责数据落盘
- exporter 负责字符串输出
- UI 只负责触发和选择

## 验证要求

完成后至少做这些验证：

- `pytest -v`
- project CRUD 测试
- chapter CRUD / 排序测试
- entry 分配到 project/chapter 的测试
- Markdown / TXT exporter 输出测试
- offscreen GUI 最小验证

如果加了文件保存对话框，自动化里可以 mock 选择路径；不要因为系统对话框导致测试不稳定。

## 汇报格式

完成后继续按这个格式汇报：

- 新增/修改文件
- 关键设计
- 验证结果
- 刻意未做

本轮完成后停下。

不要进入：

- AI chat
- packaging
- DOCX/PDF export
- 更复杂的 manuscript planning

---
