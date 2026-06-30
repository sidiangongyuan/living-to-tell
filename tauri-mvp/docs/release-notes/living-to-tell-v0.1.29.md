# Living to Tell Preview 0.1.29

This update tightens the Motif Star Map AI enrichment workflow around the exact cases that still felt brittle: reopening drafts, opening AI without a prefilled concept, resizing the dialog, and requesting broader web-context material.

## Fixed

- New-concept enrichment drafts remain applyable after closing and reopening the AI dialog. Changing the concept/name field no longer disables `创建意象`.
- The left-panel `AI` button now opens even when the new motif field is empty. The concept can be entered inside the AI enrichment dialog before generating.
- The stale-draft warning now only blocks applying a draft generated for a different selected motif; it no longer blocks normal new-concept rename/edit flows.

## Changed

- The AI enrichment dialog is now manually resizable and has a wider adaptive layout. Reference candidates stay single-column until the window is genuinely wide enough, reducing cramped candidate cards.
- Motif enrichment requests now wait up to 5 minutes before timing out.
- `请求联网补充` now asks the model for richer material: original sources, criticism, research articles, later quotations, rewrites, intertextual uses, and literary/film examples can all be considered when relevant.
- Enrichment parsing now preserves more source hints and reference candidates from richer model responses.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py::test_tauri_motifs_enrich_draft_uses_context_and_does_not_mutate -q`
- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm test -- --run src/api/base.test.ts`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Assets

- `LivingToTell_0.1.29_x64-setup.exe`
  - SHA256: `A4C32E8457BF1D9EC7A84E99BF5BB2F9325D5A80237378A5192C73A72F369698`
- `LivingToTell_0.1.29_x64_zh-CN.msi`
  - SHA256: `C64BC6D4798BB18587AAFB871EC579DDBD53253A2E5997F9B0F2C5A3FD7E0B0F`
