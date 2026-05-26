# Writer

[中文](README.zh-CN.md) · English

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)

**A calm, local-first writing studio for fragments, long-form drafts, literary references, and bounded AI assistance.**

Writer is for writers who collect scenes, sentences, moods, notes, research, and half-formed ideas before they know what the final work will become. It keeps the desk quiet: your drafts stay local, your fragments can grow into structured works, and AI only enters when you deliberately invite it.

> Status: **alpha, daily-usable, still moving fast**. The core writing flow, exports, version history, reference library, and AI workspace are working; the current focus is polish, writing feel, and better literary workflows.

## ✦ Why Writer?

| Principle | What it means |
| --- | --- |
| ✍️ Fragment first | Capture small pieces quickly, then tag, search, filter, and reuse them. |
| 📖 Long-form ready | Turn fragments into works, sections, collections, and exportable manuscripts. |
| 📚 Literary library | Browse saved passages by book-like shelves, read inside a source, and keep style specimens, character notes, setting details, and research material in one place. |
| 🤖 AI with boundaries | Polish, expand, continue, summarize, outline, diagnose structure, and ask the library without silent write-back. |
| 🔒 Local by default | Your SQLite database stays on your machine; API keys and OAuth tokens are read at request time. |
| 🪄 Built for feel | Typography controls, focus mode, typewriter scrolling, smoother transitions, and a quieter editor surface. |

## ✅ What Works Today

| Area | Highlights |
| --- | --- |
| ✍️ Writing | Fragment editor, autosave, tags, full-text search, version history, focus mode, typography controls |
| 📚 Works | Works, ordered sections, collections, TXT / Markdown / DOCX export |
| 🗂️ Reference library | Book-shelf browsing, source pages, literary quote cards, tag summaries, duplicate hints, and switchable stats views |
| 🤖 AI workspace | Polish, style-aware polish, expand, continue, summarize, outline, title ideas, structure diagnosis, consistency checks, library Q&A |
| 💬 Scoped chat | Fragment / work / collection / global chat scopes, persisted threads, context budget trimming |
| 🔐 Safety | Compare before accepting, snapshots before write-back, no stored raw AI keys |
| 🪟 Distribution | Windows portable zip, local PyInstaller build script, GitHub Actions build path |

## 🧭 Product TODO

- [x] Fragment-first writing desk
- [x] Works, sections, collections, and export
- [x] Version history and safe write-back snapshots
- [x] GPT / OpenAI-compatible providers
- [x] Gemini API key and Gemini CLI / OAuth support
- [x] AI workspace with differentiated writing tools
- [x] Scoped AI chat with persisted local history
- [x] Literary reference library with book shelves, source pages, duplicate hints, tag-based browsing, and switchable stats
- [x] Editor typography, focus mode, smoother motion, and typewriter comfort
- [ ] Public screenshot gallery and short demo videos
- [ ] Step-by-step video tutorials for common writing workflows
- [ ] Better onboarding for first-time writers
- [ ] Richer reference classification and saved custom library views
- [ ] Clickable AI reports that can locate or apply suggested edits
- [ ] Beta release hygiene: signed builds, migration checks, and clearer release notes

## 🎬 Demos And Tutorials

Public screenshots, short walkthrough videos, and workflow demos are on the roadmap. They will show a clean demo project rather than private writing, so new users can quickly understand Writer's fragment-to-work, reference library, and AI-assisted revision flow.

## ⬇️ Download

The recommended public distribution format is a **Windows portable zip**.

- Latest alpha: [Writer-0.2.0-alpha.18-portable.zip](https://github.com/sidiangongyuan/writer/releases/download/v0.2.0-alpha.18/Writer-0.2.0-alpha.18-portable.zip)
- Release page: [v0.2.0-alpha.18](https://github.com/sidiangongyuan/writer/releases/tag/v0.2.0-alpha.18)
- If you are testing the latest branch, use the **Build Windows Portable** GitHub Action artifact.
- To build locally, run the packaging command in [Build from source](#build-from-source).

After downloading, unzip the archive and launch `Writer.exe` inside the `Writer` folder.

Windows may show a SmartScreen warning for unsigned alpha builds. Verify that the archive comes from this repository's release assets before running it.

## 📘 User Guide

- [English user guide](docs/user-guide.md)
- [中文使用教程](docs/user-guide.zh-CN.md)

## 🛠️ Quick Start From Source

Requirements: Windows + Python 3.12+.

```powershell
pip install -e .[dev]
writer
```

Alternative launch command:

```powershell
python -m writer.main
```

Run tests:

```powershell
python -m pytest
```

## 📦 Build From Source

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\path\to\python.exe
```

If your active environment already has the correct Python on `PATH`:

```powershell
.\scripts\build_windows.ps1
```

Build outputs:

- `dist\Writer\Writer.exe` - unpacked portable app
- `dist\Writer-<version>-portable.zip` - versioned zip for releases
- `dist\Writer-portable.zip` - stable alias for local testing

## 🤖 AI Setup

Open **Settings** in the app and choose an AI provider:

- **GPT / OpenAI**: use `env:OPENAI_API_KEY` or another OpenAI-compatible endpoint.
- **Gemini**: use `env:GEMINI_API_KEY` or a local `~/.gemini/.env` file.
- **Gemini CLI / OAuth**: reuse an existing Gemini CLI OAuth login; Writer refreshes a short-lived access token at request time and calls Gemini Code Assist directly.

Gemini CLI / OAuth supports common text-generation presets such as:

- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

The model field remains editable, so compatible future text models can be tried without a code change. Media, embedding, Live API, robotics, and other specialized Gemini models usually need different request shapes and are not exposed as Writer presets.

## 🔒 Privacy And Security

Writer is local-first, but AI providers still receive the text you send to them. Review prompts before running AI tasks if your writing is sensitive.

Writer should never commit or store in Git:

- real API keys
- OAuth access / refresh / ID tokens
- account emails or cloud project IDs
- local SQLite databases
- private writing content
- generated `dist/` or `build/` artifacts

See [SECURITY.md](SECURITY.md) for reporting and contributor rules.

## 🗺️ Roadmap And Changelog

- [CHANGELOG.md](CHANGELOG.md) - product-facing release history
- [docs/roadmap.md](docs/roadmap.md) - alpha-to-beta roadmap
- [docs/todo.md](docs/todo.md) - public TODO list
- [docs/ai-revision-workflow.md](docs/ai-revision-workflow.md) - planned AI compare / revision workflow
- [docs/screenshots/README.md](docs/screenshots/README.md) - demo media preparation notes

## 🤝 Contributing

Pull requests are welcome while the project is alpha. Please keep changes product-facing and avoid committing internal prompts, local test data, credentials, generated builds, or private writing samples.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, pull request expectations, and release hygiene.

CI runs the Windows Python 3.12 test suite with GitHub Actions: [.github/workflows/tests.yml](.github/workflows/tests.yml).

## License

Writer is released under the MIT License. See [LICENSE](LICENSE).
