# Public TODO List

This list tracks product-facing work that would make Living to Tell more reliable, more expressive, and easier to adopt.

## First-run experience

- [x] Add a first-run checklist that reads local state without creating sample data.
- [ ] Improve onboarding for language, data location, backups, and AI provider setup.
- [x] Add a sample project that demonstrates articles, collections, references, notes, and AI setup.
- [x] Add a user-facing data location screen.
- [x] Add a safe restore workflow for backups.
- [ ] Re-enable dark mode after a complete visual pass.

## Writing experience

- [x] Add article notes for keeping ideas, reminders, and next-step thoughts beside the current article.
- [x] Restore the last article editing position and improve long-document comfort near the end of a draft.
- [ ] Add editor layout presets for compact, balanced, and wide screens.
- [ ] Improve keyboard-only navigation across Dates, Articles, Collections, and AI Edit beyond the 0.1.47 focus/contrast/dialog baseline.
- [ ] Add richer collection publishing options such as cover notes, section dividers, and saved export presets.
- [x] Add optional backup reminders for active daily writers.

## AI workflow

- [x] Make AI results safer to apply with clearer original-vs-result comparison and explicit replace / insert / copy actions.
- [x] Give polish, rewrite, expand, and continue their own focused controls.
- [x] Let users save personal prompt presets for each writing tool.
- [x] Add article-scoped AI chat with standing instructions and save-reply-as-note.
- [x] Add style / character / scene AI Cards with fixed templates and AI-assisted draft generation.
- [x] Add scene-module search and manual attachment for AI tasks.
- [x] Add a real AI connectivity test that separates local config checks from real provider requests.
- [x] Add OpenCode local-auth support with live model fetching for OpenCode models.
- [x] Add clearer long-text request size, wait-time, and timeout feedback.
- [x] Make it easier to turn AI chat ideas into articles or reference material.
- [x] Improve quota, model availability, network, proxy, credential, and HTML error messages with safe actionable diagnostics.
- [x] Unify AI settings around independent profiles, one default profile, saved health, local checks, and selected real tests.
- [x] Add recoverable article multi-model tasks with exact profile selection, partial results, local cancellation, and drift-safe write-back.
- [ ] Add provider-native token counting where available.
- [ ] Expand clickable AI reports so issues can locate source text or become follow-up tasks.

## Knowledge and planning

- [x] Add a motif star map for organizing recurring images, symbols, and source excerpts visually.
- [x] Add compact reference-library overview and active-group summaries.
- [ ] Add richer graph views for themes, character links, arguments, references, and AI-generated ideas visually.
- [ ] Add richer reference-library views for large reading collections.
- [ ] Add better cross-links between articles, collections, notes, references, and AI conversations.

## Packaging and platform

- [ ] Add optional cloud sync for writers who want the same local-first workspace across devices.
- [ ] Add signed Windows builds or published checksums for preview installers.
- [ ] Evaluate macOS and Linux packaging after the Windows workflow is mature.
- [ ] Add a clearer update path for public preview users.

## Documentation

- [x] Keep English and Chinese user guides in sync.
- [x] Add short tutorial videos or GIFs after clean demo screenshots are available.
- [x] Add English and Chinese troubleshooting pages for AI provider setup.

## Completed recently

- Renamed the public app to Living to Tell / 活着为了讲述.
- Added a motif star map with right-click capture, source anchors, co-occurrence links, deduplication, and safer unlink behavior.
- Upgraded AI Cards into style / character / scene templates, added AI draft generation, and added manual scene-module attachment.
- Added first-run checklist progress, AI settings diagnostics, long-request size feedback, and grouped global command palette search.
- Added an explicit disposable sample project that demonstrates articles, a collection manuscript structure, references, writing notes, and scene AI Cards.
- Expanded Export & Backup with restore-point selection, safety summary, real data paths, backup reminders, and recent article/collection export shortcuts.
- Reworked Collections around one manuscript structure tree and kept the board as a status overview.
- Added reference-library overview cards and AI chat capture previews for saving assistant replies as reference material or new articles.
- Added OpenCode local-auth support, live OpenCode model fetching, and real OpenCode test requests through the unified AI provider path.
- Added a real AI connectivity test and fixed Gemini proxy transport selection for custom-base `sk-...` keys.
- Added Data and Storage settings with visible paths, open-folder actions, and copy-based directory migration.
- Added article notes, focused AI writing controls, per-tool presets, and explicit AI writeback actions.
- Improved long-form editing with last-position restore, wider writing layout, and end-of-document breathing space.
- Added daily writing quote links and one-click start writing.
- Fixed the window close button flow with native ask / tray / exit behavior.
- Unified AI settings, rebuilt article AI editing around real articles/selections, moved article chat into a persistent drawer, and added a complete automated quality gate.
