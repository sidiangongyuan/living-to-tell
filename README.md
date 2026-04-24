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
- **Full-text search** — SQLite FTS5 search across all fragments
- **Tags & tag filter** — tag fragments and filter the list by tag
- **AI rewrite** — Polish / Expand / Continue via OpenAI-compatible API
  - Side-by-side compare dialog with full accept or partial (selection) accept
- **Reference library** — paste-in source material for AI context
- **Projects & chapters** — organise fragments into projects with chapters
- **Export** — fragment or full project as Markdown or plain text
- **Version history** — every AI acceptance and manual snapshot is tracked;
  restore any previous version at any time

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
- **API key source** — `env:OPENAI_API_KEY` or `literal:<your-key>`

You can also import a Codex-style `config.toml` via **AI → Settings… → Import Codex config**.

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
- `hooks/rthook_pyside6_dlls.py` — custom runtime hook that adds `PySide6/`
  and `shiboken6/` subdirectories to the Windows DLL search path via
  `os.add_dll_directory()`. This is required on Python 3.8+ where the legacy
  `PATH` environment variable is no longer used for extension-module DLL
  resolution.

## Design docs

Product and design docs live under [`docs/`](docs/):

- `docs/basic-design.md`
- `docs/implementation-handoff.md`
- `docs/product-requirements.md`
- `docs/technical-approach.md`
- `docs/development-plan.md`
