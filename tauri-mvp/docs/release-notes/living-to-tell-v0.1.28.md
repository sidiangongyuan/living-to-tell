# Living to Tell Preview 0.1.28

This update polishes the Motif Star Map AI enrichment workflow, especially compact-window layout, same-name motif handling, and draft preservation.

## Fixed

- AI Enrich now updates an existing motif when a newly typed concept has the same name, instead of trying to create a duplicate and showing `Motif name already exists`.
- AI Enrich drafts remain available after closing and reopening the dialog for the same motif or concept. They clear only when generating again, changing targets, or closing the app.
- The AI Enrich dialog now keeps footer actions visible in compact windows, keeps reference candidates scrollable, and wraps long source/reason text inside candidate cards.

## Changed

- The enrichment preview is wider and better balanced: concept profile content stays on the left, candidate sentence cards stay readable on the right, and two-column candidate layout only appears on genuinely wide screens.
- Drafts now carry a target key. If the selected motif/concept changes, the UI warns before applying and disables accidental stale application.
- Backup action E2E coverage now mocks all required page dependencies, including data-location refreshes, without weakening create/delete/restore assertions.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Assets

- `LivingToTell_0.1.28_x64-setup.exe`
  - SHA256: `DBE9F07542A72F053EECA1A5BFF8E1D9A7A496A065B2C0E4E1EA78830EE004DC`
- `LivingToTell_0.1.28_x64_zh-CN.msi`
  - SHA256: `52DCE1DCDF57E83EA268E3CFA9238D8E64AF7A6465F20954A43FD9BC51ADED30`
