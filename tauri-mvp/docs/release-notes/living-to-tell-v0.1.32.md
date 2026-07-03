# Living to Tell Preview 0.1.32

This update packages the recoverable AI workflow improvements and the latest
user-facing robustness fixes.

## Added

- AI Tools multi-model comparison now streams results as each model finishes.
  Fast models can be reviewed immediately while slower models keep running.
- Motif Star Map AI Enrich now runs as a background job during the current app
  session. The enrichment dialog can be closed while the job keeps working, then
  reopened to inspect progress, errors, or the completed draft.
- Motif AI jobs report concrete stages such as context preparation, request
  sending, model waiting, and response parsing instead of showing a silent long
  wait.

## Changed

- Multi-model comparison only runs the profiles the user selected. The default
  profile is no longer added implicitly after another profile is selected.
- The fixed three-model comparison limit has been removed.
- Completed AI comparison results stay visible until the user explicitly clears
  them; the confusing result-hiding return action has been removed.
- Frontend API errors are sanitized centrally so raw `Not Found`, `Failed to
  fetch`, provider HTML, traceback text, and key-shaped secrets are not shown to
  users.
- Sample-project and date-view copy is more consistently localized.

## Verified

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Release artifacts

- `LivingToTell_0.1.32_x64-setup.exe`
  - SHA256: `0F54953DC103CDD92FD3F3ABA7E93FA2EE44F757ED038360737242714BE98264`
- `LivingToTell_0.1.32_x64_zh-CN.msi`
  - SHA256: `2C30E4FA49FE5D17DDDD586317D654E66119BBA80DBA769C3E70FE32554DA79B`
