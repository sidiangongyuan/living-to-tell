# Writer

中文 · [English](README.md)

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)

**一个本地优先、安静克制的写作工作室：写文章，编作品集，管理文脉标本，并在需要时调用边界清晰的 AI 辅助。**

Writer 适合把日常灵感发展成完整文章：一句话、一个场景、一段氛围、一篇随笔或一组短篇。它先把文章安全地留在本地，再帮你把多篇文章编成作品集；AI 只在你主动调用时进入写作桌面。

> 状态：**alpha，可日常使用，仍在快速迭代**。核心写作流、导出、版本历史、文脉标本库和 AI 工作区已经可用；当前重点是 UI 质感、写作手感和更好的文学写作流程。

## ✦ 产品概览

Writer 把文章库、作品集、文脉标本库和 AI 工作区放在一个本地桌面应用里。
它可以用来写文章、收集灵感、编排合集、保存摘录，并在 AI 建议写入正文前进行审阅。

## ✅ 现在能做什么？

| 模块 | 功能 |
| --- | --- |
| ✍️ 写作 | 文章编辑、自动保存、标签、片段便签、全文搜索、版本历史、专注模式、字体设置 |
| 📚 作品集 | 多选加入文章、阅读预览、拖拽排序、TXT / Markdown / DOCX 导出 |
| 🗂️ 文脉标本库 | 书架浏览、书籍内页、精句卡片、标签速览、查重提示、可切换统计视图 |
| 🤖 AI 工作区 | 润色、按风格润色、扩写、续写、摘要、提纲、标题、结构诊断、一致性检查、资料库问答 |
| 💬 上下文对话 | 按文章 / 作品集 / 全局隔离对话，本地持久保存，并做上下文预算裁剪 |
| 🔐 安全机制 | 接受前对比，手动 checkpoint，写回前快照，不把原始 AI 密钥存进设置 |
| 🎨 界面 | 苹果风中性灰白皮肤、系统蓝强调色、层级化圆角、Fluent 线性导航图标、light / dark 双主题、克制的微交互 |
| 🪟 分发 | Windows 便携 zip、本地 PyInstaller 打包脚本、GitHub Actions 构建流程 |

## 🧭 产品 TODO

- [x] 文章优先的写作桌面
- [x] 文章作品集、阅读预览、排序和导出
- [x] 阅读编排式作品集：多选加入文章、拖拽排序、文章页显示所属作品集
- [x] 版本历史与写回前快照
- [x] 可见的 checkpoint 入口与版本清理能力，便于大改前后回溯
- [x] GPT / OpenAI 兼容接口
- [x] Gemini API key 与 Gemini CLI / OAuth
- [x] 差异化 AI 写作工具
- [x] 按作用域隔离并持久保存的 AI 对话
- [x] 阅读优先的文脉标本库：可折叠统计、书架浏览、书籍内页、查重提示和标签浏览
- [x] 编辑器字体、专注模式、轻量动效和打字机手感
- [x] 片段便签：记录灵感、场景提醒、未完成伏笔，并可作为 AI 参考
- [x] 可视化便签板：固定、编辑、划为完成、改颜色 / 宽度，并在正文旁整理摆放
- [x] 右侧信息栏片段便签入口，便签收起后不再占用正文页面空间
- [x] AI 统一“添加上下文”菜单，可添加文章、文脉标本和当前片段便签
- [x] AI 对话中的选中文字或最近回复可保存为当前片段便签，方便把讨论结果沉淀回写作桌面
- [x] 片段便签默认收起设置，切换片段时更安静
- [x] UI 质感优化：更清晰的工具栏、安静滚动条和防滚轮误改控件
- [x] 界面重大更新：苹果式中性灰白皮肤，系统蓝强调色，线性导航图标，层级化圆角，安静分区与精修的明暗双主题
- [x] 右侧信息栏可通过顶部工具栏收起，不再依赖拖动 splitter
- [x] Gemini API 与 Gemini CLI / OAuth 默认等待时间加长，降低长文本请求过早超时的概率
- [ ] 补齐公开截图、短视频演示和功能预览
- [ ] 常见写作流程的视频教程
- [ ] 新用户首次启动引导
- [ ] 更强的文脉标本分类与自定义视图
- [ ] AI 报告项支持定位原文或一键应用建议
- [ ] 更多 AI 对话动作：把讨论结果转为文章、便签或文脉材料
- [ ] Beta 发布准备：签名构建、迁移检查、更清晰的 release notes

## 🎬 演示与教程

公开截图、短视频 walkthrough 和写作流程演示已经列入计划。后续会用干净的演示项目展示 Writer 如何写文章、编作品集、管理文脉标本，以及如何在保留控制权的前提下使用 AI 辅助修订。

## ⬇️ 下载

推荐的公开分发方式是 **Windows 便携 zip**。

- 最新 alpha：[Writer-0.2.0-alpha.44-portable.zip](https://github.com/sidiangongyuan/writer/releases/download/v0.2.0-alpha.44/Writer-0.2.0-alpha.44-portable.zip)
- 发布页：[v0.2.0-alpha.44](https://github.com/sidiangongyuan/writer/releases/tag/v0.2.0-alpha.44)
- 如果想试最新分支，可以使用 **Build Windows Portable** GitHub Action 生成的 artifact。
- 如果要本地自己打包，见 [从源码构建](#从源码构建)。

下载后解压，进入 `Writer` 文件夹，运行 `Writer.exe`。

未签名的 alpha 版本可能触发 Windows SmartScreen 提示。运行前请确认压缩包来自本仓库 release assets。

## 📘 使用教程

- [中文使用教程](docs/user-guide.zh-CN.md)
- [English user guide](docs/user-guide.md)

## 🛠️ 从源码运行

要求：Windows + Python 3.12+。

```powershell
pip install -e .[dev]
writer
```

也可以这样启动：

```powershell
python -m writer.main
```

运行测试：

```powershell
python -m pytest
```

## 📦 从源码构建

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\path\to\python.exe
```

如果当前环境里的 `python` 已经正确：

```powershell
.\scripts\build_windows.ps1
```

构建产物：

- `dist\Writer\Writer.exe` - 解包后的便携应用
- `dist\Writer-<version>-portable.zip` - 用于发布的版本 zip
- `dist\Writer-portable.zip` - 本地测试用的稳定别名

## 🤖 AI 设置

在应用里打开 **设置**，选择 AI 提供方：

- **GPT / OpenAI**：使用 `env:OPENAI_API_KEY`，或填写 OpenAI 兼容接口。
- **Gemini**：使用 `env:GEMINI_API_KEY`，或读取本机 `~/.gemini/.env`。
- **Gemini CLI / OAuth**：复用本机 Gemini CLI OAuth 登录。

Gemini CLI / OAuth 预设支持常见文本模型：

- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

模型输入框仍然可以手动编辑，所以 Google 发布兼容的新文本模型后，可以直接尝试。图片、视频、音频、embedding、Live API、robotics 等专用模型通常需要不同请求结构，因此不会放进 Writer 的文本写作预设里。

长文本请求下，Gemini API 与 Gemini CLI / OAuth 默认最多等待 120 秒。高级用户可以通过
`WRITER_GEMINI_TIMEOUT_SECONDS` 或 `WRITER_GEMINI_CLI_TIMEOUT_SECONDS` 调整等待时间。

## 🔒 隐私与安全

Writer 本地优先，但你发给 AI 的文本仍会发送给对应 AI 提供方。如果内容敏感，请在运行 AI 任务前确认提示词和上下文。

仓库中不应该提交：

- 真实 API key
- OAuth access / refresh / ID token
- 账号邮箱或云项目 ID
- 本地 SQLite 数据库
- 私人写作内容
- 生成的 `dist/` 或 `build/` 产物

安全说明见 [SECURITY.md](SECURITY.md)。

## 🗺️ 路线图与更新记录

- [CHANGELOG.md](CHANGELOG.md) - 面向用户的更新记录
- [docs/roadmap.md](docs/roadmap.md) - alpha 到 beta 路线图
- [docs/todo.zh-CN.md](docs/todo.zh-CN.md) - 公开 TODO 列表
- [docs/screenshots/README.md](docs/screenshots/README.md) - 演示素材准备说明

## 🤝 贡献

项目仍处于 alpha，欢迎 PR。请尽量保持仓库面向产品和用户，不要提交内部提示词、个人测试数据、凭据、构建产物或私人写作样本。

开发环境、PR 要求和发布检查规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

CI 会通过 GitHub Actions 在 Windows + Python 3.12 上运行测试：[.github/workflows/tests.yml](.github/workflows/tests.yml)。

## 许可证

Writer 使用 MIT License 开源。见 [LICENSE](LICENSE)。
