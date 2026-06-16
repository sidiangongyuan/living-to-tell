# Public TODO List

This list tracks product-facing work that would make Writer more reliable and easier to adopt.

## Release quality

- Add signed Windows builds or a documented verification workflow for unsigned alpha archives.
- Add a reproducible release checklist that covers privacy review, tests, packaging, and release notes.
- Improve first-run onboarding for language, data location, backup, and AI provider setup.
- Add installer checksums to each public release.

## Writing experience

- Add a clearer focus-mode entry and exit hint.
- Add more editor layout presets for compact, balanced, and wide screens.
- Improve keyboard-only navigation across Dates, Articles, Collections, and AI Workspace.
- Add optional backup reminders for active daily writers.
- Add more ways to turn AI chat ideas into articles, notes, and reference-library items.
- Add richer collection publishing options such as cover notes, section dividers, and saved export presets.

## Data management

- Add import/export backup flows for the local SQLite data directory.
- Add a user-facing data location screen.
- Add a safe restore workflow for backups.
- Add optional encrypted-at-rest local storage research and design.

## AI workflow

- Improve revision comparison for AI edits with clearer original-vs-result review.
- Add richer controls for long prompts, including visible request size and timeout guidance.
- Add more per-context actions after the unified AI context menu, such as saved context sets and quick re-use.
- Improve quota, model availability, network, and proxy error messages.
- Add provider-native token counting where available.
- Expand clickable AI reports so issues can locate source text or become follow-up tasks.

## Packaging and platform

- Keep Windows portable zip as the primary alpha distribution.
- Evaluate installer packaging after the portable build is stable.
- Evaluate macOS and Linux packaging after the Windows workflow is mature.
- Keep GitHub Actions manual-only unless release automation is deliberately re-enabled.

## Documentation

- Keep English and Chinese user guides in sync.
- Add short tutorial videos or GIFs after clean demo screenshots are available.
- Add a troubleshooting page for AI provider setup and Windows packaging issues.

## Completed recently

- Added clean public screenshots for the Tauri preview.
- Reworked the public README into a product overview with screenshots, features, download, AI setup, privacy, and development sections.
- Changed GitHub Actions to manual-only triggers to avoid consuming free CI minutes on every push.
- Hid dark-mode UI entry points for the public preview and forced light mode until the dark theme is fully polished.
- Fixed Tauri window close behavior for ask, tray, and direct-exit modes.
