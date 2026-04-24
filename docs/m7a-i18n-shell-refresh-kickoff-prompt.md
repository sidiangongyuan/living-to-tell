# Writer M7A Internationalization + Shell Refresh Kickoff Prompt v0.1

下面这段提示词可以直接发给实现 agent，作为下一轮长任务包。

---

当前状态我这边已经核过：

- 当前 Windows 打包启动问题已修复，`dist/Writer/Writer.exe` 可以正常启动
- 当前全量测试通过：`206 passed`
- 用户已手工试过基础主线功能，当前没有明显 blocker
- 当前应用版本是 `0.1.0-alpha`
- 当前产品主线已经具备：fragment editor / search / tags / AI rewrite / partial accept / version history / projects / chapters / export / portable packaging

## Git / 协作规则

这轮实现 agent 不负责版本控制收口。

要求：

- 不要自己 `git init`
- 不要自己改 remote
- 不要自己 `git commit`
- 不要自己 `git push`
- 只在当前工作区完成代码与文档修改，并按要求汇报

这轮的 git review / commit / push / tag 由审查 agent 统一处理。

这轮不要跳去 AI chat、深色模式完整实现、DOCX/PDF、多人同步、移动端。

这轮的目标不是“补一个小功能”，而是把产品从“功能可用的 internal alpha”推进到“有明确视觉方向、可中英切换、写作体验更顺手的 `0.2.0-alpha.1`”。

## 这轮产品冻结要求

下面这些用户需求已经确认，不要再重新发散：

- 支持简体中文 / 英文界面切换
- 默认语言：英文
- 语言切换入口：设置页里有，主界面也有
- 语言切换允许“切换后重启应用生效”，不要求无重启即时热切换
- AI 默认动作名称和默认提示策略跟随界面语言一起切换
- 视觉方向：极简写作感，安静、留白、不过度装饰
- 但主界面允许明显改版，不必拘泥于现有两栏结构
- 主界面方向：专注写作式，默认让编辑区更主导，其它区域可收起或弱化
- 色彩力度：轻微点缀，不做重度品牌化，不做花哨 UI
- 动效力度：很轻，只做细微过渡和反馈，不要为了动画牺牲响应速度
- tag 颜色自动分配，不要求本轮支持用户手工选色
- tag 颜色不仅用于编辑区，也应覆盖左侧列表、筛选器、项目 / chapter / reference 等标签化元素
- 用户很在意“丝滑”：fragment 切换、搜索/tag/project 过滤、AI 流程、项目管理、编辑输入、聚焦与反馈都要更顺手
- 用户明确希望增加一些“小巧思”：
  - 最近项目 / 最近标签快捷入口
  - 命令面板 / 快捷动作搜索
  - 更聪明的自动聚焦和光标定位
  - 布局宽度记忆
  - 更清楚的空状态与引导
- 这轮版本节奏由你规划，但我建议这一轮只落一个大版本：`0.2.0-alpha.1`

## 这轮不要做的内容

明确不做：

- free-form AI chat
- 完整 dark mode
- 多 provider 路由 UI
- local model support
- sync / cloud account / web backend
- DOCX / PDF export
- 重写数据库结构
- 复杂动画系统
- 视觉上很重的品牌包装

深色模式本轮只要求：

- 在结构和样式层面预留未来适配空间
- 不要求本轮交付完整 dark theme

## 开始前先读

- [docs/implementation-handoff.md](docs/implementation-handoff.md)
- [docs/basic-design.md](docs/basic-design.md)
- [docs/development-plan.md](docs/development-plan.md)
- [README.md](README.md)

然后直接看这些实现文件：

- `src/writer/app/bootstrap.py`
- `src/writer/app/version.py`
- `src/writer/storage/repositories/settings_repository.py`
- `src/writer/services/ai/prompt_builder.py`
- `src/writer/ui/main_window.py`
- `src/writer/ui/panels/fragment_list_panel.py`
- `src/writer/ui/panels/editor_panel.py`
- `src/writer/ui/panels/project_panel.py`
- `src/writer/ui/panels/reference_library_panel.py`
- `src/writer/ui/dialogs/settings_dialog.py`
- `src/writer/ui/dialogs/rewrite_compare_dialog.py`
- 相关 UI / service tests

## 本轮总目标

请连续完成下面 6 个任务，并一次收口：

1. 建立可维护的中英双语基础设施
2. 重构主界面为更偏专注写作的布局
3. 建立自动 tag 配色系统并在多个界面复用
4. 增加一批高价值的小型 UX 改进
5. 统一并更新版本号到 `0.2.0-alpha.1`
6. 补齐回归测试并完成全量验证

不要把这轮做成纯视觉换皮。

## 任务 1：国际化基础设施（简体中文 / 英文）

### 目标

让应用所有内置 UI 文案都能在 English / 简体中文之间切换，并且后续继续加功能时不需要再到处散改字符串。

### 最低要求

1. 所有用户可见的内置界面字符串都不要再散落硬编码在各 UI 文件里
2. 至少覆盖：
   - 主窗口标题
   - 菜单栏与菜单项
   - 按钮
   - placeholder
   - 对话框标题与主要提示文案
   - 空状态文案
   - About 文案
   - 常见错误 / 提示文案
3. 语言配置持久化保存
4. 默认语言是 English
5. 在 Settings 中提供语言切换
6. 在主界面提供一个直接可见的语言切换入口
7. 允许切换后提示“重启应用后生效”，不要求运行时完全热切换
8. AI 动作的可见名称与默认 prompt 语言跟随当前界面语言

### 实现建议

你可以自由选择实现方式，但要满足可维护性：

- 可以使用轻量的 app-level translation service / string catalog
- 也可以使用 Qt 的翻译机制

但不要做成：

- 继续把英文字符串散在各 QWidget / QDialog 文件里
- 某些页面能切换，某些页面还是硬编码英文
- prompt_builder 继续假定只有英文默认文案

### 明确边界

本轮“可翻译”的是应用内置文案。

不需要翻译：

- 用户自己写的 fragment 内容
- 用户自定义 tag 名称
- 用户输入的 project / chapter / reference title

### 任务 1 必须补的测试

至少补这些测试：

1. 默认语言设置为 English
2. 语言设置可持久化保存和读取
3. 应用启动时能根据设置加载对应语言
4. 至少一个主界面入口和一个设置页入口在两种语言下都正确显示
5. prompt_builder 或等效层能根据当前语言选对默认 prompt 文案

## 任务 2：主界面 Shell 重构为“专注写作式”

### 当前问题

当前主界面还是较基础的两栏结构：

- 左侧 fragment list + 搜索 + new
- 右侧 editor

它功能上够用，但层级偏平，没有形成“默认进入写作状态”的体验。

### 本轮目标

把主界面改成更偏专注写作的结构，让编辑区成为默认视觉主角，同时不牺牲 search / tag / project / AI 的可达性。

### 建议方向

你不必机械照搬，但整体方向建议是：

- 默认主编辑区更宽、更安静
- 侧边区域可弱化、可收起、可记忆状态
- fragment / search / tags / recent shortcuts 仍要高可达
- project / reference / AI 等信息不应挤占默认写作面积

### 必须满足的行为要求

1. 新建 fragment 后，焦点和光标要落在最合理的位置，减少一次多余点击
2. 切换 fragment 时，编辑区状态和当前选中状态清晰
3. 搜索 / tag filter / project 相关入口不能因为重构而变深层难找
4. 如果使用 splitter / collapsible panel，宽度和折叠状态应持久化
5. 空列表、空搜索结果、空项目状态要比现在更清楚，不要只是空白

### 允许的设计自由度

你可以在这些方向里自行组合：

- 更像“主编辑区 + 可收起侧栏”
- 更像“专注编辑 + 辅助抽屉/面板”
- 用更明确的 section header、secondary text、toolbar hierarchy

但要避免：

- 做成信息量很重的企业后台
- 做成花哨但牺牲写作面积的 dashboard
- 动了布局却没有明显提升写作流畅度

## 任务 3：tag 颜色系统

### 目标

让 tag 从纯文本变成有辨识度但不过分抢眼的视觉元素，并且在整个产品里保持一致。

### 明确需求

1. tag 颜色自动分配
2. 同一个 tag 名在各处颜色一致
3. 不同 tag 应有稳定可重复的颜色映射
4. 配色要轻微点缀，不要高饱和乱跳
5. 至少覆盖这些位置：
   - 编辑区 tag 显示
   - fragment list 中的 tag / tag 标识
   - tag filter 下拉或等效筛选器
   - project / chapter / reference 等标签化元素

### 实现建议

- 可以基于 tag 名做 deterministic hashing，然后映射到一组经过人工挑选的浅色 token
- 尽量避免直接把随机 RGB 颜色塞进 UI

### 这里优先级要分清

本轮更重要的是：

- 一致
- 可读
- 不突兀

而不是：

- 支持复杂自定义调色盘
- 支持手工改色

### 任务 3 必须补的测试

至少补这些测试：

1. 同一 tag 返回稳定颜色
2. 不同 tag 至少会落到可区分 token 集合
3. 颜色映射函数对大小写或空白的处理规则明确且稳定

## 任务 4：一批“小巧思”级 UX 改进

这一块不要做成另一个大子系统，而是把当前最值钱的小改进集中落地。

### 本轮建议至少包含

1. 最近项目 / 最近标签快捷入口
2. 命令面板 / 快捷动作搜索（可做轻量版本，不必过度工程化）
3. 更聪明的自动聚焦与光标定位
4. splitter / panel 宽度记忆
5. 更清楚的空状态与新手引导

### 命令面板的最低标准

至少能快速触发这些常用动作中的大部分：

- new fragment
- search / focus search
- AI actions
- open projects
- open references
- open settings
- switch language

可以是轻量 dialog，不需要做成 VS Code 级别复杂系统。

### 动效要求

如果你加动效：

- 只允许细微过渡
- 时长要短
- 失败时要能优雅退化
- 不要让测试和可维护性变差很多

如果某些动效会明显拉高风险，可以优先做：

- 更好的状态反馈
- 更好的焦点管理
- 更好的层级和空状态

而不是硬上动画。

## 任务 5：版本与版本显示统一

这轮请把版本升级到：

- `0.2.0-alpha.1`

并顺手解决当前版本来源不完全统一的问题。

### 最低要求

1. `src/writer/app/version.py` 作为单一版本源
2. 启动 / About / 其他显示位置不要再各写一份版本号
3. README 如果有显式版本说明，也同步检查

如果你觉得这轮还适合补一个简洁的 `CHANGELOG.md`，可以加，但保持轻量。

## 任务 6：测试与验证

这轮是 UI / i18n / UX 改动较多的一轮，不能只靠肉眼。

### 至少要补或更新这些测试方向

1. 语言设置与启动加载
2. 关键 UI 在中英文下的基本显示
3. tag 颜色映射稳定性
4. 布局状态记忆
5. 命令面板（如果实现）最小交互
6. 任何因为文案 / 布局变化导致失效的 UI tests 全部修通

### 完成后至少做这些验证

- `D:\anaconda\envs\writer\python.exe -m pytest -q`
- 一次手工 smoke：
  - English 启动
  - 切中文并重启
  - 新建 fragment
  - 搜索 / tag filter
  - project / references / AI 入口都还能到达
  - tag 颜色可见且一致
  - About 版本显示正确

## 建议文件范围

本轮大概率会改这些文件：

- `src/writer/app/bootstrap.py`
- `src/writer/app/version.py`
- `src/writer/app/container.py`（如果需要注入 i18n / ui settings）
- `src/writer/storage/repositories/settings_repository.py`
- `src/writer/services/ai/prompt_builder.py`
- `src/writer/ui/main_window.py`
- `src/writer/ui/panels/fragment_list_panel.py`
- `src/writer/ui/panels/editor_panel.py`
- `src/writer/ui/panels/project_panel.py`
- `src/writer/ui/panels/reference_library_panel.py`
- `src/writer/ui/dialogs/settings_dialog.py`
- `src/writer/ui/dialogs/...` 下若干对话框
- `tests/ui/...`
- `tests/services/...`

也允许新增少量基础设施文件，例如：

- `src/writer/ui/i18n.py`
- `src/writer/ui/theme.py`
- `src/writer/ui/tag_colors.py`
- `src/writer/ui/dialogs/command_palette_dialog.py`

但请保持“薄而集中”，不要新建一个巨大的 UI framework。

## 建议执行顺序

请按这个顺序做：

1. 先把版本号目标和 i18n 方案定下来
2. 把字符串抽离与语言设置落地
3. 跑最小测试，确认 i18n 基础不炸
4. 再做 shell / layout 重构
5. 再落 tag 颜色系统
6. 再补小型 UX 改进
7. 修测试、跑全量验证

不要一开始同时把所有 UI 文件全推倒重来。

## 明确不接受的结果

下面这些结果不算完成：

- 只是把几处菜单改成中文，没建立可维护 i18n 结构
- 只是换样式表颜色，没有真正改进布局与交互
- tag 只是偶尔上色，但各处不一致
- 命令面板只是摆设，常用动作不能真正触发
- 版本号升级了，但 About / 启动显示仍然各写各的
- 文案切换做出来了，但测试大量失效或核心流程退化

## 汇报格式

完成后继续按这个格式汇报：

- 新增 / 修改文件
- i18n 方案如何实现
- shell / layout 如何重构
- tag 颜色系统如何做
- 哪些“小巧思”已落地
- 版本号如何统一到 `0.2.0-alpha.1`
- 验证结果
- 刻意未做

## 停止条件

这轮完成后停下，不要顺手继续做 AI chat 或 dark mode。

这轮的目标是把产品推进到一个更像“可持续打磨的写作软件”的状态：

- 双语可切换
- 主界面更像写作工具而不是初版原型
- tag 更有辨识度
- 常用操作更顺手
- 版本与 UI 基础更适合继续迭代

---