# Writer

[中文](README.zh-CN.md) · English

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)

**A calm, local-first writing studio for articles, anthologies, literary references, and bounded AI assistance.**

Writer is for writers who turn scenes, sentences, moods, notes, research, and half-formed ideas into complete articles. It keeps the desk quiet: your drafts stay local, articles can be arranged into collections, and AI only enters when you deliberately invite it.

> Status: **alpha, daily-usable, still moving fast**. The core writing flow, exports, version history, reference library, and AI workspace are working; the current focus is polish, writing feel, and better literary workflows.

## ✦ Product Overview

Writer combines an article library, article collections, a literary reference
library, and an AI workspace in one local desktop app. It is designed for
drafting essays or stories, collecting notes, arranging anthologies, and reviewing AI
suggestions before they touch the manuscript.

## ✅ What Works Today

| Area | Highlights |
| --- | --- |
| ✍️ Writing | Article editor, autosave, tags, sticky article notes, full-text search, version history, focus mode, typography controls |
| 📚 Collections | Multi-add articles, browse in reading order, drag-reorder, preview, TXT / Markdown / DOCX export |
| 🗂️ Reference library | Book-shelf browsing, source pages, literary quote cards, tag summaries, duplicate hints, and switchable stats views |
| 🤖 AI workspace | Polish, style-aware polish, expand, continue, summarize, outline, title ideas, structure diagnosis, consistency checks, library Q&A |
| 💬 Scoped chat | Article / collection / global chat scopes, persisted threads, context budget trimming |
| 🔐 Safety | Compare before accepting, checkpoints, snapshots before write-back, no stored raw AI keys |
| 🎨 Interface | Apple-style neutral light/dark themes, system-blue accent, tiered corners, line nav icons, calmer sticky notes |
| 🪟 Distribution | Windows portable zip, local PyInstaller build script, GitHub Actions build path |

## 🧭 Product TODO

- [x] Article-first writing desk
- [x] Article collections, reading preview, ordering, and export
- [x] Reading-order collection workflow with multi-add, drag reordering, and article-side collection membership
- [x] Version history and safe write-back snapshots
- [x] Visible checkpoint controls and version cleanup for recoverable writing sessions
- [x] GPT / OpenAI-compatible providers
- [x] Gemini API key and Gemini CLI / OAuth support
- [x] AI workspace with differentiated writing tools
- [x] Scoped AI chat with persisted local history
- [x] Reading-first literary reference library with collapsible stats, book shelves, source pages, duplicate hints, and tag browsing
- [x] Editor typography, focus mode, smoother motion, and typewriter comfort
- [x] Sticky fragment notes for next-session ideas, scene reminders, and AI reference context
- [x] Visual note board: pin, edit, mark done, change note colour / width, and arrange notes beside the page
- [x] Right-pane fragment note launcher that keeps the writing page free of note controls when notes are closed
- [x] Unified AI "Add context" menu for articles, literary specimens, and current article notes
- [x] Save selected AI chat text or the latest reply back into the current fragment as reusable notes
- [x] Fragment-note default-collapse setting for calmer fragment switching
- [x] UI polish: clearer toolbar controls, calmer scrollbars, and no-wheel form controls
- [x] Major UI refresh: Apple-style neutral palette, system-blue accent, line nav icons, tiered radii, and restrained motion
- [x] Collapsible right context pane controlled from the top toolbar
- [x] Longer default Gemini API and Gemini CLI / OAuth timeout for large writing prompts
- [ ] Public screenshot gallery and short demo videos
- [ ] Step-by-step video tutorials for common writing workflows
- [ ] Better onboarding for first-time writers
- [ ] Richer reference classification and saved custom library views
- [ ] Clickable AI reports that can locate or apply suggested edits
- [ ] More AI chat actions for turning conversation ideas into articles, notes, and reference material
- [ ] Beta release hygiene: signed builds, migration checks, and clearer release notes

## 🎬 Demos And Tutorials

Public screenshots, short walkthrough videos, and workflow demos are on the roadmap. They will show a clean demo project rather than private writing, so new users can quickly understand Writer's article, collection, reference-library, and AI-assisted revision flow.

## ⬇️ Download

The recommended public distribution format is a **Windows portable zip**.

- Latest alpha: [Writer-0.2.0-alpha.45-portable.zip](https://github.com/sidiangongyuan/writer/releases/download/v0.2.0-alpha.45/Writer-0.2.0-alpha.45-portable.zip)
- Release page: [v0.2.0-alpha.45](https://github.com/sidiangongyuan/writer/releases/tag/v0.2.0-alpha.45)
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
- **Gemini CLI / OAuth**: reuse an existing Gemini CLI OAuth login.

Gemini CLI / OAuth supports common text-generation presets such as:

- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

The model field remains editable, so compatible future text models can be tried without a code change. Media, embedding, Live API, robotics, and other specialized Gemini models usually need different request shapes and are not exposed as Writer presets.

For large prompts, Gemini API and Gemini CLI / OAuth wait up to 120 seconds by
default. Advanced users can override this with
`WRITER_GEMINI_TIMEOUT_SECONDS` or `WRITER_GEMINI_CLI_TIMEOUT_SECONDS`.

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
- [docs/screenshots/README.md](docs/screenshots/README.md) - demo media preparation notes

## 🤝 Contributing

Pull requests are welcome while the project is alpha. Please keep changes product-facing and avoid committing internal prompts, local test data, credentials, generated builds, or private writing samples.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, pull request expectations, and release hygiene.

CI runs the Windows Python 3.12 test suite with GitHub Actions: [.github/workflows/tests.yml](.github/workflows/tests.yml).

## License

Writer is released under the MIT License. See [LICENSE](LICENSE).
