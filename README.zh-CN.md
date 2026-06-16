<div align="center">

# Writer

### 本地优先的写作工作室：文章、作品集、文脉标本与边界清晰的 AI

中文 · [English](README.md) · [下载](https://github.com/sidiangongyuan/writer/releases/tag/tauri-v0.1.6)

[![Version](https://img.shields.io/badge/tauri%20preview-0.1.6-blue.svg)](tauri-mvp/CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/sidiangongyuan/writer/releases)
[![Built with Tauri](https://img.shields.io/badge/built%20with-Tauri%202-orange.svg)](https://tauri.app/)
[![Status](https://img.shields.io/badge/status-public%20preview-orange.svg)](tauri-mvp/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**写文章，编作品集，保存文脉标本，在不失去正文控制权的前提下使用 AI。**

[下载 Windows 预览版](https://github.com/sidiangongyuan/writer/releases/tag/tauri-v0.1.6) · [截图](#截图) · [功能](#功能) · [AI 设置](#ai-设置) · [路线图](#路线图--todo)

</div>

---

Writer 是一个面向长文本、片段、摘录和修订灵感的本地桌面写作应用。它把写作数据保存在本地，让你把文章编排成作品集，并把 AI 输出控制在“先审阅、再应用”的流程里。

## 一眼看懂

| | |
| --- | --- |
| **📝 文章工作台** | 写长文，自动保存，管理标签、搜索、题记、专注模式和导出。 |
| **📚 作品集** | 把多篇文章编排成合集，排序、预览，并导出成册。 |
| **🔖 文脉标本库** | 保存摘录、书名、作者、用途、笔记和可复制引用。 |
| **🤖 作用域 AI** | 对单篇文章、作品集或全局空间使用 AI 工具和持续对话。 |
| **🧠 AI Cards** | 保存可复用的风格、角色、场景卡片，作为后续提示词上下文。 |
| **🔒 本地优先** | 写作数据保存在本地，只有主动运行 AI 时才发送文本。 |

## 当前预览状态

| 模块 | 状态 |
| --- | --- |
| Windows 桌面应用 | ✅ 已公开预览 |
| 文章写作 | ✅ 可用 |
| 作品集 | ✅ 可用 |
| 文脉标本库 | ✅ 可用 |
| AI 工具与作用域对话 | ✅ 配置提供方后可用 |
| 深色模式 | 🚧 暂时隐藏，等待完整视觉打磨 |
| macOS / Linux 安装包 | 🗓️ Windows 稳定后评估 |

## 为什么用 Writer

| 如果你经常... | Writer 提供... |
| --- | --- |
| 写随笔、小说、札记、连载文章 | 文章编辑、自动保存、标签、搜索、题记和导出 |
| 想把多篇文章编成一个合集 | 作品集排序、预览和成册导出 |
| 阅读时保存好句和出处 | 按书籍或用途组织的文脉标本库 |
| 使用 AI 但担心误覆盖正文 | 作用域清晰的 AI 工具和对话，所有写回都需要主动操作 |
| 想要本地优先的写作流程 | 本地 SQLite 数据、显式 AI 请求、备份和 checkpoint |

## 截图

| 文章写作 | 专注模式 |
| :---: | :---: |
| ![文章写作](tauri-mvp/docs/assets/screenshots/article-writing.png) | ![专注模式](tauri-mvp/docs/assets/screenshots/focus-mode.png) |

| 作品集 | 文脉标本库 |
| :---: | :---: |
| ![作品集](tauri-mvp/docs/assets/screenshots/collections.png) | ![文脉标本库](tauri-mvp/docs/assets/screenshots/reference-library.png) |

| AI 工作区 | 设置 |
| :---: | :---: |
| ![AI 工作区](tauri-mvp/docs/assets/screenshots/ai-workspace.png) | ![设置](tauri-mvp/docs/assets/screenshots/settings.png) |

## 功能

### 写作

- 文章编辑、自动保存、标签、全文搜索、查找替换和可收起右侧上下文栏。
- 开头题记可单独编辑，并保持 Markdown、TXT、DOCX 导出干净。
- 专注模式只保留正文写作区和退出按钮。
- 日期页可查看每日写作记录，空日期可以直接开始写作。

### 作品集

- 从多篇文章创建作品集。
- 支持批量加入文章，拖拽排序，也保留上移 / 下移按钮。
- 右侧纸页预览当前文章。
- 按当前顺序导出 Markdown、TXT、DOCX。

### 文脉标本库

- 保存摘录正文、书名、作者、用途和个人笔记。
- 支持按书籍或按用途浏览。
- 日期页每日精句可跳到对应标本。
- 可复制正文，也可复制“正文 + 《书名》 + 作者”的完整引用。

### AI 工作区

- AI 工具支持润色、改写、扩写、续写、摘要、提纲和标题。
- 自由对话支持全局、单篇文章、作品集三个作用域；同一对象保留一条持续会话。
- AI Card 支持风格、角色、场景卡片，并可按类型、来源和关键词筛选。
- 支持 OpenAI 兼容接口、Codex 本地登录、Gemini API / 本地配置、Gemini CLI / OAuth。
- Writer 设置只保存凭据来源，不保存明文 API Key。

### 桌面体验

- Windows 桌面预览版提供简单安装包。
- 关闭按钮可设置为每次询问、最小化到托盘或直接退出。
- 公开预览版暂时只启用浅色模式；深色主题完整打磨后再开放入口。

## 下载

从 [GitHub Releases](https://github.com/sidiangongyuan/writer/releases/tag/tauri-v0.1.6) 下载最新公开预览版。

推荐 Windows 资产：

- `Writer_0.1.6_x64-setup.exe`

可选资产：

- `Writer_0.1.6_x64_en-US.msi`

预览版暂未签名，Windows SmartScreen 可能会提示风险。请只运行来自本仓库 Release 页的安装包。

## 快速开始

1. 从最新 Release 安装 Writer。
2. 打开“文章”，新建或选择一篇文章开始写。
3. 用“作品集”把多篇文章编成阅读顺序。
4. 用“文脉库”保存摘录和出处。
5. 如果需要 AI，在“设置”里配置提供方。

## AI 设置

打开设置，选择一个提供方：

- OpenAI 兼容接口：设置 Base URL / 模型，并使用 `env:OPENAI_API_KEY` 或 Codex 本地登录。
- Gemini API：使用 `env:GEMINI_API_KEY` 或导入本地 Gemini 配置。
- Gemini CLI / OAuth：复用本机 Gemini CLI 登录，不需要 API Key 输入框。

长文本 Gemini 请求默认等待 120 秒。高级用户可用 `WRITER_GEMINI_TIMEOUT_SECONDS` 或 `WRITER_GEMINI_CLI_TIMEOUT_SECONDS` 调整。

## 数据与隐私

- 写作数据保存在本地 SQLite 数据库。
- 只有主动运行 AI 工具或发送对话时，文本才会发给对应 AI 提供方。
- API Key 从环境变量或本地提供方配置读取。
- Writer 设置只保存提供方和凭据来源，不保存明文密钥。
- 大篇幅修改前建议先创建备份 / checkpoint。

## 最近完成

- Windows 公开预览版，包含文章写作、作品集、文脉标本和作用域 AI。
- 为主要写作、作品集、文脉库、AI 和设置界面补充了干净截图。
- 支持题记编辑、专注模式，以及 Markdown / TXT / DOCX 导出。
- 支持 AI 工具、作用域对话、AI Cards、Gemini 和 OpenAI 兼容配置。
- 日期写作页支持每日精句跳转和一键开始写作。

## 路线图 / TODO

公开 TODO 放在这里，但默认折叠，避免 README 太长。

<details>
<summary>展开详细 TODO 清单</summary>

### 首次使用体验

- [ ] 改进首次启动引导，覆盖语言、数据位置、备份和 AI 提供方设置。
- [ ] 增加示例项目，让新用户能快速理解完整工作流。
- [ ] 完整打磨深色主题后重新开放主题切换。

### 写作

- [ ] 增加适配紧凑、均衡、宽屏的编辑器布局预设。
- [ ] 改进日期、文章、作品集和 AI 工作区的纯键盘导航。
- [ ] 为高频写作者增加可选备份提醒。
- [ ] 增加更丰富的作品集出版选项，例如封面说明、分辑分隔和保存导出预设。

### AI

- [ ] 让 AI 结果写回更安全：更清晰地对比原文与结果，并提供明确的替换、插入、复制操作。
- [ ] 让润色、改写、扩写、续写拥有各自专属的关键控制项，而不是只换一个功能标题。
- [ ] 支持用户为每个写作工具保存自己的 prompt 预设。
- [ ] 为长文本请求增加更清晰的请求大小、等待时间和超时反馈。
- [ ] 更容易把 AI 对话里的灵感转成文章、便签或文脉材料。

### 知识与规划

- [ ] 后续加入思维图 / 意象合集空间，用来可视化组织主题、象征、意象、人物关系、论点、文脉标本和 AI 灵感。
- [ ] 为大型阅读摘录库增加更丰富的文脉库视图。

### 平台

- [ ] 增加 Windows 签名构建，或为预览版安装包提供公开校验信息。
- [ ] Windows 流程成熟后再评估 macOS 和 Linux 打包。
- [ ] 增加 AI 提供方设置排查页面。

</details>

完整列表见 [docs/todo.zh-CN.md](docs/todo.zh-CN.md)。

## 开发

开发命令见 [tauri-mvp/README.md](tauri-mvp/README.md)。

快速验证：

```powershell
D:\anaconda\envs\writer\python.exe -m pytest
cd tauri-mvp\frontend
npm test
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

## 许可证

Writer 使用 MIT License 开源，见 [LICENSE](LICENSE)。
