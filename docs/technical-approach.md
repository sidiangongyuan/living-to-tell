# Writer Technical Approach v0.2

## 1. Recommended Direction

For the first implementation, the most pragmatic route is:

- Desktop client: Python + PySide6
- Local storage: SQLite
- Search: SQLite FTS5
- AI integration: provider adapter over remote LLM APIs first
- Packaging: PyInstaller for Windows

This direction is recommended because the project is Windows-first, personal-use, and likely to iterate quickly. A Python desktop stack keeps the implementation surface smaller than a split frontend-backend architecture.

## 1.1 Confirmed Planning Decisions

- AI in MVP can use cloud APIs
- The writing flow is fragment-first, not strictly one-entry-per-day
- The primary output target is prose
- The default rewrite behavior is light literary polishing
- The UI direction is a minimal journal

## 2. Why This Stack

### Python + PySide6

- Fits the current workspace direction
- Fast to prototype for a personal desktop app
- Mature desktop widgets for editor, sidebar, dialogs, and local file access
- Easier for a later AI pipeline than a JS-only desktop stack

### SQLite

- Zero-config local database
- Good fit for single-user desktop software
- Easy backup story
- Supports FTS5 for built-in full-text search

### Remote LLM First

- Fastest way to validate the writing workflow
- Better output quality than most lightweight local models in early iterations
- Avoids the hardware burden of local inference in MVP
- Closest to the current chat-AI experience the user already knows

### What "Local Offline" Means Here

In this project, "local offline" means the AI model runs on the user's own machine, or through a self-hosted local service, without sending writing content to a cloud provider.

This can take two forms:

- on-device inference through a local model runner
- self-hosted local API compatible with the app

This is not required for MVP. It should be treated as a later privacy-focused option.

### What "Cloud AI" Means Here

Cloud AI means the desktop app sends the selected text and prompt to a remote model provider over the internet, then receives the rewritten result back.

In practice, this is similar to using a chat assistant interface, except the app will call the provider through an API instead of a web chat UI.

### Packaging with PyInstaller

- Straightforward Windows distribution path
- Suitable for a private self-use tool

## 3. Architecture Overview

Recommended modules:

- `ui/`: windows, editor, panels, dialogs
- `domain/`: entry, project, quote, rewrite task models
- `storage/`: SQLite schema, repositories, backup logic
- `services/ai/`: provider adapters, prompt building, output parsing
- `services/search/`: full-text and tag-based retrieval
- `services/export/`: Markdown and TXT export
- `app/`: startup, dependency wiring, settings

## 4. Core Data Model

### Entry

- id
- title
- content
- entry_type: note, fragment, draft
- created_at
- updated_at
- tags
- mood or theme labels (optional)
- project_id (nullable)

### EntryVersion

- id
- entry_id
- version_type: original, polished, expanded, continued
- content
- created_at
- ai_metadata

### ReferencePassage

- id
- source_title
- source_author
- content
- notes
- tags
- created_at

### Project

- id
- name
- description
- status

### ChapterDraft

- id
- project_id
- title
- ordered_entry_ids or linked relationship

## 5. AI Capability Design

The AI layer should be designed as a replaceable adapter rather than tied to one provider.

See [cloud-ai-strategy.md](D:/python_proj/writer/docs/cloud-ai-strategy.md) for the recommended MVP provider choice, API shape, cost controls, and replacement plan.

Suggested interface:

- `polish_text`
- `expand_text`
- `continue_text`
- `summarize_entry`
- `rewrite_with_style_references`

Each request should combine:

- user original text
- selected action
- rewrite strength
- optional style instructions
- retrieved reference passages
- guardrails such as preserve meaning, avoid copying, keep first-person voice if present

Default prompt stance for MVP:

- preserve the user's intent and emotional center
- lightly improve rhythm, imagery, and clarity
- do not over-write into a showy literary style
- use references for atmosphere only, not imitation

## 6. Reference Retrieval Strategy

For MVP, do not start with a vector database.

Use this simpler retrieval path first:

- user-selected references
- tag filtering
- keyword search via SQLite FTS5

This is enough to validate whether style-guided rewriting is useful. Semantic embeddings can be added later if retrieval quality becomes a problem.

## 7. Privacy and Configuration

Recommended approach:

- Store user content locally by default
- Store app settings locally
- Store API keys via Windows credential storage if possible, otherwise encrypted local config as an interim solution
- Make cloud usage explicit in the UI when AI calls are made
- Make AI calls opt-in per action rather than automatic background processing

## 8. Suggested MVP Screens

- Home page with recent fragments
- Entry editor page with minimal controls
- Reference library page
- Project or manuscript page
- Rewrite result comparison dialog
- Settings page for AI provider and storage options

UI principles for MVP:

- open quickly into writing
- low visual noise
- primary actions visible but restrained
- AI actions should feel like optional assistance, not the main screen focus

## 9. Milestone Plan

### Milestone 1: Writing Core

- App shell
- Entry CRUD
- Fast fragment capture flow
- SQLite persistence
- Auto-save
- Basic search

### Milestone 2: AI Rewrite Core

- Provider settings
- Polish and expand actions
- Result comparison
- Version persistence

### Milestone 3: Reference Library

- Quote import
- Tagging and source metadata
- Reference selection in rewrite flow

### Milestone 4: Manuscript Accumulation

- Project grouping
- Chapter containers
- Export to Markdown and TXT

## 10. Risks and Mitigations

### Risk: User voice gets flattened

Mitigation:

- Always preserve original version
- Make rewrite strength adjustable
- Let prompts explicitly preserve emotional intent and perspective

### Risk: Style reference becomes imitation

Mitigation:

- Prompt for tonal inspiration rather than sentence reuse
- Show reference sources clearly
- Avoid automatic direct borrowing of phrasing

### Risk: Scope expands too fast

Mitigation:

- Build only the single-user desktop path first
- Delay mobile, sync, community, and advanced manuscript tooling

## 11. Alternatives Considered

### Electron or Tauri

These are valid if the project later needs a more web-like UI or cross-platform deployment. For the current phase, they add frontend stack overhead without solving a pressing product problem.

### Local LLM First

This helps privacy, but it raises hardware and model-quality constraints early. It is better as a second-stage option after the workflow is proven.
