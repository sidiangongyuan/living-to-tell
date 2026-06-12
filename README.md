# Writer

<div align="center">

**A calm, local-first writing studio for turning fragments into finished work**

[中文](README.zh-CN.md) · English

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)
![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)

[Download Latest](#️-download) · [User Guide](docs/user-guide.md) · [Contributing](CONTRIBUTING.md)

</div>

---

## Why Writer?

Writer is for writers who work with **fragments** — scenes, sentences, notes, research, half-formed ideas — and need to **shape them into finished articles** without losing focus. 

Your drafts stay **local**. Articles can be arranged into **collections**. AI assistance is **bounded** — you review every suggestion before it touches your manuscript. No cloud sync, no subscription, no distraction.

> **Status:** Alpha, daily-usable, moving fast. Core writing flow is stable; current focus is UI modernization and cross-platform support.

### 🚀 What's New

**Active Development (June 2026):**
- 🎨 **Tauri + Vue UI Rewrite** - Migrating from Qt to modern web technologies for better layout stability and cross-platform support ([#tauri-mvp branch](https://github.com/sidiangongyuan/writer/tree/tauri-mvp))
- 🔧 Layout fixes and improved context pane reliability
- 📦 Smaller bundle size and faster startup (target: < 50MB vs current 150MB)

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

## ✨ Features

### 📝 Writing Flow
- **Fragment-first editing** - Capture ideas fast, organize later
- **Version history** - Safe snapshots before every major change
- **Focus mode** - Distraction-free writing with typography controls
- **Sticky notes** - Context for your future self, pinned beside the text
- **Full-text search** - Find any fragment instantly

### 📚 Organization
- **Collections** - Curate articles into reading-order anthologies
- **Multi-format export** - TXT, Markdown, DOCX with one click
- **Tag system** - Flexible categorization without rigid folders
- **Reference library** - Store quotes, sources, and research separately

### 🤖 AI Assistance (Bounded)
- **Compare before accepting** - Review every AI suggestion side-by-side
- **Scoped chat** - Conversations stay tied to articles or collections
- **Writing tools** - Polish, expand, summarize, outline, consistency checks
- **No stored keys** - API keys live in environment variables only

### 🎨 Interface
- **Apple-inspired design** - Neutral palette, system-blue accents, clean typography
- **Light/dark themes** - Respects your system preference
- **Three-column layout** - Navigation rail, main editor, collapsible context pane
- **Portable Windows app** - No installation, runs from a folder

---

## 🚧 Current TODO

**Near-term (Next 2 Weeks):**
- [ ] 🎨 Complete Tauri + Vue UI migration (in progress on `tauri-mvp` branch)
- [ ] 🐛 Fix context pane toggle reliability (root cause: Qt splitter constraints)
- [ ] 📦 Reduce bundle size from 150MB → <50MB
- [ ] 🎬 Add demo GIF to README showing three-column layout in action

**Mid-term (Next Month):**
- [ ] 📸 Public screenshot gallery and workflow videos
- [ ] 🎓 Step-by-step onboarding for first-time users
- [ ] 🍎 macOS build (enabled by Tauri migration)
- [ ] 🐧 Linux build (AppImage or .deb)

**Long-term Vision:**
- [ ] 🔄 Real-time sync (optional, user-controlled)
- [ ] 📱 Mobile companion app (read-only access)
- [ ] 🎯 Clickable AI reports that locate and apply suggested edits
- [ ] 🔐 Signed builds and auto-updates

<details>
<summary><b>✅ Completed Features (Click to expand)</b></summary>

- [x] Fragment-first writing desk with autosave
- [x] Article collections with reading-order preview
- [x] Version history and safe write-back snapshots
- [x] GPT / OpenAI-compatible providers
- [x] Gemini API key and Gemini CLI / OAuth support
- [x] AI workspace with bounded assistance tools
- [x] Scoped AI chat with persisted threads
- [x] Literary reference library with tag browsing
- [x] Focus mode and typography controls
- [x] Sticky fragment notes with visual board
- [x] Apple-style UI refresh (neutral palette, system-blue accent)
- [x] Collapsible context pane
- [x] Full-text search across all fragments

</details>

---

## ⬇️ Download

**Windows (Portable):**  
Latest stable: [Writer-0.2.0-alpha.45-portable.zip](https://github.com/sidiangongyuan/writer/releases/download/v0.2.0-alpha.45/Writer-0.2.0-alpha.45-portable.zip) (150MB)

- Extract the ZIP anywhere
- Run `Writer.exe` from the `Writer/` folder
- No installation required

> **Note:** Windows may show a SmartScreen warning for unsigned alpha builds. Verify the download comes from this repository's [release page](https://github.com/sidiangongyuan/writer/releases/tag/v0.2.0-alpha.45) before running.

**Other Platforms:**  
macOS and Linux builds coming soon (after Tauri migration). Track progress on the [`tauri-mvp`](https://github.com/sidiangongyuan/writer/tree/tauri-mvp) branch.

---

## 🚀 Quick Start

### Option 1: Run From Source (Developers)

**Requirements:** Windows, Python 3.12+

```powershell
# Install dependencies
pip install -e .[dev]

# Launch the app
writer

# Or use the module path
python -m writer.main
```

**Run tests:**
```powershell
python -m pytest
```

### Option 2: Build Portable Exe

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\path\to\python.exe
```

Outputs:
- `dist\Writer\Writer.exe` - Unpacked portable app
- `dist\Writer-<version>-portable.zip` - Versioned release archive

---

## 🛠️ Tech Stack

**Current (Qt Version):**
- **Frontend:** PySide6 (Qt 6) for desktop UI
- **Backend:** Python 3.12+ with SQLite
- **AI:** OpenAI API, Gemini API, Gemini CLI/OAuth
- **Packaging:** PyInstaller (Windows portable)

**In Progress (Tauri Migration):**
- **Frontend:** Tauri 2.0 + Vue 3 + Tailwind CSS
- **Backend:** FastAPI + existing Python repositories
- **Database:** Same SQLite schema (fully compatible)
- **Target:** Cross-platform (Windows, macOS, Linux), <50MB bundle

---

## 📘 Documentation

- [English User Guide](docs/user-guide.md) - Complete feature walkthrough
- [中文使用教程](docs/user-guide.zh-CN.md) - 完整功能说明
- [Contributing Guide](CONTRIBUTING.md) - Development setup and PR guidelines
- [Security Policy](SECURITY.md) - Reporting vulnerabilities
- [Roadmap](docs/roadmap.md) - Alpha-to-beta plan

---

## 🤖 AI Setup

Writer supports multiple AI providers. Open **Settings** in the app and configure:

**GPT / OpenAI:**
- Set `OPENAI_API_KEY` environment variable
- Or use any OpenAI-compatible endpoint

**Gemini:**
- **API Key:** Set `GEMINI_API_KEY` or create `~/.gemini/.env`
- **CLI/OAuth:** Reuse existing Gemini CLI login (no key needed)

**Supported Gemini models:**
- `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`
- `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-3.1-flash-lite-preview`

> **Timeout for large prompts:** Defaults to 120 seconds. Override with `WRITER_GEMINI_TIMEOUT_SECONDS` or `WRITER_GEMINI_CLI_TIMEOUT_SECONDS` environment variables.

---

## 🔒 Privacy & Security

Writer is **local-first** — your drafts stay on your machine. However:

- **AI providers** receive the text you send to them. Review prompts before running AI tasks.
- **No telemetry** - Writer does not phone home or track usage.
- **No stored keys** - API keys live in environment variables, never committed to disk.

**What Writer never stores in Git:**
- API keys or OAuth tokens
- Private writing content
- Local SQLite databases
- Build artifacts (`dist/`, `build/`)

See [SECURITY.md](SECURITY.md) for vulnerability reporting and contributor security guidelines.

---

## 🤝 Contributing

Pull requests are welcome! Writer is alpha and moving fast.

**How to help:**
- 🐛 Report bugs via [GitHub Issues](https://github.com/sidiangongyuan/writer/issues)
- 💡 Suggest features (please check [roadmap](docs/roadmap.md) first)
- 🔧 Submit PRs (see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines)
- 📖 Improve documentation

**Development setup:**
```powershell
git clone https://github.com/sidiangongyuan/writer.git
cd writer
pip install -e .[dev]
python -m pytest  # Run tests
```

CI runs Python 3.12 tests on Windows via [GitHub Actions](.github/workflows/tests.yml).

---

## 🗺️ Roadmap

**Alpha → Beta (2026 Q3-Q4):**
1. ✅ Core writing flow stable
2. ✅ Collections and reference library
3. 🚧 UI migration to Tauri (in progress)
4. ⏳ macOS and Linux builds
5. ⏳ Signed builds and auto-updates
6. ⏳ Public demo gallery

See [docs/roadmap.md](docs/roadmap.md) for detailed milestones.

---

## 📜 License

Writer is open source under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

Built with:
- [PySide6](https://doc.qt.io/qtforpython-6/) - Current Qt UI (being replaced)
- [Tauri](https://tauri.app/) - Next-gen cross-platform framework
- [Vue 3](https://vuejs.org/) - Reactive frontend
- [FastAPI](https://fastapi.tiangolo.com/) - Python backend API
- [SQLite](https://www.sqlite.org/) - Local database

---

<div align="center">

**[⬆ Back to top](#writer)**

Made with ❤️ for writers who think in fragments

</div>
