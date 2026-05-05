# Writer

中文 · [English](README.md)

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)

**一个本地优先的写作桌面：收集片段，整理长文，管理参考资料，并在需要时让 AI 帮你改写。**

Writer 适合那些还没变成完整作品的东西：一句话、一个场景、一段氛围、一个人物设定、一组零散灵感。它先把这些东西安全地留在本地，再帮你把片段组织成作品、章节、合集，并在你主动调用时提供 AI 辅助。

> 状态：**alpha，可日常使用，但仍在快速迭代**。核心写作流、导出、版本历史、AI 工作区已经可用；稳定版之前还会继续打磨 UI 和打包体验。

## 为什么做 Writer？

- **先写片段**：快速记录短文本，再搜索、打标签、筛选和复用。
- **长文组织**：把片段放进作品、节块和作品集，最后导出成 TXT / Markdown / DOCX。
- **AI 不接管写作**：AI 结果先预览，写回前保留快照，不会悄悄覆盖原文。
- **本地优先**：SQLite 数据库在你的电脑上；API key 和 OAuth token 只在请求时读取。
- **Gemini OAuth**：复用本机 Gemini CLI 登录，切换 Gemini 3 / 2.5 文本模型，并查看档位 / 额度信息。
- **Windows 便携版**：提供 zip，解压后直接运行 `Writer.exe`。

## 现在能做什么？

| 模块 | 功能 |
| --- | --- |
| 写作 | 片段编辑、自动保存、标签、全文搜索、版本历史 |
| 长文 | 作品、节块排序、作品集、TXT / Markdown / DOCX 导出 |
| 参考资料 | 按人物、地点、设定、摘录管理参考素材 |
| AI 工作区 | 润色、扩写、续写、总结、提纲、风格迁移、资料库问答、上下文对话 |
| AI 提供方 | GPT / OpenAI 兼容接口、原生 Gemini API key、Gemini CLI / OAuth |
| 安全 | 接受前对比，写回前快照，不把原始 AI 密钥存进设置 |

## 截图

公开截图必须使用干净的演示数据，不能出现真实写作、账号、token、项目 ID、本机路径等信息。截图规范见 [docs/screenshots/README.md](docs/screenshots/README.md)。

## 下载

推荐的公开分发方式是 **Windows 便携 zip**。

- 如果已有 GitHub Release，在 release assets 里下载 `Writer-<version>-portable.zip`。
- 如果想试最新分支，可以使用 **Build Windows Portable** GitHub Action 生成的 artifact。
- 如果要本地自己打包，见 [从源码构建](#从源码构建)。

下载后解压，进入 `Writer` 文件夹，运行 `Writer.exe`。

## 从源码运行

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

## 从源码构建

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\path\to\python.exe
```

如果当前环境里的 `python` 已经正确：

```powershell
.\scripts\build_windows.ps1
```

构建产物：

- `dist\Writer\Writer.exe` — 解包后的便携应用
- `dist\Writer-<version>-portable.zip` — 用于发布的版本 zip
- `dist\Writer-portable.zip` — 本地测试用的稳定别名

## AI 设置

在应用里打开 **设置**，选择 AI 提供方：

- **GPT / OpenAI**：使用 `env:OPENAI_API_KEY`，或填写 OpenAI 兼容接口。
- **Gemini**：使用 `env:GEMINI_API_KEY`，或读取本机 `~/.gemini/.env`。
- **Gemini CLI / OAuth**：复用本机 Gemini CLI OAuth 登录；Writer 会在请求时刷新短期 access token，并直接调用 Gemini Code Assist。

Gemini CLI / OAuth 预设支持常见文本模型：

- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

模型输入框仍然可以手动编辑，所以 Google 发布兼容的新文本模型后，可以直接尝试。图片、视频、音频、embedding、Live API、robotics 等专用模型通常需要不同请求结构，因此不会放进 Writer 的文本写作预设里。

## 隐私与安全

Writer 本地优先，但你发给 AI 的文本仍会发送给对应 AI 提供方。如果内容敏感，请在运行 AI 任务前确认提示词和上下文。

仓库中不应该提交：

- 真实 API key
- OAuth access / refresh / ID token
- 账号邮箱或云项目 ID
- 本地 SQLite 数据库
- 私人写作内容
- 生成的 `dist/` 或 `build/` 产物

安全说明见 [SECURITY.md](SECURITY.md)。

## 路线图与更新记录

- [CHANGELOG.md](CHANGELOG.md) — 面向用户的更新记录
- [docs/roadmap.md](docs/roadmap.md) — alpha 到 beta 路线图
- [docs/ai-revision-workflow.zh-CN.md](docs/ai-revision-workflow.zh-CN.md) — AI 对比 / 修订工作流计划
- [docs/screenshots/README.md](docs/screenshots/README.md) — 截图规范

## 贡献

项目仍处于 alpha，欢迎 PR。请尽量保持仓库面向产品和用户，不要提交内部提示词、个人测试数据、凭据、构建产物或私人写作样本。

CI 会通过 GitHub Actions 在 Windows + Python 3.12 上运行测试：[.github/workflows/tests.yml](.github/workflows/tests.yml)。

## 许可证

Writer 使用 MIT License 开源。见 [LICENSE](LICENSE)。
