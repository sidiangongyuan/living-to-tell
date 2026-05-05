# Writer

[中文](README.zh-CN.md) · English

[![Tests](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml/badge.svg)](https://github.com/sidiangongyuan/writer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)
![Windows](https://img.shields.io/badge/Windows-portable-0078D4.svg)

**A local-first writing desk for fragments, long-form drafts, references, and AI-assisted rewriting.**

Writer is built for people who collect scenes, notes, images-in-words, and half-formed ideas before they know what the final piece is. It keeps your writing local, gives fragments a path into longer works, and lets AI help only when you explicitly ask.

> Status: **alpha, daily-usable but still evolving**. The core writing flow, exports, version history, and AI workspace are working; expect more UI polish before a stable release.

## Why Writer?

- **Fragments first** — capture short pieces quickly, then search, tag, and reuse them.
- **Grow into works** — organize fragments into works, sections, collections, and exportable manuscripts.
- **AI that respects drafts** — preview results, write back safely, and keep snapshots before destructive changes.
- **Local by default** — your SQLite database stays on your machine; API keys and OAuth tokens are read only at request time.
- **Gemini OAuth support** — reuse a local Gemini CLI login, switch Gemini 3 / 2.5 text models, and inspect tier/quota status.
- **Portable Windows app** — build or download a zip, unzip it, and run `Writer.exe`.

## What you can do today

| Area | Highlights |
| --- | --- |
| Writing | Fragment editor, autosave, tags, full-text search, version history |
| Long form | Works, ordered sections, collections, TXT / Markdown / DOCX export |
| References | Reference library with typed material for characters, locations, settings, and excerpts |
| AI workspace | Polish, expand, continue, summarize, outline, style transfer, library Q&A, scoped chat |
| AI providers | GPT / OpenAI-compatible APIs, native Gemini API keys, Gemini CLI / OAuth |
| Safety | Compare before accepting, snapshots before write-back, no stored raw AI keys |

## Screenshots

Screenshots should be generated from a clean demo profile so private writing and credentials never appear in the repository. See [docs/screenshots/README.md](docs/screenshots/README.md) for the checklist.

## Download

The recommended public distribution format is a **Windows portable zip**.

- If a GitHub Release is available, download `Writer-<version>-portable.zip` from the release assets.
- If you are testing the latest branch, use the **Build Windows Portable** GitHub Action artifact.
- To build locally, run the packaging command in [Build from source](#build-from-source).

After downloading, unzip the archive and launch `Writer.exe` inside the `Writer` folder.

## Quick start from source

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

## Build from source

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\path\to\python.exe
```

If your active environment already has the correct Python on `PATH`:

```powershell
.\scripts\build_windows.ps1
```

Build outputs:

- `dist\Writer\Writer.exe` — unpacked portable app
- `dist\Writer-<version>-portable.zip` — versioned zip for releases
- `dist\Writer-portable.zip` — stable alias for local testing

## AI setup

Open **Settings** in the app and choose an AI provider:

- **GPT / OpenAI** — use `env:OPENAI_API_KEY` or another OpenAI-compatible endpoint.
- **Gemini** — use `env:GEMINI_API_KEY` or a local `~/.gemini/.env` file.
- **Gemini CLI / OAuth** — reuse an existing Gemini CLI OAuth login; Writer refreshes a short-lived access token at request time and calls Gemini Code Assist directly.

Gemini CLI / OAuth supports common text-generation presets such as:

- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

The model field remains editable, so compatible future text models can be tried without a code change. Media, embedding, Live API, robotics, and other specialized Gemini models usually need different request shapes and are not exposed as Writer presets.

## Privacy and security

Writer is local-first, but AI providers still receive the text you send to them. Review prompts before running AI tasks if your writing is sensitive.

Writer should never commit or store in Git:

- real API keys
- OAuth access / refresh / ID tokens
- account emails or cloud project IDs
- local SQLite databases
- private writing content
- generated `dist/` or `build/` artifacts

See [SECURITY.md](SECURITY.md) for reporting and contributor rules.

## Roadmap and changelog

- [CHANGELOG.md](CHANGELOG.md) — product-facing release history
- [docs/roadmap.md](docs/roadmap.md) — alpha-to-beta roadmap
- [docs/ai-revision-workflow.md](docs/ai-revision-workflow.md) — planned AI compare / revision workflow
- [docs/screenshots/README.md](docs/screenshots/README.md) — screenshot checklist

## Contributing

Pull requests are welcome while the project is alpha. Please keep changes product-facing and avoid committing internal prompts, local test data, credentials, generated builds, or private writing samples.

CI runs the Windows Python 3.12 test suite with GitHub Actions: [.github/workflows/tests.yml](.github/workflows/tests.yml).

## License

Writer is released under the MIT License. See [LICENSE](LICENSE).
