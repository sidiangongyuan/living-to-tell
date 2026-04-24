# Writer Agent Kickoff Prompt v0.1

下面这段提示词可以直接发给另一个实现 agent。

---

你现在是这个项目的实现 agent，请直接开始编码，不要重新做产品规划，不要扩大范围。

项目背景：

- 这是一个 Windows 单机、个人使用的写作软件
- 核心目标是随时记录灵感片段，并通过 AI 做轻微文学化润色
- 产品定位是极简日记本，而不是复杂写作平台
- 第一版不做自由聊天，只做写作相关的 AI 改写动作
- 原文必须始终可恢复，AI 结果不能静默覆盖原文

你开始前必须先阅读这些文档：

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/initial-scaffold.md](docs/initial-scaffold.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/product-requirements.md](docs/product-requirements.md)
- [docs/technical-approach.md](docs/technical-approach.md)
- [docs/cloud-ai-strategy.md](docs/cloud-ai-strategy.md)
- [docs/codex-style-integration.md](docs/codex-style-integration.md)
- [docs/open-source-research.md](docs/open-source-research.md)

你的实现任务分两段执行，不要一口气做完整产品。

第一段：先完成 Milestone 1

目标：

- 建立 Python 项目基础骨架
- 建立 PySide6 桌面启动能力
- 建立 SQLite 初始化能力
- 建立 settings 持久化能力
- 建立主窗口骨架

你必须优先按这个顺序创建文件：

1. [pyproject.toml](pyproject.toml)
2. [.gitignore](.gitignore)
3. [README.md](README.md)
4. [src/writer/__init__.py](src/writer/__init__.py)
5. [src/writer/main.py](src/writer/main.py)
6. [src/writer/app/paths.py](src/writer/app/paths.py)
7. [src/writer/storage/database.py](src/writer/storage/database.py)
8. [src/writer/storage/schema.sql](src/writer/storage/schema.sql)
9. [src/writer/app/settings.py](src/writer/app/settings.py)
10. [src/writer/storage/repositories/settings_repository.py](src/writer/storage/repositories/settings_repository.py)
11. [src/writer/app/container.py](src/writer/app/container.py)
12. [src/writer/ui/main_window.py](src/writer/ui/main_window.py)
13. [src/writer/app/bootstrap.py](src/writer/app/bootstrap.py)
14. [tests/test_smoke_startup.py](tests/test_smoke_startup.py)
15. [tests/storage/test_settings_repository.py](tests/storage/test_settings_repository.py)

第一段的强约束：

- 使用 Python src 布局
- 使用 PySide6
- 使用 SQLite
- 使用 platformdirs 管理用户数据路径
- 不要引入 web backend
- 不要引入 ORM
- 不要提前做 AI chat
- 不要提前做多 provider 路由
- 不要提前做 vector search
- 所有路径、设置、数据库连接逻辑要分层，不要写进 UI

第一段完成后，你必须先验证：

- 应用可以启动
- SQLite 数据库会自动初始化
- settings 可以持久化读写
- 相关测试可以运行

如果第一段验证失败，先修复，不要继续扩范围。

第二段：如果第一段稳定，再进入 Milestone 2

目标：

- recent fragments 列表
- fragment editor
- entry 持久化
- auto-save
- FTS5 搜索

第二段优先创建这些文件：

- [src/writer/domain/enums.py](src/writer/domain/enums.py)
- [src/writer/domain/models/entry.py](src/writer/domain/models/entry.py)
- [src/writer/domain/models/entry_version.py](src/writer/domain/models/entry_version.py)
- [src/writer/storage/repositories/entry_repository.py](src/writer/storage/repositories/entry_repository.py)
- [src/writer/storage/repositories/version_repository.py](src/writer/storage/repositories/version_repository.py)
- [src/writer/services/autosave_service.py](src/writer/services/autosave_service.py)
- [src/writer/services/search_service.py](src/writer/services/search_service.py)
- [src/writer/ui/panels/fragment_list_panel.py](src/writer/ui/panels/fragment_list_panel.py)
- [src/writer/ui/panels/editor_panel.py](src/writer/ui/panels/editor_panel.py)
- [tests/storage/test_entry_repository.py](tests/storage/test_entry_repository.py)

第二段的交互必须遵守这些设计：

- 主界面是左侧最近片段列表，右侧编辑器
- 没有当前内容时自动创建空白片段
- 内容模型是独立片段，不是单一长文档
- 顶部动作保持极简，只保留核心入口

编码方式要求：

- 优先最小可运行实现，不要追求大而全
- 代码要分层：app / storage / domain / services / ui
- repository 管数据库读写，UI 不直接写 SQL
- 先做薄而清晰的抽象，不做过度设计
- 保留未来接入 AI rewrite 的清晰位置，但本轮不要提前实现完整 AI 功能

你在实现时可以借鉴这些思路，但不要复制外部项目代码：

- Freenote：写作优先、干扰少、本地优先
- Manuscript：保护原文、显式接受 AI 改写
- Obsidian Text Generator：配置驱动的 AI 接入思路
- manasCore：先本地保存，再在外围增加 AI 能力

这一轮结束时，你的输出应该包括：

- 已创建和修改的文件
- 当前已完成到哪个 milestone
- 运行或测试时用了什么验证方式
- 还有哪些内容刻意没有做

如果 Milestone 1 和 2 都稳定了，再停下来汇报，不要擅自进入 AI rewrite、reference library、project/export。

---

如果你希望更稳一点，也可以只把上面提示词中的“第一段”发给实现 agent，让它先把基础骨架做完再继续。
