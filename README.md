<div align="center">

# Writer

### A local-first writing studio for articles, collections, references, and scoped AI help

[中文](README.zh-CN.md) · English

[![Version](https://img.shields.io/badge/tauri%20preview-0.1.6-blue.svg)](tauri-mvp/CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/sidiangongyuan/writer/releases)
[![Built with Tauri](https://img.shields.io/badge/built%20with-Tauri%202-orange.svg)](https://tauri.app/)
[![Status](https://img.shields.io/badge/status-preview-orange.svg)](tauri-mvp/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Download](#download) · [Screenshots](#screenshots) · [Features](#features) · [AI Setup](#ai-setup) · [Development](#development)

</div>

Writer is a calm desktop app for writing articles, arranging them into collections, saving reference passages, and using AI without giving up control of the manuscript. It keeps your writing database local and treats AI output as something to review, copy, discuss, or explicitly apply.

The current public preview is the Tauri version under [`tauri-mvp/`](tauri-mvp/). The earlier PySide/Qt implementation remains in the repository, but new public-facing work is focused on the Tauri app.

## Screenshots

| Article Writing | Focus Mode |
| :---: | :---: |
| ![Article writing](tauri-mvp/docs/assets/screenshots/article-writing.png) | ![Focus mode](tauri-mvp/docs/assets/screenshots/focus-mode.png) |

| Collections | Reference Library |
| :---: | :---: |
| ![Collections](tauri-mvp/docs/assets/screenshots/collections.png) | ![Reference library](tauri-mvp/docs/assets/screenshots/reference-library.png) |

| AI Workspace | Settings |
| :---: | :---: |
| ![AI workspace](tauri-mvp/docs/assets/screenshots/ai-workspace.png) | ![Settings](tauri-mvp/docs/assets/screenshots/settings.png) |

## Features

### Writing

- Article editor with autosave, tags, full-text search, find/replace, and a collapsible context pane.
- Epigraph editing for opening quotes, while keeping export output clean.
- Focus mode hides the surrounding interface and leaves only the writing area.
- Single-article export to Markdown, TXT, and DOCX.
- Date view for browsing daily writing activity, with a direct "start writing" action on empty days.

### Collections

- Create article collections and add multiple articles at once.
- Drag to reorder articles, or use up/down controls as a fallback.
- Preview the selected article in a paper-like reading pane.
- Export a collection in Markdown, TXT, or DOCX using the current order.

### Reference Library

- Save reference passages with source title, author, usage type, and personal notes.
- Browse by source book or by usage.
- Jump from the daily quote card to the matching reference passage.
- Copy just the passage body, or copy a complete citation with title and author.

### AI

- AI tools for polishing, rewriting, expanding, continuing, summarizing, outlining, and title generation.
- Free chat tab with one ongoing conversation per global scope, article, or collection.
- AI Cards for style, character, and setting context, with type/source filters and keyword search.
- Supports OpenAI-compatible APIs, Codex local auth, Gemini API/local config, and Gemini CLI / OAuth.
- API keys are not stored in Writer settings; only the selected credential source is saved.

### Desktop

- Windows installer builds with a bundled Python backend sidecar.
- Release builds discover the sidecar port automatically, so users do not need to run a backend manually.
- Close behavior can be set to ask every time, minimize to tray, or exit directly.
- Public preview uses light mode only; dark mode will return after a full theme pass.

## Download

Download the latest public preview from [GitHub Releases](https://github.com/sidiangongyuan/writer/releases).

Recommended Windows asset:

- `Writer_0.1.6_x64-setup.exe`

Optional assets:

- `Writer_0.1.6_x64_en-US.msi`
- `writer-app.exe` for direct smoke testing

Windows SmartScreen may warn because preview builds are unsigned. Only run installers downloaded from this repository's release page.

## Quick Start

1. Install Writer from the latest Release.
2. Open Articles and start a new article.
3. Use Collections to arrange multiple articles into a reading order.
4. Save quotes and sources in the Reference Library.
5. Configure AI in Settings if you want AI tools or scoped chat.

## AI Setup

Open Settings and choose one provider:

- OpenAI-compatible: set a base URL/model and use `env:OPENAI_API_KEY` or Codex local auth.
- Gemini API: use `env:GEMINI_API_KEY` or import local Gemini configuration.
- Gemini CLI / OAuth: reuse a local Gemini CLI login. No API key field is required.

Long Gemini requests default to a 120 second wait. Advanced users can tune this with `WRITER_GEMINI_TIMEOUT_SECONDS` or `WRITER_GEMINI_CLI_TIMEOUT_SECONDS`.

## Data & Privacy

- Writing data is stored locally in Writer's SQLite database.
- AI requests are sent only when you run an AI tool or send a chat message.
- API keys are read from environment variables or local provider configuration at runtime.
- Writer settings store the selected provider and credential source, not raw API keys.
- Use backups/checkpoints before major editing or migration tests.

## Development

See [tauri-mvp/README.md](tauri-mvp/README.md) for Tauri preview development and release commands.

Quick verification:

```powershell
D:\anaconda\envs\writer\python.exe -m pytest
cd tauri-mvp\frontend
npm test
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

GitHub Actions are manual-only to avoid consuming free CI minutes on every push. Releases are built locally and uploaded manually to GitHub Releases.

## Roadmap

- Full dark theme pass before re-enabling the theme switcher.
- First-run onboarding and sample project.
- More polished release signing and update story.
- Richer reference-library views and AI report actions.
- Claude / Anthropic provider support once the provider backend is complete.

## License

MIT © Writer contributors
