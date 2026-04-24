# Writer M3 Kickoff Prompt v0.1

下面这段提示词可以直接发给实现 agent，作为 Milestone 3 的继续指令。

---

环境我这边已经核过了，后续请统一使用 conda `writer` 环境 `D:\anaconda\envs\writer\python.exe`，不要再用仓库里的其他虚拟环境，也不要用 conda base。

我这边已确认：

- `writer` 包可导入
- `platformdirs`、`PySide6`、`openai`、`pytest` 可导入
- `pytest` 已通过，当前是 `26 passed`
- 工作区解释器已固定在 [D:/python_proj/writer/.vscode/settings.json](D:/python_proj/writer/.vscode/settings.json)

你现在继续做 Milestone 3，但必须严格遵守边界，不要扩大范围。

开始前先读这些文档：

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/cloud-ai-strategy.md](docs/cloud-ai-strategy.md)
- [docs/codex-style-integration.md](docs/codex-style-integration.md)
- [docs/initial-scaffold.md](docs/initial-scaffold.md)

你的本轮目标只有 6 件事：

1. AI provider
2. rewrite service
3. prompt builder
4. Codex config import
5. settings dialog
6. rewrite compare dialog

本轮严禁做这些内容：

- free-form AI chat
- references
- projects
- chapters
- export
- multi-provider routing UI
- local model support
- vector search
- 全局重构 UI 风格

## 具体实现要求

### 1. AI Provider

只实现一个 OpenAI-compatible provider。

要求：

- 支持 `base_url`
- 支持 `model`
- 支持 API key
- 按 `responses` API 形态发请求
- 不要把 SDK 响应对象泄漏到 UI 层
- 统一归一化成内部 `RewriteResponse`

### 2. Prompt Builder

只实现 3 个动作：

- `polish`
- `expand`
- `continue`

提示词必须遵守这些 guardrails：

- 保留原意
- 保留第一人称视角和情绪中心
- 默认做轻微文学化润色，不要写得过头
- 不要自动模仿引用素材句式
- 输出只返回结果正文，不要解释

### 3. Rewrite Service

要求：

- 接收当前选中文本或当前 fragment 正文
- 调用 provider
- 把生成结果存到 `entry_versions`
- 保存 provider / model 等 metadata
- 不要直接覆盖原文

### 4. Codex Config Import

只导入安全字段：

- `base_url`
- `model`
- `wire_api`
- provider name

不要依赖 Codex 私有 auth 存储。

### 5. Settings Dialog

第一版只做简单模式：

- base URL
- model
- API key 或 API key source
- Import Codex Config 按钮

不要提前加入高级设置项。

### 6. Rewrite Compare Dialog

必须是左右对照：

- 左边原文
- 右边改写结果
- 显式 Accept / Cancel

要求：

- 生成完成后不自动替换正文
- 只有用户显式 Accept 才把结果写回编辑器
- Cancel 不改正文

## 代码边界

继续保持当前分层，不要破坏：

- `app`
- `domain`
- `services`
- `storage`
- `ui`

要求：

- `MainWindow` 只做协调，不写 API 请求细节
- provider 细节放在 `services/ai/`
- prompt 拼装放在 `prompt_builder.py`
- settings 读写不要散落到 UI 各处
- repository 继续负责持久化

## 建议优先顺序

请按这个顺序推进：

1. 完善 `services/ai/interfaces.py`
2. 完善 `services/ai/prompt_builder.py`
3. 完善 `services/ai/openai_provider.py`
4. 完善 `services/ai/rewrite_service.py`
5. 完善 `services/ai/codex_config_importer.py`
6. 完善 `ui/dialogs/settings_dialog.py`
7. 完善 `ui/dialogs/rewrite_compare_dialog.py`
8. 接到 `container.py` 和 `main_window.py` 的最小入口

## 验证要求

完成后必须做验证，并在汇报中写清楚。

至少包括：

- `pytest`
- prompt builder 的窄测试
- Codex config import 的窄测试
- rewrite service 存储 version 的窄测试
- settings dialog 或 rewrite compare dialog 的最小交互测试（如果已有测试风格允许）

如果真实 provider 联调不稳定，可以：

- 先用 mock provider 保证业务链路
- 再补一次最小真实调用验证

## 汇报格式

完成后按下面结构汇报：

- 新增/修改文件
- 关键设计
- 验证结果
- 刻意未做的内容

如果你发现当前代码里已有部分 M3 文件或半成品实现，不要大范围推倒重来；在现有结构上补齐即可。

本轮完成后停下，不要进入 references、projects、export。

---
