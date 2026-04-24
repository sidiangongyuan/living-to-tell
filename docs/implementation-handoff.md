# Writer Implementation Handoff v0.1

## 1. What Is Frozen

The following product decisions are now stable enough for implementation:

- Windows desktop only
- single-user personal writing tool
- Python + PySide6 + SQLite + SQLite FTS5
- cloud AI first
- Codex-style config import plus direct API calls
- fragment-first writing model
- minimal journal interface
- rewrite-first MVP, no free-form AI chat in the first usable release
- references mainly added by direct paste
- source title required, source author optional
- projects plus lightweight chapter grouping belong in MVP
- export defaults to accepted content only

## 2. First Implementation Target

The first usable release should include:

- main shell window
- recent fragments list
- fragment editor
- local persistence
- search
- AI settings page
- rewrite actions for selected text or current fragment
- side-by-side comparison dialog
- reference library
- project page with lightweight chapter grouping
- Markdown and TXT export

## 3. What Should Not Be Built Yet

- free-form AI chat
- multi-provider routing
- local model support
- sync or mobile support
- advanced chapter planning boards
- complex export formatting

## 4. Recommended Starting Order

1. scaffold app structure and startup
2. implement SQLite schema and repositories
3. build recent fragments list and editor
4. add search
5. add settings storage and AI provider config
6. implement rewrite service and comparison dialog
7. add reference library
8. add project and chapter grouping
9. add export

## 5. Docs To Read First

- `docs/product-requirements.md`
- `docs/technical-approach.md`
- `docs/cloud-ai-strategy.md`
- `docs/codex-style-integration.md`
- `docs/development-plan.md`
- `docs/basic-design.md`
- `docs/open-source-research.md`
- `docs/initial-scaffold.md`

## 6. Open-Source Patterns To Borrow

The implementing agent should borrow these ideas without copying any source code:

- from `Freenote`: simple writing-first home experience and local-first framing
- from `Manuscript`: explicit diff or comparison flow and never silently overwrite original text
- from `Obsidian Text Generator`: provider-config-driven AI actions and prompt-template thinking
- from `manasCore`: save locally first, then add AI processing around the stored data

The implementing agent should not expand scope toward:

- multi-provider routing UI
- heavy analytics dashboards
- full RAG chat against the whole notebook
- novel-planning systems beyond lightweight project and chapter grouping

## 7. Core Constraint

The implementing agent should protect the user's original writing.

That means:

- original text must remain recoverable
- AI output should never silently overwrite the original
- rewrite actions should feel assistive rather than dominant
