<div align="center">

# 活着为了讲述

### 本地优先的写作工作室：文章、作品集、文脉标本与边界清晰的 AI

中文 · [English](README.md) · [下载](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.26)

[![Version](https://img.shields.io/badge/preview-0.1.26-blue.svg)](tauri-mvp/CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/sidiangongyuan/living-to-tell/releases)
[![Built with Tauri](https://img.shields.io/badge/built%20with-Tauri%202-orange.svg)](https://tauri.app/)
[![Status](https://img.shields.io/badge/status-public%20preview-orange.svg)](tauri-mvp/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**写作、拍照、唱歌、讲话，都是为了讲述。活着，就是为了讲述。**

[下载 Windows 预览版](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.26) · [官方手册](docs/user-guide.zh-CN.md) · [GIF 教程](docs/tutorials.zh-CN.md) · [截图](#截图) · [功能](#功能) · [AI 设置](#ai-设置) · [路线图](#路线图--todo)

</div>

---

活着为了讲述（Living to Tell）是一个面向长文本、片段、摘录、修订灵感和 AI 辅助写作的本地桌面应用。它把写作数据库保存在本机，让你把文章编排成作品集，并把 AI 输出控制在“先审阅、再应用”的流程里。

## 一眼看懂

| | |
| --- | --- |
| **文章工作台** | 写长文，自动保存，管理标签、搜索、题记、专注模式、文章便签、历史版本和导出。 |
| **作品集** | 把多篇文章编排成合集，也能在作品集层面规划长篇项目大纲、看板、进度、筛选并导出大纲。 |
| **文脉标本库** | 保存摘录、书名、作者、用途、笔记和可复制引用。 |
| **文章 AI** | 使用 AI 工具、文章对话和多模型结果对比，所有写回都需要明确确认。 |
| **AI Cards** | 保存可复用的风格、人物、场景卡片，支持固定模板和 AI 草稿生成。 |
| **意象星图** | 把选中文字标记为意象，回到原文锚点，查看共现关系，并用 AI 丰富抽象概念。 |
| **导出与备份** | 查看恢复点、本地数据路径、备份/检查点、存储目录、备份提醒，并导出最近文章或作品集。 |
| **本地优先** | 写作数据保存在本地，只有主动运行 AI 时才发送文本。 |

## 当前预览状态

| 模块 | 状态 |
| --- | --- |
| Windows 桌面应用 | 已公开预览 |
| 文章写作 | 可用 |
| 作品集 | 可用 |
| 文脉标本库 | 可用 |
| 文章 AI 工具与对话 | 配置提供方后可用 |
| 意象星图 | 预览可用 |
| 数据目录迁移 | 可在设置中使用 |
| 深色模式 | 暂时隐藏，等待完整视觉打磨 |
| macOS / Linux 安装包 | Windows 稳定后评估 |

## 截图

想按步骤看完整写作主链路，可以先打开 [GIF 教程](docs/tutorials.zh-CN.md)。它覆盖示例项目、文章写作、作品集规划、文脉与意象、AI 与 AI Cards、导出与备份。

| 文章写作 | 专注模式 |
| :---: | :---: |
| ![文章写作](tauri-mvp/docs/assets/screenshots/article-writing.png) | ![专注模式](tauri-mvp/docs/assets/screenshots/focus-mode.png) |

| 作品集 | 文脉标本库 |
| :---: | :---: |
| ![作品集](tauri-mvp/docs/assets/screenshots/collections.png) | ![文脉标本库](tauri-mvp/docs/assets/screenshots/reference-library.png) |

| AI 工作区 | 设置 |
| :---: | :---: |
| ![AI 工作区](tauri-mvp/docs/assets/screenshots/ai-workspace.png) | ![设置](tauri-mvp/docs/assets/screenshots/settings.png) |

| 首次使用清单 | 导出与备份 |
| :---: | :---: |
| ![首次使用清单](tauri-mvp/docs/assets/screenshots/dates-onboarding.png) | ![导出与备份中心](tauri-mvp/docs/assets/screenshots/backup-center.png) |

## 功能

### 写作

- 文章编辑、自动保存、标签、全文搜索、查找替换和可收起右侧上下文栏。
- 文章便签用于记录提醒、片段和下一步想法，不进入正文。
- 文章历史版本支持手动保存、AI 写回前快照、恢复前快照、段落对比、恢复、克隆、复制和删除。
- 开头题记可单独编辑，并保持 Markdown、TXT、DOCX 导出干净。
- 专注模式只保留正文写作区和退出按钮。
- 日期页可查看每日写作记录，空日期可以直接开始写作。

### 作品集

- 从多篇文章创建作品集。
- 支持批量加入文章，拖拽排序，也保留上移 / 下移按钮。
- 右侧纸页预览当前文章。
- 可切到“大纲”标签，在作品集层面规划长篇项目，支持分部、章节、场景、笔记。
- 大纲项可记录状态、摘要、视角、时间线、场景地点、标签、目标字数和关联文章。
- 可切到“规划看板”，按构思、草稿、修订、完成、暂停查看整个长篇项目的结构状态。
- 可从大纲项一键创建文章，也可以把已有文章关联到大纲。
- 按当前顺序导出 Markdown、TXT、DOCX。

### 文脉标本库

- 保存摘录正文、书名、作者、用途和个人笔记。
- 支持按书籍或按用途浏览。
- 日期页每日精句可跳到对应标本。
- 可复制正文，也可复制“正文 + 《书名》 + 作者”的完整引用。

### 意象星图

- 在文章或文脉正文中选中文字后右键，保存到一个或多个意象。
- 再次打开同一句话时会回填已加入意象，不重复创建摘录。
- 文章右侧意象锚点可跳回原文句子。
- 星图用节点大小、颜色和连线表达摘录数量与意象共现关系。
- 右侧详情支持 **AI 丰富**，可把“神话模式”“奴隶道德”“常人”等概念生成可保存的写作短卡。
- 在某个意象下移除摘录时，只解除当前意象链接，不误删其他意象里的同一摘录。

### AI 工作区

- 润色、改写、扩写、续写拥有各自专属控件。
- 文章对话为每篇文章保留一条持续会话。
- AI 回复可复制，也可以保存为当前文章便签；保存为文脉标本或新文章前会先打开预览确认。
- 常驻指令可保存长期风格偏好，不需要每次重新输入。
- AI 结果先预览，再通过明确的替换、插入、复制动作写回。
- 长文本请求会显示字数、段落、估算 token 和模型数量，并在模型运行时显示真实等待状态。
- AI 工具可用最多三个已保存配置档案并行运行同一任务，对比字数、段落、耗时、token 和成本信息，再手动选择胜出结果。
- 支持为每个写作工具保存个人 prompt 预设。
- AI Card 支持风格、人物、场景卡片，提供固定模板、AI 草稿生成、类型筛选和关键词搜索。
- 场景模块可在 AI 工具中手动搜索并勾选调用，只有确认选择后才会进入本轮上下文。
- 支持 OpenAI 兼容接口、Codex 本地登录、Gemini API / 本地配置、Gemini CLI / OAuth 和 OpenCode 本地登录。

### 桌面体验

- Windows 桌面预览版提供简单安装包。
- 冷启动时显示浅色启动反馈窗口，后台启动时不会黑屏等待。
- 首次使用清单可以显式创建一个可删除的示例项目，包含文章、作品集大纲、文脉标本、文章便签和场景 AI Card。示例项目不会自动创建，删除时不会按标题或标签清理用户内容。
- 应用会在启动后后台检查 GitHub Releases，发现新版本时会显示清晰的更新提示。
- 关闭按钮可设置为每次询问、最小化到托盘或直接退出。
- 导出与备份中心优先展示恢复点：可查看最新备份/检查点状态、选择恢复点、设置备份提醒；恢复前仍会自动备份当前数据库。
- 设置中的“数据与存储”会显示当前 SQLite 数据库、备份目录、检查点目录和自定义目录状态。
- 数据目录迁移采用复制方式，新旧目录都会保留。
- 公开预览版暂时只启用浅色模式；深色主题完整打磨后再开放入口。

## 下载

从 [GitHub Releases](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.26) 下载最新公开预览版。

推荐 Windows 资产：

- `LivingToTell_0.1.26_x64-setup.exe`

可选资产：

- `LivingToTell_0.1.26_x64_zh-CN.msi`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 快速开始

1. 从最新 Release 安装活着为了讲述。
2. 按 [官方手册](docs/user-guide.zh-CN.md) 完成安装、数据路径和备份检查。
3. 在日期页欢迎清单里创建第一篇文章、检查备份，或创建可选示例项目。
4. 如果想快速理解完整流程，先看 [GIF 教程](docs/tutorials.zh-CN.md) 的 6 条主链路。
5. 打开“文章”开始写作，或打开示例作品集查看完整长篇工作流。
6. 用“作品集”把多篇文章编成阅读顺序并规划大纲。
7. 用“文脉库”保存摘录和出处。
8. 如果需要 AI，在“设置”里配置提供方。

## AI 设置

打开设置，选择一个提供方：

- OpenAI 兼容接口：设置 Base URL / 模型，选择正确的接口协议，并使用 `env:OPENAI_API_KEY` 或 Codex 本地登录。
- Gemini API：使用 `env:GEMINI_API_KEY` 或导入本地 Gemini 配置。
- Gemini CLI / OAuth：复用本机 Gemini CLI 登录，不需要 API Key 输入框。
- OpenCode：复用本机 `opencode auth login` 登录状态，不需要 API Key 输入框；设置页可以真实获取当前 OpenCode 模型列表。

如果要做多模型对比，在 **AI 配置档案 → 扫描本机配置** 中查找本机 OpenCode、Codex/OpenAI、Gemini 配置，并一键导入为可选档案。扫描只确认本机配置和凭据来源存在；远端模型是否真的可用，请用 **发送真实测试请求** 验证。

OpenCode 的模型获取是实时调用。本机当前 OpenCode 可拉取的模型包括：

- `opencode/big-pickle`
- `opencode/deepseek-v4-flash-free`
- `opencode/mimo-v2.5-free`
- `opencode/nemotron-3-ultra-free`
- `opencode/north-mini-code-free`

设置页把 **检查本地配置** 和 **发送真实测试请求** 分开。前者只检查本地凭据来源是否可用；后者会发送一条短示例请求，真实验证 provider、model、base URL、key 和内部 transport。

如果 Gemini 使用 `sk-...` 形态的中转 key 且配置了自定义 Base URL，应用会自动走中转兼容的 `/v1/chat/completions` transport，但用户层面仍保持 Gemini provider。

长文本 Gemini 请求默认等待 120 秒。高级用户可用 `WRITER_GEMINI_TIMEOUT_SECONDS` 或 `WRITER_GEMINI_CLI_TIMEOUT_SECONDS` 调整。

## 数据与隐私

- 写作数据默认保存在本机 SQLite：`%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`。
- Windows 安装器通常把程序文件放在 `%LOCALAPPDATA%\活着为了讲述`；这和写作数据库不是同一个目录。
- 卸载应用不会删除文章数据库、备份或检查点。
- 可在 **设置 → 数据与存储** 查看、打开并安全迁移数据目录。迁移只复制数据，新旧目录都会保留。
- 首次启动时，如果存在旧 Writer 数据库 `%APPDATA%\Writer\Writer\writer.sqlite3`，会复制到新目录；旧数据库保留不删除。
- 只有主动运行 AI 工具或发送对话时，文本才会发给对应 AI 提供方。
- API Key 从环境变量或本地提供方配置读取。
- 设置只保存提供方和凭据来源，不保存明文密钥。
- 大篇幅修改前建议先创建备份 / checkpoint。

## 最近完成

- 公开品牌改为活着为了讲述 / Living to Tell。
- 增加文章历史版本：手动检查点、AI 写回前保护、段落对比、恢复、克隆、复制和删除。
- 增加作品集层面的“大纲”标签，用于长篇项目规划、场景卡片和关联文章。
- 增加意象星图：右键选文加入意象、原文锚点、共现关系、重复摘录合并和安全解绑。
- 增加文章级 AI 对话、常驻指令、复制回复和保存为文章便签。
- 增加首次使用清单、AI 设置诊断、长文本请求反馈和分组式全局命令面板。
- 增加显式、可删除的示例项目，用文章、作品集大纲、文脉标本、文章便签和场景 AI Card 展示完整工作流，不自动污染用户数据。
- 扩展导出与备份中心：恢复点选择、安全摘要、数据路径、备份提醒和最近文章/作品集导出集中在一处。
- 增强作品集大纲，增加按状态分组的“规划看板”，更适合长篇项目总览。
- 增强文脉库总览和当前分组摘要，可查看来源数、疑似重复、用途分布和字数。
- 增加 AI 对话保存预览，AI 回复可确认后保存为文脉标本或新文章。
- 升级 AI Cards 为风格 / 人物 / 场景三类模板，增加 AI 草稿生成和 AI 工具中的场景模块手动调用。
- 增加 AI 配置档案和 AI 工具多模型对比，可查看每个结果的统计信息并手动选择胜出结果后再写回。
- 增加 OpenCode 本地登录支持、OpenCode 模型实时获取和统一 AI provider 链路下的 OpenCode 真实测试请求。
- 增加真实 AI 连通测试，并修复 Gemini 中转 key 在自定义 Base URL 下的 transport 选择。
- 增加“数据与存储”设置，可查看数据路径、打开目录并用复制迁移方式切换位置。
- 增加 Tauri 启动反馈窗口，冷启动时不再是黑屏等待。
- 隐藏卸载时删除应用数据的危险入口，并明确卸载不会删除写作数据库。
- 支持文章便签、细化 AI 写作控件、每功能预设和明确的 AI 写回操作。
- 修复文章上次位置恢复，优化长文文末写作的舒适空白和正文宽度。
- 日期写作页支持每日精句跳转和一键开始写作。
- 修复关闭按钮，支持原生询问、最小化到托盘或直接退出。

## 路线图 / TODO

公开 TODO 放在这里，但默认折叠，避免 README 太长。

<details>
<summary>展开详细 TODO 清单</summary>

### 首次使用体验

- [x] 增加读取本机状态的首次使用清单，不创建示例数据。
- [ ] 改进首次启动引导，覆盖语言、数据位置、备份和 AI 提供方设置。
- [x] 增加示例项目，让新用户能快速理解完整工作流。
- [ ] 完整打磨深色主题后重新开放主题切换。

### 写作

- [x] 增加文章便签，用来在当前文章旁记录零散灵感。
- [x] 恢复文章上次编辑位置，并优化长文文末写作体验。
- [x] 增加文章历史版本，支持恢复和克隆。
- [ ] 增加适配紧凑、均衡、宽屏的编辑器布局预设。
- [ ] 改进日期、文章、作品集和 AI 工作区的纯键盘导航。
- [x] 增加作品集层面的长篇项目大纲规划。
- [x] 增加作品集规划看板，用于按状态查看长篇项目结构。
- [ ] 增加更丰富的作品集出版选项，例如封面说明、分辑分隔和保存导出预设。

### AI

- [x] 让 AI 结果写回更安全：更清晰地对比原文与结果，并提供明确的替换、插入、复制操作。
- [x] 让润色、改写、扩写、续写拥有各自专属的关键控制项。
- [x] 支持用户为每个写作工具保存自己的 prompt 预设。
- [x] 增加文章级 AI 对话、常驻指令和保存回复为文章便签。
- [x] 增加风格 / 人物 / 场景 AI Cards 固定模板与 AI 草稿生成。
- [x] 增加场景模块搜索和手动勾选调用。
- [x] 增加真实 AI 连通测试，显示 provider、model、transport 和响应预览。
- [x] 增加 OpenCode 本地登录支持，并支持实时获取 OpenCode 模型列表。
- [x] 为长文本请求增加更清晰的请求大小、等待时间和超时反馈。
- [x] 更容易把 AI 对话里的灵感转成文章、便签或文脉材料。

### 知识与规划

- [x] 增加意象星图，用来可视化组织反复出现的意象、象征和来源摘录。
- [x] 增加紧凑的文脉库总览和当前分组摘要。
- [ ] 后续增加更丰富的图谱视图，用来组织主题、人物关系、论点、文脉标本和 AI 灵感。
- [ ] 为大型阅读摘录库增加更丰富的文脉库视图。

### 平台

- [x] 增加可见的数据与存储设置，并支持复制式数据目录迁移。
- [x] 扩展导出与备份中心，支持恢复点选择、安全摘要、路径展示和备份提醒。
- [x] 卸载默认不删除写作数据。
- [ ] 后续推出可选云同步，让需要多设备写作的人可以同步同一个本地优先工作区。
- [ ] 增加 Windows 签名构建，或为预览版安装包提供公开校验信息。
- [ ] Windows 流程成熟后再评估 macOS 和 Linux 打包。
- [ ] 增加 AI 提供方设置排查页面。

</details>

完整列表见 [docs/todo.zh-CN.md](docs/todo.zh-CN.md)。

## 开发

开发命令见 [tauri-mvp/README.md](tauri-mvp/README.md)。

快速验证：

```powershell
python -m pytest
cd tauri-mvp\frontend
npm test
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

## 许可证

MIT License，见 [LICENSE](LICENSE)。
