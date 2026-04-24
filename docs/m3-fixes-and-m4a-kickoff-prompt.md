# Writer M3 Fixes + M4A Kickoff Prompt v0.1

下面这段提示词可以直接发给实现 agent，作为下一轮连续任务包。

---

当前状态我这边已经核过：

- 统一使用 conda `writer` 环境：`D:\anaconda\envs\writer\python.exe`
- 当前测试通过：`50 passed`
- M1、M2、M3 主线已经完成

你下一轮不要只修一个点就停，也不要直接跳去 projects/export。

这轮请按两个连续阶段执行：

1. 先修复 M3 验收里发现的 3 个问题
2. 修完后直接继续做 M4 的第一半，也就是 reference library foundation + rewrite integration

不要重新规划，不要扩大范围。

开始前先读这些文档：

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/cloud-ai-strategy.md](docs/cloud-ai-strategy.md)
- [docs/initial-scaffold.md](docs/initial-scaffold.md)

## 第一阶段：修复 M3 问题

这一阶段先做完，再进入下一阶段。

### Fix 1: Settings 里 `base_url` 可清空

当前问题：

- 用户一旦保存过自定义 `base_url`
- 后续在 settings 里把 `base_url` 清空并保存
- 实际不会回到默认 provider 端点，旧值会残留

你需要修成：

- 清空 `base_url` 后再次保存，`load_ai_config()` 应该返回默认值语义
- 可以通过删除该 setting、写入空字符串并在读取时归一化，或其他干净方式实现
- 不要留下旧值残留

### Fix 2: Rewrite Cancel 必须真正取消后续结果处理

当前问题：

- 进度框 Cancel 触发了 `requestInterruption()`
- 但 worker 仍可能继续跑完，并发出成功信号
- 用户仍可能看到 compare dialog

你需要修成：

- Cancel 后不应再弹出 compare dialog
- worker 层或 UI 协调层必须检查中断状态
- 如果无法中断底层 HTTP 请求，也至少要保证 UI 不接收并应用该结果
- 取消应表现为“本次 rewrite 已放弃”，而不是“只是关掉 loading”

### Fix 3: `wire_api` 不能是任意自由值

当前问题：

- M3 只支持 `responses`
- 但 settings dialog 允许用户输入任意 `wire_api`
- 错误会延迟到真正调用 AI 时才暴露

你需要修成：

- 第一版 UI 里把 `wire_api` 固定为 `responses`，或者改为只允许合法值
- 至少要在保存前做校验
- 不要把明显无效的配置静默保存

### 第一阶段验证要求

至少补这些测试：

- `base_url` 保存后可清空的测试
- Cancel 后不会进入成功处理链路的测试
- 非法 `wire_api` 无法保存或会被归一化的测试

第一阶段修完后再进入第二阶段，不要先并行扩功能。

## 第二阶段：M4A Reference Library Foundation

这一阶段只做 reference library 的第一半，不做 projects/export。

### 目标

- 用户能把名句或参考段落粘贴保存到本地库
- 用户能搜索和管理这些参考段落
- 用户在 rewrite 前可以选取 0 到若干条参考段落
- selected references 会真正进入 rewrite request

### 本轮要做的内容

#### 1. 数据模型与持久化

新增：

- `src/writer/domain/models/reference_passage.py`
- `src/writer/storage/repositories/reference_repository.py`

修改：

- `src/writer/storage/schema.sql`
- `src/writer/app/container.py`

要求：

- `source_title` 必填
- `source_author` 可选
- `content` 必填
- `tags` 先保持自由文本即可
- 支持基础 CRUD
- 支持 keyword search

搜索要求：

- 先用简单可靠方案即可
- 普通 SQL 搜索或 FTS5 都可以
- 不要引入向量检索

#### 2. Reference Library UI

新增：

- `src/writer/ui/panels/reference_library_panel.py`
- `src/writer/ui/dialogs/reference_picker_dialog.py`

如果确实需要一个包裹容器 dialog，也可以新增一个轻量 dialog，但不要做复杂多页面导航。

要求：

- 录入方式以直接粘贴为主
- 能新增、编辑、删除 reference
- 能按关键词筛选
- 不要做复杂富文本，只做文本字段即可

#### 3. Rewrite Flow Integration

修改：

- `src/writer/ui/main_window.py`
- 必要时修改 `src/writer/services/ai/interfaces.py`
- 必要时修改 `src/writer/services/ai/prompt_builder.py`

要求：

- 用户发起 rewrite 前，可以选择是否附带 reference passages
- 如果用户不选，rewrite 正常继续
- 如果用户选了，selected reference contents 要进入 `RewriteRequest`
- prompt 中要继续明确标注：references 仅作语调参考，不得复制

#### 4. UI 边界

继续保持分层：

- `MainWindow` 只协调
- repository 负责持久化
- prompt builder 负责拼 prompt
- provider 不处理 reference 选择逻辑

不要在这轮里顺手加入：

- AI chat
- projects
- chapters
- export
- multi-provider
- local models
- vector search
- 全局 UI 改版

## 建议文件范围

本轮大概率会新增或修改这些文件：

新增：

- `src/writer/domain/models/reference_passage.py`
- `src/writer/storage/repositories/reference_repository.py`
- `src/writer/ui/panels/reference_library_panel.py`
- `src/writer/ui/dialogs/reference_picker_dialog.py`
- `tests/storage/test_reference_repository.py`
- `tests/ui/test_reference_library.py`

修改：

- `src/writer/storage/schema.sql`
- `src/writer/app/container.py`
- `src/writer/ui/main_window.py`
- `src/writer/services/ai/interfaces.py`（如有必要）
- `src/writer/services/ai/prompt_builder.py`（如有必要）
- 与 M3 修复直接相关的 settings / worker / dialog 文件

## 推荐执行顺序

请按这个顺序推进：

1. 修 Fix 1 / Fix 2 / Fix 3
2. 补对应测试并跑通
3. 扩 schema + reference model + reference repository
4. 做 reference repository 测试
5. 做 reference library UI
6. 做 reference picker dialog
7. 接进 rewrite flow
8. 跑全量测试

## 验证要求

完成后至少做这些验证：

- `pytest -v`
- reference repository 的 CRUD + search 测试
- Cancel rewrite 后无 compare dialog/无 acceptance 链路的测试
- selected references 确实进入 rewrite request 的测试
- offscreen GUI 最小验证

## 汇报格式

完成后继续按这个格式汇报：

- 新增/修改文件
- 关键设计
- 验证结果
- 刻意未做

本轮完成后停下。

不要进入：

- projects
- chapters
- export
- AI chat

---
