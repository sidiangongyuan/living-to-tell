# Writer Development Plan v0.1

## 1. Purpose

This document turns the current product planning into an implementation sequence that another agent can execute with low ambiguity.

The project goal is to ship a Windows-first personal writing assistant with:

- low-friction fragment capture
- light AI polishing
- local storage
- a minimal journal-like interface
- a path from fragments to prose accumulation

## 2. Planning Status

### Confirmed

- Windows desktop only
- personal single-user product
- Python + PySide6 + SQLite
- cloud AI first
- fragment-first writing flow
- prose as the primary long-form target
- light literary polishing by default
- Codex-style config import plus direct API calls inside the app

### Not Yet Frozen

- final default export priority after Markdown and TXT
- exact rewrite result interaction pattern
- reference input methods in v1
- whether AI chat ships in the first executable milestone or the second
- how much project or chapter organization belongs in MVP versus Phase 2

## 3. Delivery Strategy

The best implementation strategy is not to build every planned feature at once.

Use a four-stage delivery path:

1. foundation and writing core
2. AI configuration and rewrite flow
3. reference library and project grouping
4. packaging, polish, and optional AI chat

This sequence minimizes risk because the product still has value before the AI layer is complete.

## 4. Milestones

### Milestone 0: Planning Freeze

Goal:

- finalize the MVP boundaries and the basic interaction model

Outputs:

- requirement summary
- technical direction
- AI integration strategy
- development plan
- design decision checklist

Exit criteria:

- no open blocker on core writing flow
- no open blocker on AI integration direction
- another agent can scaffold the project without guessing product intent

### Milestone 1: App Foundation

Goal:

- create the desktop shell and persistence backbone

Implementation scope:

- Python project structure
- PySide6 app startup
- SQLite database initialization
- settings storage
- repository and service layer skeletons
- initial navigation shell

Deliverables:

- runnable desktop app window
- database file creation
- basic settings read and write
- app-level folder structure for UI, storage, domain, and services

Exit criteria:

- app launches locally
- database initializes automatically
- settings persist across restarts

### Milestone 2: Writing Core

Goal:

- make the app useful as a local writing tool before AI

Implementation scope:

- create, edit, delete entry or fragment
- recent entries view
- title, body, tags, timestamps
- auto-save or save-on-change behavior
- full-text search with SQLite FTS5

Deliverables:

- working editor screen
- recent fragments list
- entry persistence and reload
- search by keyword

Exit criteria:

- user can open app, write a fragment, close app, and reopen with data intact
- user can retrieve previous fragments by search

### Milestone 3: AI Rewrite Core

Goal:

- add the main value layer without overbuilding chat first

Implementation scope:

- provider config screen
- OpenAI-compatible provider adapter
- Codex config import for safe fields
- polish selected text
- expand fragment
- continue fragment
- result comparison UI
- version persistence

Deliverables:

- AI settings page
- one working cloud provider adapter
- rewrite action from editor
- saved original and generated versions

Exit criteria:

- user can configure provider settings once
- user can rewrite selected text and compare original versus generated result
- every AI-generated result is stored with metadata

### Milestone 4: Reference Library

Goal:

- let the AI borrow atmosphere from user-collected passages

Implementation scope:

- reference passage CRUD
- source metadata
- tags
- keyword search
- attach selected references during rewrite

Deliverables:

- reference library page
- tag and keyword filtering
- rewrite flow with optional reference attachment

Exit criteria:

- user can save passages and use them during rewrite
- the app can persist source and tag information correctly

### Milestone 5: Project Accumulation

Goal:

- connect scattered fragments to longer prose work

Implementation scope:

- project CRUD
- mark entries for project inclusion
- simple chapter or section containers
- export Markdown and TXT

Deliverables:

- project page
- assign entry to project
- export selected project content

Exit criteria:

- user can group fragments into a project and export them

### Milestone 6: Optional AI Chat and Packaging

Goal:

- add free-form conversation only after the writing flow works

Implementation scope:

- local chat session persistence
- AI chat side panel or dialog
- streaming if practical
- Windows packaging with PyInstaller

Deliverables:

- optional AI chat panel
- packaged Windows executable

Exit criteria:

- packaged app launches on Windows
- chat uses the same provider config as rewrite actions

## 5. Recommended Build Order Inside the Codebase

Another agent should implement in this order:

1. app bootstrap and folder structure
2. SQLite schema and repository layer
3. entry editor and recent list
4. search support
5. AI settings storage
6. provider adapter and rewrite service
7. result comparison and versioning
8. reference library
9. project grouping and export
10. optional AI chat

## 6. Design Boundaries for the Implementing Agent

The implementing agent should avoid these mistakes:

- do not start with multi-provider routing
- do not build the whole app around AI chat
- do not add sync or mobile support
- do not introduce a web backend unless a real blocker appears
- do not ship without preserving original text versions
- do not overcomplicate chapter planning in the first pass

## 7. Suggested Handoff Package

Before implementation begins, the implementing agent should read:

- `docs/product-requirements.md`
- `docs/technical-approach.md`
- `docs/cloud-ai-strategy.md`
- `docs/codex-style-integration.md`
- `docs/design-decision-checklist.md`

The implementing agent should produce first:

- project scaffold
- database schema
- settings model
- initial editor view

## 8. Validation Strategy

Each milestone should have a narrow validation step.

Recommended validation pattern:

- run the app locally after each UI milestone
- validate database creation and persistence using a temporary test database
- verify rewrite actions with a mocked AI response before real provider calls
- verify real provider calls only after settings and metadata persistence work
- package only after local execution is stable

## 9. Current Recommendation

Do not send another agent to build the full app yet.

Use the next 2 to 3 planning rounds to freeze:

- the editor interaction model
- the rewrite comparison model
- the MVP boundary for AI chat versus rewrite-only

After that, implementation can start with much less rework.
