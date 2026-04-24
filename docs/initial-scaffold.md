# Writer Initial Scaffold v0.1

## 1. Purpose

This document tells the implementing agent exactly which files and modules to create first.

It is intentionally narrow.

The goal is to reduce early architecture drift while keeping the codebase small enough for a personal desktop app.

## 2. Recommended Repository Layout

Use a Python `src` layout.

```text
writer/
  pyproject.toml
  README.md
  .gitignore
  src/
    writer/
      __init__.py
      main.py
      app/
        __init__.py
        bootstrap.py
        container.py
        paths.py
        settings.py
      domain/
        __init__.py
        enums.py
        models/
          __init__.py
          ai_config.py
          chapter.py
          entry.py
          entry_version.py
          project.py
          reference_passage.py
      services/
        __init__.py
        autosave_service.py
        search_service.py
        ai/
          __init__.py
          codex_config_importer.py
          interfaces.py
          openai_provider.py
          prompt_builder.py
          rewrite_service.py
        export/
          __init__.py
          markdown_exporter.py
          text_exporter.py
      storage/
        __init__.py
        database.py
        schema.sql
        repositories/
          __init__.py
          chapter_repository.py
          entry_repository.py
          project_repository.py
          reference_repository.py
          settings_repository.py
          version_repository.py
      ui/
        __init__.py
        main_window.py
        dialogs/
          __init__.py
          reference_picker_dialog.py
          rewrite_compare_dialog.py
          settings_dialog.py
        panels/
          __init__.py
          editor_panel.py
          fragment_list_panel.py
          project_panel.py
          reference_library_panel.py
  tests/
    test_smoke_startup.py
    storage/
      test_settings_repository.py
      test_entry_repository.py
```

## 3. Create First, Create Later

Do not create everything at once.

Create files in milestone order.

### Milestone 1 Files

These should be created first.

```text
pyproject.toml
README.md
.gitignore
src/writer/__init__.py
src/writer/main.py
src/writer/app/__init__.py
src/writer/app/bootstrap.py
src/writer/app/container.py
src/writer/app/paths.py
src/writer/app/settings.py
src/writer/storage/__init__.py
src/writer/storage/database.py
src/writer/storage/schema.sql
src/writer/storage/repositories/__init__.py
src/writer/storage/repositories/settings_repository.py
src/writer/ui/__init__.py
src/writer/ui/main_window.py
tests/test_smoke_startup.py
tests/storage/test_settings_repository.py
```

### Milestone 2 Files

Create after the shell and persistence are stable.

```text
src/writer/domain/__init__.py
src/writer/domain/enums.py
src/writer/domain/models/__init__.py
src/writer/domain/models/entry.py
src/writer/domain/models/entry_version.py
src/writer/storage/repositories/entry_repository.py
src/writer/storage/repositories/version_repository.py
src/writer/services/__init__.py
src/writer/services/autosave_service.py
src/writer/services/search_service.py
src/writer/ui/panels/__init__.py
src/writer/ui/panels/fragment_list_panel.py
src/writer/ui/panels/editor_panel.py
tests/storage/test_entry_repository.py
```

### Milestone 3 Files

Create after the editor and entry persistence work locally.

```text
src/writer/domain/models/ai_config.py
src/writer/services/ai/__init__.py
src/writer/services/ai/interfaces.py
src/writer/services/ai/openai_provider.py
src/writer/services/ai/prompt_builder.py
src/writer/services/ai/codex_config_importer.py
src/writer/services/ai/rewrite_service.py
src/writer/ui/dialogs/__init__.py
src/writer/ui/dialogs/rewrite_compare_dialog.py
src/writer/ui/dialogs/settings_dialog.py
```

### Milestone 4 and 5 Files

Defer until rewrite is working.

```text
src/writer/domain/models/reference_passage.py
src/writer/domain/models/project.py
src/writer/domain/models/chapter.py
src/writer/storage/repositories/reference_repository.py
src/writer/storage/repositories/project_repository.py
src/writer/storage/repositories/chapter_repository.py
src/writer/services/export/__init__.py
src/writer/services/export/markdown_exporter.py
src/writer/services/export/text_exporter.py
src/writer/ui/dialogs/reference_picker_dialog.py
src/writer/ui/panels/reference_library_panel.py
src/writer/ui/panels/project_panel.py
```

## 4. Root Files

### pyproject.toml

Use this file to define project metadata and dependencies.

Minimum runtime dependencies:

- `PySide6`
- `openai`
- `platformdirs`

Minimum dev dependencies:

- `pytest`
- `ruff`

Avoid adding large frameworks unless a concrete need appears.

### README.md

Keep it short in the first pass.

It should include:

- project purpose
- how to run locally
- current milestones
- where product planning docs live

### .gitignore

Ignore at least:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `dist/`
- `build/`
- local app data or temp database files if generated in the repo

## 5. App Layer

### src/writer/main.py

Single entry point.

Responsibilities:

- create the application through `bootstrap.py`
- run the Qt event loop

This file should stay thin.

### src/writer/app/bootstrap.py

Responsibilities:

- create `QApplication`
- initialize paths and settings
- initialize SQLite database
- create repositories and services via `container.py`
- create and show `MainWindow`

### src/writer/app/container.py

Responsibilities:

- wire repositories, services, and UI dependencies
- keep object creation centralized

Use a simple hand-written container, not a dependency injection framework.

### src/writer/app/paths.py

Responsibilities:

- define user data directory
- define settings path
- define database path

Use `platformdirs` so the app does not hard-code storage paths.

### src/writer/app/settings.py

Responsibilities:

- read and write app settings
- hold AI provider config fields
- expose simple get and save methods

Do not mix UI code into settings handling.

## 6. Storage Layer

### src/writer/storage/database.py

Responsibilities:

- create SQLite connections
- apply pragmas
- expose transaction helpers if needed

Keep connection management in one place.

### src/writer/storage/schema.sql

Define the initial schema in SQL rather than scattering raw DDL across Python files.

Initial tables to create in Milestone 1 and 2:

- `app_settings`
- `entries`
- `entry_versions`

Tables to add in later milestones:

- `reference_passages`
- `projects`
- `chapters`
- `project_entries`

Search support:

- add an FTS5 virtual table for entries in Milestone 2

### Repositories

Use repository files for each aggregate rather than one giant database helper.

Initial repository responsibilities:

- `settings_repository.py`: persistent settings
- `entry_repository.py`: entry CRUD and list queries
- `version_repository.py`: generated version storage and retrieval
- `reference_repository.py`: reference CRUD and filters
- `project_repository.py`: project CRUD and entry assignment
- `chapter_repository.py`: lightweight chapter grouping

## 7. Domain Layer

Use plain dataclasses or small typed models.

Do not add a heavy ORM abstraction in the first version.

### enums.py

Suggested enums:

- `EntryType`
- `VersionType`
- `RewriteAction`

### Model Files

Use one file per core model.

Suggested minimum fields:

- `entry.py`: id, title, content, entry_type, created_at, updated_at, tags, project_id
- `entry_version.py`: id, entry_id, version_type, content, created_at, provider, model
- `ai_config.py`: provider_name, base_url, wire_api, model, api_key_source
- `reference_passage.py`: id, source_title, source_author, content, notes, tags
- `project.py`: id, name, description, status
- `chapter.py`: id, project_id, title, sort_order

## 8. Services Layer

### autosave_service.py

Responsibilities:

- debounce editor writes if needed
- trigger save of current fragment

Keep the first version simple. Timer-based save is enough.

### search_service.py

Responsibilities:

- query entry search through FTS5
- hide SQL details from UI code

### services/ai/interfaces.py

Define internal contracts.

Suggested interfaces:

- `AiProvider`
- `RewriteRequest`
- `RewriteResponse`

### services/ai/openai_provider.py

Responsibilities:

- send requests to an OpenAI-compatible `responses` endpoint
- normalize provider output into internal response models

Do not leak SDK-specific response types into UI code.

### services/ai/prompt_builder.py

Responsibilities:

- build prompts for `polish`, `expand`, and `continue`
- enforce the product guardrails around preserving the user's voice

### services/ai/codex_config_importer.py

Responsibilities:

- read a Codex config TOML file
- import safe fields such as `base_url`, `model`, and `wire_api`
- ignore or avoid private auth internals

### services/ai/rewrite_service.py

Responsibilities:

- orchestrate rewrite action requests
- call the provider adapter
- persist generated versions through `version_repository.py`

### services/export/*.py

These can wait until Milestone 5.

Responsibilities later:

- export accepted content to Markdown
- export accepted content to TXT

## 9. UI Layer

### ui/main_window.py

Responsibilities:

- host the main two-pane layout
- connect fragment list and editor panel
- expose top-level actions for new fragment, rewrite, references, projects, and settings

### ui/panels/fragment_list_panel.py

Responsibilities:

- show recent fragments
- allow selection
- support lightweight search or filter hookups later

### ui/panels/editor_panel.py

Responsibilities:

- edit title and body
- expose selected text for rewrite actions
- report save changes to autosave or repository layer

### ui/dialogs/rewrite_compare_dialog.py

Responsibilities:

- show original text on one side
- show generated text on the other side
- allow explicit accept or cancel

Do not directly overwrite content on generation.

### ui/dialogs/settings_dialog.py

Responsibilities:

- edit base URL, model, and API key source
- offer Codex config import

Keep advanced fields out of the first version.

### ui/dialogs/reference_picker_dialog.py

Defer until the reference library exists.

## 10. Tests To Create Early

Create only a few narrow tests first.

Recommended first tests:

- app startup smoke test
- settings repository read and write
- entry repository create and load

Recommended later tests:

- prompt builder output shape
- codex config import for safe fields
- rewrite service persistence behavior

Do not try to build a large UI test suite in the first pass.

## 11. File Creation Order

The implementing agent should create files in this exact order for the first pass:

1. `pyproject.toml`
2. `.gitignore`
3. `README.md`
4. `src/writer/__init__.py`
5. `src/writer/main.py`
6. `src/writer/app/paths.py`
7. `src/writer/storage/database.py`
8. `src/writer/storage/schema.sql`
9. `src/writer/app/settings.py`
10. `src/writer/storage/repositories/settings_repository.py`
11. `src/writer/app/container.py`
12. `src/writer/ui/main_window.py`
13. `src/writer/app/bootstrap.py`
14. `tests/test_smoke_startup.py`
15. `tests/storage/test_settings_repository.py`

Only after those work should the agent move to entry models, repositories, and editor panels.

## 12. What To Avoid In The Scaffold

- do not create a web backend
- do not create chat-specific modules yet
- do not add vector search yet
- do not add multi-provider abstraction beyond one internal interface and one provider adapter
- do not introduce a large state management framework
- do not mix database SQL directly into UI modules

## 13. Final Recommendation

The first build should feel like a solid local writing app with a clean architecture path toward AI rewrite features.

If the implementing agent starts by building all domain concepts at once, scope will drift.

The right move is to create the smallest durable scaffold, then layer entries, then AI rewrite, then references and projects.
