# Public Screenshot Checklist

GitHub-facing screenshots live in `tauri-mvp/docs/assets/screenshots/`. They are captured from mocked or disposable demo data and are used by the main README and user documentation.

## Privacy rules

- Never show real writing, account emails, API keys, OAuth state, provider project IDs, local usernames, or private file paths.
- Use the checked-in mock workspace or a disposable `WRITER_DATA_DIR` containing demo text only.
- Check the entire frame, including navigation, notifications, file pickers, status messages, and system chrome.
- Prefer PNG files under 1 MB with a consistent desktop viewport.
- Do not use screenshots from a personal database, even when the visible article appears harmless.

## Current public set

- `article-writing.png`
- `focus-mode.png`
- `collections.png`
- `reference-library.png`
- `motif-star-map.png`
- `ai-workspace.png`
- `settings.png`
- `settings-wizard.png`
- `article-ai-chat.png`
- `dates-onboarding.png`
- `backup-center.png`

The main screenshot flow is maintained in `tauri-mvp/frontend/e2e/visible-actions.e2e.ts`. After regenerating an image, inspect it at full resolution, verify that only demo content is visible, and run the repository secret/path scan before committing it.

Tutorial GIFs have a separate workflow documented in [`tauri-mvp/docs/assets/tutorials/README.md`](../../tauri-mvp/docs/assets/tutorials/README.md).
