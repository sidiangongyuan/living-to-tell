<div align="center">

# Living to Tell Tauri Preview

### The current Windows desktop preview for 活着为了讲述 / Living to Tell

[![Version](https://img.shields.io/badge/version-0.1.7-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/sidiangongyuan/living-to-tell/releases)
[![Built with Tauri](https://img.shields.io/badge/built%20with-Tauri%202-orange.svg)](https://tauri.app/)
[![Status](https://img.shields.io/badge/status-preview-orange.svg)](#download)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

[Download](#download) · [Screenshots](#screenshots) · [Features](#features) · [Development](#development)

</div>

Living to Tell is a calm desktop app for writing articles, arranging them into collections, saving reference passages, and using AI without giving up control of the manuscript.

The Tauri preview is the current public direction. It uses a Vue frontend, a bundled FastAPI sidecar, and a local SQLite database.

## Screenshots

| Article Writing | Focus Mode |
| :---: | :---: |
| ![Article writing](docs/assets/screenshots/article-writing.png) | ![Focus mode](docs/assets/screenshots/focus-mode.png) |

| Collections | Reference Library |
| :---: | :---: |
| ![Collections](docs/assets/screenshots/collections.png) | ![Reference library](docs/assets/screenshots/reference-library.png) |

| AI Workspace | Settings |
| :---: | :---: |
| ![AI workspace](docs/assets/screenshots/ai-workspace.png) | ![Settings](docs/assets/screenshots/settings.png) |

## Features

### Writing

- Article editor with autosave, tags, full-text search, find/replace, and a collapsible context pane.
- Article notes live beside the current article without entering the manuscript.
- Epigraphs can be edited as a separate section at the top of an article.
- Focus mode hides the surrounding interface and leaves only the writing area.
- Single-article export to Markdown, TXT, and DOCX.
- Date view for browsing daily writing activity, with a direct start-writing action on empty days.

### Collections

- Create article collections and add multiple articles at once.
- Drag to reorder articles, or use up/down controls as a fallback.
- Preview the selected article in a paper-like reading pane.
- Export a collection in Markdown, TXT, or DOCX using the current order.

### Reference Library

- Save reference passages with source title, author, usage type, and personal notes.
- Browse by source book or usage.
- Jump from the daily quote card to the matching reference passage.
- Copy just the passage body, or copy a complete citation with title and author.

### AI

- Focused AI tools for polishing, rewriting, expanding, and continuing.
- Per-tool personal presets.
- AI results are reviewed before writing back, with explicit replace, insert, and copy actions.
- Free chat tab with one ongoing conversation per global scope, article, or collection.
- AI Cards for style, character, and setting context, with type/source filters and keyword search.
- Supports OpenAI-compatible APIs, Codex local auth, Gemini API/local config, and Gemini CLI / OAuth.
- Raw API keys are not stored in app settings; only the selected credential source is saved.

### Desktop

- Windows installer builds with a bundled Python backend sidecar.
- Release builds discover the sidecar port automatically, so users do not need to run a backend manually.
- Close behavior can be set to ask every time, minimize to tray, or exit directly.
- Public preview uses light mode only; dark mode code remains available for a later full theme pass.

## Download

Download the latest public preview from [GitHub Releases](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.7).

Recommended Windows asset:

- `LivingToTell_0.1.7_x64-setup.exe`

Optional asset:

- `LivingToTell_0.1.7_x64_zh-CN.msi`

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## Quick Start

1. Install Living to Tell from the latest Release.
2. Open the app and go to Articles.
3. Create or select an article and start writing.
4. Use Collections to arrange multiple articles into a reading order.
5. Use the Reference Library to save quotes and source material.
6. Configure AI in Settings if you want AI tools or scoped chat.

## AI Setup

Open Settings and choose one provider:

- OpenAI-compatible: set a base URL/model and use `env:OPENAI_API_KEY` or Codex local auth.
- Gemini API: use `env:GEMINI_API_KEY` or import local Gemini configuration.
- Gemini CLI / OAuth: reuse a local Gemini CLI login. No API key field is required.

Long Gemini requests default to a 120 second wait. Advanced users can tune this with `WRITER_GEMINI_TIMEOUT_SECONDS` or `WRITER_GEMINI_CLI_TIMEOUT_SECONDS`.

## Data & Privacy

- Writing data is stored locally in SQLite at `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3` by default.
- The Windows installer usually places app files under `%LOCALAPPDATA%\活着为了讲述`; this is separate from your writing database.
- Uninstalling the app does not delete the writing database, backups, or checkpoints.
- Use **Settings → Data and Storage** to open or migrate the data directory. Migration copies data and keeps the old folder intact.
- First launch copies old Writer data from `%APPDATA%\Writer\Writer\writer.sqlite3` into the new location if it exists. The old database is retained.
- AI requests are sent only when you run an AI tool or send a chat message.
- API keys are read from environment variables or local provider configuration at runtime.
- Settings store the selected provider and credential source, not raw API keys.
- Use backups/checkpoints before major editing or migration tests.

## Development

Requirements:

- Windows
- Python 3.12 or a compatible local environment
- Node.js 20+
- Rust stable

Run the backend:

```powershell
cd tauri-mvp\backend
$env:WRITER_USE_DEV_DB = "1"
python run.py --dev
```

Run the frontend:

```powershell
cd tauri-mvp\frontend
npm install
npm run dev
```

Build the release package:

```powershell
cd tauri-mvp
.\build-release.ps1 -PythonExe python
```

Release artifacts are written under:

```text
tauri-mvp\frontend\src-tauri\target\release\
tauri-mvp\frontend\src-tauri\target\release\bundle\nsis\
tauri-mvp\frontend\src-tauri\target\release\bundle\msi\
```

## Verification

```powershell
python -m pytest
cd tauri-mvp\frontend
npm test
npm run test:e2e
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

## Roadmap

- Full dark theme pass before re-enabling the theme switcher.
- First-run onboarding and sample project.
- Optional cloud sync for writers who want the same local-first workspace across devices.
- Signed Windows builds or published checksums for preview installers.
- Richer reference-library views, AI report actions, and easier chat-to-note / chat-to-reference flows.
- A future mind map / imagery collection space for visually organizing themes, symbols, motifs, character links, arguments, references, and AI-generated ideas.
- macOS and Linux packages after the Windows workflow is mature.

## License

MIT © Living to Tell contributors
