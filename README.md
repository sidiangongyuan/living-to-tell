# Writer

A minimal Windows desktop personal writing tool. Capture short fragments,
search and filter them, and optionally apply lightweight AI rewrites without
ever silently overwriting the original text.

> **Status: internal alpha (dev build)** — all core writing features are
> working and daily-usable, but this is not a final release. Expect rough
> edges in packaging and UI polish.

## Features

- **Fragment editor** — write and edit short text fragments with autosave
- **Recent fragments list** — quickly switch between fragments
- **Full-text search** — SQLite FTS5 search across fragments, plus a global
  search dialog for fragments and works
- **Tags & tag filter** — tag fragments and filter the list by tag
- **Works** — create longer-form pieces with title, summary, tags, status,
  target word count, and ordered sections
- **Collections** — organise multiple works into an ordered set and export
  the whole collection together
- **Include fragment into work** — insert the selected text (or the whole
  fragment) into a chosen work section at an explicit insertion point
- **AI rewrite** — Polish / Expand / Continue via OpenAI-compatible API
  - Side-by-side compare dialog with full accept or partial (selection) accept
- **Reference library** — paste-in source material for AI context
- **Projects & chapters** — organise fragments into projects with chapters
- **Export** — fragments and projects as Markdown / plain text; works and
  collections as TXT / Markdown / DOCX
- **Version history** — fragment AI acceptances and manual snapshots are
  tracked; works also support manual snapshots and restore-to-current

## M8 Highlights

M8 adds a second writing layer above fragments:

- **Works mode** — write longer-form pieces as ordered sections (`body` and
  `heading` blocks) instead of keeping everything as loose fragments
- **Collections mode** — assemble multiple works into a book-like or
  anthology-like order, then export the whole collection with a generated
  table of contents
- **Fragment inclusion flow** — send a fragment into a work through a review
  dialog, edit the inserted text before confirming, and choose the insertion
  point inside the target section preview
- **Unified search** — search fragments and works from one dialog and jump
  directly to the matching fragment or work section

Current M8 scope is intentionally plain-text-first: no rich text, no PDF
typesetting, and no book front-matter system yet.

## Run locally (source)

Requires Python 3.12+ on Windows.  The project is developed against a
`conda` environment but a plain `venv` works equally well.

```powershell
# one-time setup
pip install -e .[dev]

# launch
writer

# alternative (no console script needed)
python -m writer.main
```

## Run tests

```powershell
pytest
# or for quieter output:
pytest -q
```

## Keyboard shortcuts

- `Ctrl+N` — new fragment
- `Ctrl+P` — command palette
- `Ctrl+S` — save current fragment
- `Ctrl+Shift+F` — global search
- `Ctrl+Shift+I` — include current fragment into a work

## Build a Windows package

See [Building for Windows](#building-for-windows) below.

## Data directory

User data (SQLite database) is stored in the platform user-data directory
via [`platformdirs`](https://github.com/platformdirs/platformdirs):

| Platform | Default location |
|----------|-----------------|
| Windows  | `%APPDATA%\Writer\Writer\` |

Override the location for development or testing:

```powershell
$env:WRITER_DATA_DIR = "C:\my\custom\path"
writer
```

## AI configuration

Open **AI → Settings…** inside the app and fill in:

- **Base URL** — your OpenAI-compatible endpoint (e.g. `https://api.openai.com/v1`)
- **Model** — model name (e.g. `gpt-4o-mini`)
- **API key source** — one of:
  - `env:VAR` (e.g. `env:OPENAI_API_KEY`) — the app reads the referenced
    environment variable at request time.
  - `codex` — the app reads `~/.codex/auth.json` (your existing local
    Codex credential file) at request time.

  In **both** modes the raw key value is **never stored on disk by this
  app** and never logged.

Click **Test AI configuration** in the same dialog to validate your settings
locally (no network call) — it checks that all required fields are filled
and that the selected credential source resolves to a non-empty key.

You can also import a Codex-style `config.toml` via
**AI → Settings… → Import Codex config**. Only the endpoint (`base_url`),
model, and wire protocol are imported — **API keys are never imported**.
If the imported config declares `requires_openai_auth = true` and a usable
`~/.codex/auth.json` exists on the machine, **API key source** is
auto-switched to `codex` so you don't have to export any environment
variable manually. Otherwise, set the corresponding environment variable
yourself before invoking AI.

## Building for Windows

The current release format is a portable Windows bundle, not a traditional
installer. After building, you can either run the unpacked folder directly or
share the generated zip file.

### Prerequisites

```powershell
pip install -e .[dev]   # installs PyInstaller alongside dev tools
```

### Build

Recommended:

```powershell
.\scripts\build_windows.ps1 -PythonExe D:\anaconda\envs\writer\python.exe
```

If your active environment already has the right `python` on PATH, this also
works:

```powershell
.\scripts\build_windows.ps1
```

Manual fallback:

```powershell
python -m PyInstaller writer.spec --noconfirm
```

### Output

The build produces:

- `dist\Writer\Writer.exe` — runnable one-folder Windows app bundle
- `dist\Writer-portable.zip` — shareable portable package

Launch the unpacked bundle with:

```powershell
dist\Writer\Writer.exe
```

> **Note:** PyInstaller 6.x places bundled data under `dist\Writer\_internal\`.
> The first build takes a few minutes while PyInstaller collects PySide6.
> Subsequent builds are faster.

### What is bundled

- All `writer` package source
- `writer/storage/schema.sql`
- PySide6 Qt runtime (plugins, translations, libraries)
- `python-docx` and its runtime dependencies for work / collection DOCX export
- `hooks/rthook_pyside6_dlls.py` — custom runtime hook that adds `PySide6/`
  and `shiboken6/` subdirectories to the Windows DLL search path via
  `os.add_dll_directory()`. This is required on Python 3.8+ where the legacy
  `PATH` environment variable is no longer used for extension-module DLL
  resolution.

## Release notes

- [docs/m9a-release-notes.md](docs/m9a-release-notes.md) — M9A summary covering
  the visual shell upgrade, theme system, reachable empty states, and the
  fragment-to-work closure flow
- [docs/m8-release-notes.md](docs/m8-release-notes.md) — M8 summary covering
  works, collections, unified search, inclusion flow, export formats, and
  current scope limits

## Design docs

Product and design docs live under [`docs/`](docs/):

- `docs/basic-design.md`
- `docs/implementation-handoff.md`
- `docs/product-requirements.md`
- `docs/technical-approach.md`
- `docs/development-plan.md`
- `docs/m9a-release-notes.md`
- `docs/m8-release-notes.md`

